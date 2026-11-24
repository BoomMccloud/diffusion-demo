import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { z } from 'zod';
import { readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
const c = new Client({name:'wps-pilot-guard',version:'1'});
await c.connect(new StreamableHTTPClientTransport(new URL('http://127.0.0.1:18766/mcp')));
async function call(name, args) {
  const r = await c.callTool({name,arguments:args});
  if (r.isError) throw new Error(`${name}: ${JSON.stringify(r.content)}`);
  return r.structuredContent ?? JSON.parse(r.content[0].text);
}
const base = '/Users/jasonbxu/Documents/WPS Clover Pilot/';
async function doc(name) {
  const {documents} = await call('wps_list_documents', {});
  const found = documents.filter(d => d.path === base + name && d.type === 'spreadsheet');
  if (found.length !== 1) throw new Error(`Open only ${name} from ${base} in WPS Sheets`);
  return found[0].documentId;
}
const server = new McpServer({name:'pilot-wps',version:'1'});
server.registerTool('run_python',{description:'Execute Python for analysis against the original task files under /workspace/input in a fresh network-disabled, read-only Linux container. Print results to stdout. Each call starts a fresh container; use openpyxl to read the workbook. Runtime is limited to 30 seconds and output to 64 KiB.',inputSchema:{code:z.string().min(1).max(16000)}},async({code})=>{
 return await new Promise(resolve=>{
  const args=['-o','BatchMode=yes','-o','ConnectTimeout=8','jx25520@192.168.3.3','timeout 30 docker run -i --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 512m --cpus 1 --tmpfs /tmp:rw,noexec,nosuid,size=32m -w /workspace ticket-weekly-l3-010__zwwisit__env-main:latest python -I -B -'];
  const child=spawn('/usr/bin/ssh',args,{stdio:['pipe','pipe','pipe']}); let stdout='',stderr='',excess=false;
  const append=(which,buf)=>{if(which==='out')stdout+=buf;else stderr+=buf;if(stdout.length+stderr.length>65536){excess=true;child.kill();}};
  child.stdout.on('data',b=>append('out',b.toString())); child.stderr.on('data',b=>append('err',b.toString()));
  child.on('error',e=>resolve({isError:true,content:[{type:'text',text:String(e)}]}));
  child.on('close',exitCode=>resolve({isError:exitCode!==0||excess,content:[{type:'text',text:JSON.stringify({exitCode,stdout:stdout.slice(0,65536),stderr:stderr.slice(0,4096),outputLimit:excess})}]}));
  child.stdin.on('error',()=>{});child.stdin.end(code);
 });
});
server.registerTool('read_input',{description:'Read the provided ticket workbook as extracted read-only data. Each row is an array; the first is the header.',inputSchema:{}},async()=>{
 try { const text=await readFile('/private/tmp/wps-one-task/input-values.json','utf8'); return {content:[{type:'text',text}]}; }
 catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
});
server.registerTool('write_output',{description:'Write the final result as rows of values to a new WPS spreadsheet and save it. Supply the header as the first row. Numbers must be JSON numbers, not strings.',inputSchema:{rows:z.array(z.array(z.union([z.string().max(500),z.number().finite(),z.null()])).min(1).max(20)).min(1).max(200)}},async({rows})=>{
 try {
  const documentId=await doc('output.xlsx');
  const v=await call('wps_create_variable',{variableName:'WPS pilot result',sourceDocumentId:documentId,code:'return true;'});
  await call('wps_run_transform',{variableId:v.variableId});
  const literal=JSON.stringify(JSON.stringify(rows));
  const code=`const rows=JSON.parse(${literal}); const sheet=wpsDocument.Worksheets.Item(1); sheet.UsedRange.ClearContents(); for(let r=0;r<rows.length;r++){for(let col=0;col<rows[r].length;col++){sheet.Range(String.fromCharCode(65+col)+String(r+1)).Value2=rows[r][col];}} wpsDocument.Save(); return {rows:rows.length};`;
  const render=await call('wps_create_render',{variableId:v.variableId,targetDocumentId:documentId,code});
  const result=await call('wps_run_render',{variableId:v.variableId,renderId:render.renderId});
  if(result.renders?.some(r=>!r.success)) throw new Error(JSON.stringify(result));
  return {content:[{type:'text',text:JSON.stringify(result)}]};
 }catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
});
server.registerTool('read_output',{description:'Read back the saved output workbook through WPS.',inputSchema:{}},async()=>{
 try { const documentId=await doc('output.xlsx'); const r=await call('wps_run_readonly_code',{documentId,code:"const s=wpsDocument.Worksheets.Item(1); return {sheet:s.Name, values:s.UsedRange.Value2};"}); return {content:[{type:'text',text:JSON.stringify(r.result)}]}; }
 catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
});
await server.connect(new StdioServerTransport());
