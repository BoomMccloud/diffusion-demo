#!/usr/bin/env python3
"""Render a labeled visual reconstruction of a saved WorkBuddy trial."""
import io, json, subprocess, tarfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import openpyxl

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'source'
OUT = ROOT / 'frames'
OUT.mkdir(exist_ok=True)
W,H=1280,720
BG='#0b1220'; PANEL='#152235'; WHITE='#edf4f7'; MUTED='#aabccc'; GREEN='#70e3b1'; BLUE='#76aefa'; LINE='#304257'
fontpath='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
if not Path(fontpath).exists(): fontpath='/System/Library/Fonts/Hiragino Sans GB.ttc'
def font(n): return ImageFont.truetype(fontpath,n)
def text(d,xy,s,n=24,fill=WHITE): d.text(xy,s,font=font(n),fill=fill)
def base(kicker,title,sub=''):
 im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
 text(d,(55,32),'CLOVER  /  WORKBUDDY OFFICE',19,GREEN)
 text(d,(55,85),title,43)
 if sub: text(d,(56,151),sub,22,MUTED)
 d.line((55,193,1225,193),fill=LINE,width=2)
 text(d,(55,677),'RECONSTRUCTED FROM A SAVED RUN  •  NOT A SCREEN RECORDING',15,MUTED)
 text(d,(1100,677),kicker,15,MUTED)
 return im,d
def card(d,box,fill=PANEL): d.rounded_rectangle(box, radius=15,fill=fill)
def table(d,rows, y=260):
 headers=['RECORD ID','DRUG','CLASS','STOCK Δ','EXPIRY','SUPPLIER']
 xs=[83,301,515,655,794,910]; widths=[210,205,125,125,100,240]
 d.rounded_rectangle((65,y-44,1215,y+7*46),radius=12,fill='#111e30')
 d.rectangle((65,y-44,1215,y),fill='#275a8b')
 for x,h in zip(xs,headers): text(d,(x,y-35),h,16)
 for i,row in enumerate(rows[:6]):
  yy=y+i*46
  if i%2==1: d.rectangle((66,yy,1214,yy+45),fill='#192a3e')
  vals=[row[0],row[1],row[2],row[4],row[5],row[6]]
  for x,v in zip(xs,vals): text(d,(x,yy+9),str(v)[:18],18)
  d.line((65,yy+45,1215,yy+45),fill=LINE,width=1)

def save(im,name): im.save(OUT / (name+'.png'))
with tarfile.open(SRC/'workspace.tar.gz') as tar:
 member=next(m for m in tar.getmembers() if m.name.endswith('.xlsx'))
 wb_in=openpyxl.load_workbook(io.BytesIO(tar.extractfile(member).read()),data_only=True)
 wb=openpyxl.load_workbook(SRC/'inventory_workbook.xlsx',data_only=True)
source=list(wb_in.active.values); sheets=[list(s.values) for s in wb]
assert len(source)-1==300 and [len(s)-1 for s in sheets]==[60,200,40]
assert json.load(open(SRC/'result.json'))['verifier_result']['rewards']['reward']==1.0
im,d=base('01 / 07','One workbook. Three useful views.','A real Clover + CodeBuddy run on a WorkBuddy Office task')
card(d,(65,235,1215,590)); text(d,(105,278),'DRUG INVENTORY',22,GREEN); text(d,(105,320),'300 records  →  3 sheets',49)
text(d,(107,410),'A saved benchmark run, reconstructed for viewing.',25,MUTED)
text(d,(107,455),'Input, actions, output and result come from the same trial.',23,MUTED); save(im,'01')
im,d=base('02 / 07','The request','Sort the original inventory records into one new workbook.')
card(d,(65,235,1215,600))
for i,(a,b) in enumerate([('01   OUTBOUND / LOSS','Stock change is zero or negative.'),('02   EXPIRY WARNING','Under 3 months and a matching class, supplier or channel.'),('03   OTHER RECORDS','Records that do not match the preceding conditions.')]):
 y=270+i*98; text(d,(100,y),a,22,GREEN); text(d,(100,y+36),b,25)
save(im,'02')
im,d=base('03 / 07','The source workbook','300 rows of inventory data, shown here as a readable excerpt.')
table(d,source[1:]); text(d,(72,612),'10 source columns  •  Original row values',20,MUTED); save(im,'03')
im,d=base('04 / 07','What Clover actually did','Selected steps from the saved CodeBuddy trajectory')
card(d,(65,230,1215,610));
for i,(a,b) in enumerate([('01','Listed the workspace and input directory'),('02','Inspected the input workbook with Python'),('03','Wrote a script to split and save the workbook'),('04','Reopened the output and checked sheet sizes')]):
 y=258+i*78; text(d,(100,y),a,25,GREEN); text(d,(164,y),b,27)
text(d,(100,580),'Recorded tool calls  •  Display order preserved',18,MUTED); save(im,'04')
for j,(title,sub) in enumerate([('Outbound / loss','Stock change ≤ 0'),('Expiry warning','Under 3 months plus a matching condition'),('Other records','All remaining records')]):
 im,d=base(f'0{j+5} / 07',title,sub); table(d,sheets[j][1:]); text(d,(73,612),f'{wb.sheetnames[j]}   •   {len(sheets[j])-1} rows   •   10 columns',21,GREEN)
 if j==2: text(d,(665,612),'VERIFIER: 15 / 15 DETERMINISTIC CHECKS',18,WHITE)
 save(im,f'0{j+5}')
manifest=OUT/'concat.txt'
durations=[5,7,6,7,6,6,8]
manifest.write_text(''.join(f"file '{OUT / f'{i:02d}.png'}'\nduration {v}\n" for i,v in enumerate(durations,1))+f"file '{OUT / '07.png'}'\n")
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(manifest),'-vf','fps=24,format=yuv420p','-c:v','libx264','-movflags','+faststart',str(ROOT/'drug-inventory-replay.mp4')],check=True)
print('Wrote',ROOT/'drug-inventory-replay.mp4')
