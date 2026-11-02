// Nisha for the Fit Lab. Persona copied from the Stylewise app (lib/voice/stylists.ts, "desi-aunty");
// every fit fact comes from POST /nisha/chat, which runs Muse Spark + the fit engine (fit-engine/stylewise_fit/nisha.py).
import type { VoiceId } from "./voice/voices";

export const NISHA = {
  id: "desi-aunty",
  name: "Nisha",
  voice: "af_heart" as VoiceId,
  greeting: "Hi beta, I'm Nisha. Tell me your measurements or pick a silhouette, and I'll check the fit with you.",
} as const;

export const FIT_API = process.env.NEXT_PUBLIC_FIT_API_URL || "/api/engine";

export type ChatTurn = { role: "user" | "assistant"; content: string };

// Mirrors contracts/fit_request.schema.json (body) and the Fit Lab form.
export type FitContext = {
  body?: {
    source?: "measured" | "preset";
    preset?: { shape: string; usual_size: string; sex?: "female" | "male" };
    height_cm: number;
    chest_cm?: number;
    waist_cm?: number;
    hip_cm?: number;
  };
  garment_id?: string;
  garment_size?: string;
  preferences?: { fit_pref?: "snug" | "regular" | "relaxed"; closure?: "front_open" | "pullover" };
};

export type NishaReply = {
  reply: string;
  report: Record<string, unknown> | null; // FitReport, see contracts/fit_report.schema.json
  source: "muse" | "engine-template";
};

export async function askNisha(messages: ChatTurn[], context: FitContext = {}): Promise<NishaReply> {
  const response = await fetch(`${FIT_API}/nisha/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, context }),
  });
  if (!response.ok) throw new Error(`Nisha is unavailable (HTTP ${response.status}). Is the fit API running on ${FIT_API}?`);
  return response.json();
}
