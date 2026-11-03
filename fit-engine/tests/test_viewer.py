from pathlib import Path
import io

import trimesh
import numpy as np
from fastapi.testclient import TestClient

from stylewise_fit.server import app
from stylewise_fit.viewer import renderer

client = TestClient(app)


def test_loose_trouser_offset_does_not_cross_the_crotch():
    body = trimesh.load(Path(__file__).resolve().parents[2] / 'fixtures/presets/female_rectangle_XL_165.glb', force='mesh', process=False)
    render = renderer()
    heights = body.vertices[body.faces][:, :, 1]
    landmarks = render.landmark_heights(body)
    keep = (~render.ARM_FACES) & (heights.max(1) >= 0.1) & (heights.min(1) <= render.waistband(landmarks))
    mesh = render.smooth_base(body).submesh([np.flatnonzero(keep)], append=True)
    before = np.asarray(mesh.vertices).copy()
    render.offset_trousers(mesh, lambda y: np.full_like(y, 0.07))
    after = np.asarray(mesh.vertices)
    assert np.all(before[:, 0] * after[:, 0] >= -1e-12)


def test_preset_scene_has_body_and_selected_garment():
    response = client.post('/viewer/scene', json={
        'body': {'source': 'preset', 'height_cm': 165,
                 'preset': {'shape': 'rectangle', 'usual_size': 'M', 'sex': 'female'}},
        'items': [{'garment_id': 'green-kurta', 'size': 'M'}],
    })
    assert response.status_code == 200
    assert response.content[:4] == b'glTF'
    scene = trimesh.load(io.BytesIO(response.content), file_type='glb')
    assert 'body' in scene.graph.nodes_geometry
    assert 'green-kurta:M' in scene.graph.nodes_geometry


def test_measured_scene_is_explicitly_unsupported():
    response = client.post('/viewer/scene', json={
        'body': {'height_cm': 168, 'chest_cm': 90, 'waist_cm': 74, 'hip_cm': 96},
        'items': [{'garment_id': 'green-kurta', 'size': 'M'}],
    })
    assert response.status_code == 422


def test_unknown_garment_is_rejected():
    response = client.post('/viewer/scene', json={
        'body': {'source': 'preset', 'height_cm': 165,
                 'preset': {'shape': 'rectangle', 'usual_size': 'M'}},
        'items': [{'garment_id': '../../secret', 'size': 'M'}],
    })
    assert response.status_code == 422
