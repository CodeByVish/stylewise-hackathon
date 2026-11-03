import base64
import io
import json

from stylewise_fit import preview as previews


def test_cached_preview_changes_when_body_or_photo_changes(tmp_path, monkeypatch):
    for name in ('fixtures/presets', 'fixtures/garment_photos', 'fit-engine/scripts',
                 'fit-engine/stylewise_fit/data'):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    mesh = tmp_path / 'fixtures/presets/female_rectangle_M_165.glb'
    mesh.write_bytes(b'body one')
    row = {'id': 'female_rectangle_M_165',
           'measured_cm': {'height': 165, 'chest': 92.5, 'waist': 78.5, 'hip': 94.5}}
    other = {'id': 'female_oval_XL_155', 'measured_cm': {'height': 155, 'chest': 107, 'waist': 100, 'hip': 108}}
    index = tmp_path / 'fixtures/presets/index.json'
    index.write_text(json.dumps([row, other]))
    (tmp_path / 'fit-engine/scripts/render_fit.py').write_text('guide')
    (tmp_path / 'fit-engine/stylewise_fit/data/catalogue_garments.json').write_text('{}')
    photo = tmp_path / 'fixtures/garment_photos/dress.jpg'
    photo.write_bytes(b'photo one')
    monkeypatch.setattr(previews, 'ROOT', tmp_path)
    monkeypatch.setattr(previews, 'PHOTOS', photo.parent)
    monkeypatch.setattr(previews, 'CACHE', tmp_path / 'cache')
    monkeypatch.setattr(previews, '_env', lambda _: 'test-key')
    monkeypatch.setattr(previews, 'guide_png', lambda *args: b'guide')
    from stylewise_fit import catalogue as catalogue_module
    monkeypatch.setattr(catalogue_module, 'catalogue', lambda: {'dress': {'name': 'Dress', 'category': 'dress'}})
    calls = []

    def generate(request, timeout):
        calls.append(request)
        content = base64.b64encode(f'image {len(calls)}'.encode()).decode()
        return io.BytesIO(json.dumps({'data': [{'b64_json': content}]}).encode())

    monkeypatch.setattr(previews.urllib.request, 'urlopen', generate)
    args = ('rectangle', 'M', 'female', 165, 'dress', 'M')
    assert previews.preview(*args) == b'image 1'
    assert previews.preview(*args) == b'image 1'
    other['measured_cm']['waist'] = 101  # a different preset re-fitted: this image stays valid
    index.write_text(json.dumps([row, other]))
    assert previews.preview(*args) == b'image 1'
    mesh.write_bytes(b'body two')
    assert previews.preview(*args) == b'image 2'
    photo.write_bytes(b'photo two')
    assert previews.preview(*args) == b'image 3'


def test_cache_only_deployment_never_calls_the_model(monkeypatch):
    from fastapi.testclient import TestClient
    from stylewise_fit.server import app

    monkeypatch.setattr(previews, '_env', lambda name: '1' if name == 'PREVIEW_CACHE_ONLY' else 'key')
    monkeypatch.setattr(previews.urllib.request, 'urlopen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('paid call')))
    r = TestClient(app).post('/preview/photo', json={
        'body': {'source': 'preset', 'height_cm': 155, 'preset': {'shape': 'oval', 'usual_size': 'XL', 'sex': 'female'}},
        'garment_id': 'emerald-wrap-dress', 'size': 'XS', 'view': 'back'})
    assert r.status_code == 404 and 'pre-generated' in r.json()['detail']
