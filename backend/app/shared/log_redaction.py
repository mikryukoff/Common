"""Сокращение и маскирование значений в логах."""

from __future__ import annotations

import json
from typing import Any


def truncate_str(value: str, max_len: int = 400) -> str:
    text = (value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "… [truncated]"


def redact_value(value: Any, max_len: int = 400) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return truncate_str(value, max_len)
    if isinstance(value, (int, float, bool)):
        return value
    try:
        raw = json.dumps(value, ensure_ascii=False)
    except TypeError:
        raw = str(value)
    return truncate_str(raw, max(200, max_len))
