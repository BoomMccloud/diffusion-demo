import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { createServer } from 'node:http';
import { z } from 'zod';
const bridge=new Client({name:'pilot-normal-guard',version:'1'});
await bridge.connect(new StreamableHTTPClientTransport(new URL('http://127.0.0.1:18766/mcp')));
async function call(name,args){const r=await bridge.callTool({name,arguments:args});if(r.isError)throw Error(JSON.stringify(r.content));return r.structuredContent??JSON.parse(r.content[0].text);}
async function outputDoc(){const {documents}=await call('wps_list_documents',{});const d=documents.filter(x=>x.path==='/Users/jasonbxu/Documents/WPS Clover Pilot/output.xlsx'&&x.type==='spreadsheet');if(d.length!==1)throw Error('Dedicated output workbook must be open in WPS');return d[0].documentId;}
function createMcp(){
 const m=new McpServer({name:'wps-pilot-output',version:'1'});
 m.registerTool('write_output',{description:'Create the final output table in the designated WPS workbook, replacing existing cells and saving. Provide headers in the first row. Optional percentage_columns is a list of 1-based column numbers: those columns should contain fractional values such as 0.727, displayed as 72.7%.',inputSchema:{rows:z.array(z.array(z.union([z.string().max(500),z.number().finite(),z.null()])).min(1).max(20)).min(1).max(200),percentage_columns:z.array(z.number().int().min(1).max(20)).max(20).optional()}},async({rows,percentage_columns=[]})=>{
  try{const id=await outputDoc();const v=await call('wps_create_variable',{variableName:'Normal tools pilot output',sourceDocumentId:id,code:'return true;'});await call('wps_run_transform',{variableId:v.variableId});
   const rowsLiteral=JSON.stringify(JSON.stringify(rows)), pctLiteral=JSON.stringify(JSON.stringify(percentage_columns));
   const code=`const rows=JSON.parse(${rowsLiteral}); const percent=JSON.parse(${pctLiteral}); const sheet=wpsDocument.Worksheets.Item(1); sheet.UsedRange.Clear(); for(let r=0;r<rows.length;r++){for(let col=0;col<rows[r].length;col++){const cell=sheet.Range(String.fromCharCode(65+col)+String(r+1)); cell.Value2=rows[r][col]; if(r>0&&percent.includes(col+1))cell.NumberFormat='0.0%';}} wpsDocument.Save(); return {rows:rows.length};`;
   const r=await call('wps_create_render',{variableId:v.variableId,targetDocumentId:id,code});const x=await call('wps_run_render',{variableId:v.variableId,renderId:r.renderId});if(!x.success||x.renders?.some(q=>!q.success))throw Error(JSON.stringify(x));return {content:[{type:'text',text:JSON.stringify(x)}]};
  }catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
 });
 m.registerTool('read_output',{description:'Read the designated saved WPS workbook for verification.',inputSchema:{}},async()=>{try{const id=await outputDoc();const x=await call('wps_run_readonly_code',{documentId:id,code:"const s=wpsDocument.Worksheets.Item(1); return {sheet:s.Name, values:s.UsedRange.Value2};"});return {content:[{type:'text',text:JSON.stringify(x.result)}]};}catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}});
 return m;
}
createServer(async(req,res)=>{if(req.method!=='POST'||req.url!=='/mcp'){res.writeHead(405);res.end();return;}try{let data=[];let size=0;for await(const x of req){size+=x.length;if(size>2000000)throw Error('too large');data.push(x);}const body=JSON.parse(Buffer.concat(data));const s=createMcp();const t=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});await s.connect(t);res.on('close',()=>{void t.close();void s.close();});await t.handleRequest(req,res,body);}catch{if(!res.headersSent)res.writeHead(400);res.end();}}).listen(18768,'127.0.0.1',()=>console.log('Restricted WPS tool listening on loopback'));
