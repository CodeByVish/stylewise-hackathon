// Deployment check: which settings this running deployment can see (true/false only, never the values).
export const dynamic = 'force-dynamic';
export function GET() {
  return Response.json({
    sam_key: Boolean(process.env.MODEL_API_KEY || process.env.META_API_KEY),
    fit_api_url: process.env.FIT_API_URL || null,
    commit: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || 'local',
    environment: process.env.VERCEL_ENV || 'local',
  }, { headers: { 'Cache-Control': 'no-store' } });
}
