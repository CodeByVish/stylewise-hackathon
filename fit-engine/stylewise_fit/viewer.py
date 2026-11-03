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


VERDICT_BANDS = {'tight': (0.80, 0.25, 0.22), 'borderline': (0.90, 0.65, 0.18), 'loose': (0.30, 0.50, 0.82)}


def solid(mesh: trimesh.Trimesh, rgb, roughness: float = 0.82) -> trimesh.visual.TextureVisuals:
    """Opaque, double-sided PBR material: open garment shells must not turn see-through when a
    face points inward (glTF materials are single-sided by default)."""
    # glTF base colours are linear; our colours are sRGB (sampled from product photos)
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    material = trimesh.visual.material.PBRMaterial(
        baseColorFactor=[*(int(round(255 * c)) for c in linear), 255], metallicFactor=0.0, roughnessFactor=roughness,
        doubleSided=True, alphaMode='OPAQUE')
    return trimesh.visual.TextureVisuals(material=material)


# mannequin finishes the shopper can pick; grey matches the realistic view
TONES = {"grey": [0.62, 0.62, 0.63], "light": [0.93, 0.80, 0.70], "medium": [0.78, 0.60, 0.45],
         "tan": [0.62, 0.45, 0.32], "deep": [0.40, 0.27, 0.19]}


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
    tone = TONES.get(data.get('tone') or 'grey', TONES['grey'])
    body.visual = solid(body, tone, roughness=0.68)  # matte mannequin finish, grey by default
    scene.add_geometry(body, node_name='body')
    # Modesty layer for the 3D view, built here (not in render_fit, so cached AI images stay valid): briefs
    # from the smoothed body surface, 6 mm out, so no anatomy reads through, cut just below the crotch;
    # a bra band for women. Dark charcoal so it reads as opaque fabric against the grey mannequin.
    H = body.bounds[1, 1]
    ys = body.vertices[body.faces][:, :, 1]
    top = render.waistband(landmarks) - 0.02 * H
    keep = (~render.ARM_FACES) & (ys.max(1) >= 0.452 * H - 0.02) & (ys.min(1) <= top + 0.02)
    briefs = render.smooth_base(body).submesh([np.where(keep)[0]], append=True)
    briefs.vertices = briefs.vertices + briefs.vertex_normals * 0.006
    parts = [render.band(briefs, 0.452 * H, top)]
    if preset.sex == 'female':
        parts.append(render.skirt_tube(body, landmarks['chest'] + 0.012 * H, landmarks['chest'] - 0.045 * H,
                                       0.006, 0.0, rings=10))
    under = trimesh.util.concatenate(parts)
    under.visual = solid(under, [0.24, 0.24, 0.26], roughness=0.8)
    scene.add_geometry(under, node_name='underwear')
    # moulded mannequin hair (bob / crop), a shade darker than the body: no strands, no face
    hair_mesh, _ = render.hair(body, preset.sex)
    hair_mesh.visual = solid(hair_mesh, [c * 0.82 for c in tone], roughness=0.6)
    scene.add_geometry(hair_mesh, node_name='hair')
    items = [catalogue()[piece['garment_id']] for piece in data['items']]
    cuts = [render.cut_for(piece['garment_id'], it['name'], it['category']) for piece, it in zip(data['items'], items)]
    if render.needs_lower(cuts, [it['category'] for it in items]):  # never a bare-legged kurta
        pyjama, pyjama_rgb = render.styling_pyjama(body, landmarks, preset.sex)
        pyjama.visual = solid(pyjama, pyjama_rgb[0])
        scene.add_geometry(pyjama, node_name='pyjama (styling, not fitted)')
    preferences = Preferences.model_validate(data.get('preferences', {}))
    for piece in data['items']:
        gid, size = piece['garment_id'], piece['size']
        garment = garment_input(gid, size)
        report = evaluate(FitRequest(body=body_input, garment=garment, preferences=preferences))
        item = catalogue()[gid]
        result = render.shell(body, report, gid, item['name'], item['category'], landmarks)
        if result:
            mesh, rgb, _ = result
            mesh.visual = solid(mesh, rgb[0])
            scene.add_geometry(mesh, node_name=f'{gid}:{size}')
            # optional fit bands (off by default: on the shell they read as seams)
            for region, r in (report.regions.items() if data.get('bands') else []):
                if r.verdict not in VERDICT_BANDS or region not in landmarks:
                    continue
                y = landmarks[region]
                # torso only: the body's arm-free width at this height, plus the garment's room
                seg, fi = trimesh.intersections.mesh_plane(body, [0, 1, 0], [0, y, 0], return_faces=True)
                torso_x = np.abs(seg[~render.ARM_FACES[fi]].reshape(-1, 3)[:, 0]).max() + 0.04 if len(seg) else 0.25
                tc = mesh.triangles_center
                faces = np.where((np.abs(tc[:, 1] - y) < 0.0125) & (np.abs(tc[:, 0]) < torso_x))[0]
                if len(faces) == 0:
                    continue
                fit_band = mesh.submesh([faces], append=True)
                fit_band.vertices = fit_band.vertices + fit_band.vertex_normals * 0.002
                fit_band.visual = solid(fit_band, VERDICT_BANDS[r.verdict])
                scene.add_geometry(fit_band, node_name=f'{gid}:{size}:{region}:{r.verdict}')
    return scene.export(file_type='glb', include_normals=True)
