#!/usr/bin/env python3
"""Record a fresh board task and render a synchronized activity panel on macOS."""
import json, os, shutil, signal, subprocess, sys, tarfile, time, urllib.request
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REPO=next(p for p in ROOT.parents if (p/'.env.local').is_file()); TMP=Path('/private/tmp/wps-qwen-video-run-'+datetime.now().strftime('%Y%m%d-%H%M%S')); TASK=TMP/'task'; HOME=TMP/'home'; NODE='/private/tmp/wps-pilot-node/node_modules/node/bin/node'; CBC='/private/tmp/wps-pilot-cbc/node_modules/@tencent-ai/codebuddy-code/bin/codebuddy'; SOURCE=Path('/private/tmp/wps-four-task-source/board-material-update-timeline-excel'); PRIOR=Path('/private/tmp/wps-board-visible'); ASSIST=Path('/private/tmp/wps-assistant-pilot')

def call(args,**kw):return subprocess.run(args,check=True,**kw)
def main():
 if TMP.exists(): raise SystemExit(f'{TMP} already exists; move or remove it before a new run')
 TASK.mkdir(parents=True);(TASK/'output').mkdir();(TASK/'.tmp').mkdir();(HOME/'.codebuddy').mkdir(parents=True)
 with tarfile.open(SOURCE/'environment/workspace.tar.gz') as f:f.extractall(TASK,filter='data')
 for name in ('models.json','settings.json'):shutil.copy('/private/tmp/wps-local-cbc-home/.codebuddy/'+name,HOME/'.codebuddy'/name)
 shutil.copy(PRIOR/'task/pilot-mcp.json',TASK/'pilot-mcp.json');shutil.copy(PRIOR/'task/pilot-prompt.txt',TASK/'pilot-prompt.txt')
 deck=TMP/'board-video.pptx';shutil.copy(TASK/'input/quarterly_governance_board_deck.pptx',deck)
 profile=(PRIOR/'sandbox.sb').read_text().replace('/private/tmp/wps-board-visible/task',str(TASK)).replace('/private/tmp/wps-board-visible/home',str(HOME)).replace('/private/tmp/wps-board-visible',str(TMP));(TMP/'sandbox.sb').write_text(profile)
 run=ROOT/'runs'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
 call(['/usr/bin/open','-a','/Applications/wpsoffice.app',str(deck)])
 swift=TMP/'windows.swift';swift.write_text('''import CoreGraphics\nimport Foundation\nlet ws=CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []\nfor w in ws { if (w[kCGWindowOwnerName as String] as? String)=="WPS Office", let b=w[kCGWindowBounds as String] as? [String:Double], (w[kCGWindowLayer as String] as? Int)==0 { let d=try! JSONSerialization.data(withJSONObject:b); print(String(data:d,encoding:.utf8)!); break }}\n''')
 time.sleep(2); box=json.loads(subprocess.check_output(['swift',str(swift)],text=True));x,y,w,h=[int(box[k])//2*2 for k in ('X','Y','Width','Height')]
 env=os.environ.copy();env.update(WPS_PILOT_TASK='board-material-update-timeline-excel',WPS_VIDEO_TASK=str(TASK),WPS_VIDEO_DECK=str(deck),WPS_VIDEO_EVENTS=str(run/'wps-events.jsonl'))
 guard=proxy=rec=None
 try:
  guard_script=ASSIST/('video-guard-'+str(os.getpid())+'.mjs');shutil.copy(ROOT/'wps-guard.mjs',guard_script)
  guard=subprocess.Popen([NODE,str(guard_script)],cwd=ASSIST,env=env,stdout=(run/'guard.log').open('w'),stderr=subprocess.STDOUT)
  proxy_env=os.environ.copy();proxy_env.update(DASHSCOPE_ENV_FILE=str(REPO/'.env.local'),PROXY_AUDIT_PATH=str(run/'model-requests.jsonl'))
  proxy=subprocess.Popen([NODE,str(ROOT.parent/'proxy-audit/qwen-proxy.mjs')],cwd=ASSIST,env=proxy_env,stdout=(run/'proxy.log').open('w'),stderr=subprocess.STDOUT)
  time.sleep(2)
  if guard.poll() is not None or proxy.poll() is not None:raise RuntimeError('WPS writer or Clover proxy failed to start; see logs')
  progress=run/'capture-progress.txt';capturelog=(run/'capture.log').open('w')
  rec=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','avfoundation','-framerate','15','-capture_cursor','1','-i','4:none','-vf',f'crop={w}:{h}:{x}:{y},fps=15','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-stats_period','0.2','-progress',str(progress),str(run/'wps.mp4')],stdin=subprocess.PIPE,stdout=capturelog,stderr=subprocess.STDOUT)
  deadline=time.time()+20;start=None
  while time.time()<deadline:
   if rec.poll() is not None:raise RuntimeError('Screen capture failed; see capture.log')
   if progress.exists():
    d=dict(line.split('=',1) for line in progress.read_text().splitlines() if '=' in line)
    if int(d.get('frame','0'))>0:
     start=time.time()-int(d.get('out_time_us','0'))/1e6;break
   time.sleep(.1)
  if start is None:raise RuntimeError('Screen capture did not produce frames')
  (run/'capture.json').write_text(json.dumps({'model':os.environ.get('QWEN_MODEL','qwen3.8-flash'),'thinking':True,'start_epoch':start,'crop':box,'sync':'first FFmpeg progress timestamp minus encoded output time; approximate','audio':False},indent=2))
  agent_env=os.environ.copy();agent_env.update(HOME=str(HOME),TMPDIR=str(TASK/'.tmp'),PATH='/private/tmp/wps-local-python/bin:/private/tmp/wps-pilot-node/node_modules/node/bin:'+os.environ.get('PATH',''),CODEBUDDY_AUTO_COMPACT_WINDOW='110000',CODEBUDDY_COMPUTER_USE_ENABLED='0',CODEBUDDY_WAIT_FOR_MCP_SERVERS_ENABLED='0',CODEBUDDY_CODE_DISABLE_SESSION_TITLE_REFRESH='1')
  prompt=(TASK/'pilot-prompt.txt').read_text()+'\n如需 Python，使用 /private/tmp/wps-local-python/bin/python，已安装 openpyxl 和 python-pptx。'
  with (HOME/'trajectory.jsonl').open('w') as out,(HOME/'agent-error.log').open('w') as err:
   agent=subprocess.run(['sandbox-exec','-f',str(TMP/'sandbox.sb'),NODE,CBC,'-p','--output-format','stream-json','-y','--model','clover-pilot','--max-turns','48','--mcp-config',str(TASK/'pilot-mcp.json'),'--',prompt],cwd=TASK,env=agent_env,stdout=out,stderr=err)
  shutil.copy(HOME/'trajectory.jsonl',run/'trajectory.jsonl');shutil.copy(HOME/'agent-error.log',run/'agent-error.log');(run/'agent-exit.txt').write_text(str(agent.returncode));time.sleep(2)
 finally:
  if rec and rec.poll() is None:
   rec.stdin.write(b'q\n');rec.stdin.flush()
   try:rec.wait(timeout=20)
   except subprocess.TimeoutExpired:rec.terminate();rec.wait()
  for proc in (guard,proxy):
   if proc and proc.poll() is None:proc.terminate();proc.wait()
 if not (TASK/'output/quarterly_governance_board_deck_revised.pptx').exists():raise RuntimeError('Agent produced no presentation; capture preserved at '+str(run))
 shutil.copy(TASK/'output/quarterly_governance_board_deck_revised.pptx',run/'result.pptx')
 call(['/private/tmp/wps-local-python/bin/python',str(ROOT/'render.py'),str(run)])
 print('RUN_DIRECTORY='+str(run),flush=True)
if __name__=='__main__':main()
