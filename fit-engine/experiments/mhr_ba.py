"""Experiment B-A on MHR: recover a body from height/chest/waist/hip alone.

Reference bodies: random MHR body-identity coeffs (first 20 of 45) + global scale.
Fit: stylewise_fit.mhr_body.fit (least squares over 20 coeffs, height by global scale).

Run (needs the research env with torch + MHR assets):
  research/mhr-env/bin/python -W ignore fit-engine/experiments/mhr_ba.py [n_bodies] --workers 32
"""
import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "fit-engine/experiments/results"
REGIONS = ("chest", "waist", "hip")


def one(i: int, seed: int, max_nfev: int, prior_weight: float, save_meshes: bool) -> dict:
    from stylewise_fit.mhr_body import N_SHAPE, fit, measure, mesh_for  # torch loads per worker

    rng = np.random.default_rng([seed, i])  # each body reproducible on its own
    true_c = rng.normal(0, 0.7, N_SHAPE)
    h = float(rng.uniform(155, 185))
    ref = mesh_for(true_c, h)
    target = {k: measure(ref)[k] for k in ("height", *REGIONS)}
    r = fit(target, max_nfev=max_nfev, prior_weight=prior_weight)
    if save_meshes:
        r["mesh"].export(OUT / f"mhr_ba_body{i}_fit.glb")
        ref.export(OUT / f"mhr_ba_body{i}_ref.glb")
    # vertex distance shows the non-uniqueness: same 4 numbers, different body
    v2v = float(np.linalg.norm(r["mesh"].vertices - ref.vertices, axis=1).mean() * 100)
    row = {"body": i, "nfev": r["nfev"], "seconds": round(r["seconds"], 1), "mean_v2v_cm": round(v2v, 2)}
    for k in ("height", *REGIONS):
        row[f"{k}_target"] = round(target[k], 2)
        row[f"{k}_err"] = round(r["error"][k], 2)
    return row


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("n_bodies", type=int, nargs="?", default=3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--max-nfev", type=int, default=25)
    p.add_argument("--prior-weight", type=float, default=0.2)  # the preset settings
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    args = [(i, a.seed, a.max_nfev, a.prior_weight, a.n_bodies <= 3) for i in range(a.n_bodies)]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, *zip(*args)))
    for r in rows:
        print(r, flush=True)
    name = "mhr_ba.csv" if a.n_bodies <= 3 else f"mhr_ba_n{a.n_bodies}.csv"
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    errs = np.array([[abs(r[f"{k}_err"]) for k in REGIONS] for r in rows])
    print(f"n={len(rows)}: mean abs err {errs.mean():.2f} cm, median {np.median(errs):.2f}, "
          f"p95 {np.percentile(errs, 95):.2f}, worst {errs.max():.2f} cm; "
          f"mean v2v {np.mean([r['mean_v2v_cm'] for r in rows]):.2f} cm -> {OUT / name}")


if __name__ == "__main__":
    main()
