#!/usr/bin/env python3
"""Animate recorded CodeBuddy Bash calls and saved workbook views."""
import json, math, subprocess, textwrap, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import openpyxl

ROOT=Path(__file__).resolve().parent; SRC=ROOT/'source'; W,H,FPS=1280,720,12
font='/System/Library/Fonts/Menlo.ttc'; cjk='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
F=lambda n: ImageFont.truetype(cjk,n)
M=lambda n: ImageFont.truetype(font,n)
BG='#0b101c'; MUTED='#90a4b8'; WHITE='#edf3f8'; GREEN='#72e5b2'; BLUE='#81b8ff'
records=[json.loads(l) for l in open(SRC/'cbc-output.txt')]
calls=[]; results={}
for rec in records:
 for c in rec.get('message',{}).get('content',[]):
  if c.get('type')=='tool_use': calls.append((c['id'],c['input']['description'],c['input']['command']))
  elif c.get('type')=='tool_result': results[c['tool_use_id']]=c.get('_meta',{}).get('renderer',{}).get('value','')
assert len(calls)==5 and all(c[0] in results for c in calls)
wb=openpyxl.load_workbook(SRC/'inventory_workbook.xlsx',data_only=True)
assert [s.max_row-1 for s in wb]==[60,200,40]
# Durations are editorial. Every shown terminal character comes from a recorded call/result.
lengths=[(3,2),(3,2),(7,5),(24,5),(6,4)]
segments=[]
t=2.5
for i,(typing,pause) in enumerate(lengths): segments.append((t,t+typing,t+typing+pause,i)); t+=typing+pause
review_start=t; total=t+16
out=ROOT/'drug-inventory-action-replay.mp4'
p=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
def txt(d,pos,s,size=20,fill=WHITE,mono=False): d.text(pos,s,font=M(size) if mono and all(ord(ch)<128 for ch in s) else F(size),fill=fill)
def wrapped(s,width=103):
 lines=[]
 for line in s.split('\n'):
  lines.extend(textwrap.wrap(line,width=width,replace_whitespace=False,drop_whitespace=False,break_long_words=True) or [''])
 return lines
for frame in range(math.ceil(total*FPS)):
 t=frame/FPS; im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
 txt(d,(32,19),'CLOVER  /  WORKBUDDY OFFICE',18,GREEN)
 txt(d,(32,48),'Drug inventory split',26)
 txt(d,(32,685),'RECONSTRUCTED REPLAY  •  RECORDED CALLS + RESULTS  •  EDITED TIMING',14,MUTED)
 if t<review_start:
  d.rounded_rectangle((30,93,1250,660),radius=12,fill='#151e2e',outline='#33465c',width=2)
  d.rectangle((31,94,1249,132),fill='#202f42')
  txt(d,(52,101),'CodeBuddy  /  Bash tool',17,WHITE)
  if t<2.5:
   txt(d,(65,174),'TASK',20,GREEN); txt(d,(65,216),'Split the drug inventory into three sheets.',29)
   txt(d,(65,272),'Use the original rules and save output/result.xlsx.',22,MUTED)
   txt(d,(65,337),'The following terminal commands are from the saved run.',21,MUTED)
  else:
   for start,end,finish,i in segments:
    if start<=t<finish: break
   cid,desc,command=calls[i]; output=results[cid]
   txt(d,(64,150),f'CALL {i+1} / 5    {desc}',20,GREEN)
   progress=min(1,max(0,(t-start)/(end-start)))
   shown=command[:int(len(command)*progress)]
   lines=wrapped('$ '+shown,108)
   # Keep the currently typed end visible, as a terminal naturally scrolls.
   if progress>=1 and t>=end: lines+=['','↳ recorded stdout:']+wrapped(output,108)
   lines=lines[-19:]
   for j,line in enumerate(lines): txt(d,(65,194+j*23),line,17,WHITE,True)
   if progress<1 and int(t*2)%2==0:
    yy=194+(len(lines)-1)*23; d.rectangle((min(1190,65+len(lines[-1])*9),yy+3,min(1198,73+len(lines[-1])*9),yy+20),fill=GREEN)
 else:
  local=t-review_start; idx=min(2,int(local/4.4)); s=wb.worksheets[idx]
  txt(d,(35,99),'Saved output workbook',26)
  txt(d,(35,139),'Reconstructed viewer: inspecting the saved artifact',18,MUTED)
  d.rounded_rectangle((30,181,1250,609),radius=10,fill='#f6f8fa')
  d.rectangle((31,182,1249,223),fill='#305e90')
  cols=[0,1,2,4,5,6]; xs=[50,260,468,610,745,880]
  for x,label in zip(xs,['RECORD_ID','DRUG_NAME','CLASS','STOCK Δ','EXPIRY','VENDOR']): txt(d,(x,190),label,16,'#ffffff')
  rows=list(s.values)[1:8]
  for j,row in enumerate(rows):
   y=223+j*44
   if j%2: d.rectangle((31,y,1249,y+44),fill='#e6edf4')
   for x,k in zip(xs,cols): txt(d,(x,y+11),str(row[k])[:17],17,'#172435')
   d.line((31,y+43,1249,y+43),fill='#c5d1dd')
  for k,sh in enumerate(wb):
   x=50+k*216; d.rounded_rectangle((x,565,x+195,599),radius=6,fill='#305e90' if k==idx else '#d3deea')
   txt(d,(x+10,572),f'{sh.title}  {sh.max_row-1}',16,'#ffffff' if k==idx else '#283c50')
  # Editorial cursor travels between tabs, not a claim of recorded mouse activity.
  phase=(local%4.4)/4.4; cx=130+idx*216; cy=582
  if local>13.2:
   d.rounded_rectangle((725,625,1245,665),radius=7,fill='#173a31'); txt(d,(744,633),'VERIFIER: 15 / 15 DETERMINISTIC CHECKS',17,GREEN)
  else:
   d.polygon([(cx,cy-18),(cx,cy+5),(cx+6,cy-1),(cx+11,cy+10),(cx+15,cy+8),(cx+10,cy-3),(cx+20,cy-3)],fill='#ffffff',outline='#111111')
 p.stdin.write(im.tobytes())
p.stdin.close(); code=p.wait()
if code: raise SystemExit(code)
print(f'Wrote {out} ({total:.1f}s)')
