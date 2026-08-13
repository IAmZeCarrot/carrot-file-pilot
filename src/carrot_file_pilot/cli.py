"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .core import PilotError, apply, plan, undo
from .models import Operation, Status


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carrot-file-pilot", description="Preview-first file organizer"
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    subparsers = parser.add_subparsers(dest="command", required=True)
    organize = subparsers.add_parser("organize", help="preview or organize a directory")
    organize.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    organize.add_argument("--config", type=Path)
    organize.add_argument("--apply", action="store_true", help="perform the previewed moves")
    organize.add_argument("--journal-dir", type=Path, default=Path(".carrot-file-pilot"))
    organize.add_argument("--log-file", type=Path)
    restore = subparsers.add_parser("undo", help="restore files from a transaction journal")
    restore.add_argument("journal", type=Path)
    restore.add_argument("--log-file", type=Path)
    return parser


def _logging(path: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def _print(operations: list[Operation]) -> None:
    if not operations:
        print("No matching files found.")
        return
    for item in operations:
        marker = {
            Status.PLANNED: "PLAN",
            Status.MOVED: "MOVED",
            Status.SKIPPED: "SKIP",
            Status.UNDONE: "UNDONE",
            Status.FAILED: "ERROR",
        }[item.status]
        detail = f" ({item.detail})" if item.detail else ""
        print(f"[{marker}] {item.source} -> {item.destination} [{item.rule}]{detail}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _logging(args.log_file)
        if args.command == "undo":
            operations = undo(args.journal)
            _print(operations)
            return 1 if any(item.status is Status.FAILED for item in operations) else 0
        config = load_config(args.config)
        operations = plan(args.path, config)
        if not args.apply:
            _print(operations)
            print("\nDry run only. Add --apply to move files.")
            return 0
        results, journal = apply(operations, args.journal_dir)
        _print(results)
        print(f"\nUndo journal: {journal}")
        return 1 if any(item.status is Status.FAILED for item in results) else 0
    except (ConfigError, PilotError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
