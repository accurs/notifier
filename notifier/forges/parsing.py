"""
Turn forge JSON into Commit and Push.
"""

from __future__ import annotations

from collections.abc import Callable

from notifier.config import Commit, Push
from notifier.constants import DELETED_SHA


def as_dict(value: object) -> dict:
    """
    Return ``value`` when it is a dict, otherwise an empty one.
    """
    return value if isinstance(value, dict) else {}


def person_name(value: object) -> str:
    """
    Return the first name-like field on a person object.
    """
    data = as_dict(value)
    for key in ("name", "username", "login", "full_name"):
        if data.get(key):
            return str(data[key])
    return ""


def commit_from_webhook(item: dict) -> Commit | None:
    """
    Read one commit from a push webhook. Returns None when it has no sha.
    """
    sha = str(item.get("id") or item.get("sha") or "")
    if not sha:
        return None
    return Commit(
        sha=sha,
        message=str(item.get("message") or ""),
        url=str(item.get("url") or item.get("html_url") or ""),
        author=person_name(item.get("author")),
    )


def commit_from_github_api(item: dict) -> Commit | None:
    """
    GitHub, Forgejo, and Gitea all return this commit shape.
    """
    sha = str(item.get("sha") or "")
    if not sha:
        return None
    commit = as_dict(item.get("commit"))
    author = person_name(commit.get("author")) or person_name(item.get("author"))
    return Commit(
        sha=sha,
        message=str(commit.get("message") or ""),
        url=str(item.get("html_url") or ""),
        author=author,
    )


def commit_from_gitlab_api(item: dict) -> Commit | None:
    """
    Read one commit from GitLab's commits API. Returns None when it has no id.
    """
    sha = str(item.get("id") or "")
    if not sha:
        return None
    return Commit(
        sha=sha,
        message=str(item.get("message") or item.get("title") or ""),
        url=str(item.get("web_url") or ""),
        author=str(item.get("author_name") or ""),
    )


def commits_from(body: object, parse: Callable[[dict], Commit | None]) -> list[Commit]:
    """
    Parse a list of API commits, skipping items that are not commits.
    """
    if not isinstance(body, list):
        raise RuntimeError(f"unexpected commits payload: {body!r}"[:200])
    commits = []
    for item in body:
        if not isinstance(item, dict):
            continue
        commit = parse(item)
        if commit:
            commits.append(commit)
    return commits


def webhook_commits(raw: object) -> tuple[Commit, ...]:
    """
    Read the commits array from a webhook, or return nothing when it is missing.
    """
    if not isinstance(raw, list):
        return ()
    commits = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        commit = commit_from_webhook(item)
        if commit:
            commits.append(commit)
    return tuple(commits)


def push_from_github_style(payload: dict, repo_fallback: str) -> Push | None:
    """
    Shared by GitHub and the Forgejo family. Tags and other refs are ignored.
    """
    ref = str(payload.get("ref") or "")
    if not ref.startswith("refs/heads/"):
        return None
    repository = as_dict(payload.get("repository"))
    return Push(
        repo=str(repository.get("full_name") or repo_fallback),
        branch=ref.removeprefix("refs/heads/"),
        commits=webhook_commits(payload.get("commits")),
        compare_url=str(payload.get("compare_url") or payload.get("compare") or ""),
        pusher=_pusher(payload),
        deleted=str(payload.get("after") or "") == DELETED_SHA,
    )


def _pusher(payload: dict) -> str:
    """
    Return the person who pushed, from either the pusher or the sender.
    """
    for key in ("pusher", "sender"):
        name = person_name(payload.get(key))
        if name:
            return name
    return ""
