from __future__ import annotations

import json
from pathlib import Path

import pytest

from carrot_file_pilot.config import ConfigError, load_config
from carrot_file_pilot.models import CollisionPolicy


def test_load_custom_config(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(
        json.dumps(
            {
                "collision": "skip",
                "recursive": True,
                "rules": [
                    {
                        "name": "receipts",
                        "destination": "Finance/Receipts",
                        "extensions": ["pdf"],
                        "names": ["receipt"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.collision is CollisionPolicy.SKIP
    assert config.recursive
    assert config.rules[0].extensions == (".pdf",)


@pytest.mark.parametrize(
    "payload,message",
    [
        ({"unknown": True}, "unknown config field"),
        ({"rules": []}, "non-empty"),
        (
            {"rules": [{"name": "bad", "destination": "../escape", "extensions": ["txt"]}]},
            "stay inside",
        ),
        ({"collision": "overwrite"}, "rename"),
    ],
)
def test_rejects_unsafe_config(tmp_path: Path, payload: object, message: str) -> None:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_config(path)
