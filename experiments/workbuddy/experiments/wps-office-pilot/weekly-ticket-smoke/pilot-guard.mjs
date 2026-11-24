import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { z } from 'zod';
import { readFile } from 'node:fs/promises';
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
  const code=`const rows=JSON.parse(${literal}); const sheet=wpsDocument.Worksheets.Item(1); for(let r=0;r<rows.length;r++){for(let col=0;col<rows[r].length;col++){sheet.Range(String.fromCharCode(65+col)+String(r+1)).Value2=rows[r][col];}} wpsDocument.Save(); return {rows:rows.length};`;
  const render=await call('wps_create_render',{variableId:v.variableId,targetDocumentId:documentId,code});
  const result=await call('wps_run_render',{variableId:v.variableId,renderId:render.renderId});
  if(result.renders?.some(r=>!r.success)) throw new Error(JSON.stringify(result));
  return {content:[{type:'text',text:JSON.stringify(result)}]};
 }catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
});
await server.connect(new StdioServerTransport());
