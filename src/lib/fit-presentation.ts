import type { EngineReport } from './engine';

export type Verdict = EngineReport['regions'][string]['verdict'];
export const regionLabel = (region: string, sex: string) =>
  region === 'chest' ? (sex === 'female' ? 'Bust' : 'Chest') : region === 'hip' ? 'Hips' : 'Waist';

// Presentation of engine verdicts only. This does not rank sizes or compute fit.
export function fitSummary(report: EngineReport | null | undefined, sex: string): { verdict: Verdict; text: string } {
  if (!report) return { verdict: 'unknown', text: 'Fit not available yet' };
  const entries = Object.entries(report.regions);
  for (const verdict of ['tight', 'borderline', 'loose', 'unknown'] as Verdict[]) {
    const match = entries.find(([, value]) => value.verdict === verdict);
    if (!match) continue;
    const name = regionLabel(match[0], sex).toLowerCase();
    return { verdict, text: verdict === 'tight' ? `Tight at the ${name}`
      : verdict === 'borderline' ? `Close at the ${name} — could go either way`
      : verdict === 'loose' ? `Roomy at the ${name}` : `Not enough information at the ${name}` };
  }
  return { verdict: 'ok', text: 'Within your selected fit range' };
}

export function dimensionLabel(value: number | null): string {
  if (value === null) return 'Not assessed';
  if (value < 0) return `${Math.abs(value)} cm less than body`;
  return value === 0 ? 'Matches body dimension' : `+${value} cm room`;
}
