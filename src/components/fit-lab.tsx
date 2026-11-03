'use client';

import { useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { createRequest, fixtureBody, fixtureCatalog, parseCatalog, parseReport, previewReport, type GarmentCatalog, type FitReport, type Measurements, type Size } from '@/lib/fit-contract';
import type { View } from './fit-viewer';
const FitViewer = dynamic(() => import('./fit-viewer'), { ssr: false, loading: () => <div className="viewer-status">Preparing your fitting room…</div> });
const labels: Record<keyof Measurements, string> = { height: 'Height', chest: 'Chest', waist: 'Waist', hip: 'Hip' };
function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    hanger: <><path d="M10 7a2 2 0 1 1 3 1.7V11l8 6a1 1 0 0 1-.6 2H3.6a1 1 0 0 1-.6-2l9-6"/></>,
    sparkle: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/></>,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
    rotate: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.sparkle}</svg>;
}
function TopDrawing() { return <svg viewBox="0 0 160 150" fill="none" aria-hidden="true"><path d="m55 24-31 18-17 35 27 13 13-22-5 65h76l-5-65 13 22 27-13-17-35-31-18c-10 12-30 12-40 0Z" fill="#7c8779" stroke="#5a6558" strokeWidth="1.5"/><path d="M60 27c3 21 37 21 40 0M47 68l4-22m62 22-4-22M44 125h72" stroke="#a4ad9b" strokeWidth="2"/></svg>; }
export default function FitLab() {
  const [measurements, setMeasurements] = useState<Measurements>(fixtureBody);
  const [catalog, setCatalog] = useState<GarmentCatalog>(fixtureCatalog);
  const garments = catalog.sizes;
  const [size, setSize] = useState<Size>('M');
  const [view, setView] = useState<View>('front');
  const [rotating, setRotating] = useState(false);
  const [showBody, setShowBody] = useState(true);
  const [preference, setPreference] = useState<'none' | 'front-opening'>('none');
  const [imported, setImported] = useState<FitReport | null>(null);
  const [message, setMessage] = useState('');
  const [photo, setPhoto] = useState<string | null>(null);
  const photoRef = useRef<HTMLInputElement>(null), reportRef = useRef<HTMLInputElement>(null), catalogRef = useRef<HTMLInputElement>(null);
  const request = createRequest(measurements, size, preference, catalog);
  const report = imported || previewReport(request);
  const negative = report.easeCm.chest < 0 || report.easeCm.waist < 0;
  const resetReport = () => { setImported(null); setMessage(''); };
  function downloadRequest() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(request, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'stylewise-fit-request.json'; link.click(); URL.revokeObjectURL(url);
    setMessage('Fit request downloaded. Measurements stay on this device.');
  }
  async function importReport(file?: File) {
    if (!file) return;
    try {
      if (file.size > 100_000) throw new Error('Choose a report smaller than 100 KB.');
      const next = parseReport(JSON.parse(await file.text())); setImported(next); setSize(next.size); setMeasurements(next.measurementsCm); setMessage('Fit report imported. Showing supplied results and mesh references.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to read report.'); }
  }
  return <div className="app-shell">
    <aside className="sidebar"><Link href="/" className="brand" aria-label="Stylewise home">s<span>✳</span></Link><div className="nav-icons"><a href="#workspace" aria-label="Fit Lab" className="nav-active"><Icon name="grid"/></a><a href="#garment" aria-label="Garment details"><Icon name="hanger"/></a><a href="#fit-insights" aria-label="Fit insights"><Icon name="sparkle"/></a></div><div className="avatar">SW</div></aside>
    <div className="main-shell"><header className="topbar"><Link href="/" className="wordmark">stylewise<span> / fit lab</span></Link><span className="prototype"><span/> Research prototype</span></header>
    <main id="workspace"><div className="page-heading"><div><div className="eyebrow">FIND YOUR SIZE BEFORE YOU BUY</div><h1>A little more certainty.<br/><em>Before you buy.</em></h1><p>Explore the size. See every angle. Understand the evidence.</p></div><div className="session-label"><span className="live-dot"/> FIT LAB / 001<br/><small>One garment. A clearer perspective.</small></div></div>
    <div className="workspace-grid">
      <section className="card input-panel" aria-label="Measurements and garment"><div className="panel-heading"><span className="step">01</span><h2>Your starting point</h2></div>
        <div className="section-label">BODY MEASUREMENTS <span>cm</span></div><div className="measurement-grid">{(Object.keys(labels) as (keyof Measurements)[]).map(key => <label key={key}>{labels[key]}<div className="number-field"><input type="number" min={key === 'height' ? 100 : 30} max={key === 'height' ? 230 : 200} step="0.5" value={measurements[key]} onChange={event => {
          const value = Number(event.target.value); if (!Number.isFinite(value)) return; resetReport(); setMeasurements(prev => ({ ...prev, [key]: value }));
        }} onBlur={() => setMeasurements(prev => ({ ...prev, [key]: Math.min(key === 'height' ? 230 : 200, Math.max(key === 'height' ? 100 : 30, prev[key])) }))} aria-label={`${labels[key]} in centimeters`}/><span>cm</span></div></label>)}</div>
        <p className="field-note">Optional demo inputs. No photos of your body needed.</p>
        <div className="divider"/><div className="section-label" id="garment">THE GARMENT <span>01 ITEM</span></div><div className="garment-product"><div className="garment-art">{photo ? <div className="photo-preview" style={{ backgroundImage: `url(${JSON.stringify(photo)})` }} role="img" aria-label="Your locally selected garment photo"/> : <TopDrawing/>}</div><div><span className="tiny-label">{catalog.id === fixtureCatalog.id ? 'STUDIO FIXTURE' : 'IMPORTED GARMENT'}</span><h3>{catalog.name}</h3><p>{catalog.id === fixtureCatalog.id ? 'Sage · short sleeve' : 'Source supplied in metadata'}</p><span className="fixture-tag">{catalog.id === fixtureCatalog.id ? 'Synthetic asset' : 'Imported specs'}</span></div></div>
        <div className="size-label">Compare a size</div><div className="size-switch">{(['S','M'] as Size[]).map(item => <button key={item} aria-pressed={size === item} className={size === item ? 'selected' : ''} onClick={() => { setSize(item); resetReport(); }}><strong>{item}</strong><span>{garments[item].chestCm} cm chest</span>{size === item && <Icon name="check" size={15}/>}</button>)}</div>
        <label className="preference-label">Dressing preference<select value={preference} onChange={e => { setPreference(e.target.value as typeof preference); resetReport(); }}><option value="none">No preference</option><option value="front-opening">Prefer a front opening</option></select></label>
        <button className="upload-button" onClick={() => photoRef.current?.click()}><Icon name="upload" size={16}/> {photo ? 'Replace garment photo' : 'Add a garment photo'}</button><input ref={photoRef} aria-label="Garment photo file" type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={async e => { const file = e.target.files?.[0]; if (!file) return; if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5_000_000) { setMessage('Choose a PNG, JPEG or WebP image under 5 MB.'); return; } const reader = new FileReader(); reader.onload = () => setPhoto(String(reader.result)); reader.readAsDataURL(file); e.target.value = ''; }}/><p className="field-note">Local preview only. SAM segmentation isn’t connected yet.</p>
        <button className="text-button" onClick={() => catalogRef.current?.click()}>Import garment metadata</button>
        <input ref={catalogRef} aria-label="Garment metadata file" hidden type="file" accept=".json,application/json" onChange={async e => {
          const file = e.target.files?.[0]; e.target.value = ''; if (!file) return;
          try { if (file.size > 100_000) throw new Error('Choose metadata smaller than 100 KB.');
            const next = parseCatalog(JSON.parse(await file.text())); setCatalog(next); setPhoto(null); resetReport(); setMessage('Garment specifications imported. Physical dimensions use the supplied source.');
          } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not import garment metadata.'); }
        }}/>
        {catalog.id !== fixtureCatalog.id && <button className="text-button" onClick={() => { setCatalog(fixtureCatalog); setPhoto(null); resetReport(); }}>Use synthetic garment</button>}
      </section>
      <section className="viewer-panel" aria-label="3D fitting room"><div className="viewer-top"><div><span className="tiny-label">THE FITTING ROOM</span><h2>A new perspective</h2></div><span className="scene-badge">3D / {size}</span></div><div className="viewer-scene"><div className="scene-rings"/><FitViewer bodyUrl={report.bodyMeshUrl} garmentUrl={report.garmentMeshUrl} view={view} rotating={rotating} showBody={showBody}/><div className="viewer-caption">{imported ? 'Imported report assets' : catalog.id === fixtureCatalog.id ? 'Fixed mannequin · synthetic garment shell' : 'Fixed mannequin · supplied garment mesh'}</div></div><div className="viewer-toolbar"><div className="view-switch">{(['front','side','back'] as View[]).map(item => <button key={item} className={view === item ? 'active' : ''} aria-pressed={view === item} onClick={() => { setView(item); setRotating(false); }}>{item}</button>)}</div><button className={`rotate-button ${rotating ? 'active' : ''}`} aria-pressed={rotating} onClick={() => setRotating(!rotating)}><Icon name="rotate" size={17}/><span>{rotating ? 'Pause' : 'Rotate'}</span></button></div><div className="viewer-bottom"><span>Drag to orbit · scroll to zoom</span><label><input type="checkbox" checked={showBody} onChange={e => setShowBody(e.target.checked)}/> Show body</label></div></section>
      <section className="card insights-panel" id="fit-insights"><div className="panel-heading"><span className="step">02</span><h2>Beyond the mirror</h2></div><div className="evidence-tag"><span/>{imported ? 'IMPORTED FIT REPORT' : catalog.id === fixtureCatalog.id ? 'FIXTURE · DIMENSION COMPARISON' : 'SUPPLIED SPECS · DIMENSION COMPARISON'}</div><h3 className="insight-title">{negative ? 'Less room than your measurements.' : 'More room in the measurements.'}</h3><p className="insight-copy">Size {size} compared with your inputs. Numbers are a starting point, not a promise of fit.</p><div className="ease-cards">{(['chest','waist'] as const).map(key => <div key={key} className={report.easeCm[key] < 0 ? 'ease negative' : 'ease'}><div><span>{labels[key]} ease</span><Icon name={report.easeCm[key] < 0 ? 'info' : 'arrow'} size={16}/></div><strong>{report.easeCm[key] > 0 ? '+' : ''}{Number(report.easeCm[key].toFixed(1))}<small>cm</small></strong><p>{imported ? 'Reported by fit engine' : `${garments[size][key === 'chest' ? 'chestCm' : 'waistCm']} garment − ${measurements[key]} body`}</p></div>)}</div><div className="nisha-note"><span className="nisha-icon"><Icon name="sparkle" size={19}/></span><div><div className="nisha-label">A NOTE FROM THE LAB</div><p>{report.advice}</p></div></div><details className="evidence-details" open><summary>What we don’t know yet <span>{report.unknowns.length}</span></summary><ul>{report.unknowns.map((text, i) => <li key={i}>{text}</li>)}</ul></details><details className="evidence-details"><summary>Sources & limitations</summary><p>{report.provenance}</p><ul>{report.warnings.map((text, i) => <li key={i}>{text}</li>)}</ul></details><button className="primary-button" onClick={downloadRequest}>Export fit request <Icon name="arrow" size={18}/></button><button className="text-button" onClick={() => reportRef.current?.click()}>Import P0 fit report</button><input ref={reportRef} aria-label="Fit report file" hidden type="file" accept=".json,application/json" onChange={e => { void importReport(e.target.files?.[0]); e.target.value = ''; }}/>{imported && <button className="text-button" onClick={resetReport}>Return to fixture results</button>}
      </section>
    </div><div className="bottom-note"><Icon name="info" size={16}/><p>Made for a more considered choice. This prototype compares dimensions; it doesn’t simulate cloth or guarantee comfort.</p><span>STYLEWISE FIT LAB</span></div><div className="message" role="status" aria-live="polite">{message}</div>
    </main><footer><span>stylewise</span><p>Less guesswork. More you.</p><span>META HACKATHON · 2026</span></footer></div>
  </div>;
}
