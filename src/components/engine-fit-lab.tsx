'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import Link from 'next/link';
import { engine, assetUrl, type BodyInput, type CatalogueItem, type PieceResult } from '@/lib/engine';
import { dimensionLabel, fitSummary, regionLabel } from '@/lib/fit-presentation';
import type { GarmentPhoto } from '@/lib/garment-photo';
import type { View } from './fit-viewer';
import RealisticView from './realistic-view';
import FittingDialog from './fitting-dialog';
import NishaChat from './nisha-chat';
import SamGarment from './sam-garment';
import GarmentPhotoCard from './garment-photo-card';
import './fitting-room.css';

const Viewer = dynamic(() => import('./fit-viewer'), { ssr: false });
// approximate height of each body area in a full-figure styled view (top = 0, feet = 1), for zoom and highlight
const REGION_HEIGHT: Record<string, number> = { chest: 0.31, waist: 0.40, hip: 0.49 };
const shapes = [
  ['hourglass', 'The Balance', 'Defined waist, balanced proportions'],
  ['triangle', 'The Anchor', 'Fuller through the hips'],
  ['inverted_triangle', 'The Summit', 'Fuller through the shoulders'],
  ['rectangle', 'The Column', 'Straight and even proportions'],
  ['oval', 'The Orbit', 'Fuller through the middle'],
];
const bodySizes = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL'];
const categories = [['all', 'All pieces'], ['dress', 'Dresses'], ['top', 'Tops'], ['bottom', 'Bottoms'], ['outfit', 'Sets']];

function Silhouette({ shape }: { shape: string }) {
  const waist = shape === 'hourglass' ? 12 : shape === 'oval' ? 24 : 17;
  const shoulder = shape === 'inverted_triangle' ? 27 : shape === 'triangle' ? 17 : 23;
  const hip = shape === 'triangle' ? 28 : shape === 'inverted_triangle' ? 17 : 23;
  return <svg viewBox="0 0 80 100" aria-hidden="true"><circle cx="40" cy="12" r="8" fill="currentColor" /><path d={`M${40 - shoulder} 28 Q${40 - waist} 46 ${40 - waist} 54 Q${40 - hip} 70 ${40 - hip} 78 L${40 + hip} 78 Q${40 + waist} 70 ${40 + waist} 54 Q${40 + waist} 46 ${40 + shoulder} 28Z`} fill="currentColor" /><path d="M30 76v17m20-17v17" stroke="currentColor" strokeWidth="10" strokeLinecap="round" /></svg>;
}
const available = (item: CatalogueItem, sex: string) => item.fittable && item.garment_id !== 'green-kurta'
  && (!item.for || item.for === 'unisex' || item.for === (sex === 'female' ? 'women' : 'men'));

export default function EngineFitLab() {
  const [catalogue, setCatalogue] = useState<CatalogueItem[]>([]);
  const [mode, setMode] = useState<'preset' | 'measured'>('preset');
  const [sex, setSex] = useState<'female' | 'male'>('female');
  const [shape, setShape] = useState('rectangle');
  const [usualSize, setUsualSize] = useState('M');
  const [height, setHeight] = useState(165);
  const [girths, setGirths] = useState({ chest_cm: 90, waist_cm: 74, hip_cm: 96 });
  const [garmentId, setGarmentId] = useState('zesica-black-midi-dress');
  const [garmentSize, setGarmentSize] = useState('M');
  const [fitPref, setFitPref] = useState<'snug' | 'regular' | 'relaxed'>('regular');
  const [closure, setClosure] = useState<'' | 'front_open' | 'pullover'>('');
  const [pairId, setPairId] = useState('');
  const [category, setCategory] = useState('all');
  const [view, setView] = useState<View>('front');
  const [look, setLook] = useState<'real' | '3d'>('real');
  const [rotating, setRotating] = useState(false);
  const [results, setResults] = useState<PieceResult[] | null>(null);
  const [pending, setPending] = useState(true);
  const [error, setError] = useState('');
  const [bodyScene, setBodyScene] = useState<{ key: string; url: string } | null>(null);
  const [bodyError, setBodyError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [photos, setPhotos] = useState<Record<string, GarmentPhoto | null>>({});
  const [dialog, setDialog] = useState<'nisha' | 'compare' | null>(null);
  const rail = useRef<HTMLDivElement>(null);

  const item = catalogue.find(value => value.garment_id === garmentId);
  const body: BodyInput = mode === 'preset'
    ? { source: 'preset', height_cm: height, preset: { shape, usual_size: usualSize, sex } }
    : { source: 'measured', height_cm: height, ...girths };
  const bodyKey = JSON.stringify(body);
  const [compareZoom, setCompareZoom] = useState<Record<string, boolean>>({});
  // Entered measurements still get visuals: the closest prepared preset (the fit itself uses the exact numbers).
  const [nearest, setNearest] = useState<{ shape: string; shape_name?: string; usual_size: string; height_cm: number; sex: string; preset_cm?: { chest?: number; waist?: number; hip?: number } } | null>(null);
  useEffect(() => {
    if (mode !== 'measured') return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch('/api/engine/presets/nearest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ sex, height_cm: height, ...girths }) })
        .then(response => response.ok ? response.json() : null)
        .then(value => { if (!controller.signal.aborted) setNearest(value); }).catch(() => {});
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [mode, sex, height, girths]);
  const visualBody = (mode === 'preset' ? body : nearest
    ? { source: 'preset', height_cm: nearest.height_cm, preset: { shape: nearest.shape, usual_size: nearest.usual_size, sex: nearest.sex } }
    : null) as BodyInput | null;
  const visualKey = JSON.stringify(visualBody);
  const preferences = { fit_pref: fitPref, ...(closure ? { closure } : {}) };
  const allSizes = item?.sizes || ['S', 'M', 'L'];
  const at = Math.max(0, allSizes.indexOf(garmentSize));
  const start = Math.max(0, Math.min(at - 1, allSizes.length - 3));
  const comparisonSizes = allSizes.slice(start, start + 3);
  const evaluationKey = JSON.stringify({ body, items: allSizes.map(size => ({ garment_id: garmentId, size })), preferences });
  const pairCategory = item?.category === 'top' ? 'bottom' : item?.category === 'bottom' ? 'top' : '';
  const pairOptions = catalogue.filter(value => available(value, sex) && value.category === pairCategory);
  const pairItem = pairOptions.find(value => value.garment_id === pairId);
  const pair = pairItem ? { garment_id: pairItem.garment_id, size: pairItem.sizes.includes(garmentSize) ? garmentSize : pairItem.sizes[0] } : null;
  const browseItems = catalogue.filter(value => (available(value, sex)) && (category === 'all' || value.category === category));
  const photo = photos[garmentId] || null;
  const updatePhoto = (next: GarmentPhoto | null) => setPhotos(previous => ({ ...previous, [garmentId]: next }));
  const report = results?.find(value => value.garment_id === garmentId && value.size === garmentSize)?.report;
  const selectedError = results?.find(value => value.garment_id === garmentId && value.size === garmentSize)?.error;
  const summary = fitSummary(report, sex);
  const shapeInfo = shapes.find(([id]) => id === shape)!;

  useEffect(() => {
    const controller = new AbortController();
    engine<CatalogueItem[]>('catalogue', undefined, controller.signal).then(setCatalogue)
      .catch(cause => { if (!controller.signal.aborted) setError(cause.message); });
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setPending(true); setError('');
      try {
        const next = await engine<PieceResult[]>('fit/outfit', JSON.parse(evaluationKey), controller.signal);
        if (!controller.signal.aborted) setResults(next);
      } catch (cause) {
        if (!controller.signal.aborted) { setResults(null); setError(cause instanceof Error ? cause.message : 'Could not check this size.'); }
      } finally { if (!controller.signal.aborted) setPending(false); }
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [evaluationKey, refresh]);

  // A separately labelled body model. Never show a previous body's mesh under new inputs.
  useEffect(() => {
    if (!visualBody) return;
    const controller = new AbortController(); let url = '';
    fetch('/api/engine/viewer/scene', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({ body: JSON.parse(visualKey), items: [], tone: 'grey' }) })
      .then(response => response.ok ? response.blob() : Promise.reject(new Error('Could not load your body model. Try again.')))
      .then(blob => {
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(blob); setBodyScene({ key: visualKey, url });
      }).catch(cause => { if (!controller.signal.aborted) setBodyError(cause.message); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visualKey, refresh]);

  // Catalogue photos and user replacements share the same selected-garment/SAM state.
  useEffect(() => {
    if (!item?.photo || photos[garmentId] !== undefined) return;
    const controller = new AbortController();
    fetch(assetUrl(`fixtures/garment_photos/${garmentId}.jpg`), { signal: controller.signal })
      .then(response => response.ok ? response.blob() : Promise.reject(new Error('Photo unavailable')))
      .then(blob => new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsDataURL(blob); }))
      .then(data => { if (!controller.signal.aborted) setPhotos(previous => previous[garmentId] === undefined ? { ...previous, [garmentId]: { data, filename: `${garmentId}.jpg`, source: `Catalogue product photo: ${item.name}` } } : previous); })
      .catch(() => {});
    return () => controller.abort();
  }, [garmentId, item?.photo, item?.name, photos]);

  useEffect(() => {
    const container = rail.current;
    const selected = container?.querySelector<HTMLButtonElement>('[aria-pressed="true"]');
    if (!container || !selected) return;
    const left = selected.getBoundingClientRect().left - container.getBoundingClientRect().left + container.scrollLeft;
    container.scrollTo({ left: Math.max(0, left - (container.clientWidth - selected.clientWidth) / 2), behavior: 'instant' });
  }, [garmentId, category, catalogue]);

  function changeBody(action: () => void) {
    setResults(null); setPending(true); setBodyError(''); setRotating(false); action();
  }
  function selectSize(size: string) {
    setGarmentSize(size); setView('front'); setRotating(false);
  }
  function selectGarment(next: CatalogueItem) {
    setResults(null); setPending(true); setGarmentId(next.garment_id); setPairId(''); setView('front'); setRotating(false);
    if (!next.sizes.includes(garmentSize)) setGarmentSize(next.sizes.includes('M') ? 'M' : next.sizes[0]);
  }
  function selectSex(nextSex: 'female' | 'male') {
    changeBody(() => {
      setSex(nextSex); setHeight(nextSex === 'female' ? 165 : 175); setCategory('all'); setPairId('');
      if (nextSex === 'male' && shape === 'hourglass') setShape('rectangle');
      if (!item || !available(item, nextSex)) {
        const next = catalogue.find(value => available(value, nextSex) && value.garment_id === (nextSex === 'male' ? 'manyavar-mens-kurta' : 'zesica-black-midi-dress'))
          || catalogue.find(value => available(value, nextSex));
        if (next) selectGarment(next);
      }
    });
  }
  function changeLook(next: 'real' | '3d') {
    setLook(next); setRotating(false); setBodyError(''); if (next === 'real' && view === 'quarter') setView('front');
  }
  const renderPhoto = (product: CatalogueItem, width: number, height: number) => product.photo
    ? <Image src={photos[product.garment_id]?.data || assetUrl(`fixtures/garment_photos/${product.garment_id}.jpg`)} alt={product.name} width={width} height={height} unoptimized />
    : <span className="room-photo-empty">Photo unavailable</span>;

  return <div className="fitting-room">
    <header className="room-header">
      <Link href="/" className="room-brand">stylewise<span>FIT LAB</span></Link>
      <nav aria-label="Fitting room"><a href="#fitting">Try on</a><button disabled={!results} onClick={() => setDialog('compare')}>Compare sizes</button><a href="/#how">How it works</a></nav>
      <button className="room-header-nisha" onClick={() => setDialog('nisha')}>Ask Nisha <span aria-hidden="true">↗</span></button>
    </header>

    <main>
      <div className="room-intro"><div><p className="room-overline">A MORE CONSIDERED WAY TO SHOP</p><h1>Find your size <em>before you buy.</em></h1></div><p>Choose your shape. Find a piece.<br />See what the size chart says.</p></div>
      <a className="room-mobile-adjust" href="#your-shape"><span>{mode === 'preset' ? `${shapeInfo[1]} · usual ${usualSize} · ${height} cm` : 'Your entered measurements'}</span><span>Edit your shape ↓</span></a>
      <div className="room-layout" id="fitting">
        <aside className="room-person" id="your-shape" aria-label="Your body and preferences">
          <div className="room-section-title"><span>01</span><h2>Made around you</h2></div>
          <details className="room-body-edit" open><summary><span>{mode === 'preset' ? `${shapeInfo[1]} · usual ${usualSize} · ${height} cm` : `Your measurements · ${height} cm`}</span><span className="room-body-edit-cta">Collapse</span></summary>
          <div className="room-mode" aria-label="Body input method"><button aria-pressed={mode === 'preset'} onClick={() => changeBody(() => { setMode('preset'); setHeight(sex === 'female' ? 165 : 175); })}>Choose a shape</button><button aria-pressed={mode === 'measured'} onClick={() => changeBody(() => { setMode('measured'); setHeight(168); })}>Enter measurements</button></div>
          <label className="room-field">Body proportions<select value={sex} onChange={event => selectSex(event.target.value as typeof sex)}><option value="female">Female proportions</option><option value="male">Male proportions</option></select></label>
          {mode === 'preset' ? <>
            <div className="room-shapes" aria-label="Choose a silhouette">{shapes.filter(([id]) => sex === 'female' || id !== 'hourglass').map(([id, name]) => <button key={id} aria-pressed={shape === id} onClick={() => changeBody(() => setShape(id))}><Silhouette shape={id} /><span>{name.replace('The ', '')}</span></button>)}</div>
            <p className="room-shape-description"><strong>{shapeInfo[1]}</strong>{shapeInfo[2]}</p>
            <fieldset className="room-options"><legend>Your usual size</legend><div>{bodySizes.map(size => <button key={size} aria-pressed={usualSize === size} onClick={() => changeBody(() => setUsualSize(size))}>{size}</button>)}</div></fieldset>
            <fieldset className="room-options"><legend>Your height</legend><div>{(sex === 'female' ? [155, 165, 175] : [165, 175, 185]).map(cm => <button key={cm} aria-pressed={height === cm} onClick={() => changeBody(() => setHeight(cm))}>{cm}<small> cm</small></button>)}</div></fieldset>
            <p className="room-small">A preset with estimated dimensions.<br />Not a scan or a photograph of you.</p>
          </> : <><div className="room-measurements">{[['height_cm', 'Height'], ['chest_cm', sex === 'female' ? 'Bust' : 'Chest'], ['waist_cm', 'Waist'], ['hip_cm', 'Hips']].map(([key, label]) => <label key={key}>{label}<span><input type="number" aria-label={`${label} in centimeters`} min={key === 'height_cm' ? 101 : key === 'waist_cm' ? 41 : 51} max={key === 'height_cm' ? 229 : 199} value={key === 'height_cm' ? height : girths[key as keyof typeof girths]} onChange={event => changeBody(() => key === 'height_cm' ? setHeight(Number(event.target.value)) : setGirths(previous => ({ ...previous, [key]: Number(event.target.value) })))} /><small>cm</small></span></label>)}</div><p className="room-small">Your inputs are compared with the chart. A photo preview needs a preset.</p></>}
          <details className="room-preferences"><summary>Preferences <span>{fitPref} fit</span></summary><label className="room-field">Preferred fit<select value={fitPref} onChange={event => changeBody(() => setFitPref(event.target.value as typeof fitPref))}><option value="snug">Snug</option><option value="regular">Regular</option><option value="relaxed">Relaxed</option></select></label><label className="room-field">Dressing preference<select value={closure} onChange={event => changeBody(() => setClosure(event.target.value as typeof closure))}><option value="">No preference</option><option value="front_open">Front opening</option><option value="pullover">Pullover</option></select></label></details>
          </details>
          <div className="room-body-link"><span className="room-overline">THE STARTING POINT</span><p>A three-dimensional body built from your selected preset.</p><button onClick={() => changeLook('3d')} disabled={mode !== 'preset'}>Explore your body model <span aria-hidden="true">↗</span></button></div>
        </aside>

        <section className="room-stage" aria-label="Garment preview">
          <div className="room-stage-heading"><div><span className="room-overline">IN THE FITTING ROOM</span><h2>{item?.name || 'Loading your garment…'}<span>Size {garmentSize}</span></h2></div><span className="room-stage-index">{look === 'real' ? 'STYLED VIEW' : '3D BODY MODEL'}</span></div>
          <div className="room-stage-image">
            {visualBody ? look === 'real'
              ? <RealisticView key={JSON.stringify({ visualBody, garmentId, garmentSize, preferences, view, pair })} body={visualBody} garmentId={garmentId} size={garmentSize} preferences={preferences} view={view} hasPhoto={!!item?.photo} pair={pair} />
              : bodyScene?.key === visualKey ? <Viewer bodyUrl={bodyScene.url} combined view={view} rotating={rotating} showBody skinTone="#a8a69f" />
                : <div className="room-stage-message" role="status">{bodyError || 'Preparing your body model…'}{bodyError && <button onClick={() => setRefresh(value => value + 1)}>Try again</button>}</div>
              : <div className="room-stage-message" role="status">Finding the closest body to your measurements…</div>}
            <div className="room-angle-controls" aria-label="Preview angle">{((look === '3d' ? ['front', 'quarter', 'side', 'back'] : ['front', 'side', 'back']) as View[]).map(angle => <button key={angle} aria-pressed={view === angle} onClick={() => { setView(angle); setRotating(false); }}>{angle === 'quarter' ? '¾' : angle}</button>)}</div>
            {look === '3d' && <button className="room-rotate" aria-pressed={rotating} onClick={() => setRotating(!rotating)}>{rotating ? 'Pause rotation' : 'Rotate model'}</button>}
          </div>
          <div className="room-stage-foot"><p>{mode === 'measured' && nearest ? `Shown on the closest prepared body: ${nearest.shape_name || nearest.shape}, ${nearest.usual_size}, ${nearest.height_cm} cm (bust ${nearest.preset_cm?.chest ?? '?'}, waist ${nearest.preset_cm?.waist ?? '?'}, hip ${nearest.preset_cm?.hip ?? '?'} cm; yours ${girths.chest_cm}/${girths.waist_cm}/${girths.hip_cm} cm). The fit uses your exact measurements. ` : ''}{look === 'real' ? 'Styled on your measured body with Meta Muse Image. Use the chart comparison to assess size.' : 'Estimated body geometry. Garments are not shown in 3D.'}</p><button disabled={!visualBody} onClick={() => changeLook(look === 'real' ? '3d' : 'real')}>{look === 'real' ? '3D body model ↗' : 'Back to styled view ↗'}</button></div>

          <section className="room-browse" aria-label="Browse garments"><div className="room-browse-heading"><h3>Find your next piece</h3><div><button aria-label="Previous garments" onClick={() => rail.current?.scrollBy({ left: -240, behavior: 'smooth' })}>←</button><button aria-label="Next garments" onClick={() => rail.current?.scrollBy({ left: 240, behavior: 'smooth' })}>→</button></div></div>
            <div className="room-categories" aria-label="Garment categories">{categories.map(([id, name]) => <button key={id} aria-pressed={category === id} onClick={() => setCategory(id)}>{name}</button>)}</div>
            <div className="room-product-rail" ref={rail}>{browseItems.map(product => <button className="room-product" key={product.garment_id} aria-pressed={garmentId === product.garment_id} aria-label={`Try ${product.name}`} onClick={() => selectGarment(product)}>{renderPhoto(product, 110, 132)}<span>{product.name}</span>{garmentId === product.garment_id && <small>Viewing</small>}</button>)}{!browseItems.length && <p className="room-small">{catalogue.length ? 'No pieces in this category for these proportions. Try another category.' : error ? 'The catalogue is unavailable. Use Try again in the fit panel.' : 'Loading the catalogue…'}</p>}</div>
          </section>
        </section>

        <aside className="room-fit" aria-label="Your fit report" aria-busy={pending}>
          <div className="room-section-title"><span>02</span><h2>The fit, explained</h2></div>
          <p className="room-overline">{item?.category === 'outfit' ? 'A COMPLETE SET' : 'YOUR SELECTED PIECE'}</p>
          <h2 className="room-product-title">{item?.name || 'Your garment'}</h2><p className="room-fabric">{item?.fabric}</p>
          <div className={`room-verdict ${pending ? 'unknown' : summary.verdict}`} role="status"><span className="room-verdict-mark" aria-hidden="true" /><div><strong>{pending ? 'Checking the size chart…' : summary.text}</strong><p>{pending ? 'Comparing your selected dimensions.' : `Size ${garmentSize} · ${fitPref} fit preference`}</p></div></div>
          {(error || selectedError) && <p role="alert" className="room-error">{error || selectedError}<button onClick={() => { setError(''); setRefresh(value => value + 1); }}>Try again</button></p>}
          <fieldset className="room-size-options"><legend>Choose a garment size <span>Size {garmentSize} selected</span></legend><div>{allSizes.map(size => {
            const result = results?.find(value => value.size === size && value.garment_id === garmentId);
            const fit = fitSummary(result?.report, sex);
            return <button key={size} aria-label={`Garment size ${size}`} aria-pressed={garmentSize === size} className={pending ? 'unknown' : fit.verdict} title={pending ? 'Checking fit' : fit.text} onClick={() => selectSize(size)}>{size}</button>;
          })}</div></fieldset>
          <p className="room-size-key"><span className="tight">Tight</span><span className="borderline">Borderline</span><span className="ok">Within range</span><span className="loose">Roomy</span></p>
          <div className="room-regions" aria-label={`How size ${garmentSize} compares`}>{['chest', 'waist', 'hip'].map(region => {
            const value = report?.regions[region];
            return <div key={region}><span>{regionLabel(region, sex)}</span><div><strong className={value?.verdict}>{pending ? 'Checking…' : dimensionLabel(value?.ease_cm ?? null)}</strong><small>{!pending && value ? value.verdict === 'borderline' ? 'Could go either way' : value.verdict === 'unknown' ? 'A measurement is missing' : value.verdict === 'ok' ? 'Within the selected range' : value.verdict === 'loose' ? 'Roomier than the selected range' : 'Below the selected range' : 'From the fit engine'}</small>{!pending && !!value?.uncertainty_cm && <small>±{value.uncertainty_cm} cm estimate</small>}{!pending && !!value?.stretch_cm && <small>{value.stretch_cm} cm modeled give</small>}</div></div>;
          })}</div>
          <button className="room-primary" onClick={() => setDialog('compare')} disabled={!results || comparisonSizes.length < 2}>Compare {comparisonSizes.join(', ')} <span aria-hidden="true">↗</span></button>
          <button className="room-secondary" onClick={() => setDialog('nisha')}>Ask Nisha about this size <span aria-hidden="true">↗</span></button>
          {report && <details className="room-evidence"><summary>How we know {report.unknowns.length > 0 && <span>{report.unknowns.length} not assessed</span>}</summary>
            <p>Room is the difference between garment and body dimensions. It does not establish comfort.</p>
            {report.warnings.map((warning, index) => <p key={index} className="room-source-warning">{warning}</p>)}
            <p>{report.provenance.garment_source}</p><p>Body: {report.provenance.body_source}</p>
            <ul>{report.advice_facts.map((fact, index) => <li key={index}>{fact}</li>)}</ul>
            {report.unknowns.length > 0 && <><p><strong>What we can’t assess</strong></p><ul>{report.unknowns.map((unknown, index) => <li key={index}>{unknown}</li>)}</ul></>}
          </details>}
          {pairCategory && <details className="room-evidence"><summary>Style it with another piece</summary><label className="room-field">Pair with<select value={pairItem ? pairId : ''} onChange={event => { setPairId(event.target.value); setView('front'); }}><option value="">{pairCategory === 'bottom' ? 'Plain trousers — styling only' : 'No additional piece'}</option>{pairOptions.map(value => <option key={value.garment_id} value={value.garment_id}>{value.name}</option>)}</select></label><p>The companion piece is styling context. The report above assesses the selected garment.</p></details>}
        </aside>
      </div>

      <details className="room-tools"><summary>Garment photo & segmentation <span>Explore how SAM isolates garment pixels</span></summary><div className="room-tools-grid"><GarmentPhotoCard key={garmentId} name={item?.name || 'Your garment'} fabric={item?.fabric} photo={photo} onChange={updatePhoto} /><SamGarment key={`sam-${garmentId}`} garment={(item?.name || 'garment').replace(/\s*\(.*\)\s*$/, '').toLowerCase()} photo={photo} onPhotoChange={updatePhoto} /></div></details>
      <footer className="room-footer"><Link href="/" className="room-brand">stylewise</Link><p>A visual guide, a size-chart comparison, and room for your judgement.</p><span>FIT LAB / RESEARCH PROTOTYPE</span></footer>
    </main>

    <FittingDialog open={dialog === 'nisha'} title="Ask Nisha" side onClose={() => setDialog(null)}><p className="room-dialog-context">{item?.name} · Size {garmentSize}</p><NishaChat context={{ body, garment_id: garmentId, garment_size: garmentSize, preferences }} /></FittingDialog>
    <FittingDialog open={dialog === 'compare'} title="Compare sizes on your shape" onClose={() => setDialog(null)}><p className="room-dialog-context">{item?.name} · {mode === 'preset' ? `${shapeInfo[1]}, usual size ${usualSize}, ${height} cm` : 'Your entered measurements'}</p><div className="room-compare-grid">{comparisonSizes.map(size => {
      const value = results?.find(result => result.size === size && result.garment_id === garmentId);
      const fit = fitSummary(value?.report, sex);
      // the body area that decides this size, for "zoom to the waist": the first tight, close or roomy area
      const issue = (['tight', 'borderline', 'loose'] as const).map(v => ['chest', 'waist', 'hip'].find(r => value?.report?.regions[r]?.verdict === v) && { verdict: v, region: ['chest', 'waist', 'hip'].find(r => value?.report?.regions[r]?.verdict === v)! }).find(Boolean) || null;
      const zoomed = issue && compareZoom[size];
      const at = issue ? REGION_HEIGHT[issue.region] : 0.4;
      return <article className={`room-compare-card ${fit.verdict}`} key={size}><div className="room-compare-image">{dialog === 'compare' && visualBody ? <>
        <div className="room-compare-zoom" style={zoomed ? { transform: 'scale(2.1)', transformOrigin: `50% ${at * 100}%` } : undefined}>
          <RealisticView key={JSON.stringify({ visualBody, garmentId, size, preferences, pair })} body={visualBody} garmentId={garmentId} size={size} preferences={preferences} view="front" hasPhoto={!!item?.photo} pair={pair} />
          {issue && zoomed && <div className={`room-issue-band ${issue.verdict}`} style={{ top: `${at * 100}%` }} aria-hidden="true" />}
        </div>
        {issue && zoomed && <p className={`room-issue-label ${issue.verdict}`}>{fit.text} · {dimensionLabel(value?.report?.regions[issue.region]?.ease_cm ?? null)}</p>}
        {issue && <button className="room-issue-zoom" onClick={() => setCompareZoom(prev => ({ ...prev, [size]: !prev[size] }))}>{zoomed ? 'Zoom out' : `Zoom to the ${regionLabel(issue.region, sex).toLowerCase()}`}</button>}
      </> : <p>Numeric comparison</p>}</div><div className="room-compare-copy"><span>SIZE {size}</span><h3>{fit.text}</h3><dl>{['chest', 'waist', 'hip'].map(region => <div key={region}><dt>{regionLabel(region, sex)}</dt><dd>{dimensionLabel(value?.report?.regions[region]?.ease_cm ?? null)}</dd></div>)}</dl>{value?.report?.warnings[0] && <p className="room-source-warning">{value.report.warnings[0]}</p>}<button onClick={() => { selectSize(size); setDialog(null); }}>View size {size} <span aria-hidden="true">↗</span></button></div></article>;
    })}</div><p className="room-comparison-note">Same preset and fit preference for each size. These are styled views generated with Meta Muse Image, not cloth simulations; body appearance may vary. Use the numeric report to compare fit.</p></FittingDialog>
  </div>;
}
