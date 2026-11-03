# Stylewise: find your size before you buy

Online shoppers guess their size from a chart, and many guess wrong. Stylewise shows **how each size of a
real garment sits on your body shape**, region by region, and explains why. It does that from the brand's
own size chart and a body built from your shape and usual size, not from a guess.

**Live demo:** _add link_ · **Video (3 min):** _add link_ · Built for the Meta Global AI Developer Hackathon
(Cerebral Valley), Oct 26 to Nov 4, 2026. Problem statement: **Build for Your World**.

## What it does

1. **You:** pick one of five body shapes, your usual size and height (or enter your measurements).
2. **A garment:** pick from the catalogue. Each item carries its brand or seller size chart, cited.
3. **Every size, explained:** the engine compares the garment's girths with your body at the bust, waist
   and hip and gives a verdict per region ("snug at the waist", "+13 cm at the hips"), with one size either
   side for comparison.
4. **See it:** a styled view of the garment on a faceless mannequin with your exact proportions, from the
   front, side and back; and your measured body in 3D.
5. **Ask Nisha:** a sizing assistant who answers from the engine's verdicts only, never inventing a number.

## How Meta's models are used

| Model | Role |
|---|---|
| **Meta MHR** (Momentum Human Rig) | 210 body presets (5 shapes × 7 sizes × 3 heights × 2 sexes), fitted to size-chart girths by least squares with explicit Jacobians on NTU's NSCC cluster, with a bust-to-underbust cap so bodies keep natural proportions |
| **Muse Spark Open** (open weights, via Baseten) | Nisha's reasoning. She calls our fit engine as a tool for every answer; falls back to Muse Spark on the Meta Model API |
| **Muse Image** (`muse-image-1.0`) | The styled view: guided by a render of the measured body with the garment placed by measured ease, told the fit region by region, and the product photo. Also generated our product photos |
| **SAM 3.1** | Isolates the garment in its product photo |

## What is new in this hackathon (and what is not)

**Built during the hackathon:** the MHR body presets and fitting pipeline; the fit engine (ease, verdicts,
fabric stretch, uncertainty); the sourced size-chart catalogue; the styled view with Muse Image (prompting,
caching, content-safe fit wording); SAM garment isolation; Nisha's fit reasoning with tool calling on Muse
Spark Open; the privacy layer; the 3D body model viewer.

**Reused from our earlier Stylewise project:** Nisha's persona and the browser voice input/output modules
(`src/lib/voice/*`, `src/hooks/useSpeechInput.ts`, `src/hooks/useSpokenReplies.ts`), and catalogue item
names. The earlier wardrobe planner is not part of this project.

## Honesty and privacy

- Ease is a tape-measure difference, not a promise of comfort. Every report says where its sizes came from;
  where a seller does not say whether a chart is body or garment measurements, we state our assumption.
- The styled view is an illustration guided by the measured fit; the measurements decide the fit.
- Nisha: names, emails, phone numbers and addresses are removed on our server before any model call. Your
  measurements are sent to the model only if you tick consent; otherwise the fit runs on our server and the
  model sees only the verdicts.
- The styled view sends a rendered faceless silhouette, never a photo of you. SAM receives product photos only.
- The fit API is stateless: no database, no logging of bodies.

## Data sources

Size charts are cited per item in `fit-engine/stylewise_fit/data/catalogue_garments.json` (ZESICA, PARTHVI,
SimpleFun, SHINFY, H&C and other Amazon SG seller charts; Manyavar; Indubindu; Uniqlo SG). Body sizes:
ANSUR II (public domain) and a general women's retail chart; shape classes: FFIT. Product photos in this
repository were generated with Meta Muse Image. Early prototypes used retailer product photos as visual
references; the submitted version replaces them.

## Run it locally

```bash
npm install
python3 -m venv fit-engine/.venv && fit-engine/.venv/bin/pip install -e "fit-engine[api,dev]"
cp .env.example .env    # or create .env: MODEL_API_KEY=<your dev.meta.ai key>
npm run fit:dev         # fit engine on :8000
npm run dev             # app on http://localhost:3000
```

Optional: run Nisha on Muse Spark Open via Baseten with `NISHA_API_BASE=https://inference.baseten.co/v1`,
`NISHA_API_KEY=<Baseten key>`, `MUSE_MODEL=meta-models/muse-spark-open-1026` in `.env`.
Tests: `cd fit-engine && .venv/bin/python -m pytest -q`.

## Deploy

App on Vercel (set `FIT_API_URL`); fit engine as a Docker service on Render (`render.yaml`, `Dockerfile`).
Set `PREVIEW_CACHE_ONLY=1` on public deployments so visitors see the pre-generated styled views and never
spend API credits.

## Limitations

No cloth simulation; the styled view is an illustration. Body presets are estimates from shape and usual
size, not a scan. Some seller charts do not say body or garment measurements. The 3D body keeps a neutral
measuring pose.

## Team and licence

Riddhima Jain (body model, fit engine, size charts, styled view, Nisha's reasoning, SAM) and Vishakha
Maheshwari (app and interface). Apache-2.0, see `LICENSE` and `NOTICE`.
