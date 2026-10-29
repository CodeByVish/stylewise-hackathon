# Stylewise shared contract v0.1.0 (frozen Oct 29)

The source of truth is `fit-engine/stylewise_fit/schemas.py`. The JSON Schemas here are generated from it by `fit-engine/scripts/make_fixtures.py`. Don't edit them by hand. If you need a change, tell P0 so the version can be bumped.

## FitRequest → FitReport
- **FitRequest** ([schema](fit_request.schema.json)) contains:
  - `body`: `height_cm` (required); `chest_cm`, `waist_cm` and `hip_cm` (optional); `pose` (`standing` or `seated`).
  - `garment`: `id`, `category`, `size`, `spec_cm{chest,waist,hip,length}`, `spec_source` and `mesh_ref`.
  - `preferences`: `closure` and `fit_pref` (`snug`, `regular` or `relaxed`).
- **FitReport** ([schema](fit_report.schema.json)) contains:
  - `regions.{chest,waist,hip}`, each with `{body_cm, garment_cm, ease_cm, verdict}`. `verdict` is one of `tight`, `ok`, `loose` or `unknown`.
  - `warnings`, `unknowns`, `provenance` and `body_fit_error_cm`.
  - `advice_facts`: the only statements Nisha may paraphrase.

Rules:
- `ease_cm = garment − body` is arithmetic only. It is not a comfort claim.
- A missing measurement → `verdict: "unknown"` and an entry in `unknowns`. It is never estimated.
- `spec_source` must name a real size chart. LLM-derived dimensions are not allowed.

## GLB conventions (bodies and garments)
- Units are **meters**, **Y-up**, and the origin is on the floor between the feet. The body faces **+Z**.
- The body is in a neutral standing pose. The fixture mannequin is a lofted torso/legs shell, not anatomical.
- A garment GLB must be authored in the same frame, so it can be dropped onto the body with an identity transform.
- One mesh per file. Use a single name per GLB (e.g. `garment_top_M`), so the viewer can toggle sizes by swapping files.
- Landmark heights as a fraction of stature: hip 0.52, waist 0.62, chest 0.72.

## Fixtures (`/fixtures`)
| File | Purpose |
|---|---|
| `body_{A,B,C}.json` + `meshes/body_*.glb` | Target vs measured cm for each mannequin body (error < 0.05 cm). |
| `garment_top_{S,M}.json` | **Synthetic** size chart. P1 replaces it with a sourced chart and provides `meshes/garment_top_*.glb`. |
| `req_{A,B,C}_{S,M}.json` / `report_*.json` | Example request and the expected engine output. Build the viewer against these. |

Body A with size M: chest +8 cm and waist +10 cm (ok). With size S: −4 cm and −2 cm (tight).
