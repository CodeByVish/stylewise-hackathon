import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from stylewise_fit.server import app  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
client = TestClient(app)


def test_health():
    assert client.get("/health").json()["ok"] is True


@pytest.mark.parametrize("name", ["A_M", "B_S", "C_M"])
def test_evaluate_matches_fixture_report(name):
    req = json.loads((FIXTURES / f"req_{name}.json").read_text())
    expected = json.loads((FIXTURES / f"report_{name}.json").read_text())
    r = client.post("/fit/evaluate", json=req)
    assert r.status_code == 200
    assert r.json()["regions"] == expected["regions"]


def test_invalid_request_is_422():
    r = client.post("/fit/evaluate", json={"body": {"height_cm": 40}})
    assert r.status_code == 422


def test_estimated_items_fit_but_warn():
    items = {i["garment_id"]: i for i in client.get("/catalogue").json()}
    assert items["blush-shell-top"]["fittable"]
    shell = client.post("/fit/outfit", json={"body": {"height_cm": 165, "chest_cm": 90},
                                             "items": [{"garment_id": "blush-shell-top", "size": "M"}]}).json()[0]
    assert shell["report"]["regions"]["chest"]["garment_cm"] == 98  # Uniqlo body M 92 + 6 ease guess
    assert any("no verified source" in w for w in shell["report"]["warnings"])


def test_outfit_reports_each_piece():
    r = client.post("/fit/outfit", json={
        "body": {"height_cm": 165, "chest_cm": 90, "waist_cm": 74, "hip_cm": 98},
        "items": [{"garment_id": "green-kurta", "size": "M"}, {"garment_id": "gold-trousers", "size": "M"},
                  {"garment_id": "no-such-item", "size": "M"}]}).json()
    kurta, trousers, missing = r
    assert kurta["report"]["regions"]["chest"]["ease_cm"] == 9  # Indubindu M bust 99 - 90
    assert trousers["report"]["regions"]["waist"]["stretch_cm"] == 6  # elastic waist 86-92
    assert missing["report"] is None and "unknown garment" in missing["error"]


def test_uniqlo_tee_chest_is_twice_body_width_and_reference_dress_warns():
    body = {"height_cm": 165, "chest_cm": 90}
    tee, dress, kurta = client.post("/fit/outfit", json={"body": body, "items": [
        {"garment_id": "uniqlo-crew-tee", "size": "M"}, {"garment_id": "reference-dress", "size": "M"},
        {"garment_id": "green-kurta", "size": "M"}]}).json()
    assert tee["report"]["regions"]["chest"]["garment_cm"] == 99  # 2 x 49.5
    assert not tee["report"]["warnings"] and not kurta["report"]["warnings"]
    assert any("no verified source" in w for w in dress["report"]["warnings"])
