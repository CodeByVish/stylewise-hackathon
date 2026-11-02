"""Generate MHR preset bodies: 2 sexes x 5 shapes x 7 sizes x 3 heights, fitted in parallel.

  python -W ignore scripts/gen_presets.py --out ../fixtures/presets --workers 8
  python -W ignore scripts/gen_presets.py --quick   # both sexes, 5 shapes, size M, middle height

Writes <out>/<preset_id>.glb and <out>/index.json (targets, achieved, errors, FFIT check).
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from stylewise_fit.presets import (DISPLAY_NAMES, HEIGHTS_CM, SEXES, SHAPES, SIZES, classify, estimate,
                                   preset_id)


def _worst(r: dict) -> float:
    return max(abs(r["error"][k]) for k in ("chest", "waist", "hip"))


def _acceptable(r: dict, shape: str, uncertainty_cm: float) -> bool:
    """A preset must keep its FFIT class and land inside the range we report to the user."""
    m = r["measured"]
    return classify(m["chest"], m["waist"], m["hip"]) == shape and _worst(r) <= uncertainty_cm


def _target(sex: str, shape: str, size: str, height: float) -> dict:
    e = estimate(shape, size, sex)
    return {"height": height, "chest": e.chest_cm, "waist": e.waist_cm, "hip": e.hip_cm}


def _entry_ok(c: dict) -> bool:
    """accepted flag of an index entry; derived for entries written before it existed."""
    if "accepted" in c:
        return c["accepted"]
    worst = max(abs(c["fit_error_cm"][k]) for k in ("chest", "waist", "hip"))
    return c["ffit_class_of_mesh"] == c["shape"] and worst <= c["uncertainty_cm"]


def run_one(sex: str, shape: str, size: str, height: float, out: str, max_nfev: int,
            prior_weight: float, neighbour: tuple | None = None) -> dict:
    """neighbour: (sex, shape, size, height) of an accepted preset to warm-start from.
    Fitting from MHR's mean body can stall in a poor local minimum on extreme targets
    (female_oval_XS_175: 4.6 cm); starting from a fitted neighbour avoids it (1.5 cm)."""
    from stylewise_fit.mhr_body import fit  # import in worker: loads torch + model per process

    e = estimate(shape, size, sex)
    target = _target(sex, shape, size, height)
    x0, extra = None, 0.0
    if neighbour:
        warm = fit(_target(*neighbour), max_nfev=max_nfev, prior_weight=prior_weight)
        x0, extra = warm["coeffs"], warm["seconds"]
    r = fit(target, max_nfev=max_nfev, prior_weight=prior_weight, x0=x0)
    r["seconds"] += extra
    pid = preset_id(shape, size, height, sex)
    r["mesh"].export(Path(out) / f"{pid}.glb")
    m = r["measured"]
    return {
        "id": pid, "sex": sex, "shape": shape, "display_name": DISPLAY_NAMES[shape], "usual_size": size,
        "mesh_ref": f"fixtures/presets/{pid}.glb", "model": "mhr-lod1",
        "target_cm": target, "measured_cm": {k: round(v, 2) for k, v in m.items()},
        "fit_error_cm": {k: round(v, 2) for k, v in r["error"].items()},
        "uncertainty_cm": e.uncertainty_cm,
        "ffit_class_of_target": classify(e.chest_cm, e.waist_cm, e.hip_cm),
        "ffit_class_of_mesh": classify(m["chest"], m["waist"], m["hip"]),
        "nfev": r["nfev"], "seconds": round(r["seconds"], 1), "prior_weight": prior_weight,
        "warm_start": preset_id(*neighbour[1:], neighbour[0]) if neighbour else None,
        "accepted": _acceptable(r, shape, e.uncertainty_cm),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "fixtures/presets"))
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--max-nfev", type=int, default=25)
    # 0.2 from experiments/prior_sweep.py: 2.0 pulled hourglass/oval toward rectangle
    p.add_argument("--prior-weight", type=float, default=0.2)
    p.add_argument("--quick", action="store_true")
    p.add_argument("--only", nargs="*", help="preset ids to (re)generate, e.g. female_oval_XS_175")
    a = p.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)

    sizes = ["M"] if a.quick else list(SIZES)
    heights = lambda sex: HEIGHTS_CM[sex][1:2] if a.quick else HEIGHTS_CM[sex]
    jobs = [(x, s, z, h) for x in SEXES for s in SHAPES for z in sizes for h in heights(x)]
    if a.only:
        jobs = [j for j in jobs if preset_id(j[1], j[2], j[3], j[0]) in a.only]
    print(f"{len(jobs)} presets on {a.workers} workers", flush=True)

    results = []
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_one, *j, a.out, a.max_nfev, a.prior_weight) for j in jobs]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(r["id"], r["fit_error_cm"], r["ffit_class_of_mesh"], f'{r["seconds"]}s', flush=True)
    # pass 2: re-fit rejected presets from the closest accepted neighbour (same sex and shape)
    pool = {r["id"]: r for r in results}
    if a.only and (Path(a.out) / "index.json").exists():
        pool = {r["id"]: r for r in json.loads((Path(a.out) / "index.json").read_text())} | pool
    retry = []
    for r in results:
        if r["accepted"]:
            continue
        cands = [c for c in pool.values() if _entry_ok(c) and c.get("sex", "female") == r["sex"]
                 and c["shape"] == r["shape"]]
        dist = lambda c: (abs(SIZES.index(c["usual_size"]) - SIZES.index(r["usual_size"])),
                          abs(c["target_cm"]["height"] - r["target_cm"]["height"]))
        if cands:
            c = min(cands, key=dist)
            retry.append(((r["sex"], r["shape"], r["usual_size"], r["target_cm"]["height"]),
                          (c.get("sex", "female"), c["shape"], c["usual_size"], c["target_cm"]["height"])))
    if retry:
        print(f"pass 2: {len(retry)} warm-start refits", flush=True)
        with ProcessPoolExecutor(a.workers) as ex:
            futs = [ex.submit(run_one, *j, a.out, a.max_nfev, a.prior_weight, nb) for j, nb in retry]
            for f in as_completed(futs):
                r2 = f.result()
                old = next(r for r in results if r["id"] == r2["id"])
                print(r2["id"], "from", r2["warm_start"], r2["fit_error_cm"], r2["ffit_class_of_mesh"], flush=True)
                if r2["accepted"] or max(abs(r2["fit_error_cm"][k]) for k in ("chest", "waist", "hip")) < \
                        max(abs(old["fit_error_cm"][k]) for k in ("chest", "waist", "hip")):
                    results[results.index(old)] = r2  # run_one already overwrote the GLB
    results.sort(key=lambda r: r["id"])
    index = Path(a.out) / "index.json"
    if a.only and index.exists():  # merge re-generated presets into the existing index
        fresh = {r["id"] for r in results}
        results = sorted([r for r in json.loads(index.read_text()) if r["id"] not in fresh] + results,
                         key=lambda r: r["id"])
    index.write_text(json.dumps(results, indent=2) + "\n")
    worst = max(abs(v) for r in results for k, v in r["fit_error_cm"].items() if k != "height")
    wrong = [r["id"] for r in results if r["ffit_class_of_mesh"] != r["shape"]]
    rejected = [r["id"] for r in results if not _entry_ok(r)]
    print(f"done: worst girth error {worst:.2f} cm; FFIT class mismatches: {wrong or 'none'}")
    print(f"warm-start refits {len(retry)}; still outside class or uncertainty: {rejected or 'none'}")


if __name__ == "__main__":
    main()
