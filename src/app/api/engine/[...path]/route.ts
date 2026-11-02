const allowed = new Map([
  ['GET:health', '/health'], ['GET:catalogue', '/catalogue'],
  ['POST:fit/outfit', '/fit/outfit'], ['POST:fit/evaluate', '/fit/evaluate'],
  ['POST:nisha/chat', '/nisha/chat'], ['POST:viewer/scene', '/viewer/scene'],
]);
async function proxy(request: Request, context: { params: Promise<{path: string[]}> }) {
  const { path } = await context.params;
  const endpoint = allowed.get(`${request.method}:${path.join('/')}`);
  if (!endpoint) return Response.json({error:'Unknown engine endpoint'}, {status:404});
  try {
    const body = request.method === 'POST' ? await request.text() : undefined;
    if (body && body.length > 100_000) return Response.json({error:'Request too large'}, {status:413});
    const response = await fetch(`${process.env.FIT_API_URL || 'http://127.0.0.1:8000'}${endpoint}`, {
      method:request.method, body, headers:{'Content-Type':'application/json'}, signal:AbortSignal.timeout(120_000), cache:'no-store',
    });
    return new Response(response.body, {status:response.status, headers:{'Content-Type':response.headers.get('Content-Type') || 'application/json', 'Cache-Control':'no-store'}});
  } catch {
    return Response.json({error:'Fit engine unavailable. Start the Python API on port 8000.'},{status:503});
  }
}
export const GET = proxy;
export const POST = proxy;
