"""Deterministic ease arithmetic and verdicts. No comfort claims: ease is garment - body."""
from . import __version__
from .fabric import fabric
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

    fab = fabric(req.garment.fabric)
    if fab is None:
        unknowns.append("fabric not given: stretch and fabric thickness are not modeled")
    elif fab.bulk_cm:
        facts.append(f"{req.garment.fabric} is a thick fabric: {fab.bulk_cm:g} cm more minimum ease is needed "
                     "(project heuristic).")
    lo_eff = lo + (fab.bulk_cm if fab else 0.0)

    def band(e: float, give: float) -> str:
        # "stretch": below the minimum relaxed, but inside it once the garment gives
        if e < lo_eff:
            return "stretch" if e + give >= lo_eff else "tight"
        return "loose" if e > hi else "ok"

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
        give = round(req.garment.stretch_cm.get(r, 0.0) + (fab.stretch_pct * garment if fab else 0.0), 1)
        # body - unc means more ease; verdict is only firm if both ends of the range agree.
        # Fitting only by stretching is not a firm "ok": it is borderline, and said so.
        lo_end, hi_end = band(ease - unc, give), band(ease + unc, give)
        verdict = lo_end if lo_end == hi_end and lo_end != "stretch" else "borderline"
        regions[r] = RegionResult(body_cm=body, garment_cm=garment, ease_cm=ease,
                                  uncertainty_cm=unc, stretch_cm=give, verdict=verdict)
        rng = f" ±{unc:.0f}" if unc else ""
        facts.append(f"{r} ease {ease:+.1f}{rng} cm (garment {garment} cm vs body {body} cm) -> {verdict} for {pref} fit")
        if "stretch" in (lo_end, hi_end):
            facts.append(f"{r}: fits only if the garment stretches (it can give about {give:g} cm).")

    if req.body.pose == "seated":
        unknowns.append("seated: seated hip/waist expansion is not modeled")
        if regions["hip"].ease_cm is not None and regions["hip"].ease_cm < 4:
            warnings.append("seated: hip ease under 4 cm may restrict sitting (heuristic, not measured)")
    if req.preferences.closure == "pullover":
        unknowns.append("pullover: neck/shoulder opening dimensions not in size chart")
    src = req.garment.spec_source.lower()
    # "unverified" alone also appears in sourced notes ("range interpretation is unverified")
    # say where the sizes came from, rather than only that they are unverified
    if "synthetic" in src and "uniqlo" in src:
        warnings.append("Sizes estimated from the Uniqlo SG women's size chart plus typical room for this garment "
                        "type, not from this product's own chart; ease is approximate.")
    elif "synthetic" in src:
        warnings.append("Sizes come from a sample test garment, not a real product's chart; ease is approximate.")
    elif "unverified reference" in src:
        warnings.append("Sizes taken from a general reference table (UNIQLO SG fit guide pattern), not this "
                        "product's own chart; ease is approximate.")
    elif src in ("", "llm", "unknown"):
        warnings.append("This garment has no size chart source; ease is approximate.")
    if "assumed garment" in src:
        warnings.append("The seller does not say whether these are body or garment measurements; we assume garment "
                        "measurements, as is usual for seller charts. If they are body sizes, the garment is roomier than shown.")
    if "range interpretation is unverified" in src:
        warnings.append("The chart ranges may describe body measurements rather than garment stretch; ease is uncertain.")

    facts.append("Ease is arithmetic difference only; it does not prove comfort.")
    return FitReport(
        body_mesh_ref=body_mesh_ref,
        garment_mesh_ref=req.garment.mesh_ref,
        body_fit_error_cm=body_fit_error_cm or {},
        regions=regions,
        warnings=warnings,
        unknowns=unknowns,
        provenance=Provenance(
            body_source="user-provided measurements" if est is None else "preset estimate (general retail size chart)",
            body_preset_id=pid,
            garment_source=req.garment.spec_source,
            body_model=body_model,
            engine_version=__version__,
        ),
        advice_facts=facts,
    )
