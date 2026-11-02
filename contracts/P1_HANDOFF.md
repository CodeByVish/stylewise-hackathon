# P0 → P1 handoff (contract v0.4.0)

Everything P1 needs from P0 to wire the Fit Lab to real data. Field-level rules are in [README.md](README.md).

## 1. Fit API

Run from `fit-engine/`:
```bash
uv pip install -e ".[api]"          # or: pip install -e ".[api]"
uvicorn stylewise_fit.server:app --port 8000
```
For Nisha on Muse, put your own key (from your dev.meta.ai account) in the repo-root `.env` as `META_API_KEY=...`. The model defaults to `muse-spark-1.3` (override with `MUSE_MODEL`). Without a key, Nisha answers from a fixed template instead.

| Endpoint | In → out |
|---|---|
| `GET /health` | `{"ok", "engine_version", "contract_version": "0.4.0", "muse": true/false}` |
| `POST /fit/evaluate` | FitRequest → FitReport (422 with field errors on bad input) |
| `GET /catalogue` | Stylewise catalogue items: `garment_id`, `name`, `category`, `fabric`, `sizes`, `fittable` |
| `POST /fit/outfit` | `{"body", "items": [{"garment_id", "size"}], "preferences"}` → one `{garment_id, size, report, error}` per piece |
| `POST /nisha/chat` | `{"messages", "context"}` → `{"reply", "report", "source": "muse" \| "engine-template"}` |

CORS allows `http://localhost:3000`. Schemas: [fit_request.schema.json](fit_request.schema.json), [fit_report.schema.json](fit_report.schema.json).

**Sample: an outfit on measured inputs** (the Fit Lab form, 168 / 90 / 74 / 96):
```json
{
  "body": {"height_cm": 168, "chest_cm": 90, "waist_cm": 74, "hip_cm": 96},
  "items": [{"garment_id": "green-kurta", "size": "M"}, {"garment_id": "gold-trousers", "size": "M"}],
  "preferences": {"fit_pref": "regular"}
}
```
Kurta: chest +9 ok, waist +17 loose. Trousers: waist +12 ok (elastic waist, `stretch_cm` 6), hip +6 ok.

**Sample: preset body** (user skips measurements): replace `body` with
`{"source": "preset", "height_cm": 168, "preset": {"shape": "rectangle", "usual_size": "M", "sex": "female"}}`.
The report then has `uncertainty_cm` ±2.7, possibly `borderline`, and `body_mesh_ref: "fixtures/presets/female_rectangle_M_165.glb"`.

**UI rules:**
- Show only `advice_facts` as explanatory text. Show `unknowns` under "What we don't know yet" and `warnings` visibly. Every estimated or unverified chart carries a warning.
- `borderline` means "could go either way", including "fits only if the garment stretches". Never show it as ok.
- Never compute ease in the frontend. Use `regions.*.ease_cm` and `regions.*.stretch_cm`.

## 2. Garments (`GET /catalogue`)

| Items | Where the cm come from | Engine warning |
|---|---|---|
| 3 kurtas, 3 trousers, 6 kurta sets | Indubindu garment chart (brand page, garment measurements) | none |
| `uniqlo-crew-tee` | Uniqlo SG product E465193, Product Size table | none (a Uniqlo L is tight on a general L body: brand sizing differs) |
| `uniqlo-dress-E487286` | Uniqlo SG product E487286, Product Size table; cotton stretch | none |
| blouse, shell top, 2 skirts, 2 dresses, `reference-dress` | **Estimated**: Uniqlo body chart + design-ease guess | "no verified source" |
| Fit Lab `top-01` (S, M) | synthetic fixture | "no verified source" |

The source of all of these is `fit-engine/scripts/make_catalogue_garments.py`, and each item's `spec_source` says exactly where its numbers came from.

## 3. Bodies and GLB conventions

- Meters, **Y-up**, origin on the floor between the feet, the body faces **+Z**, A-pose.
- **MHR presets (final, 2026-11-02):** `fixtures/presets/<sex>_<shape>_<size>_<height>.glb`. 210 files: female 155/165/175 cm, male 165/175/185 cm, XS–3XL, five shapes (The Balance / The Anchor / The Summit / The Column / The Orbit). All 210 are within their stated ± range. Women's presets have female proportions. `index.json` lists each preset's targets, fitted girths and errors.
- Mannequin fixtures: `fixtures/meshes/body_{A,B,C}.glb`.

## 4. Garment-on-body view

```bash
cd fit-engine
.venv/bin/python scripts/render_fit.py female_rectangle_M_165 green-kurta:M gold-trousers:M
.venv/bin/python scripts/render_fit.py female_triangle_M_165,female_oval_XL_165 emerald-wrap-dress:M   # several bodies
```
- Writes `fixtures/fits/<name>.png` (front/side/back, with dashed lines and verdicts at chest/waist/hip).
- For a single body it also writes `<name>.glb`: the body plus each garment as a separate node, vertex-coloured. **Load the GLB in the orbit viewer for 360°.**
- Garments are a **fit shell**: the body pushed out by the garment's ease. Skirts, dresses, kurtas and long tops hang as one piece below the hip; sleeves are typical lengths per garment type. It shows the room a garment leaves, **not cloth drape** (no folds or gravity). Say so in the UI.

## 5. SAM

See [docs/SAM_ACCESS.md](../docs/SAM_ACCESS.md). Meta Model API, `POST https://api.meta.ai/v1/responses`, `model: "sam-3.1"`, with your own `MODEL_API_KEY`. Verified on 2026-11-02 with `fit-engine/scripts/sam_smoke.py`. Masks are for display only; pixels are never turned into cm.

## 6. Nisha voice/text

Ported from the Stylewise app (`Vishakha-Kulkarni/stylewise`, branch `riddhimajain/finaltouches`): persona and voice only. Runs on **Meta Muse Spark**.
- `context`: `{"body": {...}, "garment_id": "green-kurta", "garment_size": "M", "preferences": {...}}`. Pass the item the user is looking at. Without `garment_id` it uses `top-01`.
- Muse calls `evaluate_fit`. Garment cm always come from our charts, and Nisha may only repeat the report's facts.
- Frontend:
  - `src/lib/nisha.ts`: `askNisha(messages, context)`, set `NEXT_PUBLIC_FIT_API_URL`.
  - Voice in: `src/hooks/useSpeechInput.ts` (Whisper in the browser).
  - Voice out: `src/hooks/useSpokenReplies.ts` (Kokoro in the browser, or `scripts/voice/server.py` on port 8081).
  - Run `npm install` first.

## 7. Branch

P0's work is on `riddhimakain/MHRsetup`: the API, contract v0.4.0, ANSUR II sizes, MHR presets, catalogue charts, Nisha, the fit view and the cluster scripts.
