"""Populate the seven demo combinations after final preset assets are installed.

Run from the repository root:
  PYTHONPATH=fit-engine fit-engine/.venv/bin/python fit-engine/scripts/generate_demo_previews.py

Existing results are reused only when the body, source photo, guide and inputs match.
"""
import hashlib
import json
from pathlib import Path

from stylewise_fit.catalogue import garment_input
from stylewise_fit.fit import evaluate
from stylewise_fit.preview import ROOT, fit_notes, photo_path, preview
from stylewise_fit.schemas import BodyInput, FitRequest, Preferences

INDEX = ROOT / 'fixtures/presets/index.json'
# Two verified product examples on three body sizes, plus the men's short kurta.
# Holding the garment at M makes the core claim visible: the same garment becomes
# loose, appropriate or tight as the shopper's body changes. Body size and garment
# size are deliberately independent controls in the app.
# PARTHVI's seller chart does not state whether it is a body or garment measurement.
COMBINATIONS = [
    *(("female", body_size, "zesica-black-midi-dress", "M") for body_size in ("S", "M", "L")),
    *(("female", body_size, "parthvi-anarkali-set", "M") for body_size in ("S", "M", "L")),
    ("male", "M", "manyavar-mens-kurta", "M"),
    # one body, three garment sizes: only the dress changes, so the fit difference is unambiguous
    *(("female", "M", "zesica-black-midi-dress", garment_size) for garment_size in ("S", "L")),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before = digest(INDEX)
    rows = {r['id']: r for r in json.loads(INDEX.read_text())}
    for sex, body_size, garment, size in COMBINATIONS:
        height = 165 if sex == 'female' else 175
        pid = f'{sex}_rectangle_{body_size}_{height}'
        row = rows[pid]
        if not row.get('accepted', False):
            raise RuntimeError(f'{pid} is not an accepted preset; complete and validate the cluster job first')
        if not photo_path(garment):
            raise RuntimeError(f'{garment} has no product photo')
        mesh = ROOT / 'fixtures/presets' / f'{pid}.glb'
        mesh_hash = digest(mesh)
        body = BodyInput(source='preset', height_cm=height,
                         preset={'shape': 'rectangle', 'usual_size': body_size, 'sex': sex})
        report = evaluate(FitRequest(body=body, garment=garment_input(garment, size),
                                     preferences=Preferences(fit_pref='regular')))
        notes = fit_notes(report)
        for view in ('front', 'side', 'back'):
            if digest(INDEX) != before or digest(mesh) != mesh_hash:
                raise RuntimeError('Preset assets changed during generation; rerun after the cluster job finishes')
            # garment-specific prompt notes live in preview.py, so the app requests the same cached images
            preview('rectangle', body_size, sex, height, garment, size, 'mannequin', notes, view)
            print(f'{pid} {garment} garment-{size} {view}: ready', flush=True)


if __name__ == '__main__':
    main()
