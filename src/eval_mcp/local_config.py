from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    return Path.home() / ".eval_mcp" / "config.json"


def load_local_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_local_config(data: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def clear_local_config() -> None:
    path = _config_path()
    if path.exists():
        path.unlink()
