"""Smoke test: can SAM 3.1 on the Meta Model API segment the garment in our product photo?

  python scripts/sam_smoke.py path/to/garment.png "t-shirt"

Env: MODEL_API_KEY (or META_API_KEY), META_API_BASE (default https://api.meta.ai/v1).
Same key as scripts/muse_smoke.py. Prints how many box+mask records came back; mask data uses
Meta's token format (see docs/SAM_ACCESS.md) and is decoded with Meta's client libraries.
"""
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.request

BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1").rstrip("/")
KEY = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
if not KEY or len(sys.argv) < 3:
    sys.exit("usage: MODEL_API_KEY=... python scripts/sam_smoke.py <image> <noun phrase>")
path, phrase = sys.argv[1], sys.argv[2]
mime = mimetypes.guess_type(path)[0] or "image/png"
data_url = f"data:{mime};base64,{base64.b64encode(open(path, 'rb').read()).decode()}"

body = {
    "model": "sam-3.1",
    "input": [{"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": phrase},
        {"type": "input_image", "image_url": data_url},
    ]}],
    "stream": True,
    "metadata": {"include_confidence": "true"},
}
req = urllib.request.Request(f"{BASE}/responses", data=json.dumps(body).encode(), headers={
    "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Accept": "text/event-stream"})
t0, text = time.time(), []
with urllib.request.urlopen(req, timeout=120) as r:
    for line in r:  # server-sent events; collect the text deltas
        line = line.decode().strip()
        if line.startswith("data:") and line[5:].strip() not in ("", "[DONE]"):
            event = json.loads(line[5:])
            if event.get("type") == "response.output_text.delta":
                text.append(event.get("delta", ""))
out = "".join(text)
boxes = re.findall(r"<\|box;([^|]*)\|>", out)
print(f"latency {time.time() - t0:.2f}s, {len(boxes)} match(es) for {phrase!r}")
for b in boxes:
    print("  box", b)
print("MASKS RETURNED" if "<|mask;" in out else "NO MASK — check key access to sam-3.1, image and phrase")
