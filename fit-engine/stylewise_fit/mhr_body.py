"""MHR body generation and inverse fitting from girths + height. Requires torch (research env).

Model path: $MHR_MODEL_PATH, else research/MHR/assets/mhr_model.pt under the repo root.
Height is matched with a uniform global scale (identity coeffs do not change stature).
"""
import os
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
import trimesh
from scipy.optimize import least_squares

from .measure import girth_excluding, height_cm

N_SHAPE = 20  # first 20 of 45 identity coeffs control the body (rest: head, hands)
REGIONS = ("chest", "waist", "hip")
# MHR LOD1 vertex ids, picked on the neutral body: bust point = most anterior torso vertex
# 4-16 cm off-centre at 70-82% of stature (lands at 73.9%); buttock = most posterior torso
# vertex at 42-60% (lands at 55.8%). ISO 8559-1 measures bust and hip girth at these points.
LANDMARK_VERTS = {"bust_point": 6034, "buttock": 7323}
ARM_ROOT_JOINTS = (39, 75)  # shoulders; clavicles (38, 74) stay with the torso
PRIOR_WEIGHT = 2.0  # cm of residual per unit coeff; project choice
_DEFAULT = Path(__file__).resolve().parents[2] / "research/MHR/assets/mhr_model.pt"


@lru_cache(maxsize=1)
def _model():
    torch.set_num_threads(1)  # one body per worker process; parallelise across processes
    m = torch.jit.load(os.environ.get("MHR_MODEL_PATH", str(_DEFAULT)))
    return m, m.character_torch.mesh.faces.numpy()


def mesh_for(coeffs: np.ndarray, height_target_cm: float | None = None) -> trimesh.Trimesh:
    model, faces = _model()
    g = torch.zeros(1, 45)
    g[0, :N_SHAPE] = torch.as_tensor(coeffs, dtype=torch.float32)
    with torch.no_grad():
        v, _ = model(g, torch.zeros(1, 204), torch.zeros(1, 72))
    verts = v[0].numpy() / 100.0  # cm -> m
    verts[:, 1] -= verts[:, 1].min()  # feet on floor
    if height_target_cm is not None:
        verts *= (height_target_cm / 100.0) / verts[:, 1].max()
    return trimesh.Trimesh(verts, faces, process=False)


@lru_cache(maxsize=1)
def _arm_faces() -> np.ndarray:
    """Faces whose vertices are mostly driven by a shoulder joint or anything below it."""
    model, faces = _model()
    lbs = model.character_torch.linear_blend_skinning
    parents = model.character_torch.skeleton.joint_parents.numpy()
    arm = set(ARM_ROOT_JOINTS)
    for j, p in enumerate(parents):  # joints are stored parent-first
        if p in arm:
            arm.add(j)
    W = np.zeros((int(lbs.vert_indices_flattened.max()) + 1, len(parents)))
    np.add.at(W, (lbs.vert_indices_flattened.numpy(), lbs.skin_indices_flattened.numpy()),
              lbs.skin_weights_flattened.numpy())
    return np.isin(W.argmax(1), list(arm))[faces].any(1)


def landmarks(mesh: trimesh.Trimesh, step_m: float = 0.005) -> dict[str, tuple[float, float]]:
    """ISO 8559-1-style landmarks on an MHR mesh: name -> (girth cm, height m).

    bust/chest = girth at the bust-point vertex; hip = girth at the most posterior buttock
    vertex; waist = narrowest girth between them (15% margins keep it off both). Vertex ids
    hold for every MHR body because the topology is fixed. Arm faces are excluded.
    """
    y_bust = mesh.vertices[LANDMARK_VERTS["bust_point"], 1]
    y_hip = mesh.vertices[LANDMARK_VERTS["buttock"], 1]
    gap = y_bust - y_hip
    ys = np.arange(y_hip + 0.15 * gap, y_bust - 0.15 * gap, step_m)
    waist = min(((girth_excluding(mesh, y, _arm_faces()), y) for y in ys), key=lambda v: v[0])
    return {"chest": (girth_excluding(mesh, y_bust, _arm_faces()), y_bust), "waist": waist,
            "hip": (girth_excluding(mesh, y_hip, _arm_faces()), y_hip)}


def measure(mesh: trimesh.Trimesh) -> dict[str, float]:
    lm = landmarks(mesh)
    return {"height": height_cm(mesh), **{k: lm[k][0] for k in REGIONS}}


def fit(target: dict[str, float], max_nfev: int = 15, prior_weight: float = PRIOR_WEIGHT,
        x0: np.ndarray | None = None) -> dict:
    """target: height/chest/waist/hip in cm -> coeffs, achieved measurements, errors, mesh.
    x0: warm start (e.g. a previous fit's coeffs); defaults to MHR's mean body.

    A strong prior pulls toward MHR's mean (rectangle-like) body; extreme shapes such as
    hourglass/oval need a weaker one to reach their targets.
    """
    def residuals(c):
        m = measure(mesh_for(c, target["height"]))
        return np.concatenate([[m[k] - target[k] for k in REGIONS], prior_weight * c])

    def jac(c, step=0.05):
        # explicit forward differences: scipy's built-in 2-point jac returned zero at c=0
        # (gtol stop after 1 eval). Step is large enough to cross the 5 mm slice grid.
        r0 = residuals(c)
        return np.stack([(residuals(c + step * e) - r0) / step for e in np.eye(len(c))], 1)

    t0 = time.time()
    start = np.zeros(N_SHAPE) if x0 is None else np.asarray(x0, dtype=float)
    res = least_squares(residuals, start, jac=jac, max_nfev=max_nfev)
    mesh = mesh_for(res.x, target["height"])
    got = measure(mesh)
    return {
        "coeffs": res.x,
        "measured": got,
        "error": {k: got[k] - target[k] for k in ("height", *REGIONS)},
        "nfev": res.nfev,
        "seconds": time.time() - t0,
        "mesh": mesh,
    }
