"""Attach sourced garment measurements to the Stylewise app's catalogue items.

  python scripts/make_catalogue_garments.py   # writes stylewise_fit/data/catalogue_garments.json

Catalogue items (ids, names, categories, fabrics) come from the Stylewise app's
data/fixtures/catalogue.json (Vishakha-Kulkarni/stylewise). That catalogue lists letter sizes
only, so cm come from a real brand's GARMENT chart for the same garment type. The brand differs
from the catalogue's (synthetic) brands; spec_source says so.

Covered: kurtas, trousers, kurta sets (Indubindu chart). Not covered yet (no sourced garment
chart in cm): blouses/shell tops, skirts, dresses. They are listed with no sizes so the UI can
say "no sourced measurements" instead of guessing.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "stylewise_fit/data/catalogue_garments.json"
SOURCE = ("Indubindu kurta set size chart, https://www.indubindu.com/pages/kurta-set-size-chart "
          "(accessed 2026-11-02; states 'All sizes are actual garment measurements in centimeter'). "
          "Brand chart applied to a Stylewise demo catalogue item")

# Indubindu, cm. pant waist and hip are printed as ranges (elastic/drawstring waist).
# L hip is printed as "107-44" (a typo on the page), so it is left out rather than guessed.
INDUBINDU = {
    "XS": {"bust": 89, "kurta_waist": 81, "pant_waist": (74, 81), "hip": (92, 97)},
    "S": {"bust": 94, "kurta_waist": 86, "pant_waist": (81, 87), "hip": (97, 102)},
    "M": {"bust": 99, "kurta_waist": 91, "pant_waist": (86, 92), "hip": (102, 107)},
    "L": {"bust": 104, "kurta_waist": 96.5, "pant_waist": (92, 97), "hip": None},
    "XL": {"bust": 109, "kurta_waist": 101.5, "pant_waist": (97, 104), "hip": (112, 119)},
}

# catalogue id -> (name, category, fabric, kind)
ITEMS = {
    "green-kurta": ("Green kurta", "top", "silk", "kurta"),
    "evening-kurta": ("Evening embroidered kurta", "top", "silk", "kurta"),
    "ivory-kurta": ("Ivory festive kurta", "top", "silk", "kurta"),
    "gold-trousers": ("Gold trousers", "bottom", "silk", "pants"),
    "cream-bottom": ("Cream trousers", "bottom", "silk", "pants"),
    "navy-bottom": ("Navy trousers", "bottom", "silk", "pants"),
    "ivory-set": ("Ivory festive outfit", "outfit", "silk", "set"),
    "green-set": ("Green daytime set", "outfit", "silk", "set"),
    "navy-set": ("Navy evening set", "outfit", "silk", "set"),
    "maroon-set": ("Maroon festive set", "outfit", "silk", "set"),
    "premium-set": ("Premium festive set", "outfit", "silk", "set"),
    "budget-set": ("Budget festive set (unavailable)", "outfit", "silk", "set"),
    # no sourced garment chart yet
    "cream-silk-blouse": ("Cream silk blouse", "top", "silk", None),
    "blush-shell-top": ("Blush satin shell top", "top", "satin", None),
    "silk-skirt": ("Gold silk skirt", "bottom", "silk", None),
    "charcoal-skirt": ("Charcoal pencil skirt", "bottom", "wool", None),
    "emerald-wrap-dress": ("Emerald wrap dress", "dress", "silk", None),
    "black-satin-dress": ("Black satin midi dress", "dress", "polyester", None),
}


# Uniqlo SG flat-laid "Product Size" tables pasted by the team (2026-11-02). Body width is the
# flat half-chest, so chest circumference = 2 x body width. Only chest is given: waist/hip stay
# unknown. Sizes: Uniqlo XXL -> 2XL.
UNIQLO_ITEMS = {
    "uniqlo-crew-tee": {
        "name": "Crew neck T-shirt (Uniqlo SG)", "category": "top", "fabric": None,
        "body_width": {"XS": 45.5, "S": 47.5, "M": 49.5, "L": 52.5, "XL": 55.5, "2XL": 58.5, "3XL": 61.5},
        "source": "UNIQLO SG Unisex Crew Neck T-Shirt product page, Product Size table (flat-laid body "
                  "width x2), https://www.uniqlo.com/sg/en/products/E465193-000/00 (accessed 2026-11-02). Sleeve column ignored "
                  "(76-83 cm is inconsistent with a short sleeve)",
    },
    "uniqlo-dress-E487286": {
        "name": "Long dress E487286 (Uniqlo SG)", "category": "dress", "fabric": "cotton elastane",
        "body_width": {"XS": 38, "S": 40.5, "M": 43, "L": 45.5, "XL": 48.5, "2XL": 51.5},
        # "Hip width" is read as a full circumference: doubled it would be 217-271 cm
        "hip": {"XS": 108.5, "S": 113.5, "M": 118.5, "L": 123.5, "XL": 129.5, "2XL": 135.5},
        "source": "UNIQLO SG product E487286, Product Size table (body width x2 = bust; hip width "
                  "taken as circumference), https://www.uniqlo.com/sg/en/products/E487286-000/00 "
                  "(accessed 2026-11-02). Fabric: cotton with stretch (team-confirmed), so the bust can give a little",
    },
    "manyavar-mens-kurta": {
        "name": "Men's textured green kurta (Manyavar)", "category": "top", "fabric": "viscose",
        "chest": {"S": 102, "M": 107, "L": 112, "XL": 117, "2XL": 122, "3XL": 127},
        "waist": {"S": 97, "M": 102, "L": 107, "XL": 112, "2XL": 117, "3XL": 122},
        "for": "men",
        "cut": {"hem": 0.40, "sleeve_m": 0.54, "layer": 1, "flare_cm": 3, "neck": "collar",
                "openings": [{"at": "sides", "from": "hip", "width_cm": 10}]},
        "source": "Manyavar UC103339 'Textured Green Kurta', SHORT KURTA garment measurement table (cm), "
                  "https://www.manyavar.com/en-au/kurta/textured-green-kurta/UC103339.html (accessed 2026-11-03); "
                  "blended viscose, mandarin collar",
    },
    "parthvi-anarkali-set": {
        "name": "Grey printed Anarkali kurta set (PARTHVI)", "category": "outfit", "fabric": "rayon",
        # seller chart in inches: Kurta S=36, M=38, L=40, XL=42, XXL=44 (3XL also printed as 44: left out)
        "chest": {"S": 91.4, "M": 96.5, "L": 101.6, "XL": 106.7, "2XL": 111.8},
        "for": "women",
        "cut": {"hem": 0.10, "sleeve_m": 0.40, "layer": 1, "flare_cm": 36, "neck": "round", "openings": [],
                "fall": "chest", "legs_to": 0.05},
        "source": "Amazon SG listing B0DHY1L5PX, PARTHVI Anarkali kurta & pant with dupatta, seller size chart "
                  "'Kurta-S=36\", M=38\", L=40\", XL=42\", XXL=44\"' (kurta bust, inches; whether body or garment is not "
                  "stated), https://www.amazon.sg/dp/B0DHY1L5PX (accessed 2026-11-03); rayon, calf length, 3/4 sleeves, round neck",
    },
    "itos365-mens-kurta-set": {
        "name": "Men's green kurta pyjama set (ITOS365)", "category": "outfit", "fabric": "cotton blend",
        "chest": {}, "for": "men",
        "cut": {"hem": 0.36, "sleeve_m": 0.58, "layer": 1, "flare_cm": 3, "neck": "collar",
                "openings": [{"at": "sides", "from": "hip", "width_cm": 10}], "legs_to": 0.05},
        "source": "Amazon SG listing B09J6HBQ94, ITOS365 men's cotton-blend kurta pyjama set (accessed 2026-11-03). "
                  "The listing gives no size chart in cm, so no sizes are claimed",
    },
    "zesica-black-midi-dress": {
        "name": "Black bodycon midi dress (ZESICA)", "category": "dress", "fabric": "polyester elastane",
        # the brand prints a fit range per size: garment = low end, stretch = range (91/9 poly-elastane)
        "ranges": {"S": {"chest": (84.3, 88.1), "waist": (65.5, 69.1), "hip": (92.7, 96.3)},
                   "M": {"chest": (91.9, 95.8), "waist": (72.9, 76.7), "hip": (100.3, 103.9)},
                   "L": {"chest": (99.6, 103.4), "waist": (80.5, 84.3), "hip": (108.0, 111.5)},
                   "XL": {"chest": (107.2, 111.0), "waist": (88.1, 91.9), "hip": (115.6, 119.1)}},
        "for": "women",
        "cut": {"hem": 0.13, "sleeve_m": 0.08, "layer": 1, "flare_cm": 0, "neck": "crew",
                "openings": [{"at": "front", "from": 18, "width_cm": 4}]},
        "source": "Amazon SG listing B0DR7MTRZP, ZESICA bodycon midi dress, brand size chart SG Regular "
                  "(bust/waist/hip ranges, length 112-118 cm, cm), https://www.amazon.sg/dp/B0DR7MTRZP (accessed "
                  "2026-11-03); 91% polyester 9% elastane, medium stretch, mock neck, cap sleeves, front slit",
    },
    "reference-dress": {
        "name": "Short-sleeve casual dress (reference)", "category": "dress", "fabric": None,
        "body_width": {"XS": 44.0, "S": 46.0, "M": 48.0, "L": 51.0, "XL": 54.0, "2XL": 57.0, "3XL": 60.0},
        "source": "UNVERIFIED reference table 'based on Uniqlo height-to-size mapping patterns' "
                  "(UNIQLO SG Clothing Fit Guide), not a specific product's measurements",
    },
}


# ESTIMATED garments (no product measurements yet): Uniqlo SG women's BODY chart midpoints
# (docs/sources/uniqlo_sizing_chart_dataset.pdf) + a design-ease guess per garment type.
# Labelled synthetic so every report warns. Replace with product measurements when available.
UQ_BODY = {"bust": {"XS": 81.5, "S": 86.5, "M": 92, "L": 98, "XL": 104.5},
           "waist": {"XS": 61, "S": 67, "M": 73, "L": 79, "XL": 85.5},
           "hip": {"XS": 87.5, "S": 92.5, "M": 97.5, "L": 102.5, "XL": 108.5}}
ESTIMATED_EASE = {  # cm added to body: project guesses by garment type
    "cream-silk-blouse": {"chest": 10, "waist": 12},           # relaxed woven blouse
    "blush-shell-top": {"chest": 6, "waist": 8},               # close-fitting shell
    "silk-skirt": {"waist": 1, "hip": 12},                     # A-line skirt
    "charcoal-skirt": {"waist": 1, "hip": 4},                  # pencil skirt
    "emerald-wrap-dress": {"chest": 6, "waist": 4, "hip": 10},
    "black-satin-dress": {"chest": 6, "waist": 6, "hip": 8},
}
ESTIMATED_SOURCE = ("ESTIMATED (synthetic): Uniqlo SG women's body chart midpoints + project design-ease "
                    "guess for this garment type; not product measurements")


def spec(kind: str, row: dict) -> tuple[dict, dict]:
    """-> (spec_cm, stretch_cm). Ranges: relaxed = low end, give = high - low."""
    hip = row["hip"][0] if row["hip"] else None  # low end: the garment's relaxed hip
    if kind == "kurta":
        return {"chest": row["bust"], "waist": row["kurta_waist"]}, {}
    lo, hi = row["pant_waist"]
    if kind == "pants":
        return {"waist": lo, "hip": hip}, {"waist": hi - lo}
    # set: kurta top half, pant hip; the pant's elastic waist sits under the kurta
    return {"chest": row["bust"], "waist": row["kurta_waist"], "hip": hip}, {}


# Per-item cut read from each product photo (fixtures/garment_photos): overrides the type default in
# scripts/render_fit.py CUTS. hem: fraction of stature; sleeve_m from the top of the shoulder.
ITEM_CUTS = {
    "emerald-wrap-dress": {"hem": 0.15, "sleeve_m": 0.54, "flare_cm": 5, "neck": "v", "belt": True, "openings": []},
    "green-kurta": {"hem": 0.30, "sleeve_m": 0.36, "neck": "collar",
                    "openings": [{"at": "sides", "from": "hip", "width_cm": 12}]},
    "evening-kurta": {"hem": 0.30, "sleeve_m": 0.54, "neck": "collar",
                      "openings": [{"at": "sides", "from": "hip", "width_cm": 12}]},
    "ivory-kurta": {"hem": 0.30, "sleeve_m": 0.36, "neck": "collar",
                    "openings": [{"at": "sides", "from": "hip", "width_cm": 12}]},
    "green-set": {"hem": 0.16, "sleeve_m": 0.54, "neck": "round", "flare_cm": 10,
                  "openings": [{"at": "sides", "from": "hip", "width_cm": 16}]},
    "premium-set": {"hem": 0.16, "sleeve_m": 0.54, "neck": "collar", "flare_cm": 10,
                    "openings": [{"at": "sides", "from": "hip", "width_cm": 16}]},
    "budget-set": {"hem": 0.16, "sleeve_m": 0.54, "neck": "collar", "flare_cm": 10,
                   "openings": [{"at": "sides", "from": "hip", "width_cm": 16}]},
    "maroon-set": {"hem": 0.04, "sleeve_m": 0.54, "neck": "round", "flare_cm": 40, "openings": []},
    "navy-set": {"hem": 0.10, "sleeve_m": 0.54, "neck": "collar", "flare_cm": 14, "openings": []},
    "ivory-set": {"hem": 0.42, "sleeve_m": 0.54, "neck": "v", "belt": True, "openings": []},
    "silk-skirt": {"hem": 0.30, "flare_cm": 22},
    "charcoal-skirt": {"hem": 0.28, "flare_cm": 0, "openings": [{"at": "back", "from": 16, "width_cm": 5}]},
    "cream-silk-blouse": {"hem": 0.45, "sleeve_m": 0.54, "neck": "collar"},
    "blush-shell-top": {"hem": 0.46, "sleeve_m": 0.0, "neck": "crew"},
}


# light garments on a light background: the sampler mixes in background, so set these by eye
PHOTO_COLOUR_FIX = {"ivory-set": [0.93, 0.90, 0.82], "cream-silk-blouse": [0.92, 0.89, 0.82],
                    "cream-bottom": [0.88, 0.83, 0.72]}


def photo_colour(gid: str) -> list[float] | None:
    """Median colour of the garment pixels in its product photo (background = the corners' colour)."""
    import numpy as np
    from PIL import Image

    path = Path(__file__).resolve().parents[2] / f"fixtures/garment_photos/{gid}.jpg"
    if not path.exists():
        return None
    img = np.asarray(Image.open(path).convert("RGB").resize((160, 160)), dtype=float) / 255
    corners = np.concatenate([img[:12, :12].reshape(-1, 3), img[:12, -12:].reshape(-1, 3)])
    bg = np.median(corners, 0)
    centre = img[25:135, 40:120].reshape(-1, 3)
    fg = centre[np.linalg.norm(centre - bg, axis=1) > 0.12]
    return [round(float(c), 3) for c in np.median(fg, 0)] if len(fg) else None


def main() -> None:
    out = {}
    for gid, (name, cat, fab, kind) in ITEMS.items():
        sizes = {}
        if kind:
            for size, row in INDUBINDU.items():
                cm, give = spec(kind, row)
                sizes[size] = {"spec_cm": {k: v for k, v in cm.items() if v is not None}, "stretch_cm": give}
        out[gid] = {"name": name, "category": cat, "fabric": fab, "sizes": sizes,
                    "spec_source": SOURCE if kind else None}
    for gid, ease in ESTIMATED_EASE.items():
        body_key = {"chest": "bust", "waist": "waist", "hip": "hip"}
        out[gid]["sizes"] = {z: {"spec_cm": {r: UQ_BODY[body_key[r]][z] + e for r, e in ease.items()},
                                 "stretch_cm": {}} for z in UQ_BODY["bust"]}
        out[gid]["spec_source"] = ESTIMATED_SOURCE
    for gid, u in UNIQLO_ITEMS.items():
        if "ranges" in u:  # brand fit ranges: low end is the garment, the range is how far it stretches
            sizes = {z: {"spec_cm": {r: lo for r, (lo, hi) in row.items()},
                         "stretch_cm": {r: round(hi - lo, 1) for r, (lo, hi) in row.items()}} for z, row in u["ranges"].items()}
        elif "chest" in u:  # full-girth garment table (e.g. Manyavar)
            sizes = {z: {"spec_cm": {"chest": c} | ({"waist": u["waist"][z]} if "waist" in u else {}),
                         "stretch_cm": {}} for z, c in u["chest"].items()}
        else:  # Uniqlo flat-laid body width x2
            sizes = {z: {"spec_cm": {"chest": 2 * w} | ({"hip": u["hip"][z]} if "hip" in u else {}),
                         "stretch_cm": {}} for z, w in u["body_width"].items()}
        out[gid] = {"name": u["name"], "category": u["category"], "fabric": u["fabric"], "sizes": sizes,
                    "spec_source": u["source"]} | ({"cut": u["cut"]} if "cut" in u else {})
    for gid, item in out.items():
        if gid in ITEM_CUTS:
            item["cut"] = ITEM_CUTS[gid]
        rgb = PHOTO_COLOUR_FIX.get(gid) or photo_colour(gid)
        if rgb:
            item["rgb"] = rgb
    for gid, item in out.items():  # the Stylewise app's catalogue is women's wear; the Uniqlo tee is unisex
        item["for"] = UNIQLO_ITEMS.get(gid, {}).get("for") or ("unisex" if gid == "uniqlo-crew-tee" else "women")
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"{sum(1 for g in out.values() if g['sizes'])} of {len(out)} items have garment cm (see spec_source for how each was obtained) -> {OUT}")


if __name__ == "__main__":
    main()
