import {readFileSync} from 'node:fs';
import {startProxy} from './audit-proxy.mjs';
const raw=readFileSync(process.env.DASHSCOPE_ENV_FILE,'utf8');
function get(n){const line=raw.split(/\r?\n/).find(x=>new RegExp('^\\s*(?:export\\s+)?'+n+'\\s*=').test(x));if(!line)throw Error('Missing '+n);let v=line.slice(line.indexOf('=')+1).trim();if((v.startsWith('"')&&v.endsWith('"'))||(v.startsWith("'")&&v.endsWith("'")))v=v.slice(1,-1);if(!v)throw Error('Empty '+n);return v;}
const key=get('DASHSCOPE_API_KEY'),base=new URL(get('DASHSCOPE_API_URL'));if(base.protocol!=='https:'||base.hostname.startsWith('token-plan.')||base.hostname.startsWith('coding-'))throw Error('Automated runs require general-purpose HTTPS DashScope');
const target=new URL(base.toString());target.pathname=target.pathname.replace(/\/$/,'')+'/chat/completions';
startProxy({port:Number(process.env.PROXY_PORT||18767),auditPath:process.env.PROXY_AUDIT_PATH,upstream:target.toString(),headers:{Authorization:'Bearer '+key},transform:b=>{b.model=process.env.QWEN_MODEL||'qwen3.8-flash';delete b.chat_template_kwargs;delete b.max_completion_tokens;delete b.max_output_tokens;delete b.reasoning_effort;b.enable_thinking=true;return b;}});
