from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_part_lookup_returns_verification_metadata():
    response = client.get("/api/v1/parts/077905115T")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["normalized_part_number"] == "077905115T"
    assert body["meta"]["verification_status"] == "unverified"


def test_search_accepts_part_number_alias_and_returns_typed_results():
    response = client.get("/api/v1/search", params={"q": "077-905-115-T"})
    assert response.status_code == 200
    assert response.json()["data"]["items"]
    assert response.json()["meta"]["api_version"] == "v1"


def test_vin_decode_returns_masked_unavailable_provider_result():
    response = client.post("/api/v1/vin/decode", json={"vin": "WAUZZZ4E16N012345"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["masked_vin"] == "WAU•••••••••••345"
    assert "012345" not in response.text


def test_versioned_openapi_document_is_public():
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/search" in response.json()["paths"]
