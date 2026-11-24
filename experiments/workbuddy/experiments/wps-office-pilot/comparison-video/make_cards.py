from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent; W,H=1920,1540
SPEED=float(sys.argv[1]) if len(sys.argv)>1 else 8.8
INTRO_NAME='intro-30.png' if len(sys.argv)>1 else 'intro.png'
BG='#0b1220'; PANEL='#152235'; WHITE='#edf4f7'; MUTED='#aabccc'; GREEN='#70e3b1'; BLUE='#76aefa'; LINE='#304257'
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'; BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def text(d,x,y,s,size,color=WHITE,b=False,anchor='mm'):d.text((x,y),s,font=font(size,b),fill=color,anchor=anchor)
def base(kicker,title,subtitle):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);text(d,100,82,kicker,27,GREEN,True,'lm');text(d,100,175,title,69,WHITE,True,'lm');text(d,102,250,subtitle,31,MUTED,False,'lm');d.line((100,310,1820,310),fill=LINE,width=3);return im,d
def box(d,rect):d.rounded_rectangle(rect,radius=24,fill=PANEL,outline=LINE,width=2)
im,d=base('WORKBUDDY OFFICE  /  WPS DEMO','One board deck. Two agent runs.','Update the presentation using a milestone register while preserving the original deck.')
for x,label,color,typ in [(100,'Clover',GREEN,'Diffusion language model'),(990,'Qwen3.8-Flash',BLUE,'Autoregressive language model')]:
 box(d,(x,425,x+830,970));text(d,x+415,560,label,60,color,True);text(d,x+415,650,typ,34,MUTED);text(d,x+415,760,'CodeBuddy  +  WPS Office',34,WHITE)
text(d,960,1120,'Same task and WPS editing workflow  •  One recorded attempt per model',32,WHITE)
text(d,960,1190,f'Both recordings play at the same {SPEED:.1f}× speed.',30,MUTED)
text(d,960,1390,'Activity panels are reconstructed from timestamped agent and WPS events.',27,MUTED)
im.save(P/INTRO_NAME)
im,d=base('WORKBUDDY OFFICE  /  RESULTS','Two completed attempts','Original task deterministic checks. Higher is better.')
for x,label,color,score,percent,t in [(100,'Clover',GREEN,'310 / 379','81.8%','4 min 18 sec'),(990,'Qwen3.8-Flash',BLUE,'326 / 379','86.0%','5 min 12 sec')]:
 box(d,(x,410,x+830,1080));text(d,x+415,500,label,52,color,True);text(d,x+415,650,score,76,WHITE,True);text(d,x+415,735,percent,48,color,True);text(d,x+415,850,'Agent elapsed time',30,MUTED);text(d,x+415,920,t,50,WHITE,True)
text(d,960,1190,'Timing includes deliberate pauses for WPS edits; Qwen made more edits.',30,WHITE)
text(d,960,1260,'Models, providers and settings differ. One run each; not a controlled benchmark.',28,MUTED)
text(d,960,1375,'Source: saved CodeBuddy trajectories and original deterministic verifier.',26,MUTED)
im.save(P/'outro.png')
