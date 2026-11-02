import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
export async function GET(_request: Request, { params }: {params:Promise<{path:string[]}>}) {
  const {path} = await params;
  if (path.some(part => !/^[a-zA-Z0-9_.-]+$/.test(part) || part.includes('..'))) return new Response(null,{status:400});
  const root = resolve(process.cwd(),'fixtures');
  const file = resolve(root,...path);
  if (!file.startsWith(root + sep) || !/\.(glb|json)$/.test(file)) return new Response(null,{status:404});
  try {
    const bytes = await readFile(file);
    return new Response(bytes, {headers:{'Content-Type':file.endsWith('.glb')?'model/gltf-binary':'application/json','Cache-Control':'no-store'}});
  } catch { return new Response(null,{status:404}); }
}
