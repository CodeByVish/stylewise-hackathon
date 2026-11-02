'use client';
import { useState } from 'react';
import Image from 'next/image';
import { readGarmentPhoto, type GarmentPhoto } from '@/lib/garment-photo';
type Result={masks:{id:string;bounds:{left:number;top:number;right:number;bottom:number};width:number;height:number;path:string;confidence?:number}[];provenance:{model:string;source:string;prompt:string;timestamp:string}};
export default function SamGarment({photo,onPhotoChange}:{photo:GarmentPhoto|null;onPhotoChange:(photo:GarmentPhoto|null)=>void}){
  const image=photo?.data||'';const source=photo?.source||'';const [dimensions,setDimensions]=useState({width:1,height:1});
  const [prompt,setPrompt]=useState('kurta');const [busy,setBusy]=useState(false);
  const [storedResult,setStoredResult]=useState<{input:string;data:Result}|null>(null);
  const inputKey=JSON.stringify([image,source,prompt]);
  const result=storedResult?.input===inputKey?storedResult.data:null;const [error,setError]=useState('');
  async function segment(){
    setBusy(true);setError('');setStoredResult(null);
    try{
      const response=await fetch('/api/sam',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image,prompt,source})});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'SAM unavailable');setStoredResult({input:inputKey,data});
    }catch(cause){setError(cause instanceof Error?cause.message:'Could not segment photo.');}finally{setBusy(false);}
  }
  function save(){
    if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='stylewise-sam-mask.json';link.click();URL.revokeObjectURL(url);
  }
  return <section id="garment-mask" className="card sam-panel"><span className="eyebrow">GARMENT UNDERSTANDING</span><h2>Isolate the garment</h2><p className="field-note">SAM identifies garment pixels. Measurements always come from the garment’s size chart.</p><label className="preference-label">Product photo<input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={async event=>{const file=event.target.files?.[0];event.target.value='';if(!file)return;setError('');setStoredResult(null);try{onPhotoChange(await readGarmentPhoto(file));}catch(cause){setError(cause instanceof Error?cause.message:'Could not read photo.');}}}/></label><label className="preference-label">Photo source<input value={source} maxLength={500} disabled={busy||!photo} onChange={event=>{if(photo)onPhotoChange({...photo,source:event.target.value});setStoredResult(null);}} placeholder="Product URL or source label"/></label><label className="preference-label">What garment should SAM find?<input value={prompt} maxLength={100} disabled={busy} onChange={event=>{setPrompt(event.target.value);setStoredResult(null);}} placeholder="e.g. green kurta"/></label>{image&&<div className="sam-image"><Image src={image} alt="Selected garment product photo" unoptimized width={dimensions.width} height={dimensions.height} onLoad={event=>setDimensions({width:event.currentTarget.naturalWidth,height:event.currentTarget.naturalHeight})}/>{result&&<svg viewBox={`0 0 ${dimensions.width} ${dimensions.height}`} aria-label="SAM garment mask overlay">{result.masks.map(mask=><svg key={mask.id} x={mask.bounds.left} y={mask.bounds.top} width={mask.bounds.right-mask.bounds.left} height={mask.bounds.bottom-mask.bounds.top} viewBox={`0 0 ${mask.width} ${mask.height}`} preserveAspectRatio="none"><path d={mask.path} fill="#82b35c" fillOpacity=".6"/></svg>)}</svg>}</div>}<button className="primary-button" disabled={!image||!source.trim()||!prompt.trim()||busy} onClick={()=>void segment()}>{busy?'Segmenting…':'Segment with SAM'}</button><p className="field-note">This button sends the selected photo to Meta’s Model API.</p>{error&&<p role="alert" className="engine-error">{error}</p>}{result&&<><p role="status">{result.masks.length?`${result.masks.length} garment mask(s) found.`:'No matching garment found. Try a more specific noun phrase.'}</p><p className="field-note">{result.provenance.model} · {result.provenance.timestamp}</p><button className="text-button" onClick={save}>Download masks & provenance</button></>}</section>;
}
