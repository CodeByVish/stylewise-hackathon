"""B-B: edit one measurement, re-fit, and measure leakage into what was not edited.

  PYTHONPATH=fit-engine research/mhr-env/bin/python -W ignore fit-engine/experiments/mhr_bb.py

For each base body (a preset target), fit once, then re-fit (warm-started from the base) with
one girth changed by +4 cm. Reports, per edit: the edited girth's error, the change in the two
unedited girths and the shoulder/hip ratio, and the mean vertex displacement (mm) of arms, legs
and head, which no target constrains. -> results/mhr_bb.csv
"""
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

OUT = Path(__file__).parent / "results/mhr_bb.csv"
BASES = [("female", "rectangle", "M", 165.0), ("male", "rectangle", "L", 175.0)]
EDITS = [("waist", 4.0), ("hip", 4.0), ("chest", 4.0)]


def run(base):
    from stylewise_fit.mhr_body import _arm_faces, _model, fit, shoulder_hip_target
    from stylewise_fit.presets import estimate

    sex, shape, size, h = base
    e = estimate(shape, size, sex)
    t0 = {"height": h, "chest": e.chest_cm, "waist": e.waist_cm, "hip": e.hip_cm,
          "shoulder_hip": shoulder_hip_target(sex, e.chest_cm, e.hip_cm)}
    b = fit(t0, max_nfev=25, prior_weight=0.2)
    _, faces = _model()
    arm_v = np.unique(faces[_arm_faces()])
    V0 = b["mesh"].vertices
    H = V0[:, 1].max()
    legs = np.where(V0[:, 1] < 0.45 * H)[0]
    head = np.where(V0[:, 1] > 0.87 * H)[0]
    rows = []
    for region, d in EDITS:
        t = dict(t0)
        t[region] += d
        r = fit(t, max_nfev=25, prior_weight=0.2, x0=b["coeffs"])
        disp = np.linalg.norm(r["mesh"].vertices - V0, axis=1) * 1000
        others = [k for k in ("chest", "waist", "hip") if k != region]
        rows.append({
            "body": f"{sex}_{shape}_{size}_{int(h)}", "edit": f"{region} +{d:g}",
            "edited_err_cm": round(r["error"][region], 2),
            **{f"d_{k}_cm": round(r["measured"][k] - b["measured"][k], 2) for k in others},
            "d_shoulder_hip": round(r["measured"]["shoulder_hip"] - b["measured"]["shoulder_hip"], 3),
            "arms_mm": round(float(disp[arm_v].mean()), 1), "legs_mm": round(float(disp[legs].mean()), 1),
            "head_mm": round(float(disp[head].mean()), 1), "torso_max_mm": round(float(disp.max()), 1),
        })
    return rows


def main() -> None:
    with ProcessPoolExecutor(len(BASES)) as ex:
        rows = [r for rs in ex.map(run, BASES) for r in rs]
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
