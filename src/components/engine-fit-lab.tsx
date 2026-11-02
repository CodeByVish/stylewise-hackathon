'use client';
import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { assetUrl, engine, type BodyInput, type CatalogueItem, type PieceResult } from '@/lib/engine';
import type { View } from './fit-viewer';
import NishaChat from './nisha-chat';
import SamGarment from './sam-garment';
import GarmentPhotoCard from './garment-photo-card';
import type { GarmentPhoto } from '@/lib/garment-photo';
const Viewer=dynamic(()=>import('./fit-viewer'),{ssr:false});
const shapes=[['hourglass','The Balance'],['triangle','The Anchor'],['inverted_triangle','The Summit'],['rectangle','The Column'],['oval','The Orbit']];
const sizes=['XS','S','M','L','XL','2XL','3XL'];
function Silhouette({shape}:{shape:string}) {
  const waist=shape==='hourglass'?12:shape==='oval'?24:17;
  const shoulder=shape==='inverted_triangle'?27:shape==='triangle'?17:23;
  const hip=shape==='triangle'?28:shape==='inverted_triangle'?17:23;
  return <svg viewBox="0 0 80 100" aria-hidden="true"><circle cx="40" cy="12" r="8" fill="currentColor"/><path d={`M${40-shoulder} 28 Q${40-waist} 46 ${40-waist} 54 Q${40-hip} 70 ${40-hip} 78 L${40+hip} 78 Q${40+waist} 70 ${40+waist} 54 Q${40+waist} 46 ${40+shoulder} 28Z`} fill="currentColor"/><path d="M30 76v17m20-17v17" stroke="currentColor" strokeWidth="10" strokeLinecap="round"/></svg>;
}
export default function EngineFitLab(){
  const [photos,setPhotos]=useState<Record<string,GarmentPhoto|null>>({});
  const [sceneLoading,setSceneLoading]=useState(true);
  const [catalogue,setCatalogue]=useState<CatalogueItem[]>([]);
  const [mode,setMode]=useState<'preset'|'measured'>('preset');
  const [sex,setSex]=useState<'female'|'male'>('female');
  const [shape,setShape]=useState('rectangle');
  const [usualSize,setUsualSize]=useState('M');
  const [height,setHeight]=useState(165);
  const [girths,setGirths]=useState({chest_cm:90,waist_cm:74,hip_cm:96});
  const [garmentId,setGarmentId]=useState('green-kurta');
  const [garmentSize,setGarmentSize]=useState('M');
  const [fitPref,setFitPref]=useState<'snug'|'regular'|'relaxed'>('regular');
  const [closure,setClosure]=useState<''|'front_open'|'pullover'>('');
  const [results,setResults]=useState<PieceResult[]|null>(null);
  const [pending,setPending]=useState(true);
  const [error,setError]=useState('');
  const [scene,setScene]=useState('');
  const [sceneError,setSceneError]=useState('');
  const [view,setView]=useState<View>('front');
  const [rotating,setRotating]=useState(false);
  const [showBody,setShowBody]=useState(true);
  const [refresh,setRefresh]=useState(0);
  const item=catalogue.find(item=>item.garment_id===garmentId);
  const body:BodyInput=mode==='preset'?{source:'preset',height_cm:height,preset:{shape,usual_size:usualSize,sex}}:{source:'measured',height_cm:height,...girths};
  const preferences={fit_pref:fitPref,...(closure?{closure}:{})};
  const payload={body,items:[{garment_id:garmentId,size:garmentSize}],preferences};
  const payloadKey=JSON.stringify(payload);
  const comparisonSizes=(item?.sizes||['S','M']).filter(size=>size==='S'||size==='M');
  const evaluationKey=JSON.stringify({...payload,items:[...new Set([garmentSize,...comparisonSizes])].map(size=>({garment_id:garmentId,size}))});
  const photo=photos[garmentId]||null;
  const updatePhoto=(next:GarmentPhoto|null)=>setPhotos(previous=>({...previous,[garmentId]:next}));
  useEffect(()=>{
    const controller=new AbortController();
    engine<CatalogueItem[]>('catalogue',undefined,controller.signal).then(setCatalogue).catch(cause=>{if(!controller.signal.aborted)setError(cause.message);});
    return()=>controller.abort();
  },[refresh]);
  useEffect(()=>{
    const controller=new AbortController();
    let url='';
    const timer=setTimeout(async()=>{
      setPending(true);setSceneLoading(mode==='preset');setResults(null);setError('');setScene('');setSceneError('');
      try{
        const request=JSON.parse(evaluationKey);
        const next=await engine<PieceResult[]>('fit/outfit',request,controller.signal);
        if(controller.signal.aborted)return;
        setResults(next);setPending(false);
        if(request.body.source==='preset'){
          try{
            const response=await fetch('/api/engine/viewer/scene',{method:'POST',headers:{'Content-Type':'application/json'},body:payloadKey,signal:controller.signal});
            if(!response.ok)throw new Error('The fit-shell scene could not be generated. Showing the preset body only.');
            const blob=await response.blob();
            if(controller.signal.aborted)return;
            url=URL.createObjectURL(blob);setScene(url);
          }catch(cause){if(!controller.signal.aborted)setSceneError(cause instanceof Error?cause.message:'Scene unavailable.');}
          finally{if(!controller.signal.aborted)setSceneLoading(false);}
        }
      }catch(cause){if(!controller.signal.aborted){setError(cause instanceof Error?cause.message:'Fit request failed.');setPending(false);setSceneLoading(false);}}
    },250);
    return()=>{clearTimeout(timer);controller.abort();if(url)URL.revokeObjectURL(url);};
  },[payloadKey,evaluationKey,mode,refresh]);
  // Mark prior results stale immediately, before the debounced request begins.
  function change(action:()=>void){setResults(null);setScene('');setPending(true);setSceneLoading(true);setSceneError('');action();}
  const selectedResult=results?.find(result=>result.size===garmentSize&&result.garment_id===garmentId);
  const report=selectedResult?.report;
  const presetId=`${sex}_${shape}_${usualSize}_${height}`;
  return <div className="app-shell"><aside className="sidebar"><Link href="/" className="brand">s<span>✳</span></Link><div className="nav-icons"><a href="#workspace" className="nav-active" aria-label="Fit Lab">◈</a><a href="#nisha" aria-label="Nisha">✳</a><a href="#garment-mask" aria-label="Garment segmentation">♧</a></div><div className="avatar">SW</div></aside><div className="main-shell"><header className="topbar"><Link href="/" className="wordmark">stylewise<span> / fit lab</span></Link><span className="prototype"><span/> MHR presets · engine v0.4.0</span></header><main id="workspace"><div className="page-heading"><div><div className="eyebrow">YOUR WARDROBE, BETTER UNDERSTOOD</div><h1>A little more certainty.<br/><em>Before you buy.</em></h1><p>Choose your silhouette. Compare a size. Explore every angle.</p></div><Link href="/fixtures-demo" className="text-button fixture-link">Open isolated fixture demo</Link></div><div className="workspace-grid">
  <section className="card input-panel"><div className="panel-heading"><span className="step">01</span><h2>Your starting point</h2></div><div className="mode-switch">{(['preset','measured'] as const).map(value=><button key={value} aria-pressed={mode===value} onClick={()=>change(()=>{setMode(value);if(value==='measured')setHeight(168);else setHeight(sex==='female'?165:175);})}>{value==='preset'?'Pick a silhouette':'Use measurements'}</button>)}</div>
  {mode==='preset'?<><label className="preference-label">Body proportions<select value={sex} onChange={e=>change(()=>{setSex(e.target.value as typeof sex);setHeight(e.target.value==='female'?165:175);})}><option value="female">Female proportions</option><option value="male">Male proportions</option></select></label><div className="shape-grid">{shapes.map(([id,name])=><button key={id} className={shape===id?'selected':''} aria-pressed={shape===id} onClick={()=>change(()=>setShape(id))}><Silhouette shape={id}/><span>{name}</span></button>)}</div><label className="preference-label">Usual size<select value={usualSize} onChange={e=>change(()=>setUsualSize(e.target.value))}>{sizes.map(size=><option key={size}>{size}</option>)}</select></label><label className="preference-label">Preset height<select value={height} onChange={e=>change(()=>setHeight(Number(e.target.value)))}>{(sex==='female'?[155,165,175]:[165,175,185]).map(cm=><option value={cm} key={cm}>{cm} cm</option>)}</select></label><p className="field-note">Preset proportions are estimates with a reported range, not a reconstruction of your body.</p></>:<div className="measurement-grid">{[['height_cm','Height'],['chest_cm','Chest'],['waist_cm','Waist'],['hip_cm','Hip']].map(([key,label])=><label key={key}>{label}<div className="number-field"><input type="number" aria-label={`${label} in centimeters`} value={key==='height_cm'?height:girths[key as keyof typeof girths]} min={key==='height_cm'?101:key==='waist_cm'?41:51} max={key==='height_cm'?229:199} step="0.5" onChange={e=>change(()=>key==='height_cm'?setHeight(Number(e.target.value)):setGirths(prev=>({...prev,[key]:Number(e.target.value)})))}/><span>cm</span></div></label>)}</div>}
  <div className="divider"/><div className="section-label">THE GARMENT <span>SOURCED CATALOGUE</span></div><label className="preference-label">Garment<select value={garmentId} onChange={e=>change(()=>{const next=catalogue.find(item=>item.garment_id===e.target.value);setGarmentId(e.target.value);if(next&&!next.sizes.includes(garmentSize))setGarmentSize(next.sizes[0]);})}>{catalogue.filter(item=>item.fittable).map(item=><option key={item.garment_id} value={item.garment_id}>{item.name}</option>)}</select></label><GarmentPhotoCard key={garmentId} name={item?.name||'Loading garment…'} fabric={item?.fabric} photo={photo} onChange={updatePhoto}/><div className="size-label">Garment size</div><div className="garment-sizes">{(item?.sizes||['S','M']).map(size=><button key={size} aria-pressed={garmentSize===size} onClick={()=>change(()=>setGarmentSize(size))}>{size}</button>)}</div><label className="preference-label">Preferred fit<select value={fitPref} onChange={e=>change(()=>setFitPref(e.target.value as typeof fitPref))}><option value="snug">Snug</option><option value="regular">Regular</option><option value="relaxed">Relaxed</option></select></label><label className="preference-label">Dressing preference<select value={closure} onChange={e=>change(()=>setClosure(e.target.value as typeof closure))}><option value="">No preference</option><option value="front_open">Front opening</option><option value="pullover">Pullover</option></select></label>
  </section>
  <section className="viewer-panel" aria-label="3D fitting room" aria-busy={mode==='preset'&&sceneLoading}><div className="viewer-top"><div><span className="tiny-label">THE FITTING ROOM</span><h2>{mode==='preset'?shapes.find(([id])=>id===shape)?.[1]:'Measured comparison'}</h2></div><span className="scene-badge">3D / {garmentSize}</span></div><div className="viewer-scene"><div className="scene-rings"/>{mode==='preset'?<Viewer bodyUrl={scene||assetUrl(`fixtures/presets/${presetId}.glb`)} combined={!!scene} view={view} rotating={rotating} showBody={showBody}/>:<div className="viewer-status">The engine evaluates your measurements. Choose a silhouette to explore the prepared MHR body and fit-shell scene.</div>}<div className="scene-progress" role="status" aria-live="polite">{mode==='preset'&&sceneLoading&&<><span className="loading-dot"/>{pending?'Checking sizes…':'Preparing garment preview…'}</>}</div><div className="viewer-caption">{scene?'Approximate fit shell · no cloth drape':mode==='preset'?(sceneError?'Body only · garment preview unavailable':error?'Body only · fit engine unavailable':'MHR preset body · preparing garment'):'Numeric fit report'}</div></div><div className="viewer-toolbar"><div className="view-switch">{(['front','side','back'] as View[]).map(value=><button key={value} aria-pressed={view===value} className={view===value?'active':''} onClick={()=>{setView(value);setRotating(false);}}>{value}</button>)}</div><button className="rotate-button" aria-pressed={rotating} onClick={()=>setRotating(!rotating)}>{rotating?'Pause':'Rotate'}</button></div><div className="viewer-bottom"><span>Drag to orbit · scroll to zoom</span><label><input type="checkbox" checked={showBody} onChange={e=>setShowBody(e.target.checked)}/> Show body</label></div></section>
  <section className="card insights-panel" aria-label="Engine fit report"><div className="panel-heading"><span className="step">02</span><h2>Beyond the mirror</h2></div><div className="evidence-tag">ENGINE REPORT · v0.4.0</div><h3 className="insight-title">Room to make a clearer choice.</h3>{pending&&<p role="status">Comparing your selection…</p>}{error&&<div role="alert" className="engine-error">{error}<button className="text-button" onClick={()=>setRefresh(value=>value+1)}>Retry connection</button></div>}{selectedResult?.error&&<p role="alert" className="engine-error">{selectedResult.error}</p>}{comparisonSizes.length>1&&<section className="size-comparison" aria-label="Size comparison"><div className="comparison-heading"><h3>S / M at a glance</h3><span>Ease in cm</span></div>{pending?<div className="comparison-skeleton" role="status">Loading size comparison…</div>:results?<><table><caption className="sr-only">Engine size comparison. Select a size to show it in the viewer.</caption><thead><tr><th scope="col">Region</th>{comparisonSizes.map(size=><th scope="col" key={size}><button aria-pressed={garmentSize===size} onClick={()=>change(()=>setGarmentSize(size))}>{size}{garmentSize===size&&<small>Viewing</small>}</button></th>)}</tr></thead><tbody>{['chest','waist','hip'].map(region=><tr key={region}><th scope="row">{region}</th>{comparisonSizes.map(size=>{const result=results.find(result=>result.size===size&&result.garment_id===garmentId);const value=result?.report?.regions[region];return <td key={size} className={garmentSize===size?'comparison-selected':''}><strong>{value?.ease_cm==null?'—':`${value.ease_cm>0?'+':''}${value.ease_cm}`}</strong><span className={`comparison-verdict ${value?.verdict||'unknown'}`}>{value?.verdict==='borderline'?'Borderline':value?.verdict||'Unavailable'}</span>{!!value?.uncertainty_cm&&<small>±{value.uncertainty_cm}</small>}</td>;})}</tr>)}</tbody></table><p>Borderline could go either way. Ease does not establish comfort.</p>{comparisonSizes.map(size=>{const result=results.find(result=>result.size===size);return result?.error?<p role="note" className="comparison-warning" key={size}>{size}: {result.error}</p>:result?.report?.warnings.map((warning,index)=><p className="comparison-warning" key={`${size}-${index}`}>{size}: {warning}</p>);})}</>:null}</section>}{report&&<><div className="engine-regions">{Object.entries(report.regions).map(([name,region])=><div className={`ease ${region.verdict}`} key={name}><div><span>{name} ease</span><span>{region.verdict==='borderline'?'Could go either way':region.verdict}</span></div><strong>{region.ease_cm===null?'—':`${region.ease_cm>0?'+':''}${region.ease_cm}`}<small>cm</small></strong><p>{region.uncertainty_cm>0?`±${region.uncertainty_cm} cm uncertainty`:'User-provided measurements'}{region.stretch_cm>0&&` · ${region.stretch_cm} cm modeled give`}</p></div>)}</div><div className="engine-facts">{report.advice_facts.map((fact,i)=><p key={i}>{fact}</p>)}</div>{report.warnings.map((warning,i)=><p role="note" key={i} className="engine-warning">{warning}</p>)}<details className="evidence-details" open><summary>What we don’t know yet</summary><ul>{report.unknowns.map((unknown,i)=><li key={i}>{unknown}</li>)}</ul></details><details className="evidence-details"><summary>Measurement sources</summary><p>{report.provenance.garment_source}</p><p>Body: {report.provenance.body_source} · {report.provenance.body_model}</p></details></>}{sceneError&&<p role="status" className="engine-error">{sceneError}</p>}</section>
  </div><div className="bottom-note"><p>Ease and fit-shell geometry are approximate evidence. They do not simulate cloth or establish comfort.</p></div><div className="integration-grid"><div id="nisha"><NishaChat context={{body,garment_id:garmentId,garment_size:garmentSize,preferences}}/></div><SamGarment key={garmentId} photo={photo} onPhotoChange={updatePhoto}/></div></main><footer><span>stylewise</span><p>Less guesswork. More you.</p><span>META HACKATHON · 2026</span></footer></div></div>;
}
