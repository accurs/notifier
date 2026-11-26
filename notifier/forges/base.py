"""
The small set of things every forge client can do.
"""

from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from abc import ABC, abstractmethod

from notifier.config import Commit, ForgeSettings, Push
from notifier.http import request_json


class Forge(ABC):
    name = "forge"
    signature_headers: tuple[str, ...] = ()

    def __init__(self, settings: ForgeSettings) -> None:
        """
        Keep the forge settings this client talks to.
        """
        self.settings = settings

    @property
    def repo(self) -> str:
        """
        Owner and name of the watched repository.
        """
        return self.settings.repo

    def watches(self, branch: str) -> bool:
        """
        True when this branch should be announced. ``*`` means every branch.
        """
        return self.settings.branch in ("*", branch)

    def branches_to_poll(self) -> list[str]:
        """
        Return the one watched branch, or every branch when that is ``*``.
        """
        if self.settings.branch != "*":
            return [self.settings.branch]
        found = self.list_branches()
        if not found:
            raise RuntimeError(f"{self.name} returned no branches for {self.repo}")
        return found

    @abstractmethod
    def list_branches(self) -> list[str]:
        """
        Return every branch name on the repo.
        """
        ...

    @abstractmethod
    def list_commits(self, branch: str, limit: int, page: int) -> list[Commit]:
        """
        Return one page of commits on a branch, newest first.
        """
        ...

    @abstractmethod
    def branch_url(self, branch: str) -> str:
        """
        Return the browser URL for a branch.
        """
        ...

    @abstractmethod
    def commit_url(self, sha: str) -> str:
        """
        Return the browser URL for a commit.
        """
        ...

    @abstractmethod
    def parse_push(self, payload: dict) -> Push | None:
        """
        Turn a webhook body into a push, or None when it is not a branch push.
        """
        ...

    def is_push_event(self, headers: dict, payload: dict) -> bool:
        """
        True when this delivery is a push. Subclasses check their own header.
        """
        return True

    def signature_ok(self, body: bytes, headers: dict, secret: str) -> bool:
        """
        True when the body was signed with the webhook secret.
        """
        provided = header(headers, self.signature_headers)
        return hmac_sha256_ok(body, secret, provided)

    def auth_headers(self) -> dict[str, str]:
        """
        Headers that prove who we are. Empty when the repo is public.
        """
        return {}

    def get(self, path: str, query: dict | None = None) -> list | dict:
        """
        GET one API path and return the JSON body, or raise on an error status.
        """
        url = join_url(self.settings.api, path, query)
        status, body = request_json(url, headers=self.auth_headers())
        if status >= 400:
            raise RuntimeError(f"{self.name} {path} failed ({status}): {body}")
        return body

    def web(self, *parts: str) -> str:
        """
        Join path parts onto the forge's browser URL.
        """
        root = self.settings.web.rstrip("/")
        tail = "/".join(quote(part) for part in parts if part)
        return f"{root}/{tail}"


def join_url(root: str, path: str, query: dict | None = None) -> str:
    """
    Join an API root, a path, and an optional query string.
    """
    if not path.startswith("/"):
        path = "/" + path
    url = root.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return url


def quote(part: str) -> str:
    """
    Encode one URL path part, leaving slashes in branch names alone.
    """
    return urllib.parse.quote(part, safe="/")


def header(headers: dict, names: tuple[str, ...]) -> str:
    """
    Return the first of these headers that the request actually sent.
    """
    for name in names:
        if headers.get(name):
            return headers[name]
    return ""


def hmac_sha256_ok(body: bytes, secret: str, signature: str) -> bool:
    """
    True when ``signature`` is the HMAC-SHA256 of ``body`` under ``secret``.
    """
    if not secret or not signature:
        return False
    provided = signature.strip()
    if provided.lower().startswith("sha256="):
        provided = provided.split("=", 1)[1].strip()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return same_text(expected, provided)


def same_text(left: str, right: str) -> bool:
    """
    Compare two strings without leaking which characters differed.
    """
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def branch_names(body: object) -> list[str]:
    """
    Pull branch names out of a forge's branch list.
    """
    if not isinstance(body, list):
        raise RuntimeError(f"expected a list of branches, got {type(body).__name__}")
    return [
        str(item["name"])
        for item in body
        if isinstance(item, dict) and item.get("name")
    ]
