"""Nisha for the Fit Lab: Muse Spark decides when to call the fit tool; the engine owns every number.

Muse (OpenAI-style /chat/completions on the Meta API) gets one tool, `evaluate_fit`. The tool runs
fit.evaluate on a garment from our own size-chart fixtures (the model never supplies garment cm)
and returns only the report's facts. Nisha may paraphrase those facts and nothing else.

Env (same names as scripts/muse_smoke.py): MODEL_API_KEY or META_API_KEY, MUSE_MODEL,
META_API_BASE (default https://api.meta.ai/v1). The repo-root .env is read too. Without a key, /nisha/chat still answers from
the engine with a fixed Nisha template, so the demo works offline.
"""
import json
import os
import urllib.request
from pathlib import Path

from pydantic import BaseModel

from .catalogue import catalogue, garment_input
from .fit import evaluate
from .schemas import BodyInput, FitReport, FitRequest, GarmentInput, Preferences

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
DEFAULT_MODEL = "muse-spark-1.3"  # verified with tool calling on 2026-11-02


def _env(name: str) -> str | None:
    """Process env first, then the repo-root .env (never committed)."""
    if os.environ.get(name):
        return os.environ[name]
    root = Path(__file__).resolve().parents[2]
    for filename in (".env.local", ".env"):
        dotenv = root / filename
        if dotenv.exists():
            for line in dotenv.read_text().splitlines():
                k, _, v = line.partition("=")
                if k.strip() == name and v.strip():
                    return v.strip().strip('"').strip("'")
    return None
GARMENT_SIZES = ("S", "M")
MAX_TOOL_ROUNDS = 3

# Persona from the Stylewise app (apps/web/lib/voice/stylists.ts, "desi-aunty"), rules are ours.
SYSTEM = """You are Nisha, a warm Mumbai style aunty who calls the user "beta". Mostly English, a little drama, very sharp eye.
Fit rules, which override the persona:
- Never state or estimate a body or garment measurement yourself. Call evaluate_fit and use only its facts.
- Paraphrase advice_facts, warnings and unknowns. Do not add numbers that are not in them.
- Ease is a tape-measure difference, not comfort. Never promise that something will feel comfortable or fit perfectly.
- If a verdict is "borderline", say it could go either way. If something is unknown, say so.
- Keep replies under 80 words, friendly, and end with one helpful next step.
Known context from the Fit Lab form (use it as the tool arguments unless the user changes it): {context}"""

TOOL = {
    "type": "function",
    "function": {
        "name": "evaluate_fit",
        "description": "Compare the user's body with one size of a garment: a Stylewise catalogue item "
                       "(garment_id) or, if omitted, the Fit Lab's everyday top (sizes S, M). "
                       "Returns ease per region, verdicts, warnings and the only facts you may repeat.",
        "parameters": {
            "type": "object",
            "properties": {
                "garment_id": {"type": "string",
                               "enum": [k for k, g in catalogue().items() if g["sizes"]]},
                "garment_size": {"type": "string", "enum": ["XS", "S", "M", "L", "XL"]},
                "height_cm": {"type": "number"},
                "chest_cm": {"type": "number"},
                "waist_cm": {"type": "number"},
                "hip_cm": {"type": "number"},
                "preset_shape": {"type": "string",
                                 "enum": ["hourglass", "triangle", "inverted_triangle", "rectangle", "oval"]},
                "preset_size": {"type": "string", "enum": ["XS", "S", "M", "L", "XL", "2XL", "3XL"]},
                "preset_sex": {"type": "string", "enum": ["female", "male"]},
                "fit_pref": {"type": "string", "enum": ["snug", "regular", "relaxed"]},
            },
            "required": ["garment_size", "height_cm"],
        },
    },
}


class FitContext(BaseModel):
    body: BodyInput | None = None
    garment_id: str | None = None  # catalogue item (GET /catalogue); None = the Fit Lab fixture top
    garment_size: str | None = None
    preferences: Preferences = Preferences()


class ChatTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class NishaRequest(BaseModel):
    messages: list[ChatTurn]
    context: FitContext = FitContext()


class NishaReply(BaseModel):
    reply: str
    report: FitReport | None = None
    source: str  # "muse" or "engine-template"


def garment(size: str) -> GarmentInput:
    if size not in GARMENT_SIZES:
        raise ValueError(f"unknown garment size {size!r}; expected one of {GARMENT_SIZES}")
    return GarmentInput.model_validate_json((FIXTURES / f"garment_top_{size}.json").read_text())


def run_tool(args: dict) -> FitReport:
    """Build a FitRequest from tool arguments. Garment cm always come from our charts:
    a catalogue item when garment_id is given, else the Fit Lab fixture top."""
    body = {"height_cm": args["height_cm"],
            **{k: args[k] for k in ("chest_cm", "waist_cm", "hip_cm") if args.get(k) is not None}}
    if args.get("preset_shape") and args.get("preset_size"):
        body |= {"source": "preset", "preset": {"shape": args["preset_shape"], "usual_size": args["preset_size"],
                                                "sex": args.get("preset_sex", "female")}}
    g = garment_input(args["garment_id"], args["garment_size"]) if args.get("garment_id") \
        else garment(args["garment_size"])
    req = FitRequest(body=BodyInput.model_validate(body), garment=g,
                     preferences=Preferences(fit_pref=args.get("fit_pref")))
    return evaluate(req)


def tool_payload(report: FitReport) -> str:
    """What Muse sees: verdicts and the permitted facts, not the full report."""
    return json.dumps({
        "verdicts": {k: r.verdict for k, r in report.regions.items()},
        "advice_facts": report.advice_facts, "warnings": report.warnings, "unknowns": report.unknowns,
    })


def context_args(ctx: FitContext) -> dict | None:
    if ctx.body is None or ctx.garment_size is None:
        return None
    b = ctx.body
    args = {"garment_id": ctx.garment_id, "garment_size": ctx.garment_size, "height_cm": b.height_cm, "chest_cm": b.chest_cm,
            "waist_cm": b.waist_cm, "hip_cm": b.hip_cm, "fit_pref": ctx.preferences.fit_pref}
    if b.preset:
        args |= {"preset_shape": b.preset.shape, "preset_size": b.preset.usual_size, "preset_sex": b.preset.sex}
    return args


def template_reply(report: FitReport) -> str:
    """Offline Nisha: fixed phrasing around the engine's own facts."""
    verdicts = {k: r.verdict for k, r in report.regions.items() if r.verdict != "unknown"}
    tight = [k for k, v in verdicts.items() if v == "tight"]
    close = [k for k, v in verdicts.items() if v == "borderline"]
    if tight:
        lead = f"Beta, this one is tight at the {' and '.join(tight)}."
    elif close:
        lead = f"Beta, the {' and '.join(close)} could go either way."
    else:
        lead = "Beta, the measurements give you room in this size."
    facts = [f for f in report.advice_facts if "ease" in f][:3]
    tail = "Remember, these are tape-measure numbers, not a promise of comfort."
    return " ".join([lead, *facts, tail])


def _chat(messages: list[dict]) -> dict:
    base = os.environ.get("META_API_BASE", "https://api.meta.ai/v1").rstrip("/")
    key = _env("MODEL_API_KEY") or _env("META_API_KEY")
    body = {"model": _env("MUSE_MODEL") or DEFAULT_MODEL, "messages": messages, "tools": [TOOL]}
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def muse_configured() -> bool:
    return bool(_env("MODEL_API_KEY") or _env("META_API_KEY"))


def chat(req: NishaRequest) -> NishaReply:
    preset_args = context_args(req.context)
    if not muse_configured():
        if preset_args is None:
            return NishaReply(reply="Beta, tell me your height and measurements, or pick a silhouette, "
                                    "and choose a size. Then I can check the fit.", source="engine-template")
        report = run_tool(preset_args)
        return NishaReply(reply=template_reply(report), report=report, source="engine-template")

    ctx = json.dumps({k: v for k, v in (preset_args or {}).items() if v is not None}) or "none"
    messages = [{"role": "system", "content": SYSTEM.format(context=ctx)},
                *[m.model_dump() for m in req.messages]]
    report = None
    for _ in range(MAX_TOOL_ROUNDS):
        msg = _chat(messages)["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return NishaReply(reply=msg.get("content") or "", report=report, source="muse")
        messages.append(msg)
        for call in calls:
            try:
                report = run_tool(json.loads(call["function"]["arguments"] or "{}"))
                content = tool_payload(report)
            except (ValueError, KeyError) as e:  # bad arguments go back to the model, not to the user
                content = json.dumps({"error": str(e)})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    # the model kept calling tools; answer from the last report instead of looping
    if report is None:
        return NishaReply(reply="Beta, I couldn't run the fit check just now. Please try again.", source="muse")
    return NishaReply(reply=template_reply(report), report=report, source="engine-template")
