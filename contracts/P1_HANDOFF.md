# P0 → P1 handoff (contract v0.3.0)

Everything P1 needs from P0 to wire the Fit Lab to real data. Items marked **TODO (Riddhima)** are not in the repo yet.

## 1. Fit API

Run from `fit-engine/`:
```bash
pip install -e ".[api]"            # or: uv pip install -e ".[api]"
uvicorn stylewise_fit.server:app --port 8000
```
- `GET /health` → `{"ok": true, "engine_version": "...", "contract_version": "0.3.0"}`
- `POST /fit/evaluate`: body = FitRequest JSON, response = FitReport JSON. Invalid input returns 422 with the field errors.
- CORS allows `http://localhost:3000` (the Next.js dev server).
- Schemas: [fit_request.schema.json](fit_request.schema.json), [fit_report.schema.json](fit_report.schema.json). Field rules: [README.md](README.md).

**Sample: measured body** (the Fit Lab screenshot's inputs: 168 / 90 / 74 / 96, size M):
```json
{
  "body": {"source": "measured", "height_cm": 168, "chest_cm": 90, "waist_cm": 74, "hip_cm": 96},
  "garment": {"id": "top-01", "category": "top", "size": "M",
              "spec_cm": {"chest": 98, "waist": 84, "hip": 104, "length": 68},
              "spec_source": "SYNTHETIC fixture chart (replace with sourced chart)",
              "mesh_ref": "fixtures/meshes/garment_top_M.glb"},
  "preferences": {"fit_pref": "regular"}
}
```
The response gives chest ease +8 and waist ease +10 (both `ok`), and hip ease +8, plus a warning that the size chart has no verified source.

**Sample: preset body** (user skips measurements):
```json
{
  "body": {"source": "preset", "height_cm": 168,
           "preset": {"shape": "rectangle", "usual_size": "M", "sex": "female"}},
  "garment": {"...": "same as above"}
}
```
The response includes `regions.*.uncertainty_cm` (±2.7), possibly `verdict: "borderline"`, `provenance.body_preset_id: "female_rectangle_M_165"` and `body_mesh_ref: "fixtures/presets/female_rectangle_M_165.glb"`.

**UI rules:**
- Show only `advice_facts` as explanatory text. Show `unknowns` under "What we don't know yet" (as the current design already does).
- Show `borderline` as "could go either way", never as ok/tight.
- Never compute ease in the frontend. Use `regions.*.ease_cm`.

Ready-made request/response pairs: `fixtures/req_{A,B,C}_{S,M}.json` → `fixtures/report_*.json`.

## 2. Body GLB conventions

- Meters, **Y-up**, origin on the floor between the feet, the body faces **+Z**, one mesh per file.
- **Mannequin fixtures:** `fixtures/meshes/body_{A,B,C}.glb` (lofted shell, exact girths).
- **MHR preset bodies:** `fixtures/presets/<sex>_<shape>_<size>_<height>.glb`. That's 210 files: female 155/165/175 cm, male 165/175/185 cm, sizes XS–3XL, and shapes hourglass / triangle / inverted_triangle / rectangle / oval (display names: The Balance / The Anchor / The Summit / The Column / The Orbit). `fixtures/presets/index.json` lists the targets, fitted girths and errors for each.
- MHR bodies are in an **A-pose** (arms ~45° down), and each file is ~650 KB with 18k vertices. The garment must be authored in the same frame so it drops on with an identity transform.
- **Heads up:** the MHR presets are being regenerated with ISO-style bust/waist/hip landmarks and a female/male shoulder-to-hip cue, so women's presets no longer look male. File names and conventions stay the same. Use the new `fixtures/presets/` once it lands; until then the mannequin is the safer default for demos.

## 3. Garment and size measurements

- Current fixture: `top-01` ("The everyday top"), sizes S and M, in `fixtures/garment_top_{S,M}.json`:

  | size | chest | waist | hip | length |
  |---|---|---|---|---|
  | S | 86 | 72 | 94 | 66 |
  | M | 98 | 84 | 104 | 68 |

- These are **SYNTHETIC**. `spec_source` says so, and the engine warns about it.
- **TODO (Riddhima):** which real garment and product photo we're using, and its **sourced** S/M size chart (brand page URL + access date). When it's chosen, put it in `fixtures/garment_top_{S,M}.json` with `spec_source` naming the chart. The engine refuses nothing, but it flags unsourced charts.

## 4. SAM

See [docs/SAM_ACCESS.md](../docs/SAM_ACCESS.md). In short: Meta Model API, `POST https://api.meta.ai/v1/responses` with `model: "sam-3.1"`, the **same `MODEL_API_KEY` as Muse**. Smoke test: `fit-engine/scripts/sam_smoke.py`. Masks are for display only; pixels are never turned into cm.

## 5. Nisha voice/text flow (now in this branch)

Ported from the Stylewise app (`Vishakha-Kulkarni/stylewise`, branch `riddhimajain/finaltouches`). Only the persona and voice were brought over; the wardrobe/shopping planner was left behind. Nisha runs on **Meta Muse Spark**, not AWS.

- **Backend:** `POST /nisha/chat` on the fit API (`fit-engine/stylewise_fit/nisha.py`).
  - Request: `{"messages": [{"role": "user", "content": "Will the M fit?"}], "context": {"body": {...same as FitRequest.body...}, "garment_size": "M", "preferences": {"fit_pref": "regular"}}}`
  - Response: `{"reply": "...", "report": FitReport | null, "source": "muse" | "engine-template"}`
  - Muse calls the `evaluate_fit` tool. Garment cm always come from `fixtures/garment_top_{S,M}.json`, never from the model. Nisha may only repeat the report's facts.
  - Without `MODEL_API_KEY` + `MUSE_MODEL`, it still answers with a fixed Nisha template built from the engine output, so the demo works offline. `GET /health` reports `"muse": true/false`.
- **Frontend:**
  - `src/lib/nisha.ts`: `askNisha(messages, context)`, the persona, and `NEXT_PUBLIC_FIT_API_URL` (default `http://127.0.0.1:8000`).
  - Voice in: `src/hooks/useSpeechInput.ts` (Whisper Small, runs in the browser).
  - Voice out: `src/hooks/useSpokenReplies.ts` (Kokoro in the browser, or the optional Mac voice server `scripts/voice/server.py` on port 8081).
  - Supporting files: `src/lib/voice/*`. Needs `npm install` (adds `@huggingface/transformers` and `kokoro-js`).
- Wire the Fit Lab: pass the form values as `context`, show `reply` in a chat bubble, speak it with `useSpokenReplies`, and render `report` exactly like `/fit/evaluate`.

## 6. Branch

P0's work is on `riddhimakain/MHRsetup` (not merged yet): the API, contract v0.3.0, ANSUR II sizes, MHR presets and cluster scripts.
