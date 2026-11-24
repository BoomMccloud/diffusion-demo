"""Run the 50 saved Clover Office task names serially with Qwen3.6-Flash."""
import json, os, re, signal, subprocess, time
from pathlib import Path
import yaml

root=Path('results/qwen36-flash-office-serial')
root.mkdir(parents=True,exist_ok=True)
ledger=root/'queue.jsonl'
base=yaml.safe_load(Path('configs/jobs/clover-office-full-uncapped.yaml').read_text())
names=base['task_selection']['names']
assert len(names)==50 and len(set(names))==50

def append(row):
 with ledger.open('a') as f:
  f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())

def clean_proxy(job):
 for f in Path('scripts/logs/instances').glob(job+'-*/proxy.yaml'):
  for proc in Path('/proc').iterdir():
   if not proc.name.isdigit():continue
   try:
    argv=(proc/'cmdline').read_bytes().split(b'\x00')
    if b'workbuddy_bench.proxy' in argv and str(f.resolve()).encode() in argv:os.kill(int(proc.name),signal.SIGTERM)
   except (OSError,ValueError):continue

done={r['task'] for r in (json.loads(l) for l in ledger.read_text().splitlines()) if r['status']=='completed'} if ledger.exists() else set()
for index,task in enumerate(names,1):
 if task in done:continue
 attempt=0
 while True:
  attempt+=1;tag=f'qwen36-flash-office-{index:03d}-a{attempt:03d}'
  if Path('results',tag).exists():continue
  job=dict(base,model='qwen36-flash-serial',task_selection={'mode':'name','names':[task]})
  Path(f'configs/jobs/{tag}.yaml').write_text(yaml.safe_dump(job,sort_keys=False))
  print(f'Start Office {index}/50 {task}, attempt {attempt}',flush=True)
  try:rc=subprocess.call(['bash','scripts/run.sh','--job',tag])
  finally:clean_proxy(tag)
  logs=sorted(Path('scripts/logs/proxy').glob('proxy-'+tag+'-*.log'))
  codes=[c for f in logs for c in re.findall(r'HTTP/1\.1 (\d{3})',f.read_text())]
  paths=list(Path(f'results/{tag}').glob('*/*/result.json'))
  trial=json.loads(paths[0].read_text()) if len(paths)==1 else {}
  tokens=(trial.get('agent_result') or {}).get('n_output_tokens') or 0
  if '429' in codes and (not tokens or codes[-1]=='429'):
   append(dict(task=task,job=tag,status='retry_429',http_429=codes.count('429')))
   if attempt>=3:raise SystemExit('Repeated rate limiting; stopped rather than launch further tasks')
   time.sleep(10);continue
  if rc or not trial or (not tokens and '200' not in codes):
   append(dict(task=task,job=tag,status='infrastructure_error',launcher_exit=rc,http=codes[-8:]))
   raise SystemExit(f'Infrastructure failure on {task}; checkpoint preserved')
  append(dict(task=task,job=tag,status='completed',output_tokens=tokens,http_200=codes.count('200'),http_429=codes.count('429'),result=str(paths[0])))
  print(f'Completed Office {index}/50 {task}',flush=True)
  break
print('Completed all 50 Office trials',flush=True)
