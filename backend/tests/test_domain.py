from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.migration import migrate
from app.privacy import mask_vin, normalize_vin, validate_vin
from app.parts import normalize_part_number


def test_part_number_normalization_preserves_display_format():
    assert normalize_part_number("  077-905 115-t ") == "077905115T"


def test_vin_validation_and_masking_do_not_expose_middle_characters():
    vin = "WAUZZZ4E16N012345"
    assert validate_vin(vin) == vin
    assert mask_vin(vin) == "WAU•••••••••••345"
    assert normalize_vin(" wau zzz4e16n012345 ") == vin


def test_migration_creates_domain_tables_and_seed_data(tmp_path):
    db_path = tmp_path / "parts.db"
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE products(
            id INTEGER PRIMARY KEY, name_zh TEXT NOT NULL, name_en TEXT NOT NULL,
            part_number TEXT UNIQUE NOT NULL, description_zh TEXT, source_url TEXT NOT NULL,
            status TEXT NOT NULL, category_zh TEXT, crawled_at TEXT NOT NULL
        );
        INSERT INTO products VALUES
        (1, '點火線圈', 'Ignition Coil', '077-905-115-T', 'Demo', 'https://example.test/p', 'priced', '點火系統', '2026-07-23');
        """
    )
    con.commit()
    con.close()

    migrate(db_path)

    con = sqlite3.connect(db_path)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"parts", "vehicles", "part_number_aliases", "part_vehicle_fitments", "knowledge_articles", "diagnostic_codes"} <= tables
    assert con.execute("SELECT normalized_part_number FROM parts").fetchone()[0] == "077905115T"
    assert con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] >= 5
    assert con.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0] >= 5
    first_count = con.execute("SELECT COUNT(*) FROM part_vehicle_fitments").fetchone()[0]
    first_offer_count = con.execute("SELECT COUNT(*) FROM product_offers").fetchone()[0]
    con.close()

    migrate(db_path)
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM part_vehicle_fitments").fetchone()[0] == first_count
    assert con.execute("SELECT COUNT(*) FROM product_offers").fetchone()[0] == first_offer_count
    con.close()
