from __future__ import annotations

from pathlib import Path
from typing import Any

from carrot_file_pilot.cli import main


def test_cli_defaults_to_dry_run(tmp_path: Path, capsys: Any) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("keep me", encoding="utf-8")
    assert main(["organize", str(tmp_path)]) == 0
    assert source.exists()
    assert "Dry run only" in capsys.readouterr().out


def test_cli_apply_then_undo(tmp_path: Path, capsys: Any) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("keep me", encoding="utf-8")
    journals = tmp_path / "journals"
    assert main(["organize", str(tmp_path), "--apply", "--journal-dir", str(journals)]) == 0
    assert main(["undo", str(next(journals.glob("*.json")))]) == 0
    assert source.read_text(encoding="utf-8") == "keep me"
    capsys.readouterr()


def test_cli_returns_usage_error_for_missing_directory(tmp_path: Path, capsys: Any) -> None:
    assert main(["organize", str(tmp_path / "missing")]) == 2
    assert "does not exist" in capsys.readouterr().err
