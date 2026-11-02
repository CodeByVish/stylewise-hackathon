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
                  "width x2), pasted 2026-11-02; product URL not recorded. Sleeve column ignored "
                  "(76-83 cm is inconsistent with a short sleeve)",
    },
    "uniqlo-dress-E487286": {
        "name": "Long dress E487286 (Uniqlo SG)", "category": "dress", "fabric": None,
        "body_width": {"XS": 38, "S": 40.5, "M": 43, "L": 45.5, "XL": 48.5, "2XL": 51.5},
        # "Hip width" is read as a full circumference: doubled it would be 217-271 cm
        "hip": {"XS": 108.5, "S": 113.5, "M": 118.5, "L": 123.5, "XL": 129.5, "2XL": 135.5},
        "source": "UNIQLO SG product E487286, Product Size table (body width x2 = bust; hip width "
                  "taken as circumference), https://www.uniqlo.com/sg/en/products/E487286-000/00 "
                  "(accessed 2026-11-02). Fabric not recorded; bust below body size suggests a stretch knit",
    },
    "reference-dress": {
        "name": "Short-sleeve casual dress (reference)", "category": "dress", "fabric": None,
        "body_width": {"XS": 44.0, "S": 46.0, "M": 48.0, "L": 51.0, "XL": 54.0, "2XL": 57.0, "3XL": 60.0},
        "source": "UNVERIFIED reference table 'based on Uniqlo height-to-size mapping patterns' "
                  "(UNIQLO SG Clothing Fit Guide), not a specific product's measurements",
    },
}


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
    for gid, u in UNIQLO_ITEMS.items():
        out[gid] = {"name": u["name"], "category": u["category"], "fabric": u["fabric"],
                    "sizes": {z: {"spec_cm": {"chest": 2 * w} | ({"hip": u["hip"][z]} if "hip" in u else {}),
                                  "stretch_cm": {}} for z, w in u["body_width"].items()},
                    "spec_source": u["source"]}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"{sum(1 for g in out.values() if g['sizes'])} of {len(out)} items have sourced garment cm -> {OUT}")


if __name__ == "__main__":
    main()
