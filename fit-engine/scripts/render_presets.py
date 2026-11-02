"""Render preset GLBs to PNGs: front/side/back per preset, plus a shape x size contact sheet.

  python scripts/render_presets.py --presets ../fixtures/presets --out ../fixtures/presets/renders

Needs matplotlib (not a runtime dependency). Flat-shaded orthographic views drawn with the
painter's algorithm, so no OpenGL is required. Dashed lines mark the measured chest, waist
and hip slices from stylewise_fit.measure, i.e. exactly where the fit engine measured.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from stylewise_fit.measure import landmark_circumferences  # noqa: E402
from stylewise_fit.presets import SIZES  # noqa: E402

# view name -> (screen-x axis sign/index, depth axis sign/index); body faces +Z
VIEWS = {"front": ((1, 0), (1, 2)), "side": ((-1, 2), (1, 0)), "back": ((-1, 0), (-1, 2))}
LANDMARK_COLORS = {"chest": "#d1495b", "waist": "#edae49", "hip": "#00798c"}
SKIN = np.array([0.80, 0.72, 0.66])


def draw(ax, mesh: trimesh.Trimesh, view: str, landmarks: dict | None = None) -> None:
    (sx, ix), (sd, idp) = VIEWS[view]
    tri = mesh.vertices[mesh.faces]
    x, y, depth = sx * tri[:, :, ix], tri[:, :, 1], sd * tri[:, :, idp]
    normal_toward_viewer = sd * mesh.face_normals[:, idp]
    keep = normal_toward_viewer > 0  # back-face culling
    order = np.argsort(depth[keep].mean(1))  # far to near
    shade = 0.35 + 0.65 * normal_toward_viewer[keep][order]
    polys = np.stack([x[keep], y[keep]], -1)[order]
    ax.add_collection(PolyCollection(polys, facecolors=SKIN * shade[:, None], edgecolors="none"))
    if landmarks:
        for name, (_, h) in landmarks.items():
            ax.axhline(h, color=LANDMARK_COLORS[name], lw=1, ls="--")
    lo, hi = mesh.bounds
    ax.set_xlim(-0.7, 0.7)
    ax.set_ylim(-0.02, hi[1] + 0.03)
    ax.set_aspect("equal")
    ax.axis("off")


def render_one(r: dict, presets: Path, out: Path) -> None:
    mesh = trimesh.load(presets / Path(r["mesh_ref"]).name, force="mesh")
    lm = landmark_circumferences(mesh)
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 3.6), dpi=110)
    for ax, view in zip(axes, VIEWS):
        draw(ax, mesh, view, lm)
        ax.set_title(view, fontsize=8, color="#555")
    t, m, e = r["target_cm"], r["measured_cm"], r["fit_error_cm"]
    lines = [f"{k}: target {t[k]:.1f}  got {m[k]:.1f}  ({e[k]:+.2f})" for k in ("chest", "waist", "hip")]
    ok = "ok" if r["ffit_class_of_mesh"] == r["shape"] else f"MISMATCH -> {r['ffit_class_of_mesh']}"
    fig.suptitle(f"{r['id']}  ·  {r['display_name']}  ·  FFIT {ok}", fontsize=9)
    fig.text(0.5, 0.02, "   |   ".join(lines), ha="center", fontsize=7, color="#333")
    fig.savefig(out / f"{r['id']}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def contact_sheet(rows: list[dict], presets: Path, out: Path, sex: str, height: float) -> None:
    shapes = list(dict.fromkeys(r["shape"] for r in rows))
    sizes = [z for z in SIZES if any(r["usual_size"] == z for r in rows)]
    by = {(r["shape"], r["usual_size"]): r for r in rows}
    fig, axes = plt.subplots(len(shapes), len(sizes), figsize=(1.5 * len(sizes), 2.4 * len(shapes)), dpi=110,
                             squeeze=False)
    for i, s in enumerate(shapes):
        for j, z in enumerate(sizes):
            ax = axes[i][j]
            r = by.get((s, z))
            if r is None:
                ax.axis("off")
                continue
            draw(ax, trimesh.load(presets / Path(r["mesh_ref"]).name, force="mesh"), "front")
            worst = max(abs(r["fit_error_cm"][k]) for k in ("chest", "waist", "hip"))
            bad = r["ffit_class_of_mesh"] != s
            ax.set_title(f"{z}  ±{worst:.1f}" + ("  ✗" if bad else ""), fontsize=7,
                         color="#c00" if bad or worst > r["uncertainty_cm"] else "#333")
            if j == 0:
                ax.text(-0.75, 0.85, r["display_name"], rotation=90, va="center", fontsize=8)
    fig.suptitle(f"{sex} presets at {height:.0f} cm (front, worst girth error in cm)", fontsize=10)
    fig.savefig(out / f"sheet_{sex}_{int(height)}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--presets", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--sheets-only", action="store_true")
    a = p.parse_args()
    out = a.out or a.presets / "renders"
    out.mkdir(parents=True, exist_ok=True)
    index = json.loads((a.presets / "index.json").read_text())
    groups = defaultdict(list)
    for r in index:
        groups[(r.get("sex", "female"), r["target_cm"]["height"])].append(r)
    for (sex, h), rows in sorted(groups.items()):
        contact_sheet(rows, a.presets, out, sex, h)
        print("sheet", sex, h, flush=True)
    if not a.sheets_only:
        for r in index:
            render_one(r, a.presets, out)
        print(f"{len(index)} preset renders -> {out}")


if __name__ == "__main__":
    main()
