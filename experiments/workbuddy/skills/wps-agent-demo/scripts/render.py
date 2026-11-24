#!/usr/bin/env python3
"""Make a timestamped activity panel and combine it with a WPS capture."""
import argparse, json, subprocess, textwrap
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def timestamp(value): return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
def run(cmd): subprocess.run(cmd, check=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args();d=args.directory.resolve()
 meta=json.loads((d/'capture.json').read_text()); start=meta['start_epoch']
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(d/'wps.mp4')],text=True))
 events=[]
 for line in (d/'trajectory.jsonl').read_text().splitlines():
  try:o=json.loads(line)
  except json.JSONDecodeError:continue
  for c in o.get('message',{}).get('content',[]):
   if c.get('type')=='tool_use' and o.get('__timestamp'):
    name=c.get('name',''); desc=c.get('input',{}).get('description','')
    label={'mcp__pilot_wps__inspect_presentation':'Inspect presentation in WPS','mcp__pilot_wps__update_presentation':'Submit presentation edits to WPS','Bash':'Run shell command','Read':'Read task file','Write':'Create task file','Edit':'Update task file'}.get(name,name)
    events.append((timestamp(o['__timestamp'])-start, 'AGENT',label,desc))
 if (d/'wps-events.jsonl').exists():
  for line in (d/'wps-events.jsonl').read_text().splitlines():
   e=json.loads(line);label={'select':'Select target','edit':'Update target','save':'Save document'}.get(e['type'],e['type'])
   details=e.get('location','')
   if e.get('slide') is not None:details=f"Slide {e['slide']}  |  Shape {e['shape']}"
   if e.get('row') is not None:details+=f"  |  Cell {e['row']},{e['column']}"
   events.append((timestamp(e['timestamp'])-start,'WPS',label,details))
 events=[e for e in events if 0<=e[0]<duration];events.sort();(d/'timeline.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
 font='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'; title=ImageFont.truetype(font,32); small=ImageFont.truetype(font,21); body=ImageFont.truetype(font,23)
 frames=d/'panel-frames';frames.mkdir(exist_ok=True); timeline=[(0,None)]+[(t,e) for e in events for t in [e[0]]];timeline.append((duration,None))
 lines=[];recent=[]
 for i,((t,e),(nt,_)) in enumerate(zip(timeline,timeline[1:])):
  if e:recent.append(e);recent=recent[-9:]
  if nt-t<0.025:continue
  im=Image.new('RGB',(640,720),'#101923');draw=ImageDraw.Draw(im)
  draw.text((28,25),'AGENT ACTIVITY',font=title,fill='#f5f8fa');draw.text((28,72),'Recorded tool and WPS events',font=small,fill='#94a9b8')
  draw.line((28,111,612,111),fill='#344656',width=2);y=134
  if not recent:draw.text((28,y),'Waiting for agent activity…',font=body,fill='#bdcbd3')
  for et,kind,label,detail in reversed(recent):
   draw.text((28,y),f'{et:06.1f}s  {kind}',font=small,fill='#74d5a0' if kind=='WPS' else '#8ebaff');y+=28
   for line in textwrap.wrap(label,43)[:2]:draw.text((28,y),line,font=body,fill='#f2f6f8');y+=28
   if detail:
    for line in textwrap.wrap(detail.replace('\n',' '),48)[:2]:draw.text((28,y),line,font=small,fill='#a7b9c4');y+=25
   y+=16
   if y>635:break
  frame=frames/f'{i:05d}.png';im.save(frame);lines.extend([f"file '{frame}'",f'duration {nt-t:.6f}'])
 lines.append(f"file '{frame}'"); (d/'panel.ffconcat').write_text('ffconcat version 1.0\n'+'\n'.join(lines)+'\n')
 run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(d/'panel.ffconcat'),'-i',str(d/'wps.mp4'),'-filter_complex','[1:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2[left];[0:v]scale=640:720[right];[left][right]hstack=inputs=2[v]','-map','[v]','-r','15','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-t',str(duration),str(d/'combined.mp4')])
 print('Saved',d/'combined.mp4')
if __name__=='__main__':main()
