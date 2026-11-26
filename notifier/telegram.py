"""
Post HTML messages to a Telegram channel.
"""

from __future__ import annotations

import logging
import time

from notifier.config import TelegramSettings
from notifier.constants import ATTEMPTS
from notifier.http import request_json

log = logging.getLogger("notifier")


class Telegram:
    def __init__(self, settings: TelegramSettings) -> None:
        """
        Keep the token and chat id used for every API call.
        """
        self.settings = settings

    def check(self) -> None:
        """
        Confirm the token works and the bot can see the chat.
        """
        me = self._call("getMe")
        chat = self._call("getChat", {"chat_id": self.settings.chat_id})
        title = chat.get("title") or chat.get("username") or self.settings.chat_id
        log.info("telegram @%s -> %s", me.get("username"), title)

    def send(self, text: str) -> None:
        """
        Post one HTML message, retrying when Telegram asks us to slow down.
        """
        payload = {
            "chat_id": self.settings.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if self.settings.thread_id:
            payload["message_thread_id"] = int(self.settings.thread_id)

        delay = 1.0
        error: Exception | None = None
        for attempt in range(ATTEMPTS):
            try:
                self._call("sendMessage", payload)
                return
            except RuntimeError as exc:
                error = exc
                if attempt == ATTEMPTS - 1:
                    break
                delay = _pause(exc, delay)
        raise RuntimeError(f"could not post to telegram: {error}")

    def _call(self, method: str, payload: dict | None = None) -> dict:
        """
        Call one Telegram method and return its result object.
        """
        url = f"https://api.telegram.org/bot{self.settings.token}/{method}"
        status, body = request_json(
            url,
            method="POST" if payload else "GET",
            payload=payload,
        )
        if not isinstance(body, dict) or not body.get("ok"):
            description = body.get("description") if isinstance(body, dict) else body
            raise RuntimeError(f"telegram {method} failed ({status}): {description}")
        result = body.get("result")
        return result if isinstance(result, dict) else {"result": result}


def _pause(error: RuntimeError, delay: float) -> float:
    """
    Sleep before the next try, and return the delay to use after that.
    """
    wait = _retry_after(error) or delay
    log.warning("telegram send failed (%s); retrying in %ss", error, wait)
    time.sleep(wait)
    return delay * 2


def _retry_after(error: RuntimeError) -> float | None:
    """
    Pull Telegram's ``retry after`` seconds out of an error, when it has one.
    """
    text = str(error).lower()
    if "retry after" not in text:
        return None
    digits = "".join(ch for ch in text.split("retry after", 1)[1] if ch.isdigit())
    return float(digits) if digits else None
