'use client';
import { useEffect, useState } from 'react';
import Image from 'next/image';
import { assetUrl } from '@/lib/engine';

type Region = { ease_cm: number | null; verdict: string };
type Result = { image: string; caption: string; report: { regions: Record<string, Region> } };
type Pair = { garment_id: string; size: string } | null;
type Props = { body: unknown; garmentId: string; size: string; preferences: unknown; view: string; hasPhoto: boolean; pair?: Pair };
const cache = new Map<string, Result>();
const inFlight = new Map<string, Promise<Result>>();

function draw(props: Props): Promise<Result> {
  const { body, garmentId, size, preferences, view, pair = null } = props;
  const key = JSON.stringify({ body, garmentId, size, preferences, view, pair });
  const hit = cache.get(key);
  if (hit) return Promise.resolve(hit);
  let job = inFlight.get(key);
  if (!job) {
    job = fetch('/api/engine/preview/photo', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(180_000),
      body: JSON.stringify({ body, garment_id: garmentId, size, view, preferences, style: 'mannequin',
        ...(pair ? { pair_garment_id: pair.garment_id, pair_size: pair.size } : {}) }),
    }).then(async response => {
      const json = await response.json();
      if (!response.ok) throw new Error(response.status === 404 ? (json.detail || 'This styled view is not available right now. The size-chart comparison is still available.') : 'The styled view is unavailable right now. The size-chart comparison is still available.');
      cache.set(key, json);
      return json as Result;
    }).finally(() => inFlight.delete(key));
    inFlight.set(key, job);
  }
  return job;
}

export default function RealisticView(props: Props) {
  const { body, garmentId, size, preferences, view, pair = null, hasPhoto } = props;
  const key = JSON.stringify({ body, garmentId, size, preferences, view, pair });
  const [result, setResult] = useState<Result | null>(cache.get(key) || null);
  const [loading, setLoading] = useState(!cache.has(key));
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    draw(JSON.parse(key)).then(json => { if (live) setResult(json); })
      .catch(cause => { if (live) setError(cause instanceof Error ? cause.message : 'The preview could not be prepared.'); })
      .finally(() => { if (live) setLoading(false); });
    // start the other angles too, so turning the figure is instant (each is drawn once, then cached)
    (['front', 'side', 'back'] as const).filter(other => other !== view)
      .forEach(other => draw({ ...JSON.parse(key), view: other }).catch(() => {}));
    return () => { live = false; };
  }, [key, attempt]);
  return <div className="realistic-view" aria-busy={loading}>
    {result && <Image src={result.image} alt={`AI illustration: ${garmentId.replaceAll('-', ' ')}, size ${size}, ${view} view`} fill unoptimized sizes="(max-width: 720px) 100vw, 50vw" />}
    {loading && <div className="room-preview-loading" role="status"><svg viewBox="0 0 100 70" fill="none" aria-hidden="true"><path d="M42 15a8 8 0 1 1 12 7v8l33 23a3 3 0 0 1-2 5H15a3 3 0 0 1-2-5l37-24" stroke="currentColor" strokeWidth="1.5" /></svg><strong>Preparing the {view} view</strong><p>A new combination may take up to a minute.<br />Your fit report is available beside the preview.</p></div>}
    {error && hasPhoto && <Image src={assetUrl(`fixtures/garment_photos/${garmentId}.jpg`)} alt={`Product photo reference: ${garmentId.replaceAll('-', ' ')}`} fill unoptimized sizes="(max-width: 720px) 100vw, 50vw" />}
    {error && <div className={`room-preview-error ${hasPhoto ? 'with-photo' : ''}`} role="alert"><span className="room-overline">{hasPhoto ? 'PRODUCT PHOTO · NOT A TRY-ON' : 'PREVIEW UNAVAILABLE'}</span><p>{error}</p><button onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1); }}>Try this view again</button></div>}
  </div>;
}
