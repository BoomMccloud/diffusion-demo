import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {mkdtempSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {once} from 'node:events';
import {startProxy} from './audit-proxy.mjs';

test('records streamed usage, absent usage and HTTP failures without content or credentials',async()=>{
 let index=0;const upstream=http.createServer((req,res)=>{req.resume();req.on('end',()=>{index++;if(index===3){res.writeHead(429,{'content-type':'application/json'});return res.end(JSON.stringify({error:{message:'secret error text'}}));}
  res.writeHead(200,{'content-type':'text/event-stream'});const usage=index===1?`data: ${JSON.stringify({id:'response-1',model:'test-model',usage:{prompt_tokens:12,completion_tokens:4,completion_tokens_details:{reasoning_tokens:2}}})}\n\n`:'';
  const output=`data: ${JSON.stringify({id:'response-1',choices:[{delta:{content:'secret generated text'},finish_reason:null}]})}\n\ndata: ${JSON.stringify({choices:[{delta:{},finish_reason:'stop'}]})}\n\n${usage}data: [DONE]\n\n`;const b=Buffer.from(output);res.write(b.subarray(0,19));setTimeout(()=>res.end(b.subarray(19)),15);
 });});upstream.listen(0,'127.0.0.1');await once(upstream,'listening');
 const path=join(mkdtempSync(join(tmpdir(),'wps-audit-')),'events.jsonl');
 const proxy=startProxy({port:0,upstream:`http://127.0.0.1:${upstream.address().port}/v1/chat/completions`,auditPath:path,headers:{Authorization:'Bearer SECRET_KEY'},transform:x=>x});await once(proxy,'listening');
 for(let i=0;i<3;i++){const r=await fetch(`http://127.0.0.1:${proxy.address().port}/v1/chat/completions`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({model:'test-model',stream:true,messages:[{role:'user',content:'secret prompt'}]})});await r.text();}
 await new Promise(resolve=>proxy.close(resolve));await new Promise(resolve=>upstream.close(resolve));
 const raw=readFileSync(path,'utf8');assert(!raw.includes('SECRET_KEY'));assert(!raw.includes('secret prompt'));assert(!raw.includes('secret generated text'));assert(!raw.includes('secret error text'));
 const rows=raw.trim().split('\n').map(JSON.parse);assert.equal(rows.length,6);let end=rows.filter(x=>x.event==='request_end');assert.deepEqual(end.map(x=>x.http_status),[200,200,429]);assert.equal(end[0].usage_events[0].usage.completion_tokens,4);assert.equal(end[0].usage_events[0].usage.completion_tokens_details.reasoning_tokens,2);assert.equal(end[0].finish_reasons[0],'stop');assert.equal(end[0].stream_done,true);assert(end[0].first_output_ms>=0&&end[0].end_ms>=end[0].first_output_ms);assert.deepEqual(end[1].usage_events,[]);assert(end[2].provider_error_present);assert.equal(end[0].effective_settings.stream_options.include_usage,true);
});
