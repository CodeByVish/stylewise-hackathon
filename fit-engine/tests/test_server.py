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
    # the hidden black satin dress is the last estimated item: still fittable, always warned
    dress = client.post("/fit/outfit", json={"body": {"height_cm": 165, "chest_cm": 90},
                                             "items": [{"garment_id": "black-satin-dress", "size": "M"}]}).json()[0]
    assert dress["report"]["regions"]["chest"]["garment_cm"] == 98  # Uniqlo body M 92 + 6 ease guess
    assert any("not from this product's own chart" in w or "not this product's own chart" in w for w in dress["report"]["warnings"])


def test_sourced_inch_chart_is_converted_and_assumption_stated():
    shell = client.post("/fit/outfit", json={"body": {"height_cm": 165, "chest_cm": 90},
                                             "items": [{"garment_id": "blush-shell-top", "size": "M"}]}).json()[0]
    assert shell["report"]["regions"]["chest"]["garment_cm"] == 100.1  # SimpleFun M 39.4 in
    warnings = shell["report"]["warnings"]
    assert not any("own chart" in w for w in warnings)
    assert any("we assume garment measurements" in w for w in warnings)


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
    assert any("not from this product's own chart" in w or "not this product's own chart" in w for w in dress["report"]["warnings"])


def test_preview_photo_rejects_measured_bodies():
    r = client.post("/preview/photo", json={"body": {"height_cm": 165, "chest_cm": 90}, "garment_id": "green-kurta", "size": "M"})
    assert r.status_code == 422


def test_garments_without_a_photo_are_described_in_words():
    from stylewise_fit.preview import described

    text = described("gold-trousers")
    assert "gold trousers" in text and "rgb(" not in text or "colour" in text


def test_catalogue_reports_photo_availability():
    items = {i["garment_id"]: i for i in client.get("/catalogue").json()}
    assert items["emerald-wrap-dress"]["photo"]
    assert not {"green-kurta", "ivory-set", "gold-trousers", "navy-bottom",
                "black-satin-dress", "uniqlo-dress-E487286"} & items.keys()
    assert items["uniqlo-crew-tee"]["photo"] and items["uniqlo-crew-tee"]["for"] == "unisex"  # generated photo


def test_demo_chart_ambiguity_is_visible():
    body = {"source": "preset", "height_cm": 165,
            "preset": {"shape": "rectangle", "usual_size": "M", "sex": "female"}}
    response = client.post('/fit/outfit', json={"body": body, "items": [
        {"garment_id": "zesica-black-midi-dress", "size": "M"},
        {"garment_id": "parthvi-anarkali-set", "size": "M"}]})
    assert response.status_code == 200
    reports = response.json()
    assert any('ranges may describe body measurements' in w for w in reports[0]['report']['warnings'])
    assert any('body or garment measurements' in w for w in reports[1]['report']['warnings'])


def test_measurements_get_the_closest_preset_for_visuals():
    r = client.post("/presets/nearest", json={"sex": "female", "height_cm": 162, "chest_cm": 90, "waist_cm": 74, "hip_cm": 96}).json()
    assert (r["shape"], r["usual_size"], r["height_cm"]) == ("rectangle", "M", 165.0)
    assert set(r["preset_cm"]) == {"chest", "waist", "hip"}
    men = client.post("/presets/nearest", json={"sex": "male", "height_cm": 178, "chest_cm": 90, "waist_cm": 60, "hip_cm": 92}).json()
    assert men["shape"] != "hourglass"  # not offered for men
