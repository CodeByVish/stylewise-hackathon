class StylewisePCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.stopped = false;
    this.port.onmessage = ({data}) => {
      if (data === 'stop') { this.stopped = true; this.port.postMessage({kind:'stopped'}); }
    };
  }
  process(inputs) {
    if (this.stopped) return false;
    const channel = inputs[0]?.[0];
    if (channel) { const samples = channel.slice(); this.port.postMessage({kind:'samples',samples}, [samples.buffer]); }
    return true;
  }
}
registerProcessor('stylewise-pcm', StylewisePCM);
