# Stylewise shared contract v0.4.0

**Changes in v0.4.0:** fabric and stretch.
- `garment.fabric` (e.g. `silk`, `velvet`, `cotton elastane`) and `garment.stretch_cm` (`{region: cm}`, the mechanical give of an elastic or drawstring waist taken from the size chart's range).
- `regions.*.stretch_cm`: how far the garment can give at that region (fabric + elastic).
- A region that fits **only when stretched** is `borderline`, with an `advice_facts` line saying so. Thick fabrics (velvet, wool) raise the minimum ease. Unknown fabric goes into `unknowns`. These rules are project heuristics (`fit-engine/stylewise_fit/fabric.py`), not measurements.
- New endpoints: `GET /catalogue` (Stylewise catalogue items, and whether they have sourced garment cm) and `POST /fit/outfit` (`{body, items: [{garment_id, size}], preferences}` → one FitReport per piece). The source is `fit-engine/scripts/make_catalogue_garments.py`: Indubindu garment chart for kurtas, trousers and kurta sets; blouses, skirts and dresses have no sourced chart yet.

**Changes in v0.3.0:**
- `body.preset.sex` (`female` or `male`, default `female`): picks the size chart and shape prototypes.
- `usual_size` adds `2XL` and `3XL`.
- The size chart is now **ANSUR II** (real data), not synthetic. The uncertainty is ±2.7 cm (women) / ±2.85 cm (men), down from ±4.
- Preset ids are now `<sex>_<shape>_<size>_<height>` (e.g. `female_rectangle_M_165`), and height snaps to the nearest generated stature.
- Preset reports set `body_mesh_ref` to `fixtures/presets/<id>.glb`.

**v0.2.0** added body presets: `body.source`, `body.preset`, `regions.*.uncertainty_cm`, the `borderline` verdict and `provenance.body_preset_id`.

All v0.1.0 and v0.2.0 requests are still valid.

The source of truth is `fit-engine/stylewise_fit/schemas.py`. The JSON Schemas here are generated from it by `fit-engine/scripts/make_fixtures.py`. Don't edit them by hand. If you need a change, tell P0 so the version can be bumped.

## FitRequest → FitReport
- **FitRequest** ([schema](fit_request.schema.json)) contains:
  - `body`: `height_cm` (required); `chest_cm`, `waist_cm` and `hip_cm` (optional); `pose` (`standing` or `seated`); `source` and `preset {shape, usual_size, sex}`.
  - `garment`: `id`, `category`, `size`, `spec_cm{chest,waist,hip,length}`, `spec_source` and `mesh_ref`.
  - `preferences`: `closure` and `fit_pref` (`snug`, `regular` or `relaxed`).
- **FitReport** ([schema](fit_report.schema.json)) contains:
  - `regions.{chest,waist,hip}`, each with `{body_cm, garment_cm, ease_cm, uncertainty_cm, verdict}`. `verdict` is one of `tight`, `ok`, `loose`, `borderline` or `unknown`.
  - `body_mesh_ref`, `warnings`, `unknowns`, `provenance` and `body_fit_error_cm`.
  - `advice_facts`: the only statements Nisha may paraphrase.
- HTTP: `POST /fit/evaluate` (FitRequest → FitReport, 422 on invalid input) and `GET /health`. Run with `uvicorn stylewise_fit.server:app --port 8000` from `fit-engine/`.

Rules:
- `ease_cm = garment − body` is arithmetic only. It is not a comfort claim.
- A missing measurement → `verdict: "unknown"` and an entry in `unknowns`. It is never estimated.
- `spec_source` must name a real size chart. LLM-derived dimensions are not allowed.

## Body presets (for users who don't share measurements)
The user picks a **silhouette** (no shape words in the UI, just the drawing and a neutral name), their sex, their usual size and their height. The engine estimates the girths with a ± range of half a size interval. A region's verdict is `borderline` if it would change anywhere inside that range. Any girth the user does type in overrides the estimate.

**Sizes** come from ANSUR II (US Army 2012, public domain; 1,986 women, 4,082 men), built with the ISO 8559-3 approach: chest is the primary dimension (ISO 8559-2), the central 90% (P5–P95) is split into XS–XL, and 2XL/3XL continue the same interval width above P95 so larger bodies are included. Source: `fit-engine/scripts/ansur_sizes.py` → `fit-engine/stylewise_fit/data/size_chart_ansur2.json`.

| Chest/bust cm | XS | S | M | L | XL | 2XL | 3XL |
|---|---|---|---|---|---|---|---|
| Women | 85.1 | 90.5 | 95.9 | 101.3 | 106.7 | 112.1 | 117.5 |
| Men | 95.1 | 100.8 | 106.4 | 112.2 | 117.8 | 123.6 | 129.2 |

Limitation: ANSUR II is a military sample (fitter and younger than the general public, US only). Demographic-specific charts can be added later as further entries in the size chart file.

**Shapes** are the five standard apparel categories. The boundaries follow FFIT (Simmons, Istook & Devarajan 2004), converted from inches. Each preset is a prototype well inside its category. Source: `fit-engine/stylewise_fit/presets.py`.

| id (internal) | Display name | Women: waist − bust / hip − bust | Men: waist − chest / hip − chest |
|---|---|---|---|
| `hourglass` | The Balance | −25 / +1 | −24 / 0 (hand-placed; n=0 in ANSUR men) |
| `triangle` | The Anchor | −8 / +12 | −2 / +11 (hand-placed; n=7) |
| `inverted_triangle` | The Summit | −18 / −12 | −14 / −11 (ANSUR median, n=532) |
| `rectangle` | The Column | −14 / +2 | −12.5 / −2.5 (ANSUR median, n=2987) |
| `oval` | The Orbit | −2 / −3 | −4.5 / −5 (ANSUR median, n=505) |

Notes:
- Display names are placeholders, so rename them freely.
- Generated heights: women 155/165/175 cm, men 165/175/185 cm. The 3D files are `fixtures/presets/<id>.glb`, listed in `fixtures/presets/index.json`.
- All five shapes are offered to both sexes, for inclusivity, even where ANSUR II has few such bodies.

## GLB conventions (bodies and garments)
- Units are **meters**, **Y-up**, and the origin is on the floor between the feet. The body faces **+Z**.
- The body is in a neutral standing pose. The fixture mannequin is a lofted torso/legs shell, not anatomical.
- A garment GLB must be authored in the same frame, so it can be dropped onto the body with an identity transform.
- One mesh per file. Use a single name per GLB (e.g. `garment_top_M`), so the viewer can toggle sizes by swapping files.
- Landmark heights as a fraction of stature, for the **mannequin** only: hip 0.52, waist 0.62, chest 0.72. MHR bodies search for landmarks instead (chest = max girth at 69–74% of stature, waist = min at 56–69%, hip = max at 46–56%).

## Fixtures (`/fixtures`)
| File | Purpose |
|---|---|
| `body_{A,B,C}.json` + `meshes/body_*.glb` | Target vs measured cm for each mannequin body (error < 0.05 cm). |
| `garment_top_{S,M}.json` | **Synthetic** size chart. P1 replaces it with a sourced chart and provides `meshes/garment_top_*.glb`. |
| `req_{A,B,C}_{S,M}.json` / `report_*.json` | Example request and the expected engine output. Build the viewer against these. |

Body A with size M: chest +8 cm and waist +10 cm (ok). With size S: −4 cm and −2 cm (tight).
