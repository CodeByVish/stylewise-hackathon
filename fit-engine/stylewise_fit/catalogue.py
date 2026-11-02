"""Stylewise catalogue garments with sourced cm (scripts/make_catalogue_garments.py)."""
import json
from functools import lru_cache
from pathlib import Path

from .schemas import GarmentInput, GarmentSpec

_PATH = Path(__file__).parent / "data/catalogue_garments.json"


@lru_cache(maxsize=1)
def catalogue() -> dict:
    return json.loads(_PATH.read_text())


def garment_input(garment_id: str, size: str) -> GarmentInput:
    """Raises ValueError for unknown ids, items without a sourced chart, or unknown sizes."""
    item = catalogue().get(garment_id)
    if item is None:
        raise ValueError(f"unknown garment {garment_id!r}")
    if not item["sizes"]:
        raise ValueError(f"{item['name']} has no sourced garment measurements yet")
    if size not in item["sizes"]:
        raise ValueError(f"{item['name']} comes in {list(item['sizes'])}, not {size!r}")
    s = item["sizes"][size]
    return GarmentInput(id=garment_id, category=item["category"], size=size, spec_cm=GarmentSpec(**s["spec_cm"]),
                        spec_source=item["spec_source"], fabric=item["fabric"], stretch_cm=s["stretch_cm"])
