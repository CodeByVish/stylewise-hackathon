"""Smoke test: can Muse Spark (Meta API) return a tool call for our fit tool?

Env:
  MODEL_API_KEY  required (name used by Meta's export snippet; META_API_KEY also accepted)
  MUSE_MODEL     model id from your Meta developer console
  META_API_BASE  default https://api.meta.ai/v1 (OpenAI-style /chat/completions)
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1").rstrip("/")
KEY = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
MODEL = os.environ.get("MUSE_MODEL")
if not KEY or not MODEL:
    sys.exit("Set MODEL_API_KEY (or META_API_KEY) and MUSE_MODEL")

tool = {
    "type": "function",
    "function": {
        "name": "get_fit_report",
        "description": "Compute deterministic garment ease for a user's measurements and a garment size.",
        "parameters": {
            "type": "object",
            "properties": {
                "chest_cm": {"type": "number"},
                "waist_cm": {"type": "number"},
                "size": {"type": "string", "enum": ["S", "M"]},
            },
            "required": ["size"],
        },
    },
}
body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are Nisha. Never state garment or body dimensions yourself; call tools."},
        {"role": "user", "content": "My chest is 90 and waist 74 cm. Would the M top fit?"},
    ],
    "tools": [tool],
}
req = urllib.request.Request(f"{BASE}/chat/completions", data=json.dumps(body).encode(),
                             headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=60) as r:
    resp = json.load(r)
print(f"latency {time.time() - t0:.2f}s")
print(json.dumps(resp, indent=2)[:3000])
text = json.dumps(resp)
print("\nTOOL CALL RETURNED" if "get_fit_report" in text else "\nNO TOOL CALL — check model id / tool support")
