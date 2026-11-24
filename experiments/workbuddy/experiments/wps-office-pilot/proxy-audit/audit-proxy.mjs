import http from 'node:http';
import https from 'node:https';
import {openSync,writeSync,closeSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {StringDecoder} from 'node:string_decoder';

// Retain only provider usage numbers, nested objects, booleans and null. No prompts,
// completion text, headers, credentials, response errors or tool arguments are logged.
function numericUsage(value,depth=0){
 if(depth>6)return undefined;
 if(value===null||typeof value==='boolean'||(typeof value==='number'&&Number.isFinite(value)))return value;
 if(Array.isArray(value))return value.map(x=>numericUsage(x,depth+1)).filter(x=>x!==undefined);
 if(value&&typeof value==='object'){const out={};for(const [k,v] of Object.entries(value)){const clean=numericUsage(v,depth+1);if(clean!==undefined)out[k]=clean;}return out;}
 return undefined;
}
function responseMeta(json,record,at){
 if(!json||typeof json!=='object')return;
 if(typeof json.id==='string'&&/^[a-zA-Z0-9._:-]{1,256}$/.test(json.id))record.provider_response_id=json.id;
 if(typeof json.model==='string'&&/^[a-zA-Z0-9._:/-]{1,256}$/.test(json.model))record.provider_model=json.model;
 if(json.usage&&typeof json.usage==='object'){record.usage_events.push({at_ms:at,usage:numericUsage(json.usage)});}
 if(json.error)record.provider_error_present=true;
 if(Array.isArray(json.choices))for(const choice of json.choices){
  if(typeof choice.finish_reason==='string')record.finish_reasons.push(choice.finish_reason);
  const delta=choice.delta||choice.message||{};
  const content=typeof delta.content==='string'&&delta.content.length>0;
  const reasoning=['reasoning_content','reasoning','thinking'].some(k=>typeof delta[k]==='string'&&delta[k].length>0);
  const tool=Array.isArray(delta.tool_calls)&&delta.tool_calls.length>0;
  if(content||reasoning||tool){record.content_events++;if(record.first_output_ms===null)record.first_output_ms=at;record.last_output_ms=at;}
  if(content&&record.first_text_ms===null)record.first_text_ms=at;
  if(reasoning&&record.first_reasoning_ms===null)record.first_reasoning_ms=at;
  if(tool&&record.first_tool_delta_ms===null)record.first_tool_delta_ms=at;
 }
}
export function startProxy({port,upstream,transform,headers,auditPath,includeUsage=true}){
 const fd=openSync(auditPath,'wx',0o600);
 const server=http.createServer((req,res)=>{
  if(req.method!=='POST'||req.url!=='/v1/chat/completions'){res.writeHead(404);res.end();return;}
  const start=process.hrtime.bigint(),at=()=>Number(process.hrtime.bigint()-start)/1e6;
  const record={schema_version:1,request_id:randomUUID(),started_at:new Date().toISOString(),effective_settings:null,http_status:null,first_byte_ms:null,first_output_ms:null,first_text_ms:null,first_reasoning_ms:null,first_tool_delta_ms:null,last_output_ms:null,end_ms:null,provider_response_id:null,provider_model:null,finish_reasons:[],usage_events:[],content_events:0,sse_events:0,parse_errors:0,stream_done:false,completed:false,client_disconnected:false,upstream_error:null};
  writeSync(fd,JSON.stringify({schema_version:1,event:'request_start',request_id:record.request_id,started_at:record.started_at})+'\n');
  let finished=false,up;
  function finish(){if(finished)return;finished=true;record.end_ms=at();record.ended_at=new Date().toISOString();writeSync(fd,JSON.stringify({event:'request_end',...record})+'\n');}
  let parts=[],size=0;req.on('data',c=>{size+=c.length;if(size>20000000)req.destroy();else parts.push(c);});req.on('error',()=>{record.upstream_error='client_request_error';finish();});
  req.on('aborted',()=>{record.upstream_error='client_request_aborted';finish();});req.on('end',()=>{try{
   const body=transform(JSON.parse(Buffer.concat(parts)));if(body.stream&&includeUsage)body.stream_options={...(body.stream_options||{}),include_usage:true};
   record.effective_settings={};for(const k of ['model','stream','temperature','top_p','top_k','seed','presence_penalty','frequency_penalty','repetition_penalty','max_tokens','max_completion_tokens','max_output_tokens','enable_thinking','reasoning_effort']){const v=body[k];if(typeof v==='boolean'||typeof v==='number'||(typeof v==='string'&&/^[a-zA-Z0-9._:/-]{1,128}$/.test(v)))record.effective_settings[k]=v;}
   record.effective_settings.message_count=Array.isArray(body.messages)?body.messages.length:null;record.effective_settings.tool_count=Array.isArray(body.tools)?body.tools.length:null;
   if(body.stream_options)record.effective_settings.stream_options={include_usage:body.stream_options.include_usage===true};
   if(body.chat_template_kwargs)record.effective_settings.chat_template_kwargs={enable_thinking:body.chat_template_kwargs.enable_thinking===true,preserve_thinking:body.chat_template_kwargs.preserve_thinking===true};
   const bytes=Buffer.from(JSON.stringify(body));const target=new URL(upstream);const transport=target.protocol==='https:'?https:http;
   up=transport.request({hostname:target.hostname,port:target.port||(target.protocol==='https:'?443:80),path:target.pathname+target.search,method:'POST',headers:{...headers,'Content-Type':'application/json','Content-Length':bytes.length}},r=>{
    record.http_status=r.statusCode;record.upstream_headers_ms=at();res.writeHead(r.statusCode,{'Content-Type':r.headers['content-type']||'application/json'});
    const sse=(r.headers['content-type']||'').includes('text/event-stream');const decoder=new StringDecoder('utf8');let pending='',jsonBody='',dataLines=[];
    function event(){if(!dataLines.length)return;let data=dataLines.join('\n');dataLines=[];record.sse_events++;if(data==='[DONE]'){record.stream_done=true;return;}try{responseMeta(JSON.parse(data),record,at());}catch{record.parse_errors++;}}
    function feed(text){pending+=text;let pos;while((pos=pending.indexOf('\n'))>=0){let line=pending.slice(0,pos).replace(/\r$/,'');pending=pending.slice(pos+1);if(line==='')event();else if(line.startsWith('data:'))dataLines.push(line.slice(5).replace(/^ /,''));}if(pending.length>4e6){record.parse_errors++;pending='';dataLines=[];}}
    r.on('data',chunk=>{if(record.first_byte_ms===null)record.first_byte_ms=at();if(sse)feed(decoder.write(chunk));else if(jsonBody.length<10e6)jsonBody+=decoder.write(chunk);res.write(chunk);});
    r.on('end',()=>{if(sse){feed(decoder.end()+'\n\n');event();}else{jsonBody+=decoder.end();try{responseMeta(JSON.parse(jsonBody),record,at());}catch{record.parse_errors++;}}record.completed=true;res.end();finish();});
    r.on('aborted',()=>{record.upstream_error='response_aborted';res.destroy();finish();});r.on('error',()=>{record.upstream_error='response_error';res.destroy();finish();});
   });
   up.on('error',()=>{record.upstream_error='request_error';if(!res.headersSent)res.writeHead(502);res.end();finish();});
   res.on('close',()=>{if(!res.writableFinished){record.client_disconnected=true;up.destroy();finish();}});
   up.end(bytes);
  }catch{record.upstream_error='invalid_request';if(!res.headersSent)res.writeHead(400);res.end();finish();}});
 });
 server.on('close',()=>closeSync(fd));server.listen(port,'127.0.0.1',()=>console.log('Audited proxy listening on loopback'));
 return server;
}
