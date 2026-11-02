export function resamplePCM(chunks: Float32Array[], inputRate: number, outputRate = 16000) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const input = new Float32Array(length);
  let offset = 0;
  for (const chunk of chunks) { input.set(chunk, offset); offset += chunk.length; }
  if (!length) return input;
  const output = new Float32Array(Math.ceil(length * outputRate / inputRate));
  // Area averaging preserves the sample amplitude while reducing aliasing on downsampling.
  for (let i = 0; i < output.length; i++) {
    const start = i * inputRate / outputRate;
    const end = Math.min(length, (i + 1) * inputRate / outputRate);
    let sum = 0;
    for (let j = Math.floor(start); j < Math.ceil(end); j++) {
      sum += input[j] * (Math.min(end, j + 1) - Math.max(start, j));
    }
    output[i] = end > start ? sum / (end - start) : 0;
  }
  return output;
}

export function normalizePCM(input: Float32Array) {
  if (!input.length) return input;
  const mean = input.reduce((sum, value) => sum + value, 0) / input.length;
  let peak = 0;
  for (const value of input) peak = Math.max(peak, Math.abs(value - mean));
  const gain = peak > 0 ? Math.min(4, 0.9 / peak) : 1;
  return Float32Array.from(input, value => Math.max(-1, Math.min(1, (value - mean) * gain)));
}

export function pcmWav(samples: Float32Array, rate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  text(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); text(8, "WAVE"); text(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, "data"); view.setUint32(40, samples.length * 2, true);
  samples.forEach((value, index) => view.setInt16(44 + index * 2, Math.max(-1, Math.min(1, value)) * 32767, true));
  return new Blob([buffer], {type: "audio/wav"});
}
