import type { VoiceId } from "./voices";
type Reply = {id: number; kind: "progress" | "done" | "error"; text?: string; blob?: Blob};
type Pending = {resolve: (reply: Reply) => void; reject: (error: Error) => void; progress: (text: string) => void; timer: ReturnType<typeof setTimeout>};
let worker: Worker | undefined;
let sequence = 0;
const pending = new Map<number, Pending>();
function reset(message: string) {
  worker?.terminate(); worker = undefined;
  for (const item of pending.values()) { clearTimeout(item.timer); item.reject(new Error(message)); }
  pending.clear();
}
function getWorker() {
  if (!worker) {
    worker = new Worker(new URL("./voice.worker.ts", import.meta.url), {type: "module"});
    worker.onmessage = ({data}: MessageEvent<Reply>) => {
      const item = pending.get(data.id);
      if (!item) return;
      if (data.kind === "progress") { item.progress(data.text || "Loading…"); return; }
      clearTimeout(item.timer); pending.delete(data.id);
      if (data.kind === "error") item.reject(new Error(data.text)); else item.resolve(data);
    };
    worker.onerror = () => reset("The local voice engine could not start. Try reloading the page.");
  }
  return worker;
}
export function voiceJob(task: "prepare" | "transcribe" | "speak", progress: (text: string) => void,
  payload: {samples?: Float32Array; text?: string; voice?: VoiceId} = {}) {
  return new Promise<Reply>((resolve, reject) => {
    const instance = getWorker();
    const id = ++sequence;
    const timer = setTimeout(() => reset("Voice processing timed out. Check model download access and retry."), 300000);
    pending.set(id, {resolve, reject, progress, timer});
    instance.postMessage({id, task, ...payload});
  });
}
