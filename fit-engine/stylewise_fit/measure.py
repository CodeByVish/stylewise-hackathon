"""Circumference operator: horizontal plane slice -> convex-hull perimeter.

Convex hull approximates a tape measure, which bridges concavities (e.g. between
the breasts or the small of the back). Meshes are in meters, Y-up (see contracts/README.md).
"""
import numpy as np
import trimesh
from shapely.geometry import MultiPoint


def circumference_at_height(mesh: trimesh.Trimesh, y_m: float) -> float:
    """Tape-style circumference (cm) of the slice at height y_m. Returns 0 if no slice."""
    section = mesh.section(plane_origin=[0, y_m, 0], plane_normal=[0, 1, 0])
    if section is None:
        return 0.0
    pts = np.asarray(section.vertices)[:, [0, 2]]  # project to XZ plane
    if len(pts) < 3:
        return 0.0
    return MultiPoint(pts).convex_hull.length * 100.0


def torso_circumference(mesh: trimesh.Trimesh, y_m: float, max_offset_m: float = 0.2) -> float:
    """Like circumference_at_height, but keeps only slice loops centred near the body
    axis (x=0), so arms are excluded. Legs at hip level are kept: a tape wraps both."""
    section = mesh.section(plane_origin=[0, y_m, 0], plane_normal=[0, 1, 0])
    if section is None:
        return 0.0
    loops = [l[:, [0, 2]] for l in section.discrete if abs(l[:, 0].mean()) < max_offset_m]
    if not loops:
        return 0.0
    return MultiPoint(np.concatenate(loops)).convex_hull.length * 100.0


def girth_excluding(mesh: trimesh.Trimesh, y_m: float, skip_faces: np.ndarray) -> float:
    """Tape-style girth (cm) at height y_m, ignoring slice segments from skip_faces (bool
    per face, e.g. arms). Legs are kept at hip level: a tape wraps both."""
    seg, fi = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, y_m, 0], return_faces=True)
    seg = seg[~skip_faces[fi]]
    if len(seg) < 2:
        return 0.0
    return MultiPoint(seg.reshape(-1, 3)[:, [0, 2]]).convex_hull.length * 100.0


def landmark_circumferences(mesh: trimesh.Trimesh, step_m: float = 0.005) -> dict[str, tuple[float, float]]:
    """Search-based landmarks on a standing body: name -> (circumference cm, height m).

    chest = max torso girth in 69-74% of stature, waist = min in 56-69%, hip = max in
    46-56%. Bands are project choices, documented so results are reproducible. In MHR's
    A-pose rest the arms merge with the torso at ~75% of stature, so chest stops at 74%.
    """
    lo, hi = mesh.bounds[:, 1]
    H = hi - lo
    bands = {"chest": (0.69, 0.74, max), "waist": (0.56, 0.69, min), "hip": (0.46, 0.56, max)}
    out = {}
    for name, (a, b, pick) in bands.items():
        ys = np.arange(lo + a * H, lo + b * H, step_m)
        vals = [(torso_circumference(mesh, y), y) for y in ys]
        out[name] = pick((v for v in vals if v[0] > 0), key=lambda v: v[0])
    return out


def height_cm(mesh: trimesh.Trimesh) -> float:
    lo, hi = mesh.bounds[:, 1]
    return float(hi - lo) * 100.0


def ellipse_perimeter(a: float, b: float) -> float:
    """Ramanujan II approximation; exact enough (<1e-5 rel) for body-sized ellipses."""
    h = ((a - b) / (a + b)) ** 2
    return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
