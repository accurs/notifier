"""
Pick the forge client named by FORGE.
"""

from __future__ import annotations

from notifier.config import ForgeSettings
from notifier.constants import FORGE_KINDS
from notifier.forges.base import Forge
from notifier.forges.forgejo import Forgejo
from notifier.forges.github import GitHub
from notifier.forges.gitlab import GitLab

_CLIENTS: dict[str, type[Forge]] = {
    "forgejo": Forgejo,
    "gitea": Forgejo,
    "gogs": Forgejo,
    "github": GitHub,
    "gitlab": GitLab,
}


def open_forge(settings: ForgeSettings) -> Forge:
    """
    Return the client for the forge named in settings.
    """
    client = _CLIENTS.get(settings.kind)
    if client is None:
        choices = ", ".join(FORGE_KINDS)
        raise SystemExit(f"FORGE must be one of: {choices}. Got {settings.kind!r}.")
    return client(settings)
