"""Write experiments/results/preset_landmark_heights.json (landmark heights as fractions of stature),
which stylewise_fit.viewer reads. Run after regenerating presets:
  .venv/bin/python scripts/landmark_heights.py
"""
import json
from pathlib import Path

import trimesh

from render_fit import landmark_heights

ROOT = Path(__file__).resolve().parents[2]
out = {}
for r in json.loads((ROOT / "fixtures/presets/index.json").read_text()):
    m = trimesh.load(ROOT / r["mesh_ref"], force="mesh", process=False)
    out[r["id"]] = {k: round(float(v / m.bounds[1, 1]), 4) for k, v in landmark_heights(m).items()}
(ROOT / "fit-engine/experiments/results/preset_landmark_heights.json").write_text(json.dumps(out, indent=1) + "\n")
print(len(out), "presets")
