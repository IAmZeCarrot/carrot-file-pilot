from __future__ import annotations

from pathlib import Path

import pytest

from carrot_file_pilot.core import PilotError
from carrot_file_pilot.desktop import DesktopSession
from carrot_file_pilot.models import Status


def test_desktop_session_requires_preview_before_apply(tmp_path: Path) -> None:
    session = DesktopSession()
    with pytest.raises(PilotError, match="preview required"):
        session.apply_preview(tmp_path / "journals")


def test_desktop_preview_apply_and_undo_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_text("photo", encoding="utf-8")
    session = DesktopSession()

    preview = session.preview(tmp_path)
    assert preview[0].status is Status.PLANNED
    assert source.exists()

    results, journal = session.apply_preview(tmp_path / "journals")
    assert results[0].status is Status.MOVED
    assert journal.is_file()
    assert not session.preview_ready
    assert not source.exists()

    restored = session.undo_journal()
    assert restored[0].status is Status.UNDONE
    assert source.read_text(encoding="utf-8") == "photo"
    assert session.last_journal is None


def test_changing_inputs_can_invalidate_preview(tmp_path: Path) -> None:
    (tmp_path / "report.pdf").write_text("report", encoding="utf-8")
    session = DesktopSession()
    session.preview(tmp_path)

    session.clear_preview()

    assert not session.preview_ready
    assert session.operations == []
