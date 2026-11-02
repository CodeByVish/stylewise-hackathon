export async function readVoiceStream(response: Response, onAudio: (samples: Float32Array, rate: number, prebuffer?: number) => void) {
  if (!response.ok || !response.body) throw new Error("The local voice stream is unavailable.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let frames = 0;
  function accept(line: string) {
    if (!line.trim()) return;
    const message = JSON.parse(line);
    if (message.kind === "error") throw new Error(message.message || "Voice generation failed");
    if (message.kind !== "audio") return;
    if (!Number.isFinite(message.rate) || message.rate < 8000 || message.rate > 48000) throw new Error("Invalid voice sample rate");
    const raw = atob(message.pcm);
    if (!raw.length || raw.length % 2) throw new Error("Invalid voice audio chunk");
    const bytes = Uint8Array.from(raw, char => char.charCodeAt(0));
    const view = new DataView(bytes.buffer);
    const samples = new Float32Array(bytes.length / 2);
    for (let i = 0; i < samples.length; i++) samples[i] = view.getInt16(i * 2, true) / 32768;
    onAudio(samples, message.rate, message.complete ? 0.03 : 1.2); frames++;
  }
  try {
    while (true) {
      const {value, done} = await reader.read();
      pending += decoder.decode(value, {stream: !done});
      let end;
      while ((end = pending.indexOf("\n")) >= 0) { accept(pending.slice(0, end)); pending = pending.slice(end + 1); }
      if (done) break;
    }
    accept(pending);
    if (!frames) throw new Error("The voice model returned no audio");
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
