"""Domain models used by planning and execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CollisionPolicy(str, Enum):
    RENAME = "rename"
    SKIP = "skip"


class Status(str, Enum):
    PLANNED = "planned"
    MOVED = "moved"
    SKIPPED = "skipped"
    UNDONE = "undone"
    FAILED = "failed"


@dataclass(frozen=True)
class Rule:
    name: str
    destination: str
    extensions: tuple[str, ...] = ()
    names: tuple[str, ...] = ()

    def matches(self, path: Path) -> bool:
        lower_name = path.name.casefold()
        return lower_name in self.names or path.suffix.casefold() in self.extensions


@dataclass(frozen=True)
class Operation:
    source: Path
    destination: Path
    rule: str
    status: Status = Status.PLANNED
    detail: str | None = None
