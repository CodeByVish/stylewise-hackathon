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
from scipy import sparse  # noqa: E402
from shapely.affinity import scale as shapely_scale  # noqa: E402
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
# Default cut per garment type (typical values, not measured). A catalogue item can override any key
# with its own "cut" entry, e.g. from its product photo or listing:
#   hem: fraction of stature; sleeve_m: sleeve length from the top of the shoulder; layer: 0 under / 1 over;
#   flare_cm: extra girth at the hem (None = follows the legs, i.e. trousers); legs_to: trousers under a set;
#   openings: [{"at": "sides" | "back" | "front", "from": "hip" | "waist" | <cm above hem>, "width_cm": w}]
#   - an even V, 0 cm wide at its top, w cm wide at the hem, measured along the hem line.
#   neck: one of NECKLINES (front and back are cut separately).
CUTS = {
    "kurta": {"hem": 0.33, "sleeve_m": 0.30, "layer": 1, "flare_cm": 6, "neck": "round",
              "openings": [{"at": "sides", "from": "hip", "width_cm": 12}]},
    "set": {"hem": 0.33, "sleeve_m": 0.30, "layer": 1, "flare_cm": 6, "legs_to": 0.06, "neck": "v",
            "openings": [{"at": "sides", "from": "hip", "width_cm": 12}]},
    "trousers": {"hem": 0.06, "layer": 0},
    "silk-skirt": {"hem": 0.30, "layer": 0, "flare_cm": 14},
    "pencil": {"hem": 0.36, "layer": 0, "flare_cm": 0, "openings": [{"at": "back", "from": 18, "width_cm": 5}]},
    "blouse": {"hem": 0.45, "sleeve_m": 0.55, "layer": 1, "flare_cm": 2, "neck": "collar"},
    "shell": {"hem": 0.47, "layer": 1, "flare_cm": 1, "neck": "round"},
    "tee": {"hem": 0.46, "sleeve_m": 0.14, "layer": 1, "flare_cm": 1, "neck": "crew"},
    "wrap": {"hem": 0.30, "sleeve_m": 0.14, "layer": 1, "flare_cm": 8, "neck": "v"},  # skirt overlaps: no gap
    "midi": {"hem": 0.22, "layer": 1, "flare_cm": 6, "neck": "boat", "openings": [{"at": "back", "from": 20, "width_cm": 6}]},
    "long": {"hem": 0.10, "layer": 1, "flare_cm": 10, "neck": "round"},
    "dress": {"hem": 0.30, "sleeve_m": 0.14, "layer": 1, "flare_cm": 8, "neck": "round"},
    # men's kurta: closed band (mandarin) collar with a short front placket, straight side slits
    "mens-kurta": {"hem": 0.33, "sleeve_m": 0.55, "layer": 1, "flare_cm": 4, "neck": "collar",
                   "openings": [{"at": "sides", "from": "hip", "width_cm": 10}]},
}
NECKLINE = 0.86  # top of the torso shell: the base of the neck
SHOULDER_LINE = 0.80  # hanging garments are one piece from here down (just under the armpits)
# neckline shape: (front depth cm, back depth cm, half-width cm, shape exponent: 1 = V, 2 = round,
# 4+ = flat/boat), measured down from the base of the neck; collar adds a 3 cm band up the neck
NECKLINES = {"crew": (5, 2, 8, 2), "round": (9, 3, 10, 2), "v": (16, 3, 9, 1), "boat": (4, 4, 15, 6),
             "collar": (5, 2, 8, 2)}  # a mandarin collar reads as a close crew line: no standing ring


def waistband(lm: dict[str, float]) -> float:
    """Height where trousers and briefs sit: the natural waist, ~1/3 from the hip line to the bust."""
    return lm["hip"] + 0.35 * (lm["chest"] - lm["hip"])


def band(mesh: trimesh.Trimesh, y_low: float, y_high: float) -> trimesh.Trimesh:
    """Keep the part of mesh between two horizontal planes, cutting triangles exactly on the planes:
    straight waistbands and hems instead of the triangle-staircase of whole-face selection."""
    mesh = mesh.slice_plane([0, y_low, 0], [0, 1, 0])
    return mesh.slice_plane([0, y_high, 0], [0, -1, 0])


def cut_for(gid: str, name: str, category: str) -> dict:
    key = next((k for k in CUTS if k in gid or k in name.lower()), None)
    if key is None:
        key = {"top": "tee", "bottom": "trousers", "outfit": "set"}.get(category, "dress")
    cut = {"sleeve_m": 0.0, "flare_cm": None, "legs_to": None, "openings": [], "neck": "round"} | CUTS[key]
    return cut | (catalogue().get(gid, {}).get("cut") or {})  # per-garment override wins


def below_neckline(body: trimesh.Trimesh, style: str) -> np.ndarray:
    """Faces under the neckline. Front (+Z) and back are cut to different depths."""
    H = body.bounds[1, 1]
    front_d, back_d, half_w, p = NECKLINES.get(style, NECKLINES["round"])
    c = body.triangles_center
    depth = np.where(c[:, 2] > 0, front_d, back_d) / 100
    open_y = NECKLINE * H - depth * np.clip(1 - (np.abs(c[:, 0]) / (half_w / 100)) ** p, 0, 1)
    return c[:, 1] <= open_y


def collar_band(body: trimesh.Trimesh, offset_m: float) -> trimesh.Trimesh:
    """A 3 cm band collar standing up around the base of the neck."""
    H = body.bounds[1, 1]
    return skirt_tube(body, NECKLINE * H + 0.02, NECKLINE * H - 0.005, offset_m, 0.0, n=72, rings=4)


def colour_for(name: str, gid: str | None = None) -> np.ndarray:
    """The product photo's garment colour when we have it, else a colour word in the name."""
    rgb = catalogue().get(gid, {}).get("rgb") if gid else None
    if rgb:
        return np.array(rgb)
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


def sleeves(body: trimesh.Trimesh, base: trimesh.Trimesh, length_m: float, offset_m: float) -> list:
    """Each sleeve as its own piece: arm faces up to length_m along the arm from the top of the
    shoulder, offset, then cut by a plane across the arm (a straight cuff). The length is capped at
    70% of shoulder-to-fingertip, i.e. before the wrist, so a sleeve never wraps the hand."""
    if length_m <= 0:
        return []
    out = []
    arm_v = np.unique(body.faces[ARM_FACES])
    for side in (-1, 1):
        v = arm_v[np.sign(body.vertices[arm_v, 0]) == side]
        top = body.vertices[v[body.vertices[v, 1].argmax()]]
        tip = body.vertices[v[np.abs(body.vertices[v, 0]).argmax()]]  # fingertip: furthest out in x
        axis = (tip - top) / np.linalg.norm(tip - top)
        L = min(length_m, 0.70 * float(np.linalg.norm(tip - top)))
        proj = (body.triangles_center - top) @ axis
        keep = ARM_FACES & (np.sign(body.triangles_center[:, 0]) == side) & (proj <= L + 0.03)
        m = base.submesh([np.where(keep)[0]], append=True)
        m.vertices = m.vertices + m.vertex_normals * offset_m
        m = m.slice_plane(top + axis * L, -axis)  # keep the shoulder side of the cuff plane
        out.append(m)
    return out


def smooth_neckline(sub: trimesh.Trimesh, body: trimesh.Trimesh, style: str) -> trimesh.Trimesh:
    """Snap the open edge around the neck onto the neckline curve, so it reads as a cut neckline
    instead of a triangle staircase (only boundary vertices near the neck move, and only in height)."""
    H = body.bounds[1, 1]
    front_d, back_d, half_w, p = NECKLINES.get(style, NECKLINES["round"])
    edges = sub.edges_sorted
    uniq, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = np.unique(uniq[counts == 1])
    v = sub.vertices.copy()
    x, z = v[boundary, 0], v[boundary, 2]
    depth = np.where(z > 0, front_d, back_d) / 100
    open_y = NECKLINE * H - depth * np.clip(1 - (np.abs(x) / (half_w / 100)) ** p, 0, 1)
    near = np.abs(v[boundary, 1] - open_y) < 0.03  # the neck opening only, not the lower edge
    v[boundary[near], 1] = open_y[near]
    sub.vertices = v
    return sub


def skirt_tube(body: trimesh.Trimesh, y_top: float, y_hem: float, offset_m, flare_m: float,
               n: int = 144, rings: int = 28, flare_from: float | None = None,
               openings: list[dict] | None = None, girth_at=None, fall_from: float | None = None,
               creases: list[tuple[float, float]] | None = None) -> trimesh.Trimesh:
    """A garment that hangs instead of hugging: per height, the convex outline of the body slice
    (like a tape, so it bridges the small of the back, the bust and the gap between the legs) grown
    by the ease at that height. offset_m: metres, or a function of height. flare_m is added linearly
    from flare_from (default: the top) to the hem. openings: resolved V openings
    [{"dirs": [(x, z) unit vectors], "y_from": m, "width_m": m}], cut evenly along the hem line."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ys = np.linspace(y_top, y_hem, rings)
    f0 = y_top if flare_from is None else flare_from
    verts, prev, body_len = [], None, []
    for y in ys:
        seg, fi = trimesh.intersections.mesh_plane(body, [0, 1, 0], [0, y, 0], return_faces=True)
        pts = seg[~ARM_FACES[fi]].reshape(-1, 3)[:, [0, 2]]
        t = float(np.clip((f0 - y) / max(f0 - y_hem, 1e-6), 0, 1))
        off = offset_m(y) if callable(offset_m) else offset_m
        hull = MultiPoint(pts).convex_hull.buffer(float(off) + flare_m * t)
        body_len.append(MultiPoint(pts).convex_hull.buffer(float(off)).length)  # snug outline, for folds
        target = girth_at(y) if girth_at else None
        if target and target > hull.length:  # the garment is bigger than the body here: widen to its size
            k = target / hull.length
            hull = shapely_scale(hull, k, k, origin=hull.centroid)
        # cloth falls straight from the bust down: never narrower than the ring above. Above the bust
        # it follows the body (falling from the shoulders would carry their width down: a box)
        if fall_from is not None and y <= fall_from:
            if prev is not None:
                hull = hull.union(prev).convex_hull
            prev = hull
        c = np.array(hull.centroid.coords[0])
        for a in angles:  # ray from the centroid to the outline, same angles on every ring
            ray = LineString([c, c + 2.0 * np.array([np.cos(a), np.sin(a)])])
            hit = hull.exterior.intersection(ray)
            q = np.array(hit.coords[0] if hit.geom_type == "Point" else list(hit.geoms)[0].coords[0])
            verts.append([q[0], y, q[1]])
    V = np.array(verts).reshape(rings, n, 3)
    # openings (slits, vents): per ring, vertices within half the V's width (arc length from the
    # opening's centre) are open; the first closed vertex each side is snapped exactly onto the V's
    # edge, so the slit is a straight clean line instead of a staircase
    inside = np.zeros((rings, n), bool)
    for r in range(rings):
        y = ys[r]
        ring = V[r]
        seg = np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1)
        centre = ring.mean(0)
        for o in openings or []:
            if y >= o["y_from"]:
                continue
            half = 0.5 * o["width_m"] * (o["y_from"] - y) / max(o["y_from"] - y_hem, 1e-6)
            for d in o["dirs"]:
                k = int(np.argmax((ring[:, [0, 2]] - centre[[0, 2]]) @ np.array(d)))
                rolled = np.roll(seg, -k)
                fwd = np.concatenate([[0], np.cumsum(rolled)[:-1]])  # arc from vertex k going forward
                arc = np.roll(np.minimum(fwd, rolled.sum() - fwd), k)
                inside[r] |= arc < half
                for step in (1, -1):  # snap the first closed vertex each way onto the edge
                    j = k
                    while arc[j] < half and arc[(j + step) % n] >= 0 and (j + step) % n != k:
                        nxt = (j + step) % n
                        if arc[nxt] >= half:
                            t = (half - arc[j]) / max(arc[nxt] - arc[j], 1e-9)
                            V[r, nxt] = V[r, j] + t * (V[r, nxt] - V[r, j])
                            break
                        j = nxt
    V = fit_folds(V, ys, np.array(body_len), fall_from, creases)  # after the slits are cut on the clean shape
    faces = []
    for i in range(rings - 1):
        for j in range(n):
            j1 = (j + 1) % n
            if inside[i, j] or inside[i, j1] or inside[i + 1, j] or inside[i + 1, j1]:
                continue
            p0, p1 = i * n + j, i * n + j1
            faces += [[p0, p1 + n, p0 + n], [p0, p1, p1 + n]]
    tube = trimesh.Trimesh(V.reshape(-1, 3), np.array(faces), process=False)
    pieces = tube.split(only_watertight=False)
    if len(pieces) > 1:  # keep real panels, drop slivers left along slit edges
        big = max(len(q.faces) for q in pieces)
        tube = trimesh.util.concatenate([q for q in pieces if len(q.faces) >= 0.05 * big])
    tube.fix_normals()
    return tube


def fit_folds(V: np.ndarray, ys: np.ndarray, snug_len: np.ndarray, fall_from: float | None,
              creases: list[tuple[float, float]] | None) -> np.ndarray:
    """Folds driven by measured ease, not cloth simulation. Where a ring is longer than the snug
    outline (extra fabric), it gathers into soft vertical folds: amplitude grows with the excess, one
    fold per ~11 cm of girth. Where a region is too small, fine horizontal pull lines appear there."""
    rings, n, _ = V.shape
    out = V.copy()
    lengths = np.array([np.linalg.norm(np.roll(V[r], -1, 0) - V[r], axis=1).sum() for r in range(rings)])
    excess = np.clip(lengths - snug_len, 0, None) / np.maximum(lengths, 1e-9)
    amp = np.minimum(0.022, 0.6 * excess * lengths / (2 * np.pi))
    if fall_from is not None:
        amp[ys > fall_from] = 0.0
    # smooth the fold depth over height (no tiers), and keep one fold count for the whole garment
    k = max(3, rings // 8)
    amp = np.convolve(np.pad(amp, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
    folds = max(4, int(round(np.median(lengths) / 0.11)))
    for r in range(rings):
        ring = V[r]
        centre = ring.mean(0)
        radial = ring - centre
        radial[:, 1] = 0
        unit = radial / np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-9)
        seg = np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1)
        arc = np.concatenate([[0], np.cumsum(seg)[:-1]]) / max(seg.sum(), 1e-9)
        d = amp[r] * (1 - np.cos(2 * np.pi * folds * arc)) * 0.5  # folds bulge outward: never into the body
        for y_c, strength in creases or []:  # tension lines at a too-small region
            w = np.exp(-((ys[r] - y_c) / 0.02) ** 2)
            d = d + strength * w * np.cos(2 * np.pi * (ys[r] - y_c) / 0.012)
        out[r] = ring + unit * d[:, None]
    return out


OPENING_DIRS = {"sides": [(1, 0), (-1, 0)], "back": [(0, -1)], "front": [(0, 1)]}  # body faces +Z


def resolve_openings(cut: dict, lm: dict[str, float], hem_y: float) -> list[dict]:
    out = []
    for o in cut.get("openings") or []:
        top = {"hip": lm["hip"], "waist": waistband(lm)}.get(o["from"])
        y_from = top if top is not None else hem_y + float(o["from"]) / 100
        out.append({"dirs": OPENING_DIRS[o["at"]], "y_from": y_from, "width_m": o["width_cm"] / 100})
    return out


def shell(body: trimesh.Trimesh, report, gid: str, name: str, category: str, lm: dict[str, float]):
    """Garment in its own colour. Bottoms hug the body (offset by ease) from the waistband down;
    tops, dresses, kurtas and sets hang as one piece from the bust to the hem, with flare below the
    hip and side slits for kurtas; shoulders and sleeves follow the body."""
    H = body.bounds[1, 1]
    cut = cut_for(gid, name, category)
    hem, sleeve_m, layer, flare, legs_to = cut["hem"], cut["sleeve_m"], cut["layer"], cut["flare_cm"], cut["legs_to"]
    # a too-small garment cannot be drawn smaller than the body inside it, so show the strain instead:
    # it rides up (hem rises with the shortfall), loses its flare and pulls into tension lines
    short = {r: -report.regions[r].ease_cm for r in ("chest", "waist", "hip")
             if report.regions[r].verdict == "tight" and report.regions[r].ease_cm is not None}
    if short and category != "bottom":
        hem = hem + min(max(short.values()) * 0.004, 0.06)
        flare = 0.0 if flare else flare
    openings = resolve_openings(cut, lm, hem * H)
    regions = [(r, lm[r]) for r in ("hip", "waist", "chest") if report.regions[r].ease_cm is not None]
    if not regions:
        return None
    hs = np.array([h for _, h in regions])
    eases = np.array([report.regions[r].ease_cm for r, _ in regions])
    lift = 0.004 * layer  # outer layers sit outside inner ones

    def off(y):  # tight garments still sit clear of the underwear, so nothing shows through
        return np.maximum(np.interp(y, hs, eases) / (2 * np.pi), 1.5) / 100 + lift

    base = smooth_base(body)
    ys = body.vertices[body.faces][:, :, 1]
    parts = []
    if category == "bottom" and flare is None:  # trousers: follow the legs from the waistband
        # take a margin of whole triangles, offset, then cut with planes: straight waistband and hems
        keep = (~ARM_FACES) & (ys.max(1) >= hem * H - 0.02) & (ys.min(1) <= waistband(lm) + 0.02)
        sub = base.submesh([np.where(keep)[0]], append=True)
        sub.vertices = sub.vertices + sub.vertex_normals * off(sub.vertices[:, 1])[:, None]
        parts.append(band(sub, hem * H, waistband(lm)))
    elif category == "bottom":  # skirts: hang from the waistband
        parts.append(skirt_tube(body, waistband(lm), hem * H, off, (flare or 0) / 100,
                                flare_from=lm["hip"], openings=openings))
    else:
        # hang the whole torso from the shoulder line, so underwear (bra band) and the chest sit
        # entirely inside one smooth piece; only shoulders and sleeves follow the body above it
        tube_top = SHOULDER_LINE * H
        # shoulders and sleeves follow the body above the bust; overlap the tube by 2 cm
        keep = (~ARM_FACES) & (ys.min(1) >= tube_top - 0.06) & below_neckline(body, cut["neck"])
        sub = base.submesh([np.where(keep)[0]], append=True)
        # close to the neck the fabric lies on the body: a full offset there stands off as a ring ("band")
        y = sub.vertices[:, 1]
        near_neck = np.clip((NECKLINE * H - y) / 0.06, 0.3, 1.0)
        sub.vertices = sub.vertices + sub.vertex_normals * (off(y) * near_neck)[:, None]
        sub = smooth_neckline(sub, body, cut["neck"])
        parts.append(sub)
        parts += sleeves(body, base, sleeve_m, 0.012 + lift)
        # rings every ~8 mm: coarser rings cut straight across the bust between rings and let the bra show
        rings = int(np.clip((tube_top - hem * H) / 0.008, 40, 160))
        g_cm = {r: report.regions[r].garment_cm for r in ("chest", "waist", "hip")}
        gh = [(lm[r], g_cm[r] / 100) for r in ("hip", "waist", "chest") if g_cm[r]]

        def girth_at(y):  # the garment's own girth, interpolated between its measured heights
            return float(np.interp(y, [h for h, _ in gh], [g for _, g in gh])) if gh else None

        def clear(y):  # just clearance; looseness comes from the garment girth and the straight fall
            return 0.015 + lift
        creases = [(lm[r], min(0.002 + short[r] * 0.0002, 0.006)) for r in short if r in lm]
        parts.append(skirt_tube(body, tube_top, hem * H, clear, (flare or 0) / 100, rings=rings,
                                flare_from=lm["hip"], openings=openings, girth_at=girth_at, fall_from=lm[cut.get("fall", "waist")],
                                creases=creases))
        if cut.get("belt"):  # tie belt at the natural waist: a raised 3.5 cm band over the garment
            yb = waistband(lm)
            parts.append(skirt_tube(body, yb + 0.0175, yb - 0.0175, lambda y: clear(y) + 0.006, 0.0, rings=6,
                                    girth_at=lambda y: girth_at(y) and girth_at(y) + 0.04))
        # (no separate collar band: it floated off the neckline; "collar" is a higher, closer neckline)
    if legs_to is not None:  # sets: trousers under the kurta
        legs = (~ARM_FACES) & (ys.max(1) >= legs_to * H - 0.02) & (ys.min(1) <= waistband(lm) + 0.02)
        lg = base.submesh([np.where(legs)[0]], append=True)
        lg.vertices = lg.vertices + lg.vertex_normals * 0.011
        parts.append(band(lg, legs_to * H, waistband(lm)))
    mesh = trimesh.util.concatenate(parts)
    return mesh, np.tile(colour_for(name, gid), (len(mesh.vertices), 1)), layer


UNDERWEAR_RGB = np.array([0.36, 0.33, 0.33])
PYJAMA_RGB = {"female": np.array([0.24, 0.25, 0.28]), "male": np.array([0.96, 0.96, 0.94])}  # women: charcoal trousers


def needs_lower(cuts: list[dict], categories: list[str]) -> bool:
    """A kurta (a top with side openings) is never worn bare-legged: add a styling pyjama if no
    bottom or set was chosen."""
    has_bottom = any(c in ("bottom", "outfit") for c in categories)
    return "top" in categories and not has_bottom  # a top is never shown bare-legged


def styling_pyjama(body: trimesh.Trimesh, lm: dict[str, float], sex: str):
    """Plain straight pyjama under a kurta: a styling layer only, NOT fitted (no size chart, not in
    the report). Follows the legs with comfortable room, clean waistband and hems."""
    H = body.bounds[1, 1]
    ys = body.vertices[body.faces][:, :, 1]
    # it only shows below the kurta: stop at the hip and stay close, so it never pokes through the kurta's back
    top = lm["hip"]
    keep = (~ARM_FACES) & (ys.max(1) >= 0.06 * H - 0.02) & (ys.min(1) <= top + 0.02)
    m = smooth_base(body).submesh([np.where(keep)[0]], append=True)
    m.vertices = m.vertices + m.vertex_normals * 0.009
    m = band(m, 0.06 * H, top)
    return m, np.tile(PYJAMA_RGB.get(sex, PYJAMA_RGB["female"]), (len(m.vertices), 1))
_SMOOTH: dict[int, tuple] = {}


def smooth_base(body: trimesh.Trimesh) -> trimesh.Trimesh:
    """The whole closed body, Taubin-smoothed once (volume-preserving): the surface garments and
    underwear are built on, so fabric does not follow muscle definition or anatomy."""
    hit = _SMOOTH.get(id(body))
    if hit is None or hit[0] is not body:
        base = body.copy()
        trimesh.smoothing.filter_taubin(base, lamb=0.5, nu=-0.53, iterations=25)
        # Taubin still shrinks (median ~4 mm, legs ~6 mm): put the low-frequency part of the move
        # back along the normals, so only small bumps (muscle, anatomy) stay smoothed away
        n = base.vertex_normals
        d = np.einsum("ij,ij->i", body.vertices - base.vertices, n)
        e = base.edges_unique
        A = sparse.coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])),
                              shape=(len(d), len(d))).tocsr()
        A = sparse.diags(1 / np.maximum(A.sum(1).A1, 1)) @ A
        for _ in range(40):
            d = A @ d
        base.vertices = base.vertices + n * d[:, None]
        _SMOOTH.clear()
        _SMOOTH[id(body)] = hit = (body, base)
    return hit[1]


def underwear(body: trimesh.Trimesh, lm: dict[str, float], sex: str):
    """Modesty base layer under every garment: briefs on everyone, a bra-style top on women.
    Opaque, 2 mm off the body, smoothed so no anatomy reads through."""
    H = body.bounds[1, 1]
    c = body.triangles_center[:, 1]
    top = waistband(lm) - 0.02 * H
    keep = (~ARM_FACES) & (c >= 0.41 * H) & (c <= top + 0.02)
    # on the real body (groin already smoothed in the presets), 2 mm out: the smoothed base can sit up
    # to ~6 mm outside the body, which put briefs within millimetres of tight garments
    mesh = body.submesh([np.where(keep)[0]], append=True)
    mesh.vertices = mesh.vertices + mesh.vertex_normals * 0.002
    mesh = band(mesh, 0.425 * H, top)  # clean straight waistband and leg openings
    if sex == "female":
        # a bra spans the gap between the breasts: a smooth band around the chest, not skin-tight
        bra = skirt_tube(body, lm["chest"] + 0.012 * H, lm["chest"] - 0.045 * H, 0.004, 0.0, rings=10)
        mesh = trimesh.util.concatenate([mesh, bra])
    return mesh, np.tile(UNDERWEAR_RGB, (len(mesh.vertices), 1))


HAIR_RGB = np.array([0.22, 0.16, 0.12])


def hair(body: trimesh.Trimesh, sex: str):
    """Stylised hair on the shared mannequin head (mhr_body.mannequin_head). Women: a bob, one smooth
    volume around the head with a fringe, a clean face opening and a straight line at the jaw. Men: a
    short crop above the ears. Built in the head's own frame, so it sits the same on every preset."""
    H = body.bounds[1, 1]
    hv = body.vertices[body.vertices[:, 1] > 0.895 * H]
    centre = (hv.max(0) + hv.min(0)) / 2
    axes = (hv.max(0) - hv.min(0)) / 2
    shell = trimesh.creation.icosphere(subdivisions=5)
    if sex == "female":
        # a taller volume than the skull so the bob reaches the jaw; cut at absolute heights
        scale = axes * np.array([1.18, 1.45, 1.16])
        mid = centre + np.array([0, -0.32 * axes[1], -0.008])
        shell.vertices = shell.vertices * scale + mid
        tc = shell.triangles_center
        u = (tc - mid) / scale
        jaw = 0.872 * H  # bob length: chin level all round
        brow = centre[1] + 0.30 * axes[1]
        face = (u[:, 2] > 0.15) & (tc[:, 1] < brow) & (np.abs(u[:, 0]) < 0.66)
        top = u[:, 1] > 0.98  # trim the very crown so the volume does not peak
        keep = (tc[:, 1] > jaw) & ~face & ~top
        shell.vertices[:, 1] = np.minimum(shell.vertices[:, 1], centre[1] + 1.07 * axes[1])
    else:
        scale = axes * np.array([1.06, 1.05, 1.07])
        shell.vertices = shell.vertices * scale + centre
        u = (shell.triangles_center - centre) / scale
        # short crop: hairline above the brow at the front, above the ears at the sides, nape at the back
        line = 0.42 * np.clip(u[:, 2], 0, 1) + 0.05 - 0.55 * np.clip(-u[:, 2], 0, 1)
        keep = u[:, 1] > line
    mesh = shell.submesh([np.where(keep)[0]], append=True)
    return mesh, np.tile(HAIR_RGB, (len(mesh.vertices), 1))


def draw(ax, layers, view: str) -> None:
    (sx, ix), (sd, idp) = VIEWS[view]
    polys, depth, colors = [], [], []
    for j, (mesh, vrgb) in enumerate(layers):
        tri = mesh.vertices[mesh.faces]
        facing = sd * mesh.face_normals[:, idp]
        k = facing > 0
        polys.append(np.stack([sx * tri[k][:, :, ix], tri[k][:, :, 1]], -1))
        # painter's algorithm: clothing layers win ties with the body (a 3D viewer uses a depth buffer)
        depth.append((sd * tri[k][:, :, idp]).mean(1) + 0.03 * j)
        base = vrgb[mesh.faces[k]].mean(1) if vrgb is not None else np.tile(SKIN, (k.sum(), 1))
        colors.append(base * (0.35 + 0.65 * facing[k])[:, None])
    polys, depth, colors = np.concatenate(polys), np.concatenate(depth), np.concatenate(colors)
    order = np.argsort(depth)
    # edges in the face colour close the hairline gaps between triangles (no wire-mesh look)
    ax.add_collection(PolyCollection(polys[order], facecolors=colors[order], edgecolors=colors[order],
                                     linewidths=0.4, antialiased=False))
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
    items = [catalogue()[sp.split(":")[0]] for sp in specs]
    cuts = [cut_for(sp.split(":")[0], it["name"], it["category"]) for sp, it in zip(specs, items)]
    lower = [styling_pyjama(body, lm, entry["sex"])] if needs_lower(cuts, [it["category"] for it in items]) else []
    layers = [(body, None), hair(body, entry["sex"]), underwear(body, lm, entry["sex"])] + lower + [(g[1], g[2]) for g in garments]
    title = f"{entry['display_name']} · {entry['usual_size']} · {m['height']:.0f} cm  " \
            f"(chest {m['chest']:.0f} / waist {m['waist']:.0f} / hip {m['hip']:.0f})"
    return layers, ["body", "hair", "underwear"] + (["pyjama (styling)"] if lower else []) + [g[3] for g in garments], marks, lines, title


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
