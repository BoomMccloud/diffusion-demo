import http from 'node:http';
import { readFileSync } from 'node:fs';
const line=readFileSync('/Users/jasonbxu/Documents/GitHub/diffusion-demo/.env','utf8').split(/\r?\n/).find(x=>/^\s*(?:export\s+)?CLOVER_API_KEY\s*=/.test(x));
if(!line) throw Error('Clover key unavailable');
let key=line.slice(line.indexOf('=')+1).trim();
if ((key.startsWith('"')&&key.endsWith('"'))||(key.startsWith("'")&&key.endsWith("'"))) key=key.slice(1,-1);
if (!key || /[\r\n]/.test(key)) throw Error('Invalid key');
const server=http.createServer((req,res)=>{
 if(req.method!=='POST'||req.url!=='/v1/chat/completions'){res.writeHead(404);res.end();return;}
 let parts=[]; req.on('data',p=>parts.push(p)); req.on('end',()=>{
 try{
  const body=JSON.parse(Buffer.concat(parts)); body.model='Clover-35B-A3B-Preview';
  console.log('request tools:',(body.tools||[]).map(t=>t.function?.name).filter(Boolean).join(','));
  delete body.max_tokens; delete body.max_completion_tokens; delete body.max_output_tokens;
  body.temperature=0; body.chat_template_kwargs={...(body.chat_template_kwargs||{}),enable_thinking:true,preserve_thinking:true};
  const out=Buffer.from(JSON.stringify(body));
  const up=http.request({hostname:'43.107.54.53',port:31002,path:'/v1/chat/completions',method:'POST',headers:{'Content-Type':'application/json','Content-Length':out.length,Authorization:'Bearer '+key,'X-User-ID':'wps-pilot-20261118','X-Session-ID':'wps-ticket-pilot'}},r=>{res.writeHead(r.statusCode,{'Content-Type':r.headers['content-type']||'application/json'});r.pipe(res);});
  up.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end();}); up.end(out);
 }catch {res.writeHead(400);res.end();}
 });
});
server.listen(18767,'127.0.0.1',()=>console.log('Clover proxy listening on loopback'));
