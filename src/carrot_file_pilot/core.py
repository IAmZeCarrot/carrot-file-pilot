"""Pure planning plus guarded move and undo execution."""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .models import CollisionPolicy, Operation, Status

LOG = logging.getLogger("carrot_file_pilot")
JOURNAL_VERSION = 1


class PilotError(RuntimeError):
    """A safe, user-facing operation failure."""


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _candidates(root: Path, recursive: bool) -> Iterable[Path]:
    entries = root.rglob("*") if recursive else root.iterdir()
    return sorted((p for p in entries if p.is_file()), key=lambda p: str(p).casefold())


def _available(destination: Path, reserved: set[Path]) -> Path:
    if not destination.exists() and destination not in reserved:
        return destination
    index = 1
    while True:
        candidate = destination.with_name(f"{destination.stem} ({index}){destination.suffix}")
        if not candidate.exists() and candidate not in reserved:
            return candidate
        index += 1


def plan(root: Path, config: Config) -> list[Operation]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise PilotError(f"target does not exist: {root}")
    if not root.is_dir():
        raise PilotError(f"target is not a directory: {root}")
    reserved: set[Path] = set()
    operations: list[Operation] = []
    destination_roots = {(root / rule.destination).resolve() for rule in config.rules}
    for source in _candidates(root, config.recursive):
        relative = source.relative_to(root)
        if (not config.include_hidden and _is_hidden(relative)) or any(
            destination in source.parents for destination in destination_roots
        ):
            continue
        rule = next((candidate for candidate in config.rules if candidate.matches(source)), None)
        if rule is None:
            continue
        intended = (root / rule.destination / source.name).resolve()
        if root not in intended.parents:
            raise PilotError(f"unsafe destination for rule {rule.name}")
        destination = intended
        if destination.exists() or destination in reserved:
            if config.collision is CollisionPolicy.SKIP:
                operations.append(
                    Operation(source, destination, rule.name, Status.SKIPPED, "destination exists")
                )
                continue
            destination = _available(destination, reserved)
        reserved.add(destination)
        operations.append(Operation(source, destination, rule.name))
    return operations


def apply(operations: list[Operation], journal_dir: Path) -> tuple[list[Operation], Path]:
    transaction_id = uuid.uuid4().hex
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = journal_dir / f"{transaction_id}.json"
    results: list[Operation] = []
    for operation in operations:
        if operation.status is Status.SKIPPED:
            results.append(operation)
            continue
        try:
            if not operation.source.is_file():
                raise PilotError("source disappeared or is not a file")
            if operation.destination.exists():
                raise PilotError("destination appeared after preview")
            operation.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(operation.source), str(operation.destination))
            result = replace(operation, status=Status.MOVED)
            LOG.info("moved %s -> %s", operation.source, operation.destination)
        except (OSError, PilotError) as exc:
            result = replace(operation, status=Status.FAILED, detail=str(exc))
            LOG.error("failed %s: %s", operation.source, exc)
        results.append(result)
        _write_journal(journal, transaction_id, results)
    _write_journal(journal, transaction_id, results)
    return results, journal


def _write_journal(path: Path, transaction_id: str, operations: list[Operation]) -> None:
    payload = {
        "version": JOURNAL_VERSION,
        "transaction_id": transaction_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operations": [
            {
                "source": str(item.source),
                "destination": str(item.destination),
                "rule": item.rule,
                "status": item.status.value,
                "detail": item.detail,
            }
            for item in operations
        ],
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def undo(journal: Path) -> list[Operation]:
    try:
        payload = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"cannot read journal: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != JOURNAL_VERSION:
        raise PilotError("unsupported or invalid journal")
    raw_operations = payload.get("operations")
    if not isinstance(raw_operations, list):
        raise PilotError("invalid journal operations")
    results: list[Operation] = []
    for raw in reversed(raw_operations):
        if not isinstance(raw, dict) or raw.get("status") != Status.MOVED.value:
            continue
        try:
            source = Path(raw["source"])
            destination = Path(raw["destination"])
            rule = str(raw["rule"])
        except (KeyError, TypeError) as exc:
            raise PilotError("invalid journal entry") from exc
        item = Operation(source, destination, rule)
        try:
            if source.exists():
                raise PilotError("original path is occupied; refusing to overwrite")
            if not destination.is_file():
                raise PilotError("organized file is missing")
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
            result = replace(item, status=Status.UNDONE)
            LOG.info("restored %s -> %s", destination, source)
        except (OSError, PilotError) as exc:
            result = replace(item, status=Status.FAILED, detail=str(exc))
            LOG.error("undo failed %s: %s", destination, exc)
        results.append(result)
    return results
