"""Pydantic mirrors of contracts/*.schema.json. Keep both in sync."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CONTRACT_VERSION = "0.4.0"

Pose = Literal["standing", "seated"]
# borderline: the verdict would change within the estimate's uncertainty range
Verdict = Literal["tight", "ok", "loose", "borderline", "unknown"]
Shape = Literal["hourglass", "triangle", "inverted_triangle", "rectangle", "oval"]
Size = Literal["XS", "S", "M", "L", "XL", "2XL", "3XL"]
Sex = Literal["female", "male"]


class BodyPreset(BaseModel):
    """For users who prefer not to share measurements: silhouette + usual size."""
    shape: Shape
    usual_size: Size
    # selects the size chart and shape prototypes; default keeps v0.2 requests valid
    sex: Sex = "female"


class BodyInput(BaseModel):
    # measured: user typed girths; preset: girths estimated from preset (with a range)
    source: Literal["measured", "preset"] = "measured"
    preset: Optional[BodyPreset] = None
    height_cm: float = Field(gt=100, lt=230)
    chest_cm: Optional[float] = Field(default=None, gt=50, lt=200)
    waist_cm: Optional[float] = Field(default=None, gt=40, lt=200)
    hip_cm: Optional[float] = Field(default=None, gt=50, lt=200)
    pose: Pose = "standing"

    @model_validator(mode="after")
    def _preset_matches_source(self):
        if (self.source == "preset") != (self.preset is not None):
            raise ValueError("preset must be given exactly when source == 'preset'")
        return self


class GarmentSpec(BaseModel):
    chest: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None
    length: Optional[float] = None


class GarmentInput(BaseModel):
    id: str
    category: str
    size: str
    spec_cm: GarmentSpec
    spec_source: str  # where the size chart came from; never "llm"
    mesh_ref: Optional[str] = None
    # e.g. "silk", "velvet", "cotton elastane"; unknown fabric -> stretch/bulk reported as unknown
    fabric: Optional[str] = None
    # mechanical give per region from the chart's range (elastic/drawstring waist), cm
    stretch_cm: dict[str, float] = {}


class Preferences(BaseModel):
    closure: Optional[Literal["front_open", "pullover"]] = None
    fit_pref: Optional[Literal["snug", "regular", "relaxed"]] = None


class FitRequest(BaseModel):
    contract_version: str = CONTRACT_VERSION
    body: BodyInput
    garment: GarmentInput
    preferences: Preferences = Preferences()


class RegionResult(BaseModel):
    body_cm: Optional[float]
    garment_cm: Optional[float]
    ease_cm: Optional[float]
    # +/- on body_cm and ease_cm; 0 for measured input, size half-step for presets
    uncertainty_cm: float = 0.0
    # how far the garment can give at this region (fabric + elastic); 0 for rigid
    stretch_cm: float = 0.0
    verdict: Verdict


class Provenance(BaseModel):
    body_source: str
    body_preset_id: Optional[str] = None
    garment_source: str
    body_model: str
    engine_version: str


class FitReport(BaseModel):
    contract_version: str = CONTRACT_VERSION
    body_mesh_ref: Optional[str]
    garment_mesh_ref: Optional[str]
    body_fit_error_cm: dict[str, float]
    regions: dict[str, RegionResult]
    warnings: list[str]
    unknowns: list[str]
    provenance: Provenance
    advice_facts: list[str]
