export type Size = 'S' | 'M';
export type Measurements = { height: number; chest: number; waist: number; hip: number };
export type FitRequest = {
  version: '1.0';
  measurementsCm: Measurements;
  preference: 'none' | 'front-opening';
  garment: { id: string; size: Size; chestCm: number; waistCm: number; source: string; meshUrl: string };
};
export type FitReport = {
  version: '1.0';
  size: Size;
  measurementsCm: Measurements;
  bodyMeshUrl: string;
  garmentMeshUrl: string;
  easeCm: { chest: number; waist: number };
  warnings: string[];
  unknowns: string[];
  advice: string;
  provenance: string;
};
export const fixtureBody: Measurements = { height: 168, chest: 90, waist: 74, hip: 96 };
export type GarmentSpec = { chestCm: number; waistCm: number; meshUrl: string };
export type GarmentCatalog = { id: string; name: string; source: string; sizes: Record<Size, GarmentSpec> };
export const garments = {
  S: { chestCm: 86, waistCm: 72, meshUrl: '/fixtures/top-s.glb' },
  M: { chestCm: 98, waistCm: 84, meshUrl: '/fixtures/top-m.glb' },
} satisfies Record<Size, { chestCm: number; waistCm: number; meshUrl: string }>;
export const fixtureSource = 'Synthetic demonstration specifications from the team execution plan; not a retail size chart.';
export function createRequest(measurementsCm: Measurements, size: Size, preference: FitRequest['preference'], catalog: GarmentCatalog = fixtureCatalog): FitRequest {
  return { version: '1.0', measurementsCm, preference, garment: { id: catalog.id, size, ...catalog.sizes[size], source: catalog.source } };
}
export const fixtureCatalog: GarmentCatalog = { id: 'fixture-studio-top', name: 'The everyday top', source: fixtureSource, sizes: garments };
// This is arithmetic for the UI fixture, not P0's fit evaluation engine.
export function previewReport(request: FitRequest): FitReport {
  return { version: '1.0', size: request.garment.size, measurementsCm: { ...request.measurementsCm },
    bodyMeshUrl: '/fixtures/body.glb', garmentMeshUrl: request.garment.meshUrl,
    easeCm: { chest: request.garment.chestCm - request.measurementsCm.chest, waist: request.garment.waistCm - request.measurementsCm.waist },
    warnings: ['Static fixture mannequin: changing measurements updates arithmetic only, not the 3D body.', 'Static garment meshes do not simulate cloth or resolve body intersections.'],
    unknowns: ['Fabric stretch and drape', 'Physical comfort and mobility', ...(request.preference === 'front-opening' ? ['Front-opening construction is unverified'] : [])],
    advice: 'Compare the documented dimensions before deciding. These ease differences do not establish comfort or physical fit.', provenance: request.garment.source };
}
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
const stringList = (value: unknown): value is string[] => Array.isArray(value) && value.every(v => typeof v === 'string');
const safeMesh = (value: unknown): value is string => typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !value.includes('..') && /\.glb$/.test(value);
export function parseReport(value: unknown): FitReport {
  if (!isRecord(value) || value.version !== '1.0' || !['S', 'M'].includes(String(value.size)) || !isRecord(value.easeCm) || !isRecord(value.measurementsCm)
    || !['chest', 'waist'].every(k => typeof (value.easeCm as Record<string, unknown>)[k] === 'number' && Number.isFinite((value.easeCm as Record<string, unknown>)[k]))
    || !['height', 'chest', 'waist', 'hip'].every(k => typeof (value.measurementsCm as Record<string, unknown>)[k] === 'number' && Number.isFinite((value.measurementsCm as Record<string, unknown>)[k]) && Number((value.measurementsCm as Record<string, unknown>)[k]) > 0)
    || !safeMesh(value.bodyMeshUrl) || !safeMesh(value.garmentMeshUrl)
    || !stringList(value.warnings) || !stringList(value.unknowns) || typeof value.advice !== 'string' || typeof value.provenance !== 'string') {
    throw new Error('Invalid report. Use the version 1.0 contract and same-origin .glb mesh paths.');
  }
  return value as FitReport;
}

export function parseCatalog(value: unknown): GarmentCatalog {
  if (!isRecord(value) || typeof value.id !== 'string' || !value.id.trim() || typeof value.name !== 'string' || !value.name.trim() || typeof value.source !== 'string' || !value.source.trim() || !isRecord(value.sizes)) {
    throw new Error('Garment metadata needs an id, name, source, and S/M size specifications.');
  }
  for (const size of ['S', 'M']) {
    const spec = value.sizes[size];
    if (!isRecord(spec) || !safeMesh(spec.meshUrl) || !['chestCm', 'waistCm'].every(k => typeof spec[k] === 'number' && Number.isFinite(spec[k]) && spec[k] > 0 && spec[k] <= 300)) {
      throw new Error('Each size needs positive chestCm/waistCm values up to 300 cm and a same-origin .glb meshUrl.');
    }
  }
  return value as GarmentCatalog;
}
