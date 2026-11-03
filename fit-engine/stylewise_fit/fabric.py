"""Fabric behaviour that changes how much ease a garment needs. PROJECT HEURISTICS, not measured.

stretch_pct: fraction of the garment girth the fabric itself can give (knits, elastane blends).
bulk_cm:     extra minimum ease a thick fabric needs because its own thickness uses up room.
Rigid wovens (silk, satin, cotton...) get neither: their relaxed measurement is all there is.
Mechanical stretch (elastic or drawstring waists) is per garment, from the size chart's range,
and is passed separately as GarmentInput.stretch_cm.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Fabric:
    stretch_pct: float = 0.0
    bulk_cm: float = 0.0


FABRICS = {
    # rigid wovens
    "silk": Fabric(), "satin": Fabric(), "cotton": Fabric(), "linen": Fabric(),
    "polyester": Fabric(), "nylon": Fabric(), "denim": Fabric(), "leather": Fabric(), "viscose": Fabric(),
    # thick fabrics
    "velvet": Fabric(bulk_cm=1.0), "wool": Fabric(bulk_cm=1.0), "acrylic": Fabric(bulk_cm=0.5),
    # stretch
    "jersey": Fabric(stretch_pct=0.05), "knit": Fabric(stretch_pct=0.05),
    "elastane": Fabric(stretch_pct=0.05), "spandex": Fabric(stretch_pct=0.05),
    # rib knits are cut to sit below body size; more give than a plain stretch blend
    "rib": Fabric(stretch_pct=0.10),
}


def fabric(name: str | None) -> Fabric | None:
    """None when the fabric is unknown, so callers can report it rather than assume rigid."""
    if not name:
        return None
    name = name.lower()
    # blends: any stretch fibre in the name wins ("cotton elastane", "viscose jersey")
    for key in ("rib", "elastane", "spandex", "jersey", "knit"):
        if key in name:
            return FABRICS[key]
    return next((f for k, f in FABRICS.items() if k in name), None)
