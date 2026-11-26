"""
Ask the forge on a timer, in case a webhook cannot reach us.
"""

from __future__ import annotations

import logging
import threading

from notifier.channel import Channel
from notifier.config import Commit, Push, Settings
from notifier.constants import MAX_PAGES, PAGE_SIZE, SEED_COUNT
from notifier.forges.base import Forge

log = logging.getLogger("notifier")


def poll_once(forge: Forge, channel: Channel, *, seed_only: bool = False) -> None:
    """
    Check the forge once. The first successful check only records history.
    """
    branches = forge.branches_to_poll()
    if seed_only or not channel.seen.seeded:
        channel.seen.seed(_history(forge, branches))
        return

    known = channel.seen.known()
    for branch in branches:
        commits = _unseen(forge, branch, known)
        if commits:
            channel.announce(Push(repo=forge.repo, branch=branch, commits=tuple(commits)))


def poll_loop(settings: Settings, forge: Forge, channel: Channel, stop: threading.Event) -> None:
    """
    Keep polling until ``stop`` is set. A failed poll is logged and retried.
    """
    while not stop.is_set():
        try:
            poll_once(forge, channel)
        except Exception:
            log.exception("poll failed")
        stop.wait(settings.poll_interval)


def _history(forge: Forge, branches: list[str]) -> list[str]:
    """
    Collect recent commit ids so the first run does not replay them.
    """
    shas = []
    for branch in branches:
        for commit in forge.list_commits(branch, SEED_COUNT, page=1):
            shas.append(commit.sha)
    return shas


def _unseen(forge: Forge, branch: str, known: set[str]) -> list[Commit]:
    """
    Walk newest-first, stop at the first known commit, return oldest-first.
    """
    fresh: list[Commit] = []
    for page in range(1, MAX_PAGES + 1):
        items = [commit for commit in forge.list_commits(branch, PAGE_SIZE, page) if commit.sha]
        if not items:
            break
        hit_known = False
        for commit in items:
            if commit.sha in known:
                hit_known = True
                break
            fresh.append(commit)
        if hit_known or len(items) < PAGE_SIZE:
            break
    fresh.reverse()
    return fresh
