"""Put the featureless store-mannequin head (mhr_body.mannequin_head) on existing preset GLBs in place.
Head shape is cosmetic: no landmark or girth is measured on the head, so index.json is unchanged.
  PYTHONPATH=fit-engine research/mhr-env/bin/python -W ignore fit-engine/scripts/apply_mannequin_heads.py
"""
import json
from pathlib import Path

import numpy as np
import trimesh

from stylewise_fit.mhr_body import mannequin_head

ROOT = Path(__file__).resolve().parents[2]
index = json.loads((ROOT / "fixtures/presets/index.json").read_text())
for r in index:
    path = ROOT / r["mesh_ref"]
    m = trimesh.load(path, force="mesh", process=False)
    m.vertices = mannequin_head(np.asarray(m.vertices))
    m.export(path)
print(len(index), "preset heads updated")
