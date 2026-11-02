"""Deterministic ease arithmetic and verdicts. No comfort claims: ease is garment - body."""
from . import __version__
from .presets import DISPLAY_NAMES, estimate, nearest_height, preset_id, preset_mesh_ref
from .schemas import FitReport, FitRequest, Provenance, RegionResult

# Ease bands (cm) per fit preference: (min_ok, max_ok). Project criteria, not standards.
EASE_BANDS = {
    "snug": (0.0, 6.0),
    "regular": (2.0, 12.0),
    "relaxed": (6.0, 20.0),
}
REGIONS = ("chest", "waist", "hip")


def evaluate(req: FitRequest, body_mesh_ref: str | None = None,
             body_fit_error_cm: dict[str, float] | None = None,
             body_model: str = "mannequin-v0") -> FitReport:
    pref = req.preferences.fit_pref or "regular"
    lo, hi = EASE_BANDS[pref]
    regions, unknowns, warnings, facts = {}, [], [], []

    # preset users: girths come from shape + usual size, with a range; typed values win
    est, pid = None, None
    if req.body.source == "preset":
        p = req.body.preset
        est = estimate(p.shape, p.usual_size, p.sex)
        pid = preset_id(p.shape, p.usual_size, req.body.height_cm, p.sex)
        body_mesh_ref = body_mesh_ref or preset_mesh_ref(pid)
        facts.append(f"Body is estimated from the '{DISPLAY_NAMES[p.shape]}' silhouette and usual size "
                     f"{p.usual_size} (±{est.uncertainty_cm:.0f} cm), not measured.")
        shown = nearest_height(req.body.height_cm, p.sex)
        if shown != req.body.height_cm:
            # the mesh is for display only; ease uses the size-based girth estimates above
            facts.append(f"The 3D body shown is the {shown:.0f} cm preset, the closest to your "
                         f"{req.body.height_cm:.0f} cm height.")

    def band(e: float) -> str:
        return "tight" if e < lo else "loose" if e > hi else "ok"

    for r in REGIONS:
        body = getattr(req.body, f"{r}_cm")
        unc = 0.0
        if body is None and est is not None:
            body, unc = getattr(est, f"{r}_cm"), est.uncertainty_cm
        garment = getattr(req.garment.spec_cm, r)
        if body is None or garment is None:
            missing = "body" if body is None else "garment"
            unknowns.append(f"{r}: {missing} measurement not provided")
            regions[r] = RegionResult(body_cm=body, garment_cm=garment, ease_cm=None,
                                      uncertainty_cm=unc, verdict="unknown")
            continue
        ease = round(garment - body, 1)
        # body - unc means more ease; verdict is only firm if both ends of the range agree
        verdict = band(ease) if band(ease - unc) == band(ease + unc) else "borderline"
        regions[r] = RegionResult(body_cm=body, garment_cm=garment, ease_cm=ease,
                                  uncertainty_cm=unc, verdict=verdict)
        rng = f" ±{unc:.0f}" if unc else ""
        facts.append(f"{r} ease {ease:+.1f}{rng} cm (garment {garment} cm vs body {body} cm) -> {verdict} for {pref} fit")

    if req.body.pose == "seated":
        unknowns.append("seated: garment stretch and seated hip/waist expansion are not modeled")
        if regions["hip"].ease_cm is not None and regions["hip"].ease_cm < 4:
            warnings.append("seated: hip ease under 4 cm may restrict sitting (heuristic, not measured)")
    if req.preferences.closure == "pullover":
        unknowns.append("pullover: neck/shoulder opening dimensions not in size chart")
    if req.garment.spec_source.lower() in ("", "llm", "unknown"):
        warnings.append("garment size chart has no verified source; treat ease as unverified")

    facts.append("Ease is arithmetic difference only; it does not prove comfort.")
    return FitReport(
        body_mesh_ref=body_mesh_ref,
        garment_mesh_ref=req.garment.mesh_ref,
        body_fit_error_cm=body_fit_error_cm or {},
        regions=regions,
        warnings=warnings,
        unknowns=unknowns,
        provenance=Provenance(
            body_source="user-provided measurements" if est is None else "preset estimate (ANSUR II size chart)",
            body_preset_id=pid,
            garment_source=req.garment.spec_source,
            body_model=body_model,
            engine_version=__version__,
        ),
        advice_facts=facts,
    )
