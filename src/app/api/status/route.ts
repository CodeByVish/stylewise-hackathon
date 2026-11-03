// Deployment check: which settings this running deployment can see (true/false only, never the values).
// Route handlers are dynamic by default with cacheComponents, so this reads the live environment.
export function GET() {
  return Response.json({
    sam_key: Boolean(process.env.MODEL_API_KEY || process.env.META_API_KEY),
    fit_api_url: process.env.FIT_API_URL || null,
    commit: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || 'local',
    environment: process.env.VERCEL_ENV || 'local',
  }, { headers: { 'Cache-Control': 'no-store' } });
}
