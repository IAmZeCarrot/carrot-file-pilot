from __future__ import annotations

from pathlib import Path

from carrot_file_pilot.config import Config
from carrot_file_pilot.core import apply, plan, undo
from carrot_file_pilot.models import CollisionPolicy, Status


def test_plan_is_deterministic_and_renames_collisions(tmp_path: Path) -> None:
    (tmp_path / "photo.jpg").write_text("new", encoding="utf-8")
    destination = tmp_path / "Images"
    destination.mkdir()
    (destination / "photo.jpg").write_text("old", encoding="utf-8")
    operations = plan(tmp_path, Config())
    assert [(item.source.name, item.destination.name) for item in operations] == [
        ("photo.jpg", "photo (1).jpg")
    ]


def test_skip_collision_policy(tmp_path: Path) -> None:
    (tmp_path / "report.pdf").write_text("new", encoding="utf-8")
    destination = tmp_path / "Documents"
    destination.mkdir()
    (destination / "report.pdf").write_text("old", encoding="utf-8")
    operations = plan(tmp_path, Config(collision=CollisionPolicy.SKIP))
    assert operations[0].status is Status.SKIPPED


def test_apply_and_undo_round_trip_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "report.pdf"
    source.write_text("important", encoding="utf-8")
    results, journal = apply(plan(tmp_path, Config()), tmp_path / ".journals")
    assert results[0].status is Status.MOVED
    moved = tmp_path / "Documents" / "report.pdf"
    assert moved.read_text(encoding="utf-8") == "important"
    undone = undo(journal)
    assert undone[0].status is Status.UNDONE
    assert source.read_text(encoding="utf-8") == "important"
    assert not moved.exists()


def test_undo_refuses_to_overwrite_original_path(tmp_path: Path) -> None:
    source = tmp_path / "report.pdf"
    source.write_text("first", encoding="utf-8")
    _, journal = apply(plan(tmp_path, Config()), tmp_path / ".journals")
    source.write_text("second", encoding="utf-8")
    result = undo(journal)
    assert result[0].status is Status.FAILED
    assert result[0].detail == "original path is occupied; refusing to overwrite"
    assert (tmp_path / "Documents" / "report.pdf").read_text(encoding="utf-8") == "first"
    assert source.read_text(encoding="utf-8") == "second"


def test_recursive_scan_ignores_destination_trees_and_hidden_files(tmp_path: Path) -> None:
    nested = tmp_path / "incoming"
    nested.mkdir()
    (nested / "photo.jpg").write_text("image", encoding="utf-8")
    (tmp_path / ".private.pdf").write_text("hidden", encoding="utf-8")
    existing = tmp_path / "Documents"
    existing.mkdir()
    (existing / "old.pdf").write_text("old", encoding="utf-8")
    operations = plan(tmp_path, Config(recursive=True))
    assert [item.source.name for item in operations] == ["photo.jpg"]
