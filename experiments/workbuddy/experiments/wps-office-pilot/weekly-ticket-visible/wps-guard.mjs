import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { createServer } from 'node:http';
import { copyFile } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const openFile=promisify(execFile);
import { z } from 'zod';
const bridge=new Client({name:'pilot-normal-guard',version:'1'});
await bridge.connect(new StreamableHTTPClientTransport(new URL('http://127.0.0.1:18766/mcp')));
async function call(name,args){const r=await bridge.callTool({name,arguments:args});if(r.isError)throw Error(JSON.stringify(r.content));return r.structuredContent??JSON.parse(r.content[0].text);}
async function outputDoc(){const {documents}=await call('wps_list_documents',{});const d=documents.filter(x=>x.path==='/Users/jasonbxu/Documents/WPS Clover Pilot/output.xlsx'&&x.type==='spreadsheet');if(d.length!==1)throw Error('Dedicated output workbook must be open in WPS');return d[0].documentId;}
function createMcp(){
 const m=new McpServer({name:'wps-pilot-output',version:'1'});
 m.registerTool('write_output',{description:'Create the final output table in the designated WPS workbook, replacing existing cells and saving. Provide headers in the first row. Optional percentage_columns is a list of 1-based column numbers: those columns should contain fractional values such as 0.727, displayed as 72.7%.',inputSchema:{rows:z.array(z.array(z.union([z.string().max(500),z.number().finite(),z.null()])).min(1).max(20)).min(1).max(200),percentage_columns:z.array(z.number().int().min(1).max(20)).max(20).optional()}},async({rows,percentage_columns=[]})=>{
  try{const id=await outputDoc();const v=await call('wps_create_variable',{variableName:'Normal tools pilot output',sourceDocumentId:id,code:'return true;'});await call('wps_run_transform',{variableId:v.variableId});
   await openFile('/usr/bin/open',['-a','/Applications/wpsoffice.app','/Users/jasonbxu/Documents/WPS Clover Pilot/output.xlsx']);
   let x;
   for(let row=0;row<rows.length;row++){
    const rowLiteral=JSON.stringify(JSON.stringify(rows[row])), pctLiteral=JSON.stringify(JSON.stringify(percentage_columns));
    const code=`wpsDocument.Activate(); const sheet=wpsDocument.Worksheets.Item(1); sheet.Activate(); const row=JSON.parse(${rowLiteral}), percent=JSON.parse(${pctLiteral}); ${row===0?'sheet.UsedRange.Clear();':''} sheet.Range('A${row+1}:${String.fromCharCode(64+rows[row].length)}${row+1}').Select(); for(let col=0;col<row.length;col++){const cell=sheet.Range(String.fromCharCode(65+col)+'${row+1}'); cell.Value2=row[col]; if(${row}>0&&percent.includes(col+1))cell.NumberFormat='0.0%';} ${row===rows.length-1?'wpsDocument.Save();':''} return {row:${row+1}};`;
    const r=await call('wps_create_render',{variableId:v.variableId,targetDocumentId:id,code}); x=await call('wps_run_render',{variableId:v.variableId,renderId:r.renderId}); if(!x.success||x.renders?.some(q=>!q.success))throw Error(JSON.stringify(x));
    await new Promise(resolve=>setTimeout(resolve,1200));
   }
   await copyFile('/Users/jasonbxu/Documents/WPS Clover Pilot/output.xlsx','/private/tmp/wps-visible-task/output/result.xlsx');return {content:[{type:'text',text:JSON.stringify({success:true,savedPath:'output/result.xlsx',wpsResult:x})}]};
  }catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}
 });
 m.registerTool('read_output',{description:'Read the designated saved WPS workbook for verification.',inputSchema:{}},async()=>{try{const id=await outputDoc();const x=await call('wps_run_readonly_code',{documentId:id,code:"const s=wpsDocument.Worksheets.Item(1); return {sheet:s.Name, values:s.UsedRange.Value2};"});return {content:[{type:'text',text:JSON.stringify(x.result)}]};}catch(e){return {isError:true,content:[{type:'text',text:String(e)}]};}});
 return m;
}
createServer(async(req,res)=>{if(req.method!=='POST'||req.url!=='/mcp'){res.writeHead(405);res.end();return;}try{let data=[];let size=0;for await(const x of req){size+=x.length;if(size>2000000)throw Error('too large');data.push(x);}const body=JSON.parse(Buffer.concat(data));const s=createMcp();const t=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});await s.connect(t);res.on('close',()=>{void t.close();void s.close();});await t.handleRequest(req,res,body);}catch{if(!res.headersSent)res.writeHead(400);res.end();}}).listen(18768,'127.0.0.1',()=>console.log('Restricted WPS tool listening on loopback'));
