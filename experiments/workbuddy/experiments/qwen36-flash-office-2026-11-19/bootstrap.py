"""Container bootstrap. Reads the private ephemeral credential file once."""
import json,os,sys
from pathlib import Path
import yaml
p=Path('/run/workbuddy-secret/credentials.json')
creds=json.loads(p.read_text());p.unlink()
os.environ['WORKBUDDY_QWEN_BASE_URL']=creds['url'].rstrip('/')
os.environ['DASHSCOPE_API_KEY']=creds['key']
del creds
os.environ.update(PATH=str(Path.cwd()/'.venv/bin')+':'+os.environ['PATH'],PYTHONPATH=str(Path.cwd()/'src'),PROXY_HOST='workbuddy-qwen-office-proxy',PROXY_PORT='3488',SHARD_CONCURRENCY='1',WORKBUDDY_QWEN_OFFICE_PREFLIGHT='1')
model={'model':{'name':'qwen3.6-flash','protocols':['openai'],'backend_url_env':'WORKBUDDY_QWEN_BASE_URL','backend_key_env':'DASHSCOPE_API_KEY','reasoning_passback':True,'max_concurrent':1,'context_window':131072,'params':{'temperature':0.0,'thinking_enabled':True,'extra_body':{'enable_thinking':True,'preserve_thinking':True}}}}
Path('configs/models/qwen36-flash-serial.yaml').write_text(yaml.safe_dump(model,sort_keys=False))
pipeline=Path('src/workbuddy_bench/proxy/pipeline.py');s=pipeline.read_text();old='route.slug in {"clover-spark-uncapped", "clover-spark-serial"}'
new='route.slug in {"clover-spark-uncapped", "clover-spark-serial", "qwen36-flash-serial"}'
if new not in s:
 assert s.count(old)==1
 pipeline.write_text(s.replace(old,new))
preflight=Path('scripts/workbuddy-task-proxy-preflight.sh');s=preflight.read_text();marker='if [[ "${WORKBUDDY_QWEN_OFFICE_PREFLIGHT:-0}" == 1 ]]; then'
if marker not in s:
 head='''if [[ "${WORKBUDDY_QWEN_OFFICE_PREFLIGHT:-0}" == 1 ]]; then
  docker compose -p workbuddy-preflight -f .workspace/preflight-json-screener-summary-L4-004.yaml run --rm --no-deps --entrypoint python3 main -c '
import json,sys
from urllib.request import urlopen
with urlopen("http://%s:%s/health"%(sys.argv[1],sys.argv[2]),timeout=8) as r:
 d=json.load(r); assert r.status==200 and "qwen36-flash-serial" in d.get("routes",{}); print("Task image reached Qwen proxy and route (HTTP 200)")
' "$1" "$2"
  exit 0
fi
'''
 s=s.replace('set -euo pipefail\n','set -euo pipefail\n'+head,1);preflight.write_text(s)
os.execv(sys.executable,[sys.executable,'/run/workbuddy-code/queue.py'])
