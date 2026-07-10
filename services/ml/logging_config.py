"""Structured logging with PII redaction. Feature values are NEVER logged;
we log a stable hash of the input instead."""
from __future__ import annotations

import hashlib
import json
import logging


def input_hash(features: dict) -> str:
    """Deterministic sha256 of a feature dict (order-independent)."""
    payload = json.dumps(features, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )


logger = logging.getLogger("ml_service")
