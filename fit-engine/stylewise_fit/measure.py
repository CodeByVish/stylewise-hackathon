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


def height_cm(mesh: trimesh.Trimesh) -> float:
    lo, hi = mesh.bounds[:, 1]
    return float(hi - lo) * 100.0


def ellipse_perimeter(a: float, b: float) -> float:
    """Ramanujan II approximation; exact enough (<1e-5 rel) for body-sized ellipses."""
    h = ((a - b) / (a + b)) ** 2
    return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
