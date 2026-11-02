'use client';
import { useRef, useState } from 'react';
import Image from 'next/image';
import { readGarmentPhoto, type GarmentPhoto } from '@/lib/garment-photo';
export default function GarmentPhotoCard({name,fabric,photo,onChange}:{name:string;fabric?:string;photo:GarmentPhoto|null;onChange:(photo:GarmentPhoto|null)=>void}) {
  const input=useRef<HTMLInputElement>(null);
  const [error,setError]=useState('');
  return <div className="selected-garment-card"><div className="selected-garment-photo">{photo?<Image src={photo.data} alt={`${name} product photo`} fill unoptimized sizes="90px"/>:<svg viewBox="0 0 80 80" fill="none" aria-hidden="true"><path d="M32 22a8 8 0 1 1 12 7v8l26 20a3 3 0 0 1-2 5H12a3 3 0 0 1-2-5l30-21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>}</div><div className="selected-garment-copy"><span className="tiny-label">SELECTED GARMENT</span><h3>{name}</h3><p>{fabric}</p><button className="photo-action" onClick={()=>input.current?.click()}>{photo?'Replace photo':'Add product photo'}</button>{photo&&<button className="photo-action" onClick={()=>{setError('');onChange(null);}}>Remove</button>}</div><input ref={input} type="file" hidden accept="image/png,image/jpeg,image/webp" aria-label="Selected garment photo" onChange={async event=>{const file=event.target.files?.[0];event.target.value='';if(!file)return;try{setError('');onChange(await readGarmentPhoto(file));}catch(cause){setError(cause instanceof Error?cause.message:'Could not read photo.');}}}/>{error&&<p role="alert" className="photo-error">{error}</p>}<p className="photo-caption">{photo?'Photo attached to this garment · also available in SAM':'Attach this garment’s product photo to see it here.'}</p></div>;
}
