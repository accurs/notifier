"""
Remember which commits we already posted, so a restart does not replay them.
"""

from __future__ import annotations

import json
import logging
import threading

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from notifier.constants import SEEN_LIMIT

log = logging.getLogger("notifier")


class SeenCommits:
    def __init__(self, path: Path) -> None:
        """
        Load whatever has already been saved at this path.
        """
        self.path = path
        self._lock = threading.Lock()
        self._seen: list[str] = []
        self.seeded = False
        self._load()

    def mark_new(self, shas: list[str]) -> list[str]:
        """
        Remember these commits. Returns only the ones we had not seen.
        """
        with self._lock:
            fresh = [sha for sha in shas if sha and sha not in self._seen]
            if not fresh:
                return []
            with self._edit():
                self._seen = (self._seen + fresh)[-SEEN_LIMIT:]
            return fresh

    def forget(self, shas: list[str]) -> None:
        """
        Drop commits so a failed send can be tried again.
        """
        with self._lock:
            drop = set(shas)
            with self._edit():
                self._seen = [sha for sha in self._seen if sha not in drop]

    def seed(self, shas: list[str]) -> None:
        """
        Record history that already exists, without posting it.
        """
        with self._lock:
            if self.seeded:
                return
            with self._edit():
                merged = list(self._seen)
                for sha in shas:
                    if sha and sha not in merged:
                        merged.append(sha)
                self._seen = merged[-SEEN_LIMIT:]
                self.seeded = True
            log.info(
                "seeded %d existing commit(s); only newer ones will be posted",
                len(self._seen),
            )

    def known(self) -> set[str]:
        """
        Return the commit ids we have already recorded.
        """
        with self._lock:
            return set(self._seen)

    @contextmanager
    def _edit(self) -> Iterator[None]:
        """
        Save after a change, and put the old list back if saving fails.
        """
        previous_seen = self._seen
        previous_seeded = self.seeded
        try:
            yield
            self._save()
        except Exception:
            self._seen = previous_seen
            self.seeded = previous_seeded
            raise

    def _load(self) -> None:
        """
        Read the state file, ignoring it when it is missing or broken.
        """
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("ignoring unreadable state file: %s", exc)
            return
        if not isinstance(raw, dict):
            return
        seen = raw.get("seen")
        if isinstance(seen, list):
            self._seen = [item for item in seen if isinstance(item, str)]
        self.seeded = bool(raw.get("seeded"))

    def _save(self) -> None:
        """
        Write the state file by replacing it, so a crash cannot leave it half-written.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"seeded": self.seeded, "seen": self._seen[-SEEN_LIMIT:]}),
            encoding="utf-8",
        )
        temporary.replace(self.path)
