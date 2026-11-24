import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'pilot-preflight',version:'1'});
await c.connect(new StdioClientTransport({command:'/private/tmp/wps-pilot-node/node_modules/node/bin/node',args:['/private/tmp/wps-assistant-pilot/pilot-guard.mjs']}));
async function call(name,args){const r=await c.callTool({name,arguments:args});if(r.isError)throw new Error(JSON.stringify(r.content));return JSON.parse(r.content[0].text);}
try {
 const compute=await call('run_python',{code:'print(6 * 7)'});
 if(compute.exitCode!==0||compute.stdout.trim()!=='42')throw Error('Compute preflight failed');
 const output=await call('write_output',{rows:[['WPS writer preflight',42]]});
 if(!output.success)throw Error('Write preflight failed');
 const read=await call('read_output',{});
 if(!JSON.stringify(read.values).includes('WPS writer preflight'))throw Error('Readback preflight failed');
 console.log(JSON.stringify({compute:'passed',write:'passed',read:'passed'}));
}finally{await c.close();}
