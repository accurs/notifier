"""
GitHub, including GitHub Enterprise if FORGE_WEB and FORGE_API point at it.
"""

from __future__ import annotations

from notifier.config import Commit, Push
from notifier.forges.base import Forge, branch_names
from notifier.forges.parsing import commit_from_github_api, commits_from, push_from_github_style


class GitHub(Forge):
    name = "github"
    signature_headers = ("x-hub-signature-256",)

    def auth_headers(self) -> dict[str, str]:
        """
        Send the GitHub API version, and a bearer token when one is set.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.token:
            headers["Authorization"] = f"Bearer {self.settings.token}"
        return headers

    def list_branches(self) -> list[str]:
        """
        Return branch names from the GitHub branches API.
        """
        return branch_names(self.get(f"/repos/{self.repo}/branches", {"per_page": 50}))

    def list_commits(self, branch: str, limit: int, page: int) -> list[Commit]:
        """
        Return one page of commits on a branch.
        """
        body = self.get(
            f"/repos/{self.repo}/commits",
            {"sha": branch, "per_page": limit, "page": page},
        )
        return commits_from(body, commit_from_github_api)

    def branch_url(self, branch: str) -> str:
        """
        Return the GitHub tree URL for a branch.
        """
        return self.web(self.repo, "tree", branch)

    def commit_url(self, sha: str) -> str:
        """
        Return the GitHub URL for a commit.
        """
        return self.web(self.repo, "commit", sha)

    def parse_push(self, payload: dict) -> Push | None:
        """
        Read a GitHub push webhook. Tag pushes are ignored.
        """
        return push_from_github_style(payload, self.repo)

    def is_push_event(self, headers: dict, payload: dict) -> bool:
        """
        True for a push event. A ping, or any other event, is not.
        """
        event = headers.get("x-github-event", "")
        if event:
            return event == "push"
        return isinstance(payload.get("commits"), list)
