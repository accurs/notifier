"""
Settings, and the Commit and Push shapes the rest of the program uses.

Nothing here invents a value. A missing line stops startup and names itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from notifier.constants import FORGE_KINDS, OPTIONAL, REQUIRED


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str
    url: str
    author: str

    @property
    def short_sha(self) -> str:
        """
        First seven characters of the sha, or ``?`` when it is missing.
        """
        return self.sha[:7] if self.sha else "?"


@dataclass(frozen=True)
class Push:
    repo: str
    branch: str
    commits: tuple[Commit, ...]
    compare_url: str = ""
    pusher: str = ""
    deleted: bool = False

    def with_commits(self, commits: tuple[Commit, ...]) -> Push:
        """
        Return a copy of this push that lists only these commits.
        """
        return replace(self, commits=commits)


@dataclass(frozen=True)
class TelegramSettings:
    token: str
    chat_id: str
    thread_id: str

    @classmethod
    def from_env(cls) -> TelegramSettings:
        """
        Build Telegram settings from the environment.
        """
        return cls(
            token=text("TELEGRAM_BOT_TOKEN"),
            chat_id=text("TELEGRAM_CHAT_ID"),
            thread_id=text("TELEGRAM_THREAD_ID", allow_blank=True),
        )


@dataclass(frozen=True)
class ForgeSettings:
    kind: str
    web: str
    api: str
    repo: str
    branch: str
    token: str

    @classmethod
    def from_env(cls) -> ForgeSettings:
        """
        Build forge settings from the environment.
        """
        kind = text("FORGE").lower()
        if kind not in FORGE_KINDS:
            choices = ", ".join(FORGE_KINDS)
            raise SystemExit(f"FORGE must be one of: {choices}. Got {kind!r}.")
        return cls(
            kind=kind,
            web=text("FORGE_WEB").rstrip("/"),
            api=text("FORGE_API").rstrip("/"),
            repo=text("FORGE_REPO").strip("/"),
            branch=text("FORGE_BRANCH"),
            token=text("FORGE_TOKEN", allow_blank=True),
        )


@dataclass(frozen=True)
class WebhookSettings:
    secret: str
    host: str
    port: int
    path: str

    @classmethod
    def from_env(cls) -> WebhookSettings:
        """
        Build webhook settings from the environment.
        """
        path = text("WEBHOOK_PATH")
        if not path.startswith("/"):
            raise SystemExit("WEBHOOK_PATH has to start with /, for example /webhook.")
        return cls(
            secret=text("WEBHOOK_SECRET"),
            host=text("WEBHOOK_HOST"),
            port=number("WEBHOOK_PORT"),
            path=path,
        )


@dataclass(frozen=True)
class Settings:
    telegram: TelegramSettings
    forge: ForgeSettings
    webhook: WebhookSettings
    poll_interval: int
    state_path: Path

    @property
    def polling(self) -> bool:
        """
        True when the backup poll is turned on.
        """
        return self.poll_interval > 0

    @classmethod
    def from_env(cls) -> Settings:
        """
        Build the full settings object from the environment.
        """
        return cls(
            telegram=TelegramSettings.from_env(),
            forge=ForgeSettings.from_env(),
            webhook=WebhookSettings.from_env(),
            poll_interval=number("POLL_INTERVAL"),
            state_path=Path(text("STATE_PATH")),
        )


def load_env_file(path: Path) -> None:
    """
    Fill in keys the process does not already have.

    A real environment variable wins, so Docker can inject the same file
    without this reader getting in the way.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _unquote(value.strip()))


def load_settings() -> Settings:
    """
    Load settings, or stop and list every missing env line.
    """
    problems = missing_keys()
    if problems:
        lines = "\n".join(f"  - {item}" for item in problems)
        raise SystemExit(
            "The env file is incomplete:\n"
            f"{lines}\n"
            "Copy .env.example to .env and fill in every line."
        )
    return Settings.from_env()


def missing_keys() -> list[str]:
    """
    Return a human sentence for each required key that is absent or blank.
    """
    problems = []
    for name in REQUIRED:
        if name not in os.environ:
            problems.append(f"{name} is missing")
        elif not _unquote(os.environ[name].strip()):
            problems.append(f"{name} is empty")
    for name in OPTIONAL:
        if name not in os.environ:
            problems.append(f"{name} is missing (leave it blank if you do not need it)")
    return problems


def text(name: str, *, allow_blank: bool = False) -> str:
    """
    Read one env value, stripped of surrounding quotes.
    """
    value = _unquote(os.environ[name].strip())
    if not value and not allow_blank:
        raise SystemExit(f"{name} is empty.")
    return value


def number(name: str) -> int:
    """
    Read one env value as a whole number.
    """
    raw = text(name)
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"{name} has to be a whole number, got {raw!r}.") from None


def _unquote(value: str) -> str:
    """
    Remove one layer of matching quotes added by an env file.
    """
    return value.strip("'").strip('"')
