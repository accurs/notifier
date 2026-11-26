"""
Forgejo, Gitea, and Gogs. They share the v1 API; the branch page URL differs.
"""

from __future__ import annotations

from notifier.config import Commit, ForgeSettings, Push
from notifier.constants import EVENT_HEADERS
from notifier.forges.base import Forge, branch_names, header
from notifier.forges.parsing import (
    commit_from_github_api,
    commits_from,
    push_from_github_style,
)


class Forgejo(Forge):
    signature_headers = (
        "x-forgejo-signature",
        "x-gitea-signature",
        "x-gogs-signature",
    )

    def __init__(self, settings: ForgeSettings) -> None:
        """
        Use the configured kind as the name shown in errors.
        """
        super().__init__(settings)
        self.name = settings.kind

    def auth_headers(self) -> dict[str, str]:
        """
        Send a token header when the repo is private.
        """
        if not self.settings.token:
            return {}
        return {"Authorization": f"token {self.settings.token}"}

    def list_branches(self) -> list[str]:
        """
        Return branch names from the v1 branches API.
        """
        return branch_names(self.get(f"/repos/{self.repo}/branches", {"limit": 50}))

    def list_commits(self, branch: str, limit: int, page: int) -> list[Commit]:
        """
        Return one page of commits, without file stats.
        """
        body = self.get(
            f"/repos/{self.repo}/commits",
            {
                "sha": branch,
                "limit": limit,
                "page": page,
                "stat": "false",
                "files": "false",
            },
        )
        return commits_from(body, commit_from_github_api)

    def branch_url(self, branch: str) -> str:
        """
        Return the browser URL for a branch.

        Gogs has no ``/branch/`` segment. Forgejo and Gitea do.
        """
        if self.settings.kind == "gogs":
            return self.web(self.repo, "src", branch)
        return self.web(self.repo, "src", "branch", branch)

    def commit_url(self, sha: str) -> str:
        """
        Return the browser URL for a commit.
        """
        return self.web(self.repo, "commit", sha)

    def parse_push(self, payload: dict) -> Push | None:
        """
        Read a Forgejo, Gitea, or Gogs push webhook.
        """
        return push_from_github_style(payload, self.repo)

    def is_push_event(self, headers: dict, payload: dict) -> bool:
        """
        True when the delivery header, or the body, says this is a push.
        """
        event = header(headers, EVENT_HEADERS)
        if event:
            return event == "push"
        return "commits" in payload
