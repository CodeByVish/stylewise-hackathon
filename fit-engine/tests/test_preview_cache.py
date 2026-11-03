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
    assert r.status_code == 404 and "isn't prepared yet" in r.json()['detail']


def test_daily_budget_allows_live_try_ons_then_stops(tmp_path, monkeypatch):
    env = {'PREVIEW_DAILY_LIMIT': '2', 'MODEL_API_KEY': 'key'}
    monkeypatch.setattr(previews, '_env', lambda name: env.get(name))
    monkeypatch.setattr(previews, '_BUDGET', {'day': None, 'used': 0})
    previews._spend_budget(); previews._spend_budget()  # two new images allowed today
    import pytest
    with pytest.raises(previews.CacheOnly):
        previews._spend_budget()


def test_exhausted_primary_key_switches_to_backup(monkeypatch):
    import io, json, urllib.error
    env = {'MODEL_API_KEY': 'primary', 'MODEL_API_KEY_BACKUP': 'backup'}
    monkeypatch.setattr(previews, '_env', lambda name: env.get(name))
    monkeypatch.setattr(previews, 'KEY_STATUS', {'active': 'primary', 'switched_at': None, 'reason': None})
    used = []

    def fake(req, timeout=0):
        key = req.headers['Authorization'].split()[-1]; used.append(key)
        if key == 'primary':
            raise urllib.error.HTTPError(req.full_url, 402, 'Payment Required', {}, io.BytesIO(b'{"error":"insufficient credits"}'))
        return io.BytesIO(json.dumps({'data': [{'b64_json': 'aGk='}]}).encode())

    monkeypatch.setattr(previews.urllib.request, 'urlopen', fake)
    assert previews._generate({}, previews.api_keys()) == {'b64_json': 'aGk='}
    assert used == ['primary', 'backup'] and previews.KEY_STATUS['active'] == 'backup'
    assert previews.api_keys() == ['backup']  # later images go straight to the backup key


def test_cache_hits_never_spend_the_daily_budget(tmp_path, monkeypatch):
    import json as _json
    row = {'id': 'female_rectangle_M_165', 'measured_cm': {'height': 165, 'chest': 92.5, 'waist': 78.5, 'hip': 94.5}}
    for name in ('fixtures/presets', 'fixtures/garment_photos', 'fit-engine/scripts'):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / 'fixtures/presets/female_rectangle_M_165.glb').write_bytes(b'body')
    (tmp_path / 'fixtures/presets/index.json').write_text(_json.dumps([row]))
    (tmp_path / 'fit-engine/scripts/render_fit.py').write_text('guide')
    (tmp_path / 'fixtures/garment_photos/dress.jpg').write_bytes(b'photo')
    env = {'PREVIEW_DAILY_LIMIT': '1', 'MODEL_API_KEY': 'key'}
    monkeypatch.setattr(previews, 'ROOT', tmp_path)
    monkeypatch.setattr(previews, 'PHOTOS', tmp_path / 'fixtures/garment_photos')
    monkeypatch.setattr(previews, 'CACHE', tmp_path / 'cache')
    monkeypatch.setattr(previews, '_env', lambda name: env.get(name))
    monkeypatch.setattr(previews, '_BUDGET', {'day': None, 'used': 0})
    monkeypatch.setattr(previews, 'guide_png', lambda *args: b'guide')
    from stylewise_fit import catalogue as catalogue_module
    monkeypatch.setattr(catalogue_module, 'catalogue', lambda: {'dress': {'name': 'Dress', 'category': 'dress', 'sizes': {}}})
    calls = []
    monkeypatch.setattr(previews.urllib.request, 'urlopen',
                        lambda req, timeout=0: calls.append(1) or io.BytesIO(_json.dumps({'data': [{'b64_json': 'aGk='}]}).encode()))
    args = ('rectangle', 'M', 'female', 165, 'dress', 'M')
    assert previews.preview(*args) == b'hi'          # miss: one paid image, the whole budget of 1
    for _ in range(5):
        assert previews.preview(*args) == b'hi'      # hits: served from the cache, no budget, no call
    assert len(calls) == 1 and previews._BUDGET['used'] == 1
