"""Configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CollisionPolicy, Rule


class ConfigError(ValueError):
    """Raised for invalid user configuration."""


DEFAULT_RULES: tuple[Rule, ...] = (
    Rule("documents", "Documents", (".doc", ".docx", ".odt", ".pdf", ".txt")),
    Rule("images", "Images", (".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp")),
    Rule("audio", "Audio", (".flac", ".m4a", ".mp3", ".ogg", ".wav")),
    Rule("video", "Video", (".avi", ".mkv", ".mov", ".mp4", ".webm")),
    Rule("archives", "Archives", (".7z", ".gz", ".rar", ".tar", ".zip")),
    Rule("spreadsheets", "Spreadsheets", (".csv", ".ods", ".xls", ".xlsx")),
)


@dataclass(frozen=True)
class Config:
    rules: tuple[Rule, ...] = DEFAULT_RULES
    collision: CollisionPolicy = CollisionPolicy.RENAME
    recursive: bool = False
    include_hidden: bool = False


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{field} must be an array of strings")
    return tuple(item.casefold() for item in value)


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read config: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be an object")
    allowed = {"rules", "collision", "recursive", "include_hidden"}
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigError(f"unknown config field(s): {', '.join(sorted(unknown))}")
    raw_rules = raw.get("rules")
    rules = DEFAULT_RULES
    if raw_rules is not None:
        if not isinstance(raw_rules, list) or not raw_rules:
            raise ConfigError("rules must be a non-empty array")
        parsed: list[Rule] = []
        destinations: set[str] = set()
        for index, item in enumerate(raw_rules):
            if not isinstance(item, dict):
                raise ConfigError(f"rules[{index}] must be an object")
            if set(item) - {"name", "destination", "extensions", "names"}:
                raise ConfigError(f"rules[{index}] has unknown fields")
            name, destination = item.get("name"), item.get("destination")
            if not isinstance(name, str) or not name.strip():
                raise ConfigError(f"rules[{index}].name must be a non-empty string")
            if not isinstance(destination, str) or not destination.strip():
                raise ConfigError(f"rules[{index}].destination must be a non-empty string")
            dest_path = Path(destination)
            if dest_path.is_absolute() or ".." in dest_path.parts:
                raise ConfigError(f"rules[{index}].destination must stay inside the target")
            key = destination.casefold()
            if key in destinations:
                raise ConfigError(f"duplicate destination: {destination}")
            destinations.add(key)
            extensions = _strings(item.get("extensions", []), f"rules[{index}].extensions")
            names = _strings(item.get("names", []), f"rules[{index}].names")
            extensions = tuple(ext if ext.startswith(".") else f".{ext}" for ext in extensions)
            if not extensions and not names:
                raise ConfigError(f"rules[{index}] needs extensions or names")
            parsed.append(Rule(name, destination, extensions, names))
        rules = tuple(parsed)
    try:
        collision = CollisionPolicy(raw.get("collision", "rename"))
    except ValueError as exc:
        raise ConfigError("collision must be 'rename' or 'skip'") from exc
    recursive = raw.get("recursive", False)
    include_hidden = raw.get("include_hidden", False)
    if not isinstance(recursive, bool) or not isinstance(include_hidden, bool):
        raise ConfigError("recursive and include_hidden must be booleans")
    return Config(rules, collision, recursive, include_hidden)
