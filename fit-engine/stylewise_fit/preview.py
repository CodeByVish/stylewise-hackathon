"""Visual preview with Meta muse-image-1.0, guided by our measured preset. Not a fit claim.

Image 1 is our fit-shell front render (the preset's exact silhouette with the garment placed by
measured ease); image 2 is the product photo. The default style is a faceless dress-form mannequin:
real fabric and colour on the user's proportions, with no face or identity, so nobody compares
themselves to a model. 'illustration' gives a soft fashion sketch instead. Results are cached per
(preset, garment, size, style): the same request never pays for a second generation.
"""
import base64
import hashlib
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

from .nisha import _env

ROOT = Path(__file__).resolve().parents[2]
PHOTOS = ROOT / "fixtures/garment_photos"
# Every generated picture is kept on disk: the same request is paid for once, even across restarts.
CACHE = ROOT / "fixtures/preview_cache"
# Stated up front so the image model sees the purpose before the fit details: a sizing check on a
# clothed store mannequin (not a person), for shoppers. Without it, honest "too small" results on
# fuller figures were sometimes filtered.
PURPOSE = ("Context: this image is for a clothing size-check tool in an online shop. It shows a fully clothed, "
           "faceless store mannequin (not a real person) so a shopper can see whether a garment size fits before "
           "buying. It is a neutral, non-sexual product image; showing a poor fit honestly is the point of the tool. ")
STYLES = {
    "mannequin": (
        "Photorealistic e-commerce product photo of the garment from image 2 worn by a faceless dress-form "
        "mannequin. The WHOLE mannequin, including head, neck, arms, hands and feet, is one even matte light-grey "
        "(about #b8b8b6), with no beige or skin tone, and a smooth seamless neck with no visible joints or seams. "
        "Its head has no face and {hair}. The mannequin has EXACTLY the body shape, proportions and height of the "
        "figure in image 1 (do not slim, widen, lengthen or reshape it); {measures} {pose} "
        "Keep the garment identical to image 2: colour, fabric, print, sleeves, length and especially the NECKLINE: "
        "copy its shape and depth exactly from image 2, worn closed and modest, never opened, plunging or lower than "
        "in image 2, with no bare chest showing. "
        "FIT: {fit} "
        "Plain light background, soft studio light, {view} view as in image 1, full figure."),
    "illustration": (
        "Soft, minimal fashion illustration (flat colour, light pencil lines) of the garment from image 2 on a "
        "faceless figure with EXACTLY the body shape and proportions of image 1 (do not slim or reshape); {measures} {pose} "
        "Keep the garment's colour, print, neckline, sleeves and length from image 2. No facial features. "
        "Its head has {hair}. FIT: {fit} Plain off-white background, {view} view as in image 1, full figure."),
}
HAIR = {"female": "smooth sculpted hair moulded in the same grey: a neat chin-length bob, like a display mannequin",
        "male": "smooth sculpted hair moulded in the same grey: a short neat crop, like a display mannequin"}
POSE = {"female": ("Pose: relaxed and natural, like a styled boutique mannequin: soft shoulders, elbows slightly bent, "
                   "wrists relaxed with gently curved fingers, arms a little away from the body, and the feet close "
                   "together (a narrow natural stance, about a hand's width apart)."),
        "male": ("Pose: relaxed and natural: elbows slightly bent, wrists relaxed, feet about hip-width apart.")}


def measures_text(entry: dict) -> str:
    m = entry["measured_cm"]
    return (f"its measurements are bust {m['chest']:.0f} cm, waist {m['waist']:.0f} cm, hip {m['hip']:.0f} cm at "
            f"{m['height']:.0f} cm tall, so draw exactly that size.")


class CacheOnly(RuntimeError):
    """A preview that is not pre-generated, on a deployment that only serves cached images."""


CAPTION = "AI-generated illustration; proportions, garment details and fit may be inaccurate. Refer to the measurements."

REGION_WORDS = {"chest": "chest area", "waist": "waist area", "hip": "hip area"}


def fit_notes(report) -> str:
    """Turn the FitReport into neutral garment-construction instructions (content-policy safe), so the
    picture shows the fit honestly: a too-small region looks strained, a too-big one looks baggy."""
    tight, snug, good, loose = [], [], [], []
    for region, r in report.regions.items():
        if r.ease_cm is None:
            continue
        where = REGION_WORDS[region]
        {"tight": tight, "borderline": snug, "loose": loose}.get(r.verdict, good).append(
            f"{where} ({abs(r.ease_cm):.0f} cm)" if r.verdict in ("tight", "loose") else where)
    lines = []
    if tight:
        # wording kept neutral: stronger body-tension phrasing trips the image model's content policy
        lines.append("This garment is a size too small for this mannequin at the " + ", ".join(tight) + ": the front "
                     "cannot overlap or close fully, visible tension creases across those areas, and any belt or "
                     "closure sits strained.")
    if snug:
        lines.append("Snug at the " + ", ".join(snug) + ": fabric just touching, light tension lines.")
    if loose:
        lines.append("Visibly TOO BIG at the " + ", ".join(loose) + ": extra fabric hangs in loose folds and stands "
                     "away from the figure.")
    if good:
        lines.append("Comfortable at the " + ", ".join(good) + ": fabric skims the figure with a little room.")
    return " ".join(lines)


def photo_path(garment_id: str) -> Path | None:
    path = PHOTOS / f"{garment_id}.jpg"
    return path if path.exists() else None


def described(garment_id: str) -> str:
    """Without a product photo, the garment is drawn from its catalogue entry instead."""
    from .catalogue import catalogue

    item = catalogue()[garment_id]
    cut = item.get("cut") or {}
    rgb = item.get("rgb")
    colour = f" in the colour rgb({', '.join(str(round(255 * c)) for c in rgb)})" if rgb else ""
    sleeves = ("long sleeves" if cut.get("sleeve_m", 0) > 0.4 else "short sleeves" if cut.get("sleeve_m", 0) > 0
               else "no sleeves")
    return (f"a {item['name'].lower()}{colour}, made of {item.get('fabric') or 'woven fabric'}, "
            f"{cut.get('neck', 'round')} neckline, {sleeves}, length as shown in image 1")


def guide_png(preset: dict, garment_id: str, size: str, view: str = "front", pair: tuple[str, str] | None = None) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh

    from .catalogue import catalogue, garment_input
    from .fit import evaluate
    from .presets import preset_id
    from .schemas import BodyInput, FitRequest
    from .viewer import renderer

    render = renderer()
    pid = preset_id(preset["shape"], preset["usual_size"], preset["height_cm"], preset.get("sex", "female"))
    entry = next(r for r in json.loads((ROOT / "fixtures/presets/index.json").read_text()) if r["id"] == pid)
    body = trimesh.load(ROOT / entry["mesh_ref"], force="mesh", process=False)
    m, lm = entry["measured_cm"], render.landmark_heights(body)
    item = catalogue()[garment_id]
    measured = BodyInput(height_cm=m["height"], chest_cm=round(m["chest"], 1), waist_cm=round(m["waist"], 1),
                         hip_cm=round(m["hip"], 1))
    pieces = [(garment_id, size)] + ([pair] if pair else [])
    shells, cuts, cats = [], [], []
    for gid, z in pieces:
        it = catalogue()[gid]
        report = evaluate(FitRequest(body=measured, garment=garment_input(gid, z)))
        shells.append(render.shell(body, report, gid, it["name"], it["category"], lm))
        cuts.append(render.cut_for(gid, it["name"], it["category"]))
        cats.append(it["category"])
    lower = [render.styling_pyjama(body, lm, entry["sex"])] if render.needs_lower(cuts, cats) else []
    # bottoms first, so a top over them is drawn on top
    order = sorted(range(len(pieces)), key=lambda i: cats[i] != "bottom")
    # no hair in the guide: the image model copies it, and the realistic view is a clean faceless mannequin
    layers = ([(body, None), render.underwear(body, lm, entry["sex"])] + lower
              + [(shells[i][0], shells[i][1]) for i in order if shells[i]])
    fig, ax = plt.subplots(figsize=(4, 6), dpi=160)
    render.draw(ax, layers, view)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="#e8e8e6")
    plt.close(fig)
    return buf.getvalue()


def preview(shape: str, usual_size: str, sex: str, height_cm: float, garment_id: str, size: str,
            style: str = "mannequin", fit: str = "", view: str = "front", pair: tuple[str, str] | None = None) -> bytes:
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; expected one of {list(STYLES)}")
    from .presets import preset_id

    preset = {"shape": shape, "usual_size": usual_size, "sex": sex, "height_cm": height_cm}
    if view not in ("front", "side", "back"):
        raise ValueError(f"unknown view {view!r}; expected front, side or back")
    photo = photo_path(garment_id)
    from .catalogue import catalogue

    pid = preset_id(shape, usual_size, height_cm, sex)
    entry = next(r for r in json.loads((ROOT / "fixtures/presets/index.json").read_text()) if r["id"] == pid)
    template = STYLES[style].replace("{hair}", HAIR.get(sex, HAIR["female"])) \
        .replace("{pose}", POSE.get(sex, POSE["female"])).replace("{measures}", measures_text(entry))
    images_from = [photo] if photo else []
    if not photo:  # no photo: describe the garment in words instead of "the garment from image 2"
        template = (template.replace("the garment from image 2", described(garment_id))
                    .replace("Keep the garment identical to image 2: colour, fabric, print, sleeves, length and especially the NECKLINE: "
                             "copy its shape and depth exactly from image 2, worn closed and modest, never opened, plunging or lower than "
                             "in image 2, with no bare chest showing. ", "The neckline is worn closed and modest, with no bare chest showing. ")
                    .replace("Keep the garment's colour, print, neckline, sleeves and length from image 2. ", ""))
    if pair:  # styled with a second piece: its photo is the next image, or its description
        pair_photo = photo_path(pair[0])
        if pair_photo:
            images_from.append(pair_photo)
            other = f"the garment from image {len(images_from) + 1}"
        else:
            other = described(pair[0])
        template = template.replace("FIT: {fit}", f"Styled together with {other}, exactly as in image 1. FIT (first garment): {{fit}}")
    if garment_id == 'zesica-black-midi-dress' and view != 'front':
        template += (" This is one continuous, uninterrupted dress from shoulder to hem: no exposed midriff, waist "
                     "cut-out, crop top or separate skirt. The small gold loop at one side of the ruched waist is "
                     "decorative only and does not open the dress.")
    if garment_id == 'manyavar-mens-kurta':
        template += (" The kurta is a straight, short men's kurta with a level, unbunched hem; "
                     "the hem hangs freely over the trousers, never tucked in.")
    # A result is valid only for the inputs that shape it: this body (mesh + its index row), these
    # garments (catalogue entries + photos), the guide renderer and the final prompt. Unrelated presets
    # or garments changing must not throw away paid-for images.
    cat = catalogue()
    files = [ROOT / "fixtures/presets" / f"{pid}.glb", ROOT / "fit-engine/scripts/render_fit.py", *images_from]
    tag = json.dumps([pid, entry, garment_id, size, cat[garment_id], pair, pair and cat[pair[0]], style, fit, view,
                      template, [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]], sort_keys=True, default=str)
    cached = CACHE / f"{garment_id}_{size}_{view}_{hashlib.sha1(tag.encode()).hexdigest()[:12]}.png"
    if cached.exists():
        return cached.read_bytes()
    # Public deployments set PREVIEW_CACHE_ONLY=1: visitors see the pre-generated demo set, and nobody can
    # spend the team's Meta credits by clicking through new combinations.
    if (_env("PREVIEW_CACHE_ONLY") or "").lower() in ("1", "true", "yes"):
        raise CacheOnly("This combination isn't pre-generated in the public demo. Try The Column with garment "
                        "size M on body S, M or L, or run Stylewise locally to draw any combination.")
    key = _env("MODEL_API_KEY") or _env("META_API_KEY")
    if not key:
        raise RuntimeError("no Meta API key: set META_API_KEY in .env")
    guide = guide_png(preset, garment_id, size, view, pair)
    uri = lambda b, mime: f"data:{mime};base64,{base64.b64encode(b).decode()}"  # noqa: E731
    images = [{"image_url": uri(guide, "image/png")}] + [{"image_url": uri(f.read_bytes(), "image/jpeg")} for f in images_from]
    # The image model's safety filter sometimes rejects strained-fabric results on curvy figures. Fall back
    # to milder but still honest descriptions rather than to a flattering picture.
    attempts = [fit or "no measurements given.",
                " ".join(x for x in (fit or "").split(". ") if "too small" in x)[:220] or "Fits as described.",
                "This garment is a size too small for this mannequin." if "too small" in (fit or "") else "Fits as described."]
    last = None
    for fit_text in dict.fromkeys(attempts):  # unique, in order
        body = {"model": "muse-image-1.0", "prompt": PURPOSE + template.format(fit=fit_text, view=view), "n": 1, "images": images}
        req = urllib.request.Request("https://api.meta.ai/v1/images/edits", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                item = json.load(r)["data"][0]
            break
        except urllib.error.HTTPError as error:
            last = error.read()[:300].decode(errors="replace")
            if "content_policy" not in last:
                break
    else:
        raise RuntimeError(f"image model refused every variant: {last}")
    if last and "item" not in locals():
        raise RuntimeError(f"image model refused the request: {last}")
    png = base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"]).read()
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(png)
    return png
