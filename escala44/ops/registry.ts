// This function stores only a tunnel address and heartbeat; never police data.
const expectedHash = "d44d1dc7fb83da61c0c62ed4ca38ef803847638c56d677f625b73afcc8dbcdc9";
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
Deno.serve(async(req:Request)=>{
 const token=req.headers.get('x-escala-registry-key')||'';
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token)))).map(b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==expectedHash)return json({error:'Unauthorized'},401);
 const secrets=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')||'{}');
 const key=secrets.default||Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
 if(!key)return json({error:'Registry unavailable'},503);
 const endpoint=Deno.env.get('SUPABASE_URL')+'/rest/v1/escala44_tunnel_registry';
 const headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'};
 try{
  if(req.method==='POST'){
   if(Number(req.headers.get('content-length')||0)>2048)return json({error:'Too large'},413);
   const body=await req.json();const url=String(body.url||'');
   if(!/^https:\/\/[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com$/.test(url))return json({error:'Invalid tunnel URL'},400);
   const result=await fetch(endpoint+'?on_conflict=id',{method:'POST',headers:{...headers,'Prefer':'resolution=merge-duplicates'},body:JSON.stringify({id:1,url,updated_at:new Date().toISOString()})});
   if(!result.ok){console.error('Registry write',result.status);return json({error:'Registry write failed'},503)}
   return json({ok:true});
  }
  if(req.method!=='GET')return json({error:'Method not allowed'},405);
  const result=await fetch(endpoint+'?id=eq.1&select=url,updated_at',{headers});
  if(!result.ok)return json({error:'Registry read failed'},503);
  const rows=await result.json();const row=rows[0];
  if(!row||Date.now()-Date.parse(row.updated_at)>180000)return json({error:'Local server offline'},503);
  return json(row);
 }catch(e){console.error('Tunnel registry request failed');return json({error:'Registry unavailable'},503)}
});
