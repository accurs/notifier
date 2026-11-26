"""
Small JSON client shared by Telegram and the forges.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from notifier.constants import TIMEOUT_SECONDS, USER_AGENT


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict | list | str]:
    """
    Send one HTTP request and return the status plus a parsed JSON body.

    A non-JSON body is returned as text. HTTP error statuses are returned
    the same way, not raised.
    """
    body = None
    outgoing = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        outgoing.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode()
        outgoing["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=outgoing, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        status = exc.code

    if not raw:
        return status, {}
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw
