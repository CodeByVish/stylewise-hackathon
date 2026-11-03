"""Photoreal 'on a model' preview with Meta muse-image-1.0, guided by our measured preset.

  python scripts/photo_preview.py <preset_dir> <preset_id> <garment_id>:<size> <product_photo> <out.png>

Image 1 is our fit-shell front render (exact silhouette and proportions of the preset, garment
already placed by measured ease); image 2 is the product photo. The model is asked to draw a
photographic model with image 1's body and pose wearing image 2's garment. A visual impression
only: fit claims come from the engine's FitReport, never from this picture.
"""
import base64
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import trimesh  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from render_fit import draw, hair, landmark_heights, shell, underwear  # noqa: E402

from stylewise_fit.catalogue import catalogue, garment_input  # noqa: E402
from stylewise_fit.fit import evaluate  # noqa: E402
from stylewise_fit.nisha import _env  # noqa: E402
from stylewise_fit.schemas import BodyInput, FitRequest  # noqa: E402

PROMPT = (
    "Photorealistic full-length e-commerce studio photo. Use the person in image 1 ONLY for body shape, "
    "proportions, height, pose and how loose or tight the garment sits; render them as a real {sex} model "
    "with natural skin, hair and a friendly neutral face. They wear exactly the garment from image 2: same "
    "colour, fabric, print, neckline, sleeves and length. Plain light-grey seamless background, soft light, "
    "front view, full body including feet. Do not slim or reshape the body."
)


def guide_png(preset_dir: Path, pid: str, spec: str) -> bytes:
    entry = next(r for r in json.loads((preset_dir / "index.json").read_text()) if r["id"] == pid)
    body = trimesh.load(preset_dir / f"{pid}.glb", force="mesh", process=False)
    m, lm, sex = entry["measured_cm"], landmark_heights(body), entry["sex"]
    gid, size = spec.split(":")
    item = catalogue()[gid]
    report = evaluate(FitRequest(body=BodyInput(height_cm=m["height"], chest_cm=round(m["chest"], 1),
                                                 waist_cm=round(m["waist"], 1), hip_cm=round(m["hip"], 1)),
                                 garment=garment_input(gid, size)))
    g = shell(body, report, gid, item["name"], item["category"], lm)
    fig, ax = plt.subplots(figsize=(4, 6), dpi=160)
    draw(ax, [(body, None), hair(body, sex), underwear(body, lm, sex), (g[0], g[1])], "front")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="#e8e8e6")
    return buf.getvalue(), sex


def main() -> None:
    preset_dir, pid, spec, photo, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5])
    guide, sex = guide_png(preset_dir, pid, spec)
    out.with_suffix(".guide.png").write_bytes(guide)
    uri = lambda b, mime: f"data:{mime};base64,{base64.b64encode(b).decode()}"  # noqa: E731
    body = {"model": "muse-image-1.0", "prompt": PROMPT.format(sex="woman" if sex == "female" else "man"), "n": 1,
            "images": [{"image_url": uri(guide, "image/png")}, {"image_url": uri(photo.read_bytes(), "image/jpeg")}]}
    key = _env("MODEL_API_KEY") or _env("META_API_KEY")
    req = urllib.request.Request("https://api.meta.ai/v1/images/edits", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)
    item = resp["data"][0]
    img = base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"]).read()
    out.write_bytes(img)
    print("->", out)


if __name__ == "__main__":
    main()
