"""
Decide what is new, format it, and post it. Undo the mark if the send fails.
"""

from __future__ import annotations

import logging
import threading

from notifier.config import Push
from notifier.forges.base import Forge
from notifier.messages import render
from notifier.state import SeenCommits
from notifier.telegram import Telegram

log = logging.getLogger("notifier")


class Channel:
    def __init__(self, forge: Forge, telegram: Telegram, seen: SeenCommits) -> None:
        """
        Wire the forge, the channel, and the list of commits already posted.
        """
        self.forge = forge
        self.telegram = telegram
        self.seen = seen
        self._send_lock = threading.Lock()

    def announce(self, push: Push) -> int:
        """
        Post the commits we have not seen yet. Returns how many were posted.
        """
        reason = self._skip(push)
        if reason:
            log.info("%s", reason)
            return 0

        fresh_ids = self.seen.mark_new([commit.sha for commit in push.commits])
        if not fresh_ids:
            return 0

        wanted = set(fresh_ids)
        fresh = tuple(commit for commit in push.commits if commit.sha in wanted)
        try:
            self._send(render(self.forge, push.with_commits(fresh)))
        except Exception:
            self.seen.forget([commit.sha for commit in fresh])
            raise

        log.info("posted %d commit(s) on %s", len(fresh), push.branch)
        return len(fresh)

    def handle_delivery(self, payload: dict) -> int:
        """
        Turn a webhook body into a post, or ignore it when it is not a branch push.
        """
        push = self.forge.parse_push(payload)
        if push is None:
            log.info("ignoring a delivery that is not a branch push")
            return 0
        return self.announce(push)

    def _skip(self, push: Push) -> str:
        """
        Return why this push should not be posted, or an empty string when it should.
        """
        if push.deleted:
            return f"branch {push.branch} was deleted; nothing to post"
        if push.repo.lower() != self.forge.repo.lower():
            return f"ignoring push for {push.repo}; watching {self.forge.repo}"
        if not self.forge.watches(push.branch):
            return f"ignoring {push.branch}; watching {self.forge.settings.branch}"
        if not push.commits:
            return f"push to {push.branch} had no commits"
        return ""

    def _send(self, messages: list[str]) -> None:
        """
        Post each message, one at a time, so two deliveries cannot interleave.
        """
        with self._send_lock:
            for message in messages:
                self.telegram.send(message)
