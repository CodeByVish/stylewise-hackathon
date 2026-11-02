"use client";
import { useEffect, useRef, useState } from "react";
import { voiceJob } from "../lib/voice/client";
import { normalizePCM, pcmWav, resamplePCM } from "../lib/voice/recording";

type Recording = {stop: () => void; dispose: () => void};
export function useSpeechInput(onTranscript: (text: string) => void, embedded = false, stopOnPause = false) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState("");
  const [microphones, setMicrophones] = useState<MediaDeviceInfo[]>([]);
  const [microphoneId, setMicrophoneId] = useState("");
  const [level, setLevel] = useState(0);
  const [recordingURL, setRecordingURL] = useState("");
  const [microphoneName, setMicrophoneName] = useState("");
  const recordingObjectURL = useRef("");
  const recording = useRef<Recording | null>(null);
  const active = useRef(0);
  const starting = useRef(false);
  const callback = useRef(onTranscript);
  useEffect(() => { callback.current = onTranscript; }, [onTranscript]);
  useEffect(() => {
    queueMicrotask(() => setSupported(typeof navigator.mediaDevices?.getUserMedia === "function" && typeof AudioWorkletNode !== "undefined" && typeof AudioContext !== "undefined" && typeof Worker !== "undefined" && typeof WebAssembly !== "undefined"));
    const refresh = () => navigator.mediaDevices?.enumerateDevices?.().then(devices => setMicrophones(devices.filter(device => device.kind === "audioinput"))).catch(() => {});
    void refresh();
    navigator.mediaDevices?.addEventListener?.("devicechange", refresh);
    return () => { navigator.mediaDevices?.removeEventListener?.("devicechange", refresh); active.current++; recording.current?.dispose(); recording.current = null; if (recordingObjectURL.current) URL.revokeObjectURL(recordingObjectURL.current); };
  }, []);

  async function toggle() {
    if (embedded) { setStatus("Open this page in Chrome to use the microphone. VS Code embedded preview is not supported for voice."); return; }
    if (recording.current) { recording.current.stop(); return; }
    if (starting.current) return;
    starting.current = true;
    const id = ++active.current;
    const alive = () => active.current === id;
    let stream: MediaStream | undefined;
    let context: AudioContext | undefined;
    try {
      // Resume from the click, before permission prompts or downloads consume user activation.
      context = new AudioContext();
      const resumed = context.resume();
      setProcessing(true); setStatus("Allow microphone access to start recording.");
      stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1, ...(microphoneId ? {deviceId: {exact: microphoneId}} : {})}, video: false});
      if (!alive()) { stream.getTracks().forEach(track => track.stop()); void context.close(); return; }
      await resumed;
      if (context.state !== "running") throw new Error("Microphone audio is suspended. Open this page in Chrome.");
      setMicrophoneName(stream.getAudioTracks?.()[0]?.label || "Default microphone");
      const devices = await navigator.mediaDevices.enumerateDevices?.();
      if (devices) setMicrophones(devices.filter(device => device.kind === "audioinput"));
      await context.audioWorklet.addModule("/voice/pcm-processor.js");
      if (!alive()) { stream.getTracks().forEach(track => track.stop()); void context.close(); return; }
      const source = context.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(context, "stylewise-pcm");
      source.connect(node); node.connect(context.destination);
      const chunks: Float32Array[] = [];
      let heardSpeech = false;
      let stopping = false;
      let finished = false;
      let flushTimer: ReturnType<typeof setTimeout> | undefined;
      const started = Date.now(); let lastSound = started;
      const currentContext = context;
      const currentStream = stream;
      const dispose = () => {
        clearInterval(timer); clearTimeout(flushTimer); node.port.onmessage = null;
        source.disconnect(); node.disconnect(); currentStream.getTracks().forEach(track => track.stop());
        if (currentContext.state !== "closed") void currentContext.close();
      };
      const finish = async () => {
        if (finished) return;
        finished = true;
        const sampleRate = currentContext.sampleRate;
        dispose(); recording.current = null;
        if (!alive()) return;
        setListening(false); setLevel(0);
        if (!heardSpeech || !chunks.length) {
          setStatus("No speech heard. Try speaking closer to the microphone, or type your request.");
          setProcessing(false); starting.current = false; return;
        }
        setProcessing(true); setStatus("Transcribing on your device…");
        try {
          const samples = normalizePCM(resamplePCM(chunks, sampleRate));
          if (recordingObjectURL.current) URL.revokeObjectURL(recordingObjectURL.current);
          recordingObjectURL.current = URL.createObjectURL(pcmWav(samples));
          setRecordingURL(recordingObjectURL.current);
          const result = await voiceJob("transcribe", text => { if (alive()) setStatus(text); }, {samples});
          if (!alive()) return;
          const text = result.text?.trim();
          if (text) { setStatus("Transcription ready."); callback.current(text); }
          else setStatus("No speech heard. Try again, or type your request.");
        } catch (error) {
          console.error("Local Whisper transcription failed:", error);
          if (alive()) setStatus(`Whisper could not transcribe this recording. ${error instanceof Error ? error.message.slice(0, 140) : "Please retry."} You can still type your request.`);
        } finally {
          if (alive()) { setProcessing(false); starting.current = false; }
        }
      };
      const stop = () => {
        if (stopping) return;
        stopping = true;
        clearInterval(timer);
        node.port.postMessage("stop");
        // Recover if a backgrounded browser suspends the worklet before its flush acknowledgement.
        flushTimer = setTimeout(() => { void finish(); }, 500);
      };
      const timer = setInterval(() => {
        const now = Date.now();
        if ((stopOnPause && heardSpeech && now - lastSound > 4000) || (!heardSpeech && now - started > 7000) || now - started > 30000) stop();
      }, 100);
      node.port.onmessage = ({data}: MessageEvent<{kind: string; samples?: Float32Array}>) => {
        if (data.kind === "stopped") { void finish(); return; }
        if (data.samples && !finished) {
          chunks.push(data.samples);
          const rms = Math.sqrt(data.samples.reduce((sum, sample) => sum + sample * sample, 0) / data.samples.length);
          setLevel(Math.min(1, rms * 12));
          if (rms > 0.003) { heardSpeech = true; lastSound = Date.now(); }
        }
      };
      recording.current = {stop, dispose};
      setListening(true); setProcessing(false);
      setStatus(stopOnPause ? "Listening now. A four-second pause stops recording. Maximum 30 seconds." : "Listening now. Finish your sentence, then press Stop microphone. Maximum 30 seconds.");
    } catch (error) {
      recording.current?.dispose(); recording.current = null;
      stream?.getTracks().forEach(track => track.stop()); if (context && context.state !== "closed") void context.close();
      if (alive()) {
        setListening(false); setProcessing(false); starting.current = false;
        setStatus(error instanceof DOMException && (error.name === "NotAllowedError" || error.name === "SecurityError")
          ? "Microphone permission denied. Allow access in your browser settings, or type your request."
          : `Local speech recognition could not start. ${error instanceof Error ? error.message.slice(0, 140) : "Check model download access."} You can still type your request.`);
      }
    }
  }
  return {supported, listening, processing, status, level, recordingURL, microphoneName, microphones, microphoneId, setMicrophoneId, toggle};
}
