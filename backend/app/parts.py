from __future__ import annotations

import re


def normalize_part_number(value: str) -> str:
    """Return a lookup-safe part number while retaining the original elsewhere."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())

