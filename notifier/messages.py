"""
Turn a push into the channel message.
"""

from __future__ import annotations

import html

from notifier.config import Commit, Push
from notifier.constants import MESSAGE_LINE, TELEGRAM_MESSAGE_LIMIT
from notifier.forges.base import Forge


def render(forge: Forge, push: Push) -> list[str]:
    """
    Turn a push into one or more Telegram HTML messages.
    """
    header = _header(forge, push)
    commits = [_commit_line(forge, commit) for commit in push.commits]
    text = "\n".join([header, "", *commits]).strip()
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]
    return _pages(header, commits)


def _header(forge: Forge, push: Push) -> str:
    """
    Build the repo, branch, and count lines that open a message.
    """
    count = len(push.commits)
    noun = "commit" if count == 1 else "commits"
    who = f" · {escape(push.pusher)}" if push.pusher else ""
    branch = code_link(forge.branch_url(push.branch), push.branch)
    lines = [
        f"<b>{escape(push.repo)}</b>",
        f"{branch} · {count} new {noun}{who}",
    ]
    if push.compare_url:
        lines.append(link(push.compare_url, "compare"))
    return "\n".join(lines)


def _commit_line(forge: Forge, commit: Commit) -> str:
    """
    Build one bullet: short hash, subject, and author.
    """
    url = commit.url or forge.commit_url(commit.sha)
    summary = escape(first_line(commit.message))
    author = f" — {escape(commit.author)}" if commit.author else ""
    return f"• {link(url, commit.short_sha)} {summary}{author}"


def _pages(header: str, commits: list[str]) -> list[str]:
    """
    Split a long push into messages that fit Telegram's length limit.
    """
    pages: list[str] = []
    current = header
    for line in commits:
        extra = "\n" + line
        if len(current) + len(extra) > TELEGRAM_MESSAGE_LIMIT:
            pages.append(current)
            current = header + extra
        else:
            current += extra
    if current:
        pages.append(current)
    return pages


def first_line(message: str, limit: int = MESSAGE_LINE) -> str:
    """
    Return the commit subject, shortened when it is too long to read.
    """
    lines = (message or "").strip().splitlines()
    line = lines[0].strip() if lines else ""
    if not line:
        return "(no message)"
    if len(line) <= limit:
        return line
    return line[: limit - 1] + "…"


def escape(value: object) -> str:
    """
    Escape text so it is safe inside Telegram HTML.
    """
    return html.escape(str(value), quote=False)


def link(url: str, label: str) -> str:
    """
    Return an HTML link with the label escaped.
    """
    href = html.escape(url, quote=True)
    return f'<a href="{href}">{escape(label)}</a>'


def code_link(url: str, label: str) -> str:
    """
    Return an HTML link whose label is shown as code.
    """
    href = html.escape(url, quote=True)
    return f'<a href="{href}"><code>{escape(label)}</code></a>'
