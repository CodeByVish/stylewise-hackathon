"""Body-shape presets: shape + usual size + height -> estimated measurements with a range.

Shapes are the five standard apparel categories. Their bust/waist/hip relations follow
the FFIT thresholds (Simmons, Istook & Devarajan, 2004, J. Textile & Apparel Tech. Mgmt),
converted from inches to cm. Each preset is a prototype that sits safely inside its
category, not on a boundary. Size -> bust comes from a general retail body chart
(data/size_chart_standard.json); ANSUR II still informs the sex cue and shape priors.
"""
import json
from dataclasses import dataclass
from pathlib import Path

# FFIT thresholds in cm (inches * 2.54), kept here for traceability
IN = 2.54
FFIT = {
    "hourglass": "|bust - hip| <= 1in and (bust - waist >= 9in or hip - waist >= 10in)",
    "triangle": "hip - bust >= 3.6in and hip - waist < 9in",
    "inverted_triangle": "bust - hip >= 3.6in and bust - waist < 9in",
    "rectangle": "|hip - bust| < 3.6in and bust - waist < 9in and hip - waist < 10in",
    "oval": "waist close to or above bust and hip (FFIT 'oval'; commonly called apple)",
}

SEXES = ("female", "male")

# offsets from bust/chest in cm: (waist - bust, hip - bust); chosen as category prototypes.
# Men: rectangle, inverted triangle and oval are ANSUR II medians of men in that FFIT class
# (n=2987, 532, 505). Hourglass (n=0) and triangle (n=7) are rare in men; those two are
# hand-placed inside the class so every user can pick any silhouette.
SHAPE_OFFSETS = {
    "female": {
        "hourglass": (-25.0, 1.0),
        "triangle": (-8.0, 12.0),
        "inverted_triangle": (-18.0, -12.0),
        "rectangle": (-14.0, 2.0),
        "oval": (-2.0, -3.0),
    },
    "male": {
        "hourglass": (-24.0, 0.0),
        "triangle": (-2.0, 11.0),
        "inverted_triangle": (-14.0, -11.0),
        "rectangle": (-12.5, -2.5),
        "oval": (-4.5, -5.0),
    },
}
SHAPES = tuple(SHAPE_OFFSETS["female"])

# neutral display names, shown next to a silhouette; ids above stay standard for papers
DISPLAY_NAMES = {
    "hourglass": "The Balance",
    "triangle": "The Anchor",
    "inverted_triangle": "The Summit",
    "rectangle": "The Column",
    "oval": "The Orbit",
}

# usual size -> bust cm: midpoint of a general retail body chart (data/size_chart_standard.json).
# ANSUR II (data/size_chart_ansur2.json) ran ~1 size large for a general shopper (military sample).
SIZE_CHART = json.loads((Path(__file__).parent / "data/size_chart_standard.json").read_text())
SIZE_BUST = {sex: {r["size"]: sum(r["bust"]) / 2 for r in SIZE_CHART["sexes"][sex]["sizes"]} for sex in SEXES}
SIZES = tuple(SIZE_BUST["female"])
# +/- range on each estimated girth: half the widest printed bust range
SIZE_UNCERTAINTY_CM = {
    sex: round(max(r["bust"][1] - r["bust"][0] for r in SIZE_CHART["sexes"][sex]["sizes"]) / 2, 1)
    for sex in SEXES}
# generated statures, spanning roughly ANSUR II P5-P95 per sex
HEIGHTS_CM = {"female": (155.0, 165.0, 175.0), "male": (165.0, 175.0, 185.0)}


@dataclass(frozen=True)
class Estimate:
    chest_cm: float
    waist_cm: float
    hip_cm: float
    uncertainty_cm: float


def estimate(shape: str, usual_size: str, sex: str = "female") -> Estimate:
    if sex not in SEXES:
        raise ValueError(f"unknown sex {sex!r}; expected one of {list(SEXES)}")
    if shape not in SHAPES:
        raise ValueError(f"unknown shape {shape!r}; expected one of {sorted(SHAPES)}")
    if usual_size not in SIZES:
        raise ValueError(f"unknown size {usual_size!r}; expected one of {list(SIZES)}")
    bust = SIZE_BUST[sex][usual_size]
    dw, dh = SHAPE_OFFSETS[sex][shape]
    return Estimate(bust, round(bust + dw, 1), round(bust + dh, 1), SIZE_UNCERTAINTY_CM[sex])


def classify(bust: float, waist: float, hip: float) -> str:
    """FFIT-style check used to verify that generated bodies land in their category."""
    if abs(bust - hip) <= 1 * IN and (bust - waist >= 9 * IN or hip - waist >= 10 * IN):
        return "hourglass"
    if hip - bust >= 3.6 * IN and hip - waist < 9 * IN:
        return "triangle"
    if bust - hip >= 3.6 * IN and bust - waist < 9 * IN:
        return "inverted_triangle"
    if waist >= min(bust, hip) - 1 * IN:
        return "oval"
    if abs(hip - bust) < 3.6 * IN and bust - waist < 9 * IN and hip - waist < 10 * IN:
        return "rectangle"
    return "other"


def nearest_height(height_cm: float, sex: str = "female") -> float:
    """Closest pre-generated preset stature; ties go to the shorter one."""
    return min(HEIGHTS_CM[sex], key=lambda h: (abs(h - height_cm), h))


def preset_id(shape: str, size: str, height_cm: float, sex: str = "female") -> str:
    """Id of the generated preset mesh, snapped to the nearest generated height."""
    return f"{sex}_{shape}_{size}_{int(nearest_height(height_cm, sex))}"


def preset_mesh_ref(pid: str) -> str:
    # same layout gen_presets.py writes and index.json lists
    return f"fixtures/presets/{pid}.glb"
