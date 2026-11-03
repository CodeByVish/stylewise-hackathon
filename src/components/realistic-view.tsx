'use client';
// Realistic fitting-room view (P0): Meta muse-image draws the real fabric (from the product photo) on a
// faceless mannequin, guided by our measured 3D render for this view and told the measured fit, so a
// too-small size looks strained and a too-big one hangs loose. Each view is generated once, then kept.
import { useEffect, useState } from 'react';

type Region = { ease_cm: number | null; verdict: string };
type Result = { image: string; caption: string; report: { regions: Record<string, Region> } };
type Pair = { garment_id: string; size: string } | null;
type Props = { body: unknown; garmentId: string; size: string; preferences: unknown; view: string; hasPhoto: boolean; pair?: Pair };

const cache = new Map<string, Result>();
const inFlight = new Map<string, Promise<Result>>();

// one request per (body, garment, size, view), shared by the shown view and the background prefetch
function draw(body: unknown, garmentId: string, size: string, view: string, preferences: unknown, pair: Pair): Promise<Result> {
  const key = JSON.stringify({ body, garmentId, size, view, preferences, pair });
  const hit = cache.get(key);
  if (hit) return Promise.resolve(hit);
  let job = inFlight.get(key);
  if (!job) {
    job = fetch('/api/engine/preview/photo', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body, garment_id: garmentId, size, view, preferences, style: 'mannequin',
        ...(pair ? { pair_garment_id: pair.garment_id, pair_size: pair.size } : {}) }),
    }).then(async response => {
      const json = await response.json();
      if (!response.ok) throw new Error(json.detail || json.error || 'The realistic view could not be drawn.');
      cache.set(key, json);
      return json as Result;
    }).finally(() => inFlight.delete(key));
    inFlight.set(key, job);
  }
  return job;
}

export default function RealisticView({ body, garmentId, size, preferences, view, hasPhoto, pair = null }: Props) {
  const key = JSON.stringify({ body, garmentId, size, view, preferences, pair });
  const [result, setResult] = useState<Result | null>(cache.get(key) || null);
  const [loading, setLoading] = useState(!cache.has(key));
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    draw(body, garmentId, size, view, preferences, pair)
      .then(json => { if (live) setResult(json); })
      .catch(e => { if (live) setError(e instanceof Error ? e.message : 'The realistic view could not be drawn.'); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, hasPhoto]);

  return <div className="realistic-view">
    {result && <img src={result.image} alt={`Size ${size} on a mannequin, ${view} view`} />}
    {loading && <div className="scene-progress"><span className="loading-dot" />Drawing the {view} view in this fabric… (up to a minute, once)</div>}
    {error && <div className="viewer-status error">{error}</div>}
    {result && <div className="preview-verdicts realistic-verdicts">{Object.entries(result.report.regions).filter(([, r]) => r.ease_cm !== null).map(([name, r]) =>
      <span key={name} className={`comparison-verdict ${r.verdict}`}>{name} {r.ease_cm! > 0 ? '+' : ''}{r.ease_cm} cm · {r.verdict === 'borderline' ? 'could go either way' : r.verdict}</span>)}</div>}
  </div>;
}
