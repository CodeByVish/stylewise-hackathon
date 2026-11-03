"""Relaxed pose for presets: lower the arms from MHR's A-pose towards the body, keeping a gap so the
hands never touch the hips. Girths are unaffected (arms are excluded from every measurement).
Uses MHR's own skinning weights (data/mhr_arm_weights.npy), blended so the shoulder bends smoothly.

  .venv/bin/python scripts/repose.py               # all presets in place
"""
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = np.load(Path(__file__).resolve().parents[1] / "stylewise_fit/data/mhr_arm_weights.npy")
LOWER_DEG = 28.0


def repose(verts: np.ndarray, degrees: float = LOWER_DEG) -> np.ndarray:
    v = verts.copy()
    for w in WEIGHTS:
        arm = w > 0.5
        side = np.sign(v[arm, 0].mean())
        shoulder = (w > 0.35) & (w < 0.65)
        pivot = v[shoulder].mean(0)
        a = np.radians(degrees) * side  # rotate in the frontal plane, hand moving down towards the body
        c, s = np.cos(a), np.sin(a)
        d = v - pivot
        rot = np.stack([c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1], d[:, 2]], 1) + pivot
        ww = np.clip((w - 0.2) / 0.6, 0, 1)[:, None]  # smooth bend across the shoulder
        v = v + ww * (rot - v)
    return v


def main() -> None:
    index = json.loads((ROOT / "fixtures/presets/index.json").read_text())
    for r in index:
        path = ROOT / r["mesh_ref"]
        m = trimesh.load(path, force="mesh", process=False)
        m.vertices = repose(np.asarray(m.vertices))
        m.export(path)
    print(len(index), "presets re-posed")


if __name__ == "__main__":
    main()
