"""Garment-on-body fit view: a fit shell over an MHR preset, coloured by verdict.

  python scripts/render_fit.py female_rectangle_M_165 green-kurta:M gold-trousers:M
  python scripts/render_fit.py male_rectangle_L_175 uniqlo-crew-tee:L --out ../fixtures/fits

Each garment is drawn as the body surface pushed outward by that garment's ease at each
height (girth difference e cm -> radial offset e / 2pi), so the gap you see is the room the
size chart gives. It is NOT cloth simulation: no drape, folds or gravity. Colours come from
the FitReport verdicts. Writes <name>.png (front/side/back) and <name>.glb (body + shells,
vertex-coloured) for the viewer. Needs matplotlib.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from shapely.geometry import LineString, MultiPoint  # noqa: E402

from stylewise_fit.catalogue import catalogue, garment_input  # noqa: E402
from stylewise_fit.fit import evaluate  # noqa: E402
from stylewise_fit.measure import girth_excluding  # noqa: E402
from stylewise_fit.schemas import BodyInput, FitRequest  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ARM_FACES = np.load(Path(__file__).resolve().parents[1] / "stylewise_fit/data/mhr_arm_faces.npy")
BUST_VERT, BUTTOCK_VERT = 6034, 7323  # mhr_body.LANDMARK_VERTS (kept here so torch is not needed)
VIEWS = {"front": ((1, 0), (1, 2)), "side": ((-1, 2), (1, 0)), "back": ((-1, 0), (-1, 2))}
SKIN = np.array([0.80, 0.72, 0.66])
VERDICT_RGB = {"ok": (0.30, 0.62, 0.42), "borderline": (0.90, 0.62, 0.15), "tight": (0.82, 0.22, 0.20),
               "loose": (0.30, 0.48, 0.82), "unknown": (0.62, 0.62, 0.62)}
COLOURS = {"green": (0.30, 0.52, 0.36), "emerald": (0.10, 0.45, 0.32), "gold": (0.80, 0.64, 0.25),
           "ivory": (0.93, 0.90, 0.80), "cream": (0.91, 0.86, 0.72), "navy": (0.16, 0.20, 0.38),
           "maroon": (0.45, 0.12, 0.18), "blush": (0.93, 0.74, 0.72), "charcoal": (0.27, 0.27, 0.29),
           "black": (0.12, 0.12, 0.13), "evening": (0.38, 0.18, 0.40), "premium": (0.60, 0.15, 0.25)}
DEFAULT_COLOUR = (0.45, 0.50, 0.58)
# cut by item: (hem as fraction of stature, sleeve length m from the top of the shoulder,
# layer 0 = worn under / 1 = over, skirt flare at the hem in cm or None = follows the legs,
# legs_to = fraction of stature trousers reach under a skirted top, for sets). Typical cuts.
CUTS = {
    "kurta": (0.33, 0.30, 1, 6, None), "set": (0.33, 0.30, 1, 6, 0.06), "trousers": (0.06, 0.0, 0, None, None),
    "silk-skirt": (0.30, 0.0, 0, 14, None), "pencil": (0.36, 0.0, 0, 0, None), "blouse": (0.45, 0.55, 1, 2, None),
    "shell": (0.47, 0.0, 1, 1, None), "tee": (0.46, 0.14, 1, 1, None), "wrap": (0.30, 0.14, 1, 8, None),
    "midi": (0.22, 0.0, 1, 6, None), "long": (0.10, 0.0, 1, 10, None), "dress": (0.30, 0.14, 1, 8, None),
}
NECKLINE = 0.82  # garments stop below the neck


def cut_for(gid: str, name: str, category: str) -> tuple:
    key = next((k for k in CUTS if k in gid or k in name.lower()), None)
    if key is None:
        key = {"top": "tee", "bottom": "trousers", "outfit": "set"}.get(category, "dress")
    return CUTS[key]


def colour_for(name: str) -> np.ndarray:
    return np.array(next((c for k, c in COLOURS.items() if k in name.lower()), DEFAULT_COLOUR))


def landmark_heights(mesh: trimesh.Trimesh) -> dict[str, float]:
    y_bust, y_hip = mesh.vertices[BUST_VERT, 1], mesh.vertices[BUTTOCK_VERT, 1]
    gap = y_bust - y_hip
    ys = np.arange(y_hip + 0.15 * gap, y_bust - 0.15 * gap, 0.005)
    y_waist = min(ys, key=lambda y: girth_excluding(mesh, y, ARM_FACES))
    return {"chest": y_bust, "waist": y_waist, "hip": y_hip}


def sleeve_faces(body: trimesh.Trimesh, length_m: float) -> np.ndarray:
    """Arm faces within length_m of the top of each shoulder (per side)."""
    keep = np.zeros(len(body.faces), bool)
    if length_m <= 0:
        return keep
    centroids = body.triangles_center
    arm_v = np.unique(body.faces[ARM_FACES])
    for side in (-1, 1):
        v = arm_v[np.sign(body.vertices[arm_v, 0]) == side]
        top = body.vertices[v[body.vertices[v, 1].argmax()]]
        on_side = ARM_FACES & (np.sign(centroids[:, 0]) == side)
        keep |= on_side & (np.linalg.norm(centroids - top, axis=1) <= length_m)
    return keep


def skirt_tube(body: trimesh.Trimesh, y_top: float, y_hem: float, offset_m: float, flare_m: float,
               n: int = 72, rings: int = 28) -> trimesh.Trimesh:
    """One tube hanging around both legs: per height, the convex hull of the body slice (a tape
    around the hips/thighs) grown by the hip ease, flaring linearly to the hem."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    verts = []
    for t, y in zip(np.linspace(0, 1, rings), np.linspace(y_top, y_hem, rings)):
        seg, fi = trimesh.intersections.mesh_plane(body, [0, 1, 0], [0, y, 0], return_faces=True)
        pts = seg[~ARM_FACES[fi]].reshape(-1, 3)[:, [0, 2]]
        hull = MultiPoint(pts).convex_hull.buffer(offset_m + flare_m * t)
        c = np.array(hull.centroid.coords[0])
        ring = []
        for a in angles:  # ray from the centroid to the hull edge, same angles on every ring
            ray = LineString([c, c + 2.0 * np.array([np.cos(a), np.sin(a)])])
            hit = hull.exterior.intersection(ray)
            q = np.array(hit.coords[0] if hit.geom_type == "Point" else list(hit.geoms)[0].coords[0])
            ring.append([q[0], y, q[1]])
        verts.extend(ring)
    faces = []
    for i in range(rings - 1):
        for j in range(n):
            p0, p1 = i * n + j, i * n + (j + 1) % n
            faces += [[p0, p1 + n, p0 + n], [p0, p1, p1 + n]]
    tube = trimesh.Trimesh(np.array(verts), np.array(faces), process=False)
    tube.fix_normals()
    return tube


def shell(body: trimesh.Trimesh, report, gid: str, name: str, category: str, lm: dict[str, float]):
    """Garment in its own colour: body offset by ease above the hip; below it a hanging skirt
    tube (dresses, skirts, kurtas) or leg-following legs (trousers)."""
    H = body.bounds[1, 1]
    hem, sleeve_m, layer, flare, legs_to = cut_for(gid, name, category)
    top = lm["waist"] / H + 0.02 if category == "bottom" else NECKLINE
    regions = [(r, lm[r]) for r in ("hip", "waist", "chest") if report.regions[r].ease_cm is not None]
    if not regions:
        return None
    hs = np.array([h for _, h in regions])
    eases = np.array([report.regions[r].ease_cm for r, _ in regions])
    lift = 0.004 * layer  # outer layers sit outside inner ones

    def off(e):  # tight garments would sit inside the body: keep them just visible
        return np.maximum(e / (2 * np.pi), 0.3) / 100 + lift

    skirted = flare is not None and hem * H < lm["hip"]
    upper_lo = lm["hip"] if skirted else hem * H
    lo_legs = (legs_to * H) if legs_to else None
    ys = body.vertices[body.faces][:, :, 1]
    keep = ((~ARM_FACES) & (ys.min(1) >= upper_lo) & (ys.max(1) <= top * H)) | sleeve_faces(body, sleeve_m)
    parts = []
    sub = body.submesh([np.where(keep)[0]], append=True)
    sub.vertices = sub.vertices + sub.vertex_normals * off(np.interp(sub.vertices[:, 1], hs, eases))[:, None]
    parts.append(sub)
    if skirted:
        parts.append(skirt_tube(body, lm["hip"] + 0.03, hem * H, float(off(np.interp(lm["hip"], hs, eases))), flare / 100))
    if lo_legs is not None:  # sets: trousers under the kurta's skirt
        legs = (~ARM_FACES) & (ys.min(1) >= lo_legs) & (ys.max(1) <= lm["hip"])
        lg = body.submesh([np.where(legs)[0]], append=True)
        lg.vertices = lg.vertices + lg.vertex_normals * (0.004)
        parts.append(lg)
    mesh = trimesh.util.concatenate(parts)
    return mesh, np.tile(colour_for(name), (len(mesh.vertices), 1)), layer


def draw(ax, layers, view: str) -> None:
    (sx, ix), (sd, idp) = VIEWS[view]
    polys, depth, colors = [], [], []
    for mesh, vrgb in layers:
        tri = mesh.vertices[mesh.faces]
        facing = sd * mesh.face_normals[:, idp]
        k = facing > 0
        polys.append(np.stack([sx * tri[k][:, :, ix], tri[k][:, :, 1]], -1))
        depth.append((sd * tri[k][:, :, idp]).mean(1))
        base = vrgb[mesh.faces[k]].mean(1) if vrgb is not None else np.tile(SKIN, (k.sum(), 1))
        colors.append(base * (0.35 + 0.65 * facing[k])[:, None])
    polys, depth, colors = np.concatenate(polys), np.concatenate(depth), np.concatenate(colors)
    order = np.argsort(depth)
    ax.add_collection(PolyCollection(polys[order], facecolors=colors[order], edgecolors="none"))
    hi = max(m.bounds[1, 1] for m, _ in layers)
    ax.set_xlim(-0.7, 0.7)
    ax.set_ylim(-0.02, hi + 0.03)
    ax.set_aspect("equal")
    ax.axis("off")


def fit_body(preset_id: str, specs: list[str], fit_pref: str | None):
    entry = next(r for r in json.loads((ROOT / "fixtures/presets/index.json").read_text()) if r["id"] == preset_id)
    body = trimesh.load(ROOT / entry["mesh_ref"], force="mesh", process=False)
    m = entry["measured_cm"]  # the mesh's own girths, so ease matches what is drawn
    body_in = BodyInput(height_cm=m["height"], chest_cm=round(m["chest"], 1),
                        waist_cm=round(m["waist"], 1), hip_cm=round(m["hip"], 1))
    lm = landmark_heights(body)
    garments, marks, lines = [], [], []
    for spec in specs:
        gid, size = spec.split(":")
        report = evaluate(FitRequest(body=body_in, garment=garment_input(gid, size), preferences={"fit_pref": fit_pref}))
        item = catalogue()[gid]
        s = shell(body, report, gid, item["name"], item["category"], lm)
        if s:
            garments.append((s[2], s[0], s[1], spec))
        for r, v in report.regions.items():
            if v.ease_cm is not None:
                marks.append((lm[r], f"{item['name'].split(' (')[0]} {size} · {r} {v.ease_cm:+.0f} cm {v.verdict}", v.verdict))
        lines.append(f"{item['name']} {size}" + ("  (unverified chart)" if report.warnings else ""))
    garments.sort(key=lambda g: g[0])  # under-layers first
    layers = [(body, None)] + [(g[1], g[2]) for g in garments]
    title = f"{entry['display_name']} · {entry['usual_size']} · {m['height']:.0f} cm  " \
            f"(chest {m['chest']:.0f} / waist {m['waist']:.0f} / hip {m['hip']:.0f})"
    return layers, ["body"] + [g[3] for g in garments], marks, lines, title


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("presets", help="preset id(s), comma-separated: one row per body")
    p.add_argument("garments", nargs="+", help="garment_id:size, e.g. green-kurta:M")
    p.add_argument("--out", type=Path, default=ROOT / "fixtures/fits")
    p.add_argument("--fit-pref", default=None, choices=["snug", "regular", "relaxed"])
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    presets = a.presets.split(",")
    fig, axes = plt.subplots(len(presets), 3, figsize=(11, 4.4 * len(presets)), dpi=110, squeeze=False)
    name = ("multi" if len(presets) > 1 else presets[0]) + "__" + "+".join(g.replace(":", "_") for g in a.garments)
    for row, pid in zip(axes, presets):
        layers, labels, marks, lines, title = fit_body(pid, a.garments, a.fit_pref)
        for ax, view in zip(row, VIEWS):
            draw(ax, layers, view)
            ax.set_title(view, fontsize=8, color="#555")
        # where the engine measured: dashed line + verdict label beside the front view
        last = None
        for h, text, verdict in sorted(marks, key=lambda m: -m[0]):
            row[0].plot([-0.35, 0.35], [h, h], ls="--", lw=0.8, color=VERDICT_RGB[verdict])
            ty = h if last is None else min(h, last - 0.045)  # keep labels from overlapping
            row[0].text(-0.72, ty, text, ha="right", va="center", fontsize=6.5, color=VERDICT_RGB[verdict])
            last = ty
        row[1].set_title(f"{title}\n" + "; ".join(lines), fontsize=8)
        if len(presets) == 1:
            scene = trimesh.Scene()
            for j, (mesh, rgb) in enumerate(layers):
                mm = mesh.copy()
                mm.visual.vertex_colors = (np.tile(SKIN, (len(mm.vertices), 1)) if rgb is None else rgb) * 255
                scene.add_geometry(mm, node_name=labels[j])
            scene.export(a.out / f"{name}.glb")
    fig.legend(handles=[Patch(color=c, label=k) for k, c in VERDICT_RGB.items() if k != "unknown"],
               loc="lower center", ncol=4, fontsize=7, frameon=False,
               title="Dashed lines: where the fit was measured (garment colours are the garments)", title_fontsize=7)
    fig.savefig(a.out / f"{name}.png", bbox_inches="tight", facecolor="white")
    print("->", a.out / f"{name}.png")


if __name__ == "__main__":
    main()
