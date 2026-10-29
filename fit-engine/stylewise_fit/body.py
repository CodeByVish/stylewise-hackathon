"""Parametric mannequin fallback: a lofted stack of elliptical cross-sections.

Not anatomically realistic; it exists so measurements map to a mesh exactly and
deterministically while MHR is evaluated. Landmark heights are fractions of stature.
"""
from dataclasses import dataclass

import numpy as np
import trimesh
from scipy.optimize import brentq

from .measure import ellipse_perimeter

# fraction of height -> (landmark name). Values chosen from typical adult proportions.
LANDMARKS = {"hip": 0.52, "waist": 0.62, "chest": 0.72}
DEPTH_RATIO = {"hip": 0.75, "waist": 0.72, "chest": 0.70}  # depth / width semi-axis


@dataclass
class Measurements:
    height_cm: float
    chest_cm: float
    waist_cm: float
    hip_cm: float


def _semi_axes(circ_cm: float, ratio: float) -> tuple[float, float]:
    """Width/depth semi-axes (m) of an ellipse with the given perimeter and aspect."""
    c = circ_cm / 100.0
    a = brentq(lambda a: ellipse_perimeter(a, a * ratio) - c, 1e-3, 1.0)
    return a, a * ratio


def mannequin_mesh(m: Measurements, ring_segments: int = 64) -> trimesh.Trimesh:
    H = m.height_cm / 100.0
    hip = _semi_axes(m.hip_cm, DEPTH_RATIO["hip"])
    waist = _semi_axes(m.waist_cm, DEPTH_RATIO["waist"])
    chest = _semi_axes(m.chest_cm, DEPTH_RATIO["chest"])
    neck = (0.06, 0.055)
    # (height fraction, (a, b)) control rings from feet to crown
    rings = [
        (0.0, (hip[0] * 0.55, hip[1] * 0.6)),
        (0.30, (hip[0] * 0.75, hip[1] * 0.8)),
        (0.47, (hip[0] * 0.97, hip[1] * 0.97)),
        (LANDMARKS["hip"], hip),
        (0.57, ((hip[0] + waist[0]) / 2, (hip[1] + waist[1]) / 2)),
        (LANDMARKS["waist"], waist),
        (0.67, ((waist[0] + chest[0]) / 2, (waist[1] + chest[1]) / 2)),
        (LANDMARKS["chest"], chest),
        (0.78, (chest[0] * 0.95, chest[1] * 0.9)),
        (0.84, neck),
        (0.88, neck),
        (0.93, (0.08, 0.095)),
        (1.0, (0.01, 0.01)),
    ]
    # dense rings, plus exact rings at landmarks so measurement slices hit them
    ys = np.unique(np.concatenate([np.linspace(0, 1, 201), list(LANDMARKS.values())]))
    fr = np.array([r[0] for r in rings])
    A = np.interp(ys, fr, [r[1][0] for r in rings])
    B = np.interp(ys, fr, [r[1][1] for r in rings])

    t = np.linspace(0, 2 * np.pi, ring_segments, endpoint=False)
    verts = []
    for y, a, b in zip(ys, A, B):
        verts.append(np.stack([a * np.cos(t), np.full_like(t, y * H), b * np.sin(t)], 1))
    verts = np.concatenate(verts)
    faces = []
    n = ring_segments
    for i in range(len(ys) - 1):
        for j in range(n):
            p, q = i * n + j, i * n + (j + 1) % n
            faces += [[p, q + n, p + n], [p, q, q + n]]
    # caps
    bottom = len(verts)
    top = bottom + 1
    verts = np.vstack([verts, [0, 0, 0], [0, H, 0]])
    last = (len(ys) - 1) * n
    for j in range(n):
        faces.append([bottom, (j + 1) % n, j])
        faces.append([top, last + j, last + (j + 1) % n])
    return trimesh.Trimesh(verts, np.array(faces), process=True)


def landmark_heights_m(height_cm: float) -> dict[str, float]:
    return {k: v * height_cm / 100.0 for k, v in LANDMARKS.items()}
