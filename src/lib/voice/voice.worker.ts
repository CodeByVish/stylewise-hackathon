import { env, pipeline, type AutomaticSpeechRecognitionPipeline } from "@huggingface/transformers";
import { KokoroTTS } from "kokoro-js";
import type { VoiceId } from "./voices";

env.allowLocalModels = false;
// Works without cross-origin isolation headers on Amplify's static hosting.
if (env.backends.onnx.wasm) env.backends.onnx.wasm.numThreads = 1;
let recognizer: AutomaticSpeechRecognitionPipeline | undefined;
let speaker: KokoroTTS | undefined;
type Job = {id: number; task: "prepare" | "transcribe" | "speak"; samples?: Float32Array; text?: string; voice?: VoiceId};

async function run(job: Job) {
  const progress = (event: {status: string; progress?: number}) => {
    if (event.status === "progress") self.postMessage({id: job.id, kind: "progress", text: `Downloading voice model: ${Math.round(event.progress || 0)}% of current file`});
  };
  try {
    if (job.task === "prepare" || job.task === "transcribe") {
      if (!recognizer) {
        self.postMessage({id: job.id, kind: "progress", text: "Loading Whisper Small for transcription. First use downloads a larger free model."});
        const loadRecognizer = pipeline as unknown as (task: string, model: string, options: object) => Promise<AutomaticSpeechRecognitionPipeline>;
        recognizer = await loadRecognizer("automatic-speech-recognition", "onnx-community/whisper-small", {device: "wasm", dtype: "q8", progress_callback: progress});
      }
      if (job.task === "prepare") { self.postMessage({id: job.id, kind: "done"}); return; }
      const result = await recognizer(job.samples!, {language: "english", task: "transcribe", return_timestamps: false});
      self.postMessage({id: job.id, kind: "done", text: (Array.isArray(result) ? result[0].text : result.text).trim()});
    } else {
      if (!speaker) {
        self.postMessage({id: job.id, kind: "progress", text: "Loading Kokoro reply voice. First use downloads the model."});
        speaker = await KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", {device: "wasm", dtype: "q8", progress_callback: progress});
      }
      self.postMessage({id: job.id, kind: "progress", text: "Generating reply audio on your device…"});
      // Expand the currency abbreviation without changing the displayed answer.
      const text = job.text!.replace(/\bSGD\s*(\d+)/g, "$1 Singapore dollars");
      const audio = await speaker.generate(text, {voice: job.voice || "af_heart", speed: 0.95});
      self.postMessage({id: job.id, kind: "done", blob: audio.toBlob()});
    }
  } catch (error) {
    self.postMessage({id: job.id, kind: "error", text: error instanceof Error ? error.message : "Voice processing failed"});
  }
}
// Avoid overlapping inference calls and the associated memory spikes.
let queue = Promise.resolve();
self.onmessage = (event: MessageEvent<Job>) => { queue = queue.then(() => run(event.data)); };
