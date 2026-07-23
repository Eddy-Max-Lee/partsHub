from __future__ import annotations
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("PARTSHUB_DB_PATH", ROOT / "data" / "parts.db"))
APP_VERSION = "4.0.0"
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("PARTSHUB_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",") if x.strip()]
