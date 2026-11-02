"""Browser GLB adapter for P0's existing fit-shell renderer; no cloth simulation."""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import trimesh

from .catalogue import catalogue, garment_input
from .fit import evaluate
from .presets import preset_id
from .schemas import BodyInput, FitRequest, Preferences

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def renderer():
    spec = importlib.util.spec_from_file_location("stylewise_render_fit", ROOT / "fit-engine/scripts/render_fit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=24)
def scene_bytes(payload: str) -> bytes:
    data = json.loads(payload)
    body_input = BodyInput.model_validate(data['body'])
    if body_input.source != 'preset':
        raise ValueError('A fit-shell scene requires a preset body; measured-body fitting is not enabled here.')
    preset = body_input.preset
    pid = preset_id(preset.shape, preset.usual_size, body_input.height_cm, preset.sex)
    body = trimesh.load(ROOT / f'fixtures/presets/{pid}.glb', force='mesh', process=False)
    render = renderer()
    landmark_file = ROOT / 'fit-engine/experiments/results/preset_landmark_heights.json'
    fractions = json.loads(landmark_file.read_text())[pid]
    landmarks = {key: value * body.bounds[1, 1] for key, value in fractions.items()}
    scene = trimesh.Scene()
    body.visual = trimesh.visual.ColorVisuals(mesh=body, vertex_colors=np.tile([204, 184, 168, 255], (len(body.vertices), 1)))
    scene.add_geometry(body, node_name='body')
    preferences = Preferences.model_validate(data.get('preferences', {}))
    for piece in data['items']:
        gid, size = piece['garment_id'], piece['size']
        garment = garment_input(gid, size)
        report = evaluate(FitRequest(body=body_input, garment=garment, preferences=preferences))
        item = catalogue()[gid]
        result = render.shell(body, report, gid, item['name'], item['category'], landmarks)
        if result:
            mesh, rgb, _ = result
            mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=np.column_stack([rgb * 255, np.full(len(rgb), 255)]).astype(np.uint8))
            scene.add_geometry(mesh, node_name=f'{gid}:{size}')
    return scene.export(file_type='glb', include_normals=True)
