from __future__ import annotations

import re


VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def normalize_vin(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def validate_vin(value: str) -> str:
    vin = normalize_vin(value)
    if not VIN_RE.fullmatch(vin):
        raise ValueError("VIN 必須為 17 碼，且不可包含 I、O、Q")
    return vin


def mask_vin(value: str) -> str:
    vin = normalize_vin(value)
    if len(vin) < 8:
        return "••••"
    return f"{vin[:3]}{'•' * (len(vin) - 6)}{vin[-3:]}"

