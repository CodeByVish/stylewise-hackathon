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


def preset_req(shape, usual_size, chest, waist, height=165):
    return FitRequest.model_validate({
        "body": {"source": "preset", "preset": {"shape": shape, "usual_size": usual_size}, "height_cm": height},
        "garment": {"id": "top-01", "category": "top", "size": "M",
                    "spec_cm": {"chest": chest, "waist": waist}, "spec_source": "fixture size chart"},
    })


def test_preset_fills_estimates_with_range():
    r = evaluate(preset_req("rectangle", "M", 103.9, 86))  # ANSUR II est chest 95.9, waist 81.9
    assert r.regions["chest"].ease_cm == 8
    assert r.regions["chest"].uncertainty_cm == 2.7
    assert r.regions["chest"].verdict == "ok"  # 5.3..10.7 stays inside regular 2..12
    assert r.provenance.body_preset_id == "female_rectangle_M_165"


def test_preset_snaps_to_generated_height_and_links_mesh():
    r = evaluate(preset_req("oval", "L", 110, 100, height=168))
    assert r.provenance.body_preset_id == "female_oval_L_165"
    assert r.body_mesh_ref == "fixtures/presets/female_oval_L_165.glb"
    assert any("165 cm preset" in f for f in r.advice_facts)


def test_measured_body_has_no_preset_mesh():
    assert evaluate(req("M", 98, 84)).body_mesh_ref is None


def test_preset_near_band_edge_is_borderline():
    r = evaluate(preset_req("rectangle", "M", 98.9, 86))  # chest ease +3 ±2.7 crosses 2
    assert r.regions["chest"].verdict == "borderline"


def test_measured_values_override_preset():
    req = preset_req("rectangle", "M", 98, 86)
    req.body.chest_cm = 90
    r = evaluate(req)
    assert r.regions["chest"].ease_cm == 8
    assert r.regions["chest"].uncertainty_cm == 0


def test_preset_requires_source():
    import pydantic, pytest
    with pytest.raises(pydantic.ValidationError):
        FitRequest.model_validate({
            "body": {"preset": {"shape": "oval", "usual_size": "M"}, "height_cm": 165},
            "garment": {"id": "t", "category": "top", "size": "M", "spec_cm": {}, "spec_source": "x"},
        })


def test_unsourced_spec_warns():
    r = req("M", 98, 84)
    r.garment.spec_source = "llm"
    assert evaluate(r).warnings
