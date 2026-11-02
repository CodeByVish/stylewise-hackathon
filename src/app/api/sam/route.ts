import { parseImageStream, recordsOfKind, decodeMaskToSVGPath, type ResponsesEvent } from '@meta-sam/parser';

async function* events(body:ReadableStream<Uint8Array>):AsyncGenerator<ResponsesEvent> {
  const reader=body.getReader();const decoder=new TextDecoder();let pending='';
  try{
    while(true){
      const {value,done}=await reader.read();pending+=decoder.decode(value,{stream:!done});
      const lines=pending.split('\n');pending=lines.pop()||'';
      for(const line of lines){if(line.startsWith('data:')){const data=line.slice(5).trim();if(data&&data!=='[DONE]')yield JSON.parse(data);}}
      if(done){if(pending.startsWith('data:')){const data=pending.slice(5).trim();if(data&&data!=='[DONE]')yield JSON.parse(data);}break;}
    }
  }finally{reader.releaseLock();}
}
export async function POST(request:Request){
  const key=process.env.MODEL_API_KEY||process.env.META_API_KEY;
  if(!key)return Response.json({error:'Save MODEL_API_KEY in .env.local and restart Next.js to enable SAM.'},{status:503});
  try{
    if(Number(request.headers.get('Content-Length'))>7_000_000)return Response.json({error:'Image too large'},{status:413});
    const raw=await request.text();if(raw.length>7_000_000)return Response.json({error:'Image too large'},{status:413});
    const {image,prompt,source}=JSON.parse(raw);
    if(typeof image!=='string'||!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(image)||typeof prompt!=='string'||!prompt.trim()||prompt.length>100||typeof source!=='string'||source.length>500)return Response.json({error:'Supply an image, a short garment noun phrase, and a source label.'},{status:400});
    const response=await fetch(`${(process.env.META_API_BASE||'https://api.meta.ai/v1').replace(/\/$/,'')}/responses`,{
      method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json',Accept:'text/event-stream'},signal:AbortSignal.timeout(120_000),
      body:JSON.stringify({model:'sam-3.1',input:[{type:'message',role:'user',content:[{type:'input_text',text:prompt.trim()},{type:'input_image',image_url:image}]}],stream:true,metadata:{mask_encoding:'one_bit',include_confidence:'true'}}),
    });
    if(!response.ok||!response.body)return Response.json({error:`SAM request failed (HTTP ${response.status}). Check key access and quota.`},{status:502});
    const result=await parseImageStream(events(response.body)).finalResult;
    if(result.outcome.status!=='completed')return Response.json({error:'SAM response was incomplete. Retry the image.'},{status:502});
    const masks=recordsOfKind(result.records,'mask').map(record=>{
      if(record.mask.width*record.mask.height>16_000_000)throw new Error('Mask exceeds display limit');
      return {id:record.objectId,bounds:record.bounds,width:record.mask.width,height:record.mask.height,path:decodeMaskToSVGPath(record.mask),confidence:record.confidence};
    });
    return Response.json({masks,provenance:{model:'sam-3.1',source,prompt:prompt.trim(),timestamp:new Date().toISOString()}},{headers:{'Cache-Control':'no-store'}});
  }catch{return Response.json({error:'SAM could not process this image. Check the connection and try again.'},{status:502});}
}
