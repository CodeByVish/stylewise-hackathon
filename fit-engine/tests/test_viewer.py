import io

import trimesh
from fastapi.testclient import TestClient

from stylewise_fit.server import app

client = TestClient(app)


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
