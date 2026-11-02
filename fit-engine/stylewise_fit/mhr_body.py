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
# Sex cue: shoulder-joint distance / hip breadth on the mesh. ANSUR II biacromial/hip breadth
# medians are 1.037 (F) and 1.204 (M). Assuming MHR's mean body sits midway between them, its
# mesh ratio 0.914 maps to 1.12, giving mesh targets F 0.846, M 0.983. Calibration assumption.
SHOULDER_HIP_TARGET = {"female": 0.846, "male": 0.983}
# ANSUR II median hip - bust girth (cm): the hip a typical body of that sex has at a given bust
TYPICAL_HIP_MINUS_BUST = {"female": 7.7, "male": -3.7}
SHAPE_RATIO_WEIGHT = 100.0


def shoulder_hip_target(sex: str, bust_cm: float, hip_cm: float) -> float:
    """Sex target adjusted for the shape's own hips (hip breadth ~ hip girth): narrow-hipped
    shapes (inverted triangle) get broader-looking shoulders, wide-hipped ones narrower."""
    typical_hip = bust_cm + TYPICAL_HIP_MINUS_BUST[sex]
    return SHOULDER_HIP_TARGET[sex] * typical_hip / hip_cm
PRIOR_WEIGHT = 2.0  # cm of residual per unit coeff; project choice
_DEFAULT = Path(__file__).resolve().parents[2] / "research/MHR/assets/mhr_model.pt"


@lru_cache(maxsize=1)
def _model():
    torch.set_num_threads(1)  # one body per worker process; parallelise across processes
    m = torch.jit.load(os.environ.get("MHR_MODEL_PATH", str(_DEFAULT)))
    return m, m.character_torch.mesh.faces.numpy()


def mesh_for(coeffs: np.ndarray, height_target_cm: float | None = None,
             bones: dict[int, float] | None = None) -> trimesh.Trimesh:
    """bones: optional MHR model-parameter values (e.g. per-bone scales, see experiments/height_bones.py).
    The global scale to height_target_cm is applied after them."""
    model, faces = _model()
    g = torch.zeros(1, 45)
    g[0, :N_SHAPE] = torch.as_tensor(coeffs, dtype=torch.float32)
    mp = torch.zeros(1, 204)
    for i, val in (bones or {}).items():
        mp[0, i] = val
    with torch.no_grad():
        v, skel = model(g, mp, torch.zeros(1, 72))
    verts = v[0].numpy() / 100.0  # cm -> m
    verts[:, 1] -= verts[:, 1].min()  # feet on floor
    scale = 1.0
    if height_target_cm is not None:
        scale = (height_target_cm / 100.0) / verts[:, 1].max()
        verts *= scale
    mesh = trimesh.Trimesh(verts, faces, process=False)
    sh = skel[0, list(ARM_ROOT_JOINTS), :3].numpy() / 100.0
    mesh.metadata["shoulder_m"] = float(np.linalg.norm(sh[0] - sh[1])) * scale  # joint centres
    return mesh


def shoulder_hip_ratio(mesh: trimesh.Trimesh) -> float:
    """Shoulder-joint distance / hip breadth (arm-free slice at the buttock vertex). A sex cue."""
    y = mesh.vertices[LANDMARK_VERTS["buttock"], 1]
    seg, fi = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, y, 0], return_faces=True)
    x = seg[~_arm_faces()[fi]].reshape(-1, 3)[:, 0]
    return mesh.metadata["shoulder_m"] / float(x.max() - x.min())


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
        x0: np.ndarray | None = None, bones: dict[int, float] | None = None) -> dict:
    """target: height/chest/waist/hip in cm -> coeffs, achieved measurements, errors, mesh.
    x0: warm start (e.g. a previous fit's coeffs); defaults to MHR's mean body.

    A strong prior pulls toward MHR's mean (rectangle-like) body; extreme shapes such as
    hourglass/oval need a weaker one to reach their targets.
    """
    def residuals(c):
        mesh = mesh_for(c, target["height"], bones)
        m = measure(mesh)
        extra = []
        if "shoulder_hip" in target:  # optional sex cue; 0.01 of ratio weighs like 1 cm of girth
            extra = [SHAPE_RATIO_WEIGHT * (shoulder_hip_ratio(mesh) - target["shoulder_hip"])]
        return np.concatenate([[m[k] - target[k] for k in REGIONS], extra, prior_weight * c])

    def jac(c, step=0.05):
        # explicit forward differences: scipy's built-in 2-point jac returned zero at c=0
        # (gtol stop after 1 eval). Step is large enough to cross the 5 mm slice grid.
        r0 = residuals(c)
        return np.stack([(residuals(c + step * e) - r0) / step for e in np.eye(len(c))], 1)

    t0 = time.time()
    start = np.zeros(N_SHAPE) if x0 is None else np.asarray(x0, dtype=float)
    res = least_squares(residuals, start, jac=jac, max_nfev=max_nfev)
    mesh = mesh_for(res.x, target["height"], bones)
    got = {k: float(v) for k, v in (measure(mesh) | {"shoulder_hip": shoulder_hip_ratio(mesh)}).items()}
    return {
        "coeffs": res.x,
        "measured": got,
        "error": {k: got[k] - target[k] for k in ("height", *REGIONS)},
        "nfev": res.nfev,
        "seconds": time.time() - t0,
        "mesh": mesh,
    }
