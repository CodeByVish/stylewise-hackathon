"""Optional, free Mac-local expressive voice service. Never part of the AWS API."""
import io
import logging
import re
from contextlib import asynccontextmanager
from functools import lru_cache
from threading import Lock

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-4bit"
DESCRIPTIONS = {
    "desi-aunty": "A mature Indian woman in her fifties with a LOW-PITCHED, DEEP, resonant chest voice, slight huskiness and a distinctly INDIAN ENGLISH accent, not American. Hindi-influenced syllable timing, Indian consonants and vowels, affectionate maternal warmth. Playful and confident auntie speaking to someone she calls beta. Naturally animated emphasis, flowing conversational delivery, no long pauses, never an announcer.",
    "chinese-aunty": "一位五十岁中国阿姨，说流利但带明显中文口音的英语，不是美式口音。 A mature Chinese woman speaking fluent English with a DISTINCT natural Mandarin-influenced English accent, not American. Lower midrange voice, warm and bright, brisk conversational rhythm, expressive friendly emphasis, continuous natural delivery without long pauses.",
    "american-genz": "A young adult American woman with a relaxed contemporary American English accent. Bright, playful, energetic best-friend delivery with natural emphasis and conversational rhythm, expressive rather than announcer-like.",
    "british-bestie": "A young adult man with a DISTINCT modern London / southern British English accent, non-rhotic British vowels, not American. Relaxed mate-to-mate delivery, warm, witty and slightly cheeky, conversational flowing rhythm, natural understated emphasis, no long pauses.",
    "streetwear-bro": "A young adult American man with a relaxed American English accent. Friendly, confident, upbeat conversational delivery, natural warmth, an easygoing style-friend voice.",
}
lock = Lock()


@lru_cache(maxsize=1)
def model():
    from mlx_audio.tts.utils import load_model
    return load_model(MODEL_ID)


@asynccontextmanager
async def lifespan(app):
    # Native Mac voices are ready immediately. Load the optional Qwen model only
    # if a generated-voice route is actually requested.
    logging.info("Voice service ready; generated VoiceDesign loads on demand")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000", "http://127.0.0.1:3002", "http://127.0.0.1:3003"],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    stylist: str = "american-genz"


@app.get("/health")
def health():
    return {"status": "ready", "engine": "qwen3-voice-design", "model": MODEL_ID, "local_only": True, "voices": {"desi-aunty": "Tara (Indian English)", "british-bestie": "Daniel (British English)", "chinese-aunty": "Tingting (Chinese voice)", "others": "Qwen VoiceDesign streaming"}}


NATIVE_VOICES = {"desi-aunty": ("Tara", 165), "chinese-aunty": ("Tingting", 175), "british-bestie": ("Daniel", 180)}


@lru_cache(maxsize=24)
def native_audio(text: str, stylist: str):
    import subprocess
    import tempfile
    from pathlib import Path
    voice, rate = NATIVE_VOICES[stylist]
    # macOS's renderer may run adjacent sentences together even when the source
    # contains punctuation. Render complete sentences independently and insert
    # real silence into the waveform so the delivery is always intelligible.
    # The simulator disclosure belongs in the visual UI, never in a natural
    # spoken response. Keep this server-side too, so stale browser bundles
    # cannot accidentally read it aloud.
    text = re.sub(r"\bAll offers are simulated[.!]?\s*", "", text, flags=re.IGNORECASE).strip()
    phrases = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text)
    phrases = [phrase.strip() for phrase in phrases if phrase.strip()] or [text]
    with tempfile.TemporaryDirectory(prefix="stylewise-native-") as directory:
        rendered: list[np.ndarray] = []
        sample_rate: int | None = None
        for index, phrase in enumerate(phrases):
            output = Path(directory) / f"speech-{index}.aiff"
            if stylist == "desi-aunty":
                helper = Path(__file__).resolve().parents[2] / ".local" / "native-expressive"
                if not helper.is_file():
                    raise RuntimeError("Compile scripts/voice/native_expressive.swift before starting Nisha's voice")
                command = [str(helper), str(output), phrase]
            else:
                command = ["/usr/bin/say", "-v", voice, "-r", str(rate), "-o", str(output), phrase]
            subprocess.run(command, check=True, timeout=50, capture_output=True)
            samples, phrase_rate = sf.read(output, dtype="float32")
            if not len(samples):
                raise RuntimeError("The selected Mac voice generated no audio")
            sample_rate = sample_rate or phrase_rate
            if phrase_rate != sample_rate:
                raise RuntimeError("Mac voice changed sample rate between sentences")
            rendered.append(samples.reshape(-1))
            if index < len(phrases) - 1:
                # A question gets a slightly longer conversational beat.
                pause_seconds = 0.42 if phrase.rstrip().endswith("?") else 0.30
                rendered.append(np.zeros(round(sample_rate * pause_seconds), dtype="float32"))
        return np.concatenate(rendered), sample_rate


@lru_cache(maxsize=24)
def render(text: str, stylist: str):
    if stylist in NATIVE_VOICES:
        samples, rate = native_audio(text, stylist)
        buffer = io.BytesIO()
        sf.write(buffer, samples, rate, format="WAV", subtype="PCM_16")
        return buffer.getvalue()
    import mlx.core as mx
    with lock:
        mx.random.seed(42)
        outputs = list(model().generate(
            text=text, instruct=DESCRIPTIONS[stylist], lang_code="English",
            temperature=0.7, max_tokens=900, verbose=False))
        if not outputs:
            raise ValueError("The model produced no audio")
        samples = np.concatenate([np.asarray(output.audio).reshape(-1) for output in outputs])
        buffer = io.BytesIO()
        sf.write(buffer, samples, outputs[0].sample_rate, format="WAV", subtype="PCM_16")
        return buffer.getvalue()


@app.post("/speak")
def speak(request: SpeechRequest):
    if request.stylist not in DESCRIPTIONS:
        raise HTTPException(422, "Unknown stylist")
    try:
        return Response(render(request.text, request.stylist), media_type="audio/wav", headers={"Cache-Control": "no-store"})
    except Exception:
        logging.exception("Local voice generation failed")
        raise HTTPException(503, "Local voice generation failed. Check the voice server terminal.")

# Audio is sent as it is generated, rather than collecting a whole sentence first.
# Each inference runs on one thread; disconnecting a client cancels at the next chunk.
import asyncio
import base64
import json
import queue
import threading
import time
from collections import OrderedDict
from fastapi.responses import StreamingResponse

stream_cache = OrderedDict()


@app.post("/speak/stream")
async def speak_stream(request: SpeechRequest):
    if request.stylist not in DESCRIPTIONS:
        raise HTTPException(422, "Unknown stylist")
    messages = queue.Queue()
    cancelled = threading.Event()

    def produce():
        started = time.monotonic()
        try:
            if request.stylist in NATIVE_VOICES:
                samples, sample_rate = native_audio(request.text, request.stylist)
                # The native renderer is faster than playback; schedule its output as one utterance.
                pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
                if not cancelled.is_set():
                    messages.put({"kind": "audio", "pcm": base64.b64encode(pcm).decode("ascii"), "rate": sample_rate, "complete": True,
                                  "elapsed": round(time.monotonic() - started, 3)})
                return
            import mlx.core as mx
            with lock:
                if cancelled.is_set():
                    return
                key = (request.text, request.stylist)
                if key in stream_cache:
                    stream_cache.move_to_end(key)
                    for chunk in stream_cache[key]:
                        messages.put(chunk)
                    return
                mx.random.seed(42)
                chunks = []
                generator = model().generate(
                    text=request.text, instruct=DESCRIPTIONS[request.stylist], lang_code="English",
                    temperature=0.65, max_tokens=1200, stream=True, streaming_interval=0.8, verbose=False)
                try:
                    for result in generator:
                        if cancelled.is_set():
                            break
                        samples = np.asarray(result.audio).reshape(-1)
                        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
                        chunk = {"kind": "audio", "pcm": base64.b64encode(pcm).decode("ascii"),
                                 "rate": result.sample_rate, "elapsed": round(time.monotonic() - started, 3)}
                        chunks.append(chunk)
                        messages.put(chunk)
                finally:
                    generator.close()
                if chunks and not cancelled.is_set():
                    stream_cache[key] = tuple(chunks)
                    while len(stream_cache) > 16:
                        stream_cache.popitem(last=False)
        except Exception:
            logging.exception("Streaming voice generation failed")
            messages.put({"kind": "error", "message": "Local streaming voice generation failed."})
        finally:
            messages.put({"kind": "done"})

    threading.Thread(target=produce, daemon=True).start()

    async def body():
        try:
            while True:
                message = await asyncio.to_thread(messages.get)
                yield json.dumps(message) + "\n"
                if message["kind"] == "done":
                    break
        finally:
            cancelled.set()

    return StreamingResponse(body(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
