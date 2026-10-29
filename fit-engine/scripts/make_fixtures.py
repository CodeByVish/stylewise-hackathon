"""Regenerate contracts/*.schema.json and fixtures/ from the Python source of truth.

Run from fit-engine/:  .venv/bin/python scripts/make_fixtures.py
"""
import json
from pathlib import Path

from stylewise_fit.body import Measurements, landmark_heights_m, mannequin_mesh
from stylewise_fit.fit import evaluate
from stylewise_fit.measure import circumference_at_height, height_cm
from stylewise_fit.schemas import FitReport, FitRequest

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS, FIXTURES = ROOT / "contracts", ROOT / "fixtures"

BODIES = {
    "A": Measurements(165, 90, 74, 98),
    "B": Measurements(178, 104, 90, 102),
    "C": Measurements(155, 84, 68, 92),
}
# Synthetic size chart for development only; P1 replaces with a sourced chart.
GARMENTS = {
    "S": {"chest": 86, "waist": 72, "hip": 94, "length": 66},
    "M": {"chest": 98, "waist": 84, "hip": 104, "length": 68},
}


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n")


def main() -> None:
    CONTRACTS.mkdir(exist_ok=True)
    (FIXTURES / "meshes").mkdir(parents=True, exist_ok=True)
    dump(CONTRACTS / "fit_request.schema.json", FitRequest.model_json_schema())
    dump(CONTRACTS / "fit_report.schema.json", FitReport.model_json_schema())

    for size, spec in GARMENTS.items():
        dump(FIXTURES / f"garment_top_{size}.json", {
            "id": "top-01", "category": "top", "size": size, "spec_cm": spec,
            "spec_source": "SYNTHETIC fixture chart (replace with sourced chart)",
            "mesh_ref": f"fixtures/meshes/garment_top_{size}.glb",
        })

    for name, m in BODIES.items():
        mesh = mannequin_mesh(m)
        mesh_ref = f"fixtures/meshes/body_{name}.glb"
        mesh.export(ROOT / mesh_ref)
        measured = {"height": height_cm(mesh)}
        for lm, y in landmark_heights_m(m.height_cm).items():
            measured[lm] = circumference_at_height(mesh, y)
        error = {k: round(measured[k] - getattr(m, f"{k}_cm"), 2) for k in measured}
        dump(FIXTURES / f"body_{name}.json", {
            "id": f"body_{name}", "mesh_ref": mesh_ref, "model": "mannequin-v0",
            "target_cm": m.__dict__, "measured_cm": {k: round(v, 2) for k, v in measured.items()},
            "fit_error_cm": error,
        })
        for size in GARMENTS:
            req = FitRequest.model_validate({
                "body": {"height_cm": m.height_cm, "chest_cm": m.chest_cm,
                         "waist_cm": m.waist_cm, "hip_cm": m.hip_cm},
                "garment": json.loads((FIXTURES / f"garment_top_{size}.json").read_text()),
            })
            dump(FIXTURES / f"req_{name}_{size}.json", req.model_dump())
            report = evaluate(req, body_mesh_ref=mesh_ref, body_fit_error_cm=error)
            dump(FIXTURES / f"report_{name}_{size}.json", report.model_dump())
    print(f"wrote {CONTRACTS} and {FIXTURES}")


if __name__ == "__main__":
    main()
