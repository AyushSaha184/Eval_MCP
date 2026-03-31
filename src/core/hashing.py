from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


def _canonicalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonicalize(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        return sorted(_canonicalize(item) for item in value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        _canonicalize(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_digest(payload: Any) -> str:
    data = payload if isinstance(payload, str) else stable_json_dumps(payload)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_dataset_cases(cases: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
    normalized_cases = []
    for case in cases:
        normalized_case = dict(case)
        if "labels" in normalized_case and isinstance(normalized_case["labels"], list):
            normalized_case["labels"] = sorted({str(label).strip() for label in normalized_case["labels"]})
        normalized_cases.append(normalized_case)
    payload = {
        "cases": normalized_cases,
        "metadata": metadata or {},
    }
    return sha256_digest(payload)


def hash_prompt_snapshot(snapshot: dict[str, Any]) -> str:
    return sha256_digest(snapshot)


def build_cache_key(payload: dict[str, Any]) -> str:
    return sha256_digest(payload)
