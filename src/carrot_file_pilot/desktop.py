"""Testable state and actions for the desktop interface."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import load_config
from .core import PilotError, apply, plan, undo
from .models import Operation, Status


def default_data_dir() -> Path:
    """Return a per-user location for journals without creating it."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "CarrotFilePilot"
    return Path.home() / ".local" / "share" / "carrot-file-pilot"


@dataclass
class DesktopSession:
    """Own a preview so applying is always an explicit second step."""

    operations: list[Operation] = field(default_factory=list)
    preview_ready: bool = False
    last_journal: Path | None = None

    def preview(self, target: Path, config_path: Path | None = None) -> list[Operation]:
        config = load_config(config_path)
        self.operations = plan(target, config)
        self.preview_ready = True
        return list(self.operations)

    def clear_preview(self) -> None:
        self.operations = []
        self.preview_ready = False

    def apply_preview(self, journal_dir: Path | None = None) -> tuple[list[Operation], Path]:
        if not self.preview_ready:
            raise PilotError("preview required before files can be organized")
        directory = journal_dir or default_data_dir() / "journals"
        results, journal = apply(self.operations, directory)
        self.operations = results
        self.preview_ready = False
        self.last_journal = journal
        return list(results), journal

    def undo_journal(self, journal: Path | None = None) -> list[Operation]:
        selected = journal or self.last_journal
        if selected is None:
            raise PilotError("choose an undo journal first")
        results = undo(selected)
        if not any(item.status is Status.FAILED for item in results):
            self.last_journal = None
        return results
