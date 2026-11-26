"""
Listen for forge push deliveries and hand them to the channel.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.parse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from notifier.channel import Channel
from notifier.config import Settings
from notifier.constants import DELIVERY_HEADERS, MAX_WEBHOOK_BODY
from notifier.forges.base import Forge

log = logging.getLogger("notifier")


def serve(settings: Settings, forge: Forge, channel: Channel, stop: threading.Event) -> None:
    """
    Listen for webhook deliveries until the process is stopped.
    """
    Listener(settings, forge, channel).serve(stop)


class Listener:
    def __init__(self, settings: Settings, forge: Forge, channel: Channel) -> None:
        """
        Keep what a delivery needs: settings, the forge, and the channel.
        """
        self.settings = settings
        self.forge = forge
        self.channel = channel

    def serve(self, stop: threading.Event) -> None:
        """
        Bind the webhook port and serve until interrupted.
        """
        webhook = self.settings.webhook
        server = ThreadingHTTPServer((webhook.host, webhook.port), self._handler())
        log.info("webhook listening on http://%s:%s%s", webhook.host, webhook.port, webhook.path)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("shutting down")
        finally:
            stop.set()
            server.server_close()

    def on_get(self, request: BaseHTTPRequestHandler) -> None:
        """
        Answer health checks. Anything else is not found.
        """
        path = urllib.parse.urlsplit(request.path).path
        if path in ("/", "/health"):
            reply(request, 200, b"ok\n")
            return
        reply(request, 404, b"not found\n")

    def on_post(self, request: BaseHTTPRequestHandler) -> None:
        """
        Check the signature, then hand a push delivery to the channel.
        """
        path = urllib.parse.urlsplit(request.path).path
        if path != self.settings.webhook.path:
            reply(request, 404, b"not found\n")
            return

        length = int(request.headers.get("Content-Length") or "0")
        if length <= 0 or length > MAX_WEBHOOK_BODY:
            reply(request, 400, b"bad content length\n")
            return

        body = request.rfile.read(length)
        headers = {key.lower(): value for key, value in request.headers.items()}
        if not self.forge.signature_ok(body, headers, self.settings.webhook.secret):
            log.warning("rejected a delivery with a bad or missing signature")
            reply(request, 401, b"bad signature\n")
            return

        payload = _object(body)
        if payload is None:
            reply(request, 400, b"bad json\n")
            return

        if not self.forge.is_push_event(headers, payload):
            event = headers.get("x-github-event") or headers.get("x-gitlab-event") or "other"
            log.info("ignoring %s event", event)
            reply(request, 200, b"ignored\n")
            return

        try:
            self.channel.handle_delivery(payload)
        except Exception:
            log.exception("failed to handle push %s", _delivery_id(headers))
            reply(request, 500, b"delivery failed\n")
            return
        reply(request, 204)

    def _handler(self):
        """
        Build the request class the HTTP server constructs per connection.
        """
        listener = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args) -> None:
                """
                Send the server's access line through our logger.
                """
                log.info("%s - " + fmt, self.address_string(), *args)

            def do_GET(self) -> None:
                """
                Handle a GET by asking the listener.
                """
                listener.on_get(self)

            def do_POST(self) -> None:
                """
                Handle a POST by asking the listener.
                """
                listener.on_post(self)

        return Handler


def reply(request: BaseHTTPRequestHandler, status: int, body: bytes = b"") -> None:
    """
    Write a plain-text response and close the headers.
    """
    request.send_response(status)
    request.send_header("Content-Type", "text/plain")
    request.send_header("Content-Length", str(len(body)))
    request.end_headers()
    if body:
        request.wfile.write(body)


def _object(body: bytes) -> dict | None:
    """
    Parse a JSON object, or return None when the body is not one.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _delivery_id(headers: dict) -> str:
    """
    Return the forge's delivery id, when the request has one.
    """
    for name in DELIVERY_HEADERS:
        if headers.get(name):
            return headers[name]
    return ""
