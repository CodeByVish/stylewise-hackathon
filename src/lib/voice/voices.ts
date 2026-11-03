// Curated model voices, independent of the computer's installed voices.
export const VOICES = [
  {id: "af_heart", name: "Heart · American English · feminine"},
  {id: "af_bella", name: "Bella · American English · feminine"},
  {id: "am_michael", name: "Michael · American English · masculine"},
  {id: "bf_emma", name: "Emma · British English · feminine"},
  {id: "bm_george", name: "George · British English · masculine"},
] as const;
export type VoiceId = typeof VOICES[number]["id"];
export const VOICE_PREVIEW = "Hello beta, pick a garment and a size, and I will check how it sits on your shape.";
