from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone


def new_uuid() -> str:
    return str(uuid.uuid4())


def generate_public_id(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(6)
    return f"{prefix}_{timestamp}_{suffix}"


def generate_run_id() -> str:
    return generate_public_id("run")

