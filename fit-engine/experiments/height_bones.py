"""Height via per-bone scales vs global scale (small experiment; presets unchanged).

  PYTHONPATH=fit-engine research/mhr-env/bin/python -W ignore fit-engine/experiments/height_bones.py

MHR's identity coeffs do not change stature, so presets reach height by a uniform global scale,
which keeps every proportion fixed. Real people are not scaled copies: in ANSUR II, crotch height /
stature rises with stature (women 0.475 at 155 cm -> 0.494 at 185 cm). Here height comes from
lengthening legs (scale params 149 thigh, 150 shank) and spine (139) instead, solved so the body
hits both the target stature and the ANSUR proportion for that stature; a tiny global scale
absorbs any residual. -> results/height_bones.csv
"""
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from stylewise_fit.mhr_body import fit, mesh_for
from stylewise_fit.presets import estimate

OUT = Path(__file__).parent / "results/height_bones.csv"
LEG, SPINE = (149, 150), 139
# ANSUR II linear fit, crotch height = b * stature + a (cm)
CROTCH = {"female": (0.590, -17.9), "male": (0.582, -17.6)}


def crotch_cm(mesh) -> float:
    v = mesh.vertices * 100
    H = v[:, 1].max()
    mid = (np.abs(v[:, 0]) < 1.5) & (v[:, 1] > 0.35 * H) & (v[:, 1] < 0.6 * H)
    return float(v[mid, 1].min())


def ratio_target(sex: str, h: float, neutral_ratio: float) -> float:
    """Keep MHR's own crotch definition, shift it by how ANSUR's ratio changes with stature."""
    b, a = CROTCH[sex]
    r = lambda s: (b * s + a) / s  # noqa: E731
    return neutral_ratio + r(h) - r(172.7)


def solve_bones(sex: str, h: float, neutral_ratio: float) -> dict[int, float]:
    want_ratio = ratio_target(sex, h, neutral_ratio)

    def res(x):
        bones = {LEG[0]: x[0], LEG[1]: x[0], SPINE: x[1]}
        m = mesh_for(np.zeros(20), None, bones)
        H = m.vertices[:, 1].max() * 100
        return [H - h, 100 * (crotch_cm(m) / H - want_ratio)]

    x = least_squares(res, [0.0, 0.0], diff_step=0.05, max_nfev=30).x
    return {LEG[0]: float(x[0]), LEG[1]: float(x[0]), SPINE: float(x[1])}


def main() -> None:
    neutral = mesh_for(np.zeros(20))
    neutral_ratio = crotch_cm(neutral) / (neutral.vertices[:, 1].max() * 100)
    rows = []
    for sex, shape, size in (("female", "rectangle", "M"), ("male", "rectangle", "L")):
        e = estimate(shape, size, sex)
        for h in ((155, 165, 175) if sex == "female" else (165, 175, 185)):
            target = {"height": h, "chest": e.chest_cm, "waist": e.waist_cm, "hip": e.hip_cm}
            bones = solve_bones(sex, h, neutral_ratio)
            for method, bn in (("global", None), ("bones", bones)):
                r = fit(target, max_nfev=25, prior_weight=0.2, bones=bn)
                H = r["mesh"].vertices[:, 1].max() * 100
                rows.append({"sex": sex, "height": h, "method": method,
                             "crotch_ratio": round(crotch_cm(r["mesh"]) / H, 4),
                             "ansur_target_ratio": round(ratio_target(sex, h, neutral_ratio), 4),
                             **{f"{k}_err": round(r["error"][k], 2) for k in ("chest", "waist", "hip")},
                             "leg_param": round(bones[LEG[0]], 3) if bn else 0, "spine_param": round(bones[SPINE], 3) if bn else 0})
                print(rows[-1], flush=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
