# SAM 3.1 access (garment photo masks)

**Status:** verified 2026-11-02. `scripts/sam_smoke.py` on a catalogue product photo (`blush-shell-top.jpg`, prompt "top") returned masks through the Meta Model API.

**What SAM is for in Stylewise:** cutting the garment out of a product photo (a pixel mask) for the Fit Lab card and the viewer texture. **A mask is never a size.** Garment cm only come from a sourced size chart (`spec_source`).

## Option A: Meta Model API (recommended)

No hosting and no GPU. **Uses the same key as Muse** (`MODEL_API_KEY`, from dev.meta.ai → API keys).

- Endpoint: `POST https://api.meta.ai/v1/responses`
- Model: `sam-3.1`
- Input: one user message with
  - `input_text`: a short noun phrase, e.g. `"t-shirt"`, **or** box/point tokens (not both)
  - `input_image`: `image_url` as a public URL or a `data:image/png;base64,...` URL
- `stream: true` is recommended. The output arrives as `response.output_text.delta` events.
- Output: one record per match, a box then a mask, in Meta's token format:
  `<0f>0<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;x=0;y=0;data=...|>`.
  Decode masks with Meta's client libraries (linked from the docs). `metadata.mask_encoding` can be `"lossless"` (default) or `"one_bit"`. `metadata.include_confidence: "true"` adds a score.
- Box prompt example (inside `input_text`): `<0f>1<|box;x1=444;y1=626;x2=675;y2=849;w=1800;h=1200|>`
- Price: $2.50 per 1,000 images (video $0.20 per 1,000 frames).

```bash
curl -N -X POST "https://api.meta.ai/v1/responses" \
  -H "Authorization: Bearer $MODEL_API_KEY" -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"model":"sam-3.1","input":[{"type":"message","role":"user","content":[
        {"type":"input_text","text":"t-shirt"},
        {"type":"input_image","image_url":"https://example.com/top.png"}]}],"stream":true}'
```

## Option B: open weights (offline / GPU)

- Hugging Face repo **`facebook/sam3.1`** (gated): click "request access" on the model page, wait for approval, then `huggingface-cli login`. The checkpoint is `sam3.1_multiplex.pt`, under Meta's SAM License.
- Hugging Face approval is separate from the Meta API account.
- Only worth it if the API is blocked, or for batch work on the NSCC GPUs. Third-party mirrors exist but are not official; don't use them.

## Steps for P1

1. Create a `MODEL_API_KEY` in your own Meta developer account (dev.meta.ai → API keys). It is the same kind of key Muse uses, so one key covers both. Put it in `.env.local` and never commit it.
2. Pick the garment product photo, and record its source URL and licence next to the size chart.
3. Smoke test: `MODEL_API_KEY=... python fit-engine/scripts/sam_smoke.py top.png "t-shirt"`. You should see `MASKS RETURNED`.
4. Save the mask (or the cut-out PNG) as `fixtures/garment_top_mask.png` and record the request and timestamp for provenance.

## Sources
- Meta model page: https://dev.meta.ai/models/sam-3-1/
- API docs: https://dev.meta.ai/docs/sam/segmenting
- Overview: https://dev.meta.ai/docs/sam/overview
