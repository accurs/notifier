"""
GitLab. The webhook secret is a plain token header, not an HMAC signature.
"""

from __future__ import annotations

import urllib.parse

from notifier.config import Commit, Push
from notifier.constants import DELETED_SHA
from notifier.forges.base import Forge, branch_names, same_text
from notifier.forges.parsing import (
    as_dict,
    commit_from_gitlab_api,
    commits_from,
    person_name,
    webhook_commits,
)


class GitLab(Forge):
    name = "gitlab"

    def auth_headers(self) -> dict[str, str]:
        """
        Send a private-token header when the project is private.
        """
        if not self.settings.token:
            return {}
        return {"PRIVATE-TOKEN": self.settings.token}

    def list_branches(self) -> list[str]:
        """
        Return branch names from the repository branches API.
        """
        body = self.get(
            f"/projects/{self._project}/repository/branches",
            {"per_page": 50},
        )
        return branch_names(body)

    def list_commits(self, branch: str, limit: int, page: int) -> list[Commit]:
        """
        Return one page of commits on a branch.
        """
        body = self.get(
            f"/projects/{self._project}/repository/commits",
            {"ref_name": branch, "per_page": limit, "page": page},
        )
        return commits_from(body, commit_from_gitlab_api)

    def branch_url(self, branch: str) -> str:
        """
        Return the GitLab tree URL for a branch.
        """
        return self.web(self.repo, "-", "tree", branch)

    def commit_url(self, sha: str) -> str:
        """
        Return the GitLab URL for a commit.
        """
        return self.web(self.repo, "-", "commit", sha)

    def parse_push(self, payload: dict) -> Push | None:
        """
        Read a GitLab push hook. Tag pushes are ignored.
        """
        ref = str(payload.get("ref") or "")
        if payload.get("object_kind") not in (None, "push"):
            return None
        if not ref.startswith("refs/heads/"):
            return None
        project = as_dict(payload.get("project"))
        after = str(payload.get("after") or payload.get("checkout_sha") or "")
        return Push(
            repo=str(project.get("path_with_namespace") or self.repo),
            branch=ref.removeprefix("refs/heads/"),
            commits=webhook_commits(payload.get("commits")),
            compare_url=str(payload.get("compare_url") or ""),
            pusher=_pusher(payload),
            deleted=after == DELETED_SHA,
        )

    def is_push_event(self, headers: dict, payload: dict) -> bool:
        """
        True for a Push Hook, and false for the other GitLab hook types.
        """
        event = headers.get("x-gitlab-event", "")
        if event:
            return event == "Push Hook"
        return payload.get("object_kind") in (None, "push")

    def signature_ok(self, body: bytes, headers: dict, secret: str) -> bool:
        """
        True when ``X-Gitlab-Token`` matches the secret.

        GitLab sends the secret back as a header. It does not sign the body.
        """
        return same_text(secret, headers.get("x-gitlab-token", "").strip())

    @property
    def _project(self) -> str:
        """
        Return the project path encoded the way GitLab's API expects it.
        """
        return urllib.parse.quote(self.repo, safe="")


def _pusher(payload: dict) -> str:
    """
    Return the GitLab user who pushed.
    """
    named = str(payload.get("user_username") or payload.get("user_name") or "")
    return named or person_name(payload.get("user"))
