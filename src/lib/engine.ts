import type { FitContext } from './nisha';
export type BodyInput = NonNullable<FitContext['body']>;
export type CatalogueItem = {garment_id:string;name:string;category:string;fabric:string;sizes:string[];fittable:boolean};
export type EngineReport = {
  contract_version:string;body_mesh_ref:string|null;garment_mesh_ref:string|null;
  regions:Record<string,{body_cm:number|null;garment_cm:number|null;ease_cm:number|null;uncertainty_cm:number;stretch_cm:number;verdict:'tight'|'ok'|'loose'|'borderline'|'unknown'}>;
  advice_facts:string[];warnings:string[];unknowns:string[];
  provenance:{body_source:string;body_preset_id:string|null;garment_source:string;body_model:string;engine_version:string};
};
export type PieceResult = {garment_id:string;size:string;report:EngineReport|null;error:string|null};
export async function engine<T>(path:string, body?:unknown, signal?:AbortSignal):Promise<T> {
  const response = await fetch(`/api/engine/${path}`,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal});
  const data=await response.json();
  if (!response.ok) throw new Error(typeof data.error==='string'?data.error:typeof data.detail==='string'?data.detail:`Fit engine returned HTTP ${response.status}. Check your inputs.`);
  return data;
}
export const assetUrl = (ref:string) => `/api/assets/${ref.replace(/^fixtures\//,'')}`;
