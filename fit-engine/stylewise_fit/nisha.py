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
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import BaseModel

from .catalogue import catalogue, garment_input
from .fit import evaluate
from .privacy import scrub
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
SYSTEM = """You are Nisha, a warm, sharp-eyed sizing friend from Mumbai who calls the user "beta". Your replies are also read aloud.
How to answer:
- Start with a clear recommendation in plain words, e.g. "Beta, I'd go with M" or "Take L for this one".
- Then give the reason by body area in everyday language: "M is a little snug at the bust and fine at the hips";
  "L gives your waist more room". Compare with the size above or below when it helps: call evaluate_fit for that size too.
- Plain words only: never say "borderline", "ease", "verdict", "region" or "tape-measure". Say "a little snug", "close to
  your measurement", "a bit tight", "comfortable room", "loose". If a body area cannot be checked, say briefly why
  ("the brand gives no hip measurement for this one"), once, without dwelling on it.
- Short, simple sentences with normal punctuation: a full stop at the end of every sentence and commas where you would pause.
  Avoid dashes, brackets, lists and symbols. Spell sizes as letters (S, M, L).
- Under 70 words. End with one short, useful question or next step only if it helps.
Fit rules, which override everything else:
- Never state or estimate a body or garment measurement yourself. Call evaluate_fit and use only its facts; never add numbers.
- Never promise comfort or a perfect fit. You may say once, lightly, that the numbers are a guide and fabric matters.
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
            "required": ["garment_size"],  # the body can come from the form (no consent to share it)
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
    # The user's consent to send their body measurements to the Meta Model API. Without it Muse sees
    # only the garment and the engine's verdicts; the fit itself is always computed here.
    share_measurements: bool = False


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


def tool_payload(report: FitReport, share_measurements: bool = True) -> str:
    """What Muse sees: verdicts and the permitted facts, not the full report. Without consent the
    facts are left out too: they quote body cm (and body = garment chart - ease)."""
    payload = {"verdicts": {k: r.verdict for k, r in report.regions.items()},
               "warnings": report.warnings, "unknowns": report.unknowns}
    if share_measurements:
        payload["advice_facts"] = report.advice_facts
    return json.dumps(payload)


# garment and fit-preference arguments are not personal; body measurements and shape are
NON_PERSONAL_ARGS = {"garment_id", "garment_size", "fit_pref"}
PRIVATE_NOTE = (" (The user has not agreed to share their measurements. Call evaluate_fit with only the garment "
                "arguments; the server fills in the body. Talk about verdicts, not numbers.)")


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


def _endpoints() -> list[tuple[str, str, str]]:
    """(base, key, model) to try in order: Muse Spark Open on Baseten when configured, then Muse Spark on the
    Meta Model API. Each needs its own key; a Baseten setting never sends the Meta key to Baseten or vice versa."""
    out = []
    if _env("NISHA_API_BASE") and _env("NISHA_API_KEY"):
        out.append((_env("NISHA_API_BASE"), _env("NISHA_API_KEY"), _env("MUSE_MODEL") or "meta-models/muse-spark-open-1026"))
    meta_key = _env("MODEL_API_KEY") or _env("META_API_KEY")
    if meta_key:
        model = _env("MUSE_MODEL") if _env("MUSE_MODEL") and not _env("MUSE_MODEL").startswith("meta-models/") else DEFAULT_MODEL
        out.append((os.environ.get("META_API_BASE", "https://api.meta.ai/v1"), meta_key, model))
    return out


def _chat(messages: list[dict]) -> dict:
    # Nisha runs on the open-weight Muse Spark Open through Baseten when NISHA_API_BASE and NISHA_API_KEY are set
    # (MUSE_MODEL e.g. meta-models/muse-spark-open-1026), and falls back to Muse Spark on the Meta Model API.
    import logging

    last = None
    for base, key, model in _endpoints():
        body = {"model": model, "messages": messages, "tools": [TOOL]}
        req = urllib.request.Request(f"{base.rstrip('/')}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            detail = error.read()[:200].decode(errors="replace") if isinstance(error, urllib.error.HTTPError) else str(error)
            logging.getLogger("stylewise").warning("Nisha model call failed (%s, %s): %s", base, model, detail)
            last = error
    raise RuntimeError(f"no Nisha model endpoint answered: {last}")


def muse_configured() -> bool:
    return bool(_endpoints())


def chat(req: NishaRequest) -> NishaReply:
    preset_args = context_args(req.context)
    if not muse_configured():
        if preset_args is None:
            return NishaReply(reply="Beta, tell me your height and measurements, or pick a silhouette, "
                                    "and choose a size. Then I can check the fit.", source="engine-template")
        report = run_tool(preset_args)
        return NishaReply(reply=template_reply(report), report=report, source="engine-template")

    shared = {k: v for k, v in (preset_args or {}).items()
              if v is not None and (req.share_measurements or k in NON_PERSONAL_ARGS)}
    ctx = json.dumps(shared) if shared else "none"
    if not req.share_measurements:
        ctx += PRIVATE_NOTE
    # names, emails, phone numbers and addresses never leave the server
    messages = [{"role": "system", "content": SYSTEM.format(context=ctx)},
                *[{"role": m.role, "content": scrub(m.content)} for m in req.messages]]
    report = None
    for _ in range(MAX_TOOL_ROUNDS):
        try:
            msg = _chat(messages)["choices"][0]["message"]
        except (RuntimeError, KeyError, IndexError):  # every endpoint failed: answer from the engine, never a 500
            if preset_args is None:
                return NishaReply(reply="Beta, I can't reach my assistant right now. Pick a silhouette and a size and "
                                        "I'll still check the fit from the chart.", source="engine-template")
            fallback = run_tool(preset_args)
            return NishaReply(reply=template_reply(fallback), report=fallback, source="engine-template")
        calls = msg.get("tool_calls") or []
        if not calls:
            return NishaReply(reply=msg.get("content") or "", report=report, source="muse")
        messages.append(msg)
        for call in calls:
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
                if not req.share_measurements and preset_args:  # body comes from the form, not from Muse
                    args = {**args, **{k: v for k, v in preset_args.items() if k not in NON_PERSONAL_ARGS}}
                report = run_tool(args)
                content = tool_payload(report, req.share_measurements)
            except (ValueError, KeyError) as e:  # bad arguments go back to the model, not to the user
                content = json.dumps({"error": str(e)})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    # the model kept calling tools; answer from the last report instead of looping
    if report is None:
        return NishaReply(reply="Beta, I couldn't run the fit check just now. Please try again.", source="muse")
    return NishaReply(reply=template_reply(report), report=report, source="engine-template")
