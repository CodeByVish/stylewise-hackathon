'use client';
// Visual fit preview (P0): a faceless mannequin with the selected silhouette, drawn by Meta muse-image
// from the measured FitReport, so a too-small size looks strained and a too-big one looks baggy.
// Generated on demand (15-80 s the first time, then cached by the engine).
import { useState } from 'react';

type Region = { ease_cm: number | null; verdict: string };
type Preview = { image: string; caption: string; report: { regions: Record<string, Region> } };
type Props = { body: unknown; garmentId: string; size: string; preferences: unknown; enabled: boolean; hasPhoto: boolean };

const label = (verdict: string) => verdict === 'borderline' ? 'could go either way' : verdict;

export default function FitPreview({ body, garmentId, size, preferences, enabled, hasPhoto }: Props) {
  const [style, setStyle] = useState<'mannequin' | 'illustration'>('mannequin');
  const [result, setResult] = useState<Preview | null>(null);
  const [shownFor, setShownFor] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const key = JSON.stringify({ body, garmentId, size, style });
  const stale = result !== null && shownFor !== key;

  async function show() {
    setLoading(true); setError('');
    try {
      const response = await fetch('/api/engine/preview/photo', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body, garment_id: garmentId, size, style, preferences }),
      });
      const json = await response.json();
      if (!response.ok) throw new Error(json.detail || json.error || 'The preview could not be drawn.');
      setResult(json); setShownFor(key);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The preview could not be drawn.');
    } finally { setLoading(false); }
  }

  return <section className="card fit-preview" aria-label="Visual fit preview">
    <div className="nisha-chat-heading"><span className="tiny-label">SEE THE FIT</span><span className="scene-badge">{size}</span></div>
    <h2>How size {size} sits</h2>
    {!enabled ? <p className="field-note">Pick a silhouette to see this size on a mannequin with that shape.</p>
      : <>
        {!hasPhoto && <p className="field-note">No product photo yet: drawn from the catalogue description.</p>}
        <div className="mode-switch">{(['mannequin', 'illustration'] as const).map(value =>
          <button key={value} aria-pressed={style === value} onClick={() => setStyle(value)}>{value === 'mannequin' ? 'Mannequin' : 'Sketch'}</button>)}</div>
        <button className="primary-button" onClick={show} disabled={loading}>{loading ? 'Drawing the fit… (up to a minute)' : result && !stale ? 'Redraw' : 'Show this fit'}<span>→</span></button>
        {error && <p role="alert" className="engine-error">{error}</p>}
        {result && <div className={stale ? 'preview-stale' : ''}>
          <img className="preview-image" src={result.image} alt={`Mannequin wearing size ${size}`} />
          {stale && <p className="field-note">Selection changed. Press Show this fit to redraw.</p>}
          <div className="preview-verdicts">{Object.entries(result.report.regions).filter(([, r]) => r.ease_cm !== null).map(([name, r]) =>
            <span key={name} className={`comparison-verdict ${r.verdict}`}>{name} {r.ease_cm! > 0 ? '+' : ''}{r.ease_cm} cm · {label(r.verdict)}</span>)}</div>
          <p className="field-note">{result.caption}</p>
        </div>}
      </>}
  </section>;
}
