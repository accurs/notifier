"""
Start the webhook, and the backup poll when POLL_INTERVAL is not 0.
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

from notifier.channel import Channel
from notifier.config import Push, Settings, load_env_file, load_settings
from notifier.forges import open_forge
from notifier.forges.base import Forge
from notifier.messages import render
from notifier.poll import poll_loop, poll_once
from notifier.state import SeenCommits
from notifier.telegram import Telegram
from notifier.webhook import serve

log = logging.getLogger("notifier")


def main() -> None:
    """
    Load settings, then preview, send once, or run until stopped.
    """
    load_env_file(Path(".env"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    args = _parser().parse_args()
    settings = load_settings()
    forge = open_forge(settings.forge)

    if args.preview:
        _preview(forge)
        return

    channel = _channel(settings, forge)
    if args.send_latest:
        _send_latest(forge, channel)
        return

    stop = threading.Event()
    if settings.polling:
        _start_poller(settings, forge, channel, stop)
    else:
        log.info("polling is off (POLL_INTERVAL=0)")
    serve(settings, forge, channel, stop)


def _channel(settings: Settings, forge: Forge) -> Channel:
    """
    Check Telegram, then build the object that posts commits.
    """
    telegram = Telegram(settings.telegram)
    telegram.check()
    return Channel(forge, telegram, SeenCommits(settings.state_path))


def _start_poller(
    settings: Settings,
    forge: Forge,
    channel: Channel,
    stop: threading.Event,
) -> None:
    """
    Record existing history, then poll in the background.
    """
    try:
        poll_once(forge, channel, seed_only=not channel.seen.seeded)
    except Exception:
        log.exception("initial seed failed; will retry on the next poll")
    threading.Thread(
        target=poll_loop,
        args=(settings, forge, channel, stop),
        name="poller",
        daemon=True,
    ).start()
    log.info("polling %s every %ss", forge.repo, settings.poll_interval)


def _preview(forge: Forge) -> None:
    """
    Print the message for the latest commit, without posting it.
    """
    branch = _one_branch(forge)
    commits = list(reversed(forge.list_commits(branch, limit=5, page=1)))
    if not commits:
        raise SystemExit(f"no commits on {forge.repo}@{branch}")
    message = render(
        forge,
        Push(repo=forge.repo, branch=branch, commits=tuple(commits[-1:])),
    )
    print("\n\n".join(message))


def _send_latest(forge: Forge, channel: Channel) -> None:
    """
    Post the current latest commit even if it was already seen.
    """
    branch = _one_branch(forge)
    latest = forge.list_commits(branch, limit=1, page=1)
    if not latest:
        raise SystemExit(f"no commits on {forge.repo}@{branch}")
    channel.seen.forget([latest[0].sha])
    channel.announce(Push(repo=forge.repo, branch=branch, commits=tuple(latest)))


def _one_branch(forge: Forge) -> str:
    """
    Return the configured branch, which preview and send-latest both need.
    """
    if forge.settings.branch == "*":
        raise SystemExit("FORGE_BRANCH is *; pick a branch for --preview and --send-latest.")
    return forge.settings.branch


def _parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser.
    """
    parser = argparse.ArgumentParser(description="Post git pushes to a Telegram channel.")
    parser.add_argument("--preview", action="store_true", help="print the latest commit and exit")
    parser.add_argument(
        "--send-latest",
        action="store_true",
        help="post the current latest commit once, even if it was already seen",
    )
    return parser


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
