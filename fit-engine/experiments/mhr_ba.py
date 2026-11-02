"""Experiment B-A on MHR: recover a body from height/chest/waist/hip alone.

Reference bodies: random MHR body-identity coeffs (first 20 of 45) + global scale.
Fit: stylewise_fit.mhr_body.fit (least squares over 20 coeffs, height by global scale).

Run (needs the research env with torch + MHR assets):
  research/mhr-env/bin/python -W ignore fit-engine/experiments/mhr_ba.py [n_bodies]
"""
import csv
import sys
from pathlib import Path

import numpy as np

from stylewise_fit.mhr_body import N_SHAPE, REGIONS, fit, measure, mesh_for

ROOT = Path(__file__).resolve().parents[2]


def main(n_bodies: int = 3, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    out = ROOT / "fit-engine/experiments/results"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(n_bodies):
        true_c = rng.normal(0, 0.7, N_SHAPE)
        h = float(rng.uniform(155, 185))
        ref = mesh_for(true_c, h)
        target = measure(ref)
        r = fit(target)
        r["mesh"].export(out / f"mhr_ba_body{i}_fit.glb")
        ref.export(out / f"mhr_ba_body{i}_ref.glb")
        # vertex distance shows the non-uniqueness: same 4 numbers, different body
        v2v = float(np.linalg.norm(r["mesh"].vertices - ref.vertices, axis=1).mean() * 100)
        row = {"body": i, "nfev": r["nfev"], "seconds": round(r["seconds"], 1), "mean_v2v_cm": round(v2v, 2)}
        for k in ("height", *REGIONS):
            row[f"{k}_target"] = round(target[k], 2)
            row[f"{k}_err"] = round(r["error"][k], 2)
        rows.append(row)
        print(row, flush=True)
    with open(out / "mhr_ba.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    errs = np.array([[abs(r[f"{k}_err"]) for k in REGIONS] for r in rows])
    print(f"mean abs err {errs.mean():.2f} cm, worst {errs.max():.2f} cm")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
