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
