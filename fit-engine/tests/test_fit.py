from stylewise_fit.fit import evaluate
from stylewise_fit.schemas import FitRequest


def req(size, chest, waist, **extra):
    return FitRequest.model_validate({
        "body": {"height_cm": 165, "chest_cm": 90, "waist_cm": 74, **extra.get("body", {})},
        "garment": {"id": "top-01", "category": "top", "size": size,
                    "spec_cm": {"chest": chest, "waist": waist}, "spec_source": "fixture size chart"},
        "preferences": extra.get("preferences", {}),
    })


def test_readme_arithmetic_size_m():
    r = evaluate(req("M", 98, 84))
    assert r.regions["chest"].ease_cm == 8
    assert r.regions["waist"].ease_cm == 10
    assert r.regions["chest"].verdict == "ok"


def test_readme_arithmetic_size_s():
    r = evaluate(req("S", 86, 72))
    assert r.regions["chest"].ease_cm == -4
    assert r.regions["waist"].ease_cm == -2
    assert r.regions["chest"].verdict == "tight"


def test_missing_hip_is_unknown_not_guessed():
    r = evaluate(req("M", 98, 84))
    assert r.regions["hip"].verdict == "unknown"
    assert r.regions["hip"].ease_cm is None
    assert any(u.startswith("hip") for u in r.unknowns)


def test_preference_changes_verdict():
    assert evaluate(req("M", 98, 84)).regions["chest"].verdict == "ok"
    snug = evaluate(req("M", 98, 84, preferences={"fit_pref": "snug"}))
    assert snug.regions["chest"].verdict == "loose"


def test_unsourced_spec_warns():
    r = req("M", 98, 84)
    r.garment.spec_source = "llm"
    assert evaluate(r).warnings
