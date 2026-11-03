"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { normalizeSpokenText, speechPieces } from "../lib/voice/spoken-text";
import { readVoiceStream } from "../lib/voice/stream";
import { voiceJob } from "../lib/voice/client";
import type { VoiceId } from "../lib/voice/voices";

function preferredBrowserVoice(stylistId: string) {
  const voices = window.speechSynthesis.getVoices();
  const locale = stylistId === "chinese-aunty" ? ["en-SG", "zh-SG", "zh-CN", "en-US"]
    : stylistId === "british-bestie" ? ["en-GB", "en-AU", "en-US"]
    : stylistId === "desi-aunty" ? ["en-IN", "en-SG", "en-US", "en-GB"] : ["en-US", "en-SG", "en-GB"];
  const feminine = /ava|samantha|victoria|zira|jenny|aria|allison|karen|moira|tara|serena|siri|female|veena|isha|lekha|kajal|heera|neerja|swara/i;
  for (const code of locale) {
    const match = voices.find(item => item.lang.toLowerCase() === code.toLowerCase() && feminine.test(item.name));
    if (match) return match;
  }
  for (const code of locale) {
    const match = voices.find(item => item.lang.toLowerCase() === code.toLowerCase());
    // Do not let a hosted female stylist silently become a male fallback.
    if (match && !["desi-aunty", "chinese-aunty", "american-genz"].includes(stylistId)) return match;
  }
  const anyFeminine = voices.find(item => feminine.test(item.name));
  if (anyFeminine) return anyFeminine;
  return ["desi-aunty", "chinese-aunty", "american-genz"].includes(stylistId)
    ? undefined
    : voices.find(item => item.lang.toLowerCase().startsWith("en"));
}

function speakInBrowser(text: string, stylistId: string) {
  return new Promise<void>((resolve, reject) => {
    if (!window.speechSynthesis) { reject(new Error("Browser speech is unavailable.")); return; }
    const utterance = new SpeechSynthesisUtterance(text.replace(/\bSGD\s*(\d+)/g, "$1 Singapore dollars"));
    const voice = preferredBrowserVoice(stylistId);
    if (!voice && ["desi-aunty", "chinese-aunty", "american-genz"].includes(stylistId)) {
      reject(new Error("A matching female browser voice is unavailable.")); return;
    }
    utterance.voice = voice || null;
    utterance.rate = 1;
    utterance.onend = () => resolve();
    utterance.onerror = event => event.error === "canceled" ? resolve() : reject(new Error("Browser speech playback failed."));
    window.speechSynthesis.speak(utterance);
  });
}

export function useSpokenReplies() {
  const [localVoice, setLocalVoice] = useState(false);
  const [remoteVoice, setRemoteVoice] = useState(false);
  const [localReady, setLocalReady] = useState(false);
  const [supported, setSupported] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const active = useRef(0);
  const context = useRef<AudioContext | null>(null);
  const sources = useRef(new Set<AudioBufferSourceNode>());
  const request = useRef<AbortController | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  const finishPlayback = useRef<(() => void) | null>(null);

  // Call synchronously from a click so browser autoplay rules don't block a later model reply.
  const unlock = useCallback(() => {
    if (!context.current || context.current.state === "closed") context.current = new AudioContext();
    return context.current.resume();
  }, []);
  const stop = useCallback(() => {
    active.current++;
    request.current?.abort(); request.current = null;
    sources.current.forEach(player => player.stop()); sources.current.clear();
    finishPlayback.current?.(); finishPlayback.current = null;
    setSpeaking(false); setStatus("");
  }, []);
  useEffect(() => {
    const useLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
    const remoteUrl = process.env.NEXT_PUBLIC_VOICE_URL || "";
    const useRemote = !useLocal && remoteUrl.startsWith("https://");
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setSupported(typeof window.speechSynthesis !== "undefined" ||
        (typeof Worker !== "undefined" && typeof WebAssembly !== "undefined" && typeof AudioContext !== "undefined"));
      setRemoteVoice(useRemote);
      setLocalVoice(useLocal || useRemote);
      try { setEnabled(localStorage.getItem("stylewise-spoken-replies") === "true"); } catch { /* Storage is optional. */ }
    });
    const check = async () => {
      if (!useLocal && !useRemote) return;
      try {
        const response = await fetch(`${useRemote ? remoteUrl.replace(/\/$/, "") : "http://127.0.0.1:8081"}/health`, {signal: AbortSignal.timeout(2000)});
        const health = await response.json();
        if (!cancelled) setLocalReady(response.ok && ["qwen3-voice-design", "stylewise-mac-voice"].includes(health.engine));
      } catch { if (!cancelled) setLocalReady(false); }
    };
    void check();
    const timer = setInterval(() => { void check(); }, 10000);
    if (typeof BroadcastChannel !== "undefined") {
      channel.current = new BroadcastChannel("stylewise-audio");
      channel.current.onmessage = () => stop();
    }
    return () => {
      cancelled = true; clearInterval(timer);
      channel.current?.close();
      active.current++; request.current?.abort(); sources.current.forEach(player => player.stop()); sources.current.clear(); finishPlayback.current?.();
      if (context.current && context.current.state !== "closed") void context.current.close();
    };
  }, [stop]);
  const speak = useCallback(async (text: string, voice: VoiceId, stylistId = "american-genz") => {
    text = normalizeSpokenText(text);
    if (!supported || !text) return;
    channel.current?.postMessage("speaking");
    stop(); setError(""); setSpeaking(true); setStatus("Preparing your stylist's voice…");
    const id = active.current;
    try {
      // Nisha: an Indian English system voice (e.g. Veena, Isha) reads clearer, with natural rhythm, than the
      // small in-browser model, so use it when the device has one; otherwise fall through to the model.
      const native = stylistId === "desi-aunty" && typeof window !== "undefined" && window.speechSynthesis
        ? preferredBrowserVoice(stylistId) : undefined;
      if (native && native.lang.toLowerCase() === "en-in") {
        setStatus("Speaking…");
        for (const piece of speechPieces(text, 220)) {
          if (active.current !== id) return;
          await speakInBrowser(piece, stylistId);
        }
        if (active.current === id) { setSpeaking(false); setStatus(""); }
        return;
      }
      await unlock();
      if (active.current !== id) return;
      const audioContext = context.current!;
      if (localVoice && (localReady || remoteVoice)) {
        const controller = new AbortController(); request.current = controller;
        let nextTime = 0;
        const playing: Promise<void>[] = [];
        const enqueue = (samples: Float32Array, rate: number, prebuffer = 1.2) => {
          if (active.current !== id) return;
          const buffer = audioContext.createBuffer(1, samples.length, rate);
          buffer.copyToChannel(new Float32Array(samples), 0);
          const player = audioContext.createBufferSource();
          player.buffer = buffer; player.connect(audioContext.destination); sources.current.add(player);
          // Read/generate ahead while previously scheduled audio is playing.
          const startAt = nextTime ? Math.max(nextTime, audioContext.currentTime + .03) : audioContext.currentTime + prebuffer;
          nextTime = startAt + buffer.duration;
          playing.push(new Promise<void>(resolve => {
            player.onended = () => { sources.current.delete(player); player.disconnect(); resolve(); };
            player.start(startAt);
          }));
          setStatus(remoteVoice ? "Speaking…" : "Speaking · streaming audio from your Mac…");
        };
        const pieces = speechPieces(text.replace(/\s+/g, " "), 1000);
        for (const piece of pieces) {
          if (active.current !== id) return;
          if (!nextTime) setStatus("Starting your stylist's voice stream…");
          const remoteUrl = (process.env.NEXT_PUBLIC_VOICE_URL || "").replace(/\/$/, "");
          const token = remoteVoice ? sessionStorage.getItem("stylewise-access-token") : null;
          // Jules remains the visual/conversational persona, voiced by the approved female
          // Tara renderer in the public demo. VoiceDesign's generated gender is not stable enough
          // for a recorded demo, so never send Jules to that variable route when hosted.
          const renderedStylist = remoteVoice && stylistId === "american-genz" ? "desi-aunty" : stylistId;
          if (remoteVoice && !token) throw new Error("Sign in to hear your selected stylist.");
          const headers: Record<string, string> = {"Content-Type": "application/json"};
          if (token) headers.Authorization = `Bearer ${token}`;
          const response = await fetch(remoteVoice ? `${remoteUrl}/speak` : "http://127.0.0.1:8081/speak/stream", {
            method: "POST", headers,
            body: JSON.stringify({text: piece.replace(/\bSGD\s*(\d+)/g, "$1 Singapore dollars"), stylist: renderedStylist}),
            signal: controller.signal,
          });
          if (remoteVoice) {
            if (!response.ok) throw new Error(response.status === 401 ? "Please sign in again to hear your stylist." : "The demo voice host is unavailable.");
            const buffer = await audioContext.decodeAudioData(await response.arrayBuffer());
            enqueue(buffer.getChannelData(0), buffer.sampleRate, 0.03);
          } else await readVoiceStream(response, enqueue);
        }
        await Promise.all(playing);
      } else {
        const pieces = speechPieces(text.replace(/\s+/g, " "), 220);
        for (const piece of pieces) {
          if (active.current !== id) return;
          const result = await voiceJob("speak", value => { if (active.current === id) setStatus(value); }, {text: piece, voice});
          if (active.current !== id) return;
          if (!result.blob) throw new Error("No audio generated");
          const buffer = await audioContext.decodeAudioData(await result.blob.arrayBuffer());
          if (active.current !== id) return;
          const player = audioContext.createBufferSource();
          player.buffer = buffer; player.connect(audioContext.destination); sources.current.add(player);
          setStatus("Speaking…");
          await new Promise<void>(resolve => { finishPlayback.current = resolve; player.onended = () => resolve(); player.start(); });
          sources.current.delete(player); player.disconnect();
        }
      }
      if (active.current === id) { setSpeaking(false); setStatus(""); }
    } catch (cause) {
      if (active.current === id) {
        // The real Qwen/Tara service is primary. If its temporary host or tunnel is unavailable,
        // keep the experience usable on any judge's computer with a local browser voice.
        if (remoteVoice && typeof window.speechSynthesis !== "undefined") {
          try {
            request.current = null;
            setStatus("Voice host unavailable · using this browser's voice…");
            await speakInBrowser(text, stylistId);
            if (active.current === id) { setSpeaking(false); setStatus(""); }
            return;
          } catch { /* report the original model failure below */ }
        }
        stop();
        setError(`Your stylist could not speak. ${cause instanceof Error ? cause.message.slice(0, 100) : "Audio playback failed."} Try Hear stylist in Chrome. The text reply is still available.`);
      }
    }
  }, [supported, stop, unlock, localVoice, remoteVoice, localReady]);
  function toggleEnabled(value: boolean) {
    setEnabled(value);
    try { localStorage.setItem("stylewise-spoken-replies", String(value)); } catch { /* Storage is optional. */ }
    if (value) void unlock().catch(() => setError("Open this page in Chrome and tap Hear stylist to enable audio."));
    else stop();
  }
  return {localVoice, remoteVoice, localReady, supported, enabled, toggleEnabled, speaking, status, error, speak, stop, unlock, claimMicrophone: () => { channel.current?.postMessage("microphone"); }};
}
