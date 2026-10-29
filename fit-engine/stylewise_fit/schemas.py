"""Pydantic mirrors of contracts/*.schema.json. Keep both in sync."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

CONTRACT_VERSION = "0.1.0"

Pose = Literal["standing", "seated"]
Verdict = Literal["tight", "ok", "loose", "unknown"]


class BodyInput(BaseModel):
    height_cm: float = Field(gt=100, lt=230)
    chest_cm: Optional[float] = Field(default=None, gt=50, lt=200)
    waist_cm: Optional[float] = Field(default=None, gt=40, lt=200)
    hip_cm: Optional[float] = Field(default=None, gt=50, lt=200)
    pose: Pose = "standing"


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
    verdict: Verdict


class Provenance(BaseModel):
    body_source: str
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
