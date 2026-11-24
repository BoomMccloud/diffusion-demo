from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(__file__).resolve().parent;W,H=1920,1540
BG='#0b1220';PANEL='#152235';WHITE='#edf4f7';MUTED='#aabccc';GREEN='#70e3b1';BLUE='#76aefa';LINE='#304257';FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(d,x,y,s,size,color=WHITE,b=False,anchor='mm'):d.text((x,y),s,font=ImageFont.truetype(BOLD if b else FONT,size),fill=color,anchor=anchor)
def base(kicker,title,subtitle):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);text(d,100,82,kicker,27,GREEN,True,'lm');text(d,100,175,title,69,WHITE,True,'lm');text(d,102,250,subtitle,31,MUTED,False,'lm');d.line((100,310,1820,310),fill=LINE,width=3);return im,d
def box(d,x):d.rounded_rectangle((x,410,x+830,1080),radius=24,fill=PANEL,outline=LINE,width=2)
im,d=base('WORKBUDDY OFFICE  /  WPS DEMO','One board deck. Two agent runs.','Update the presentation using a milestone register while preserving the original deck.')
for x,label,color,kind in [(100,'Clover',GREEN,'Diffusion language model'),(990,'Qwen3.6-Flash',BLUE,'Autoregressive language model')]:
 box(d,x);text(d,x+415,545,label,57,color,True);text(d,x+415,650,kind,33,MUTED);text(d,x+415,755,'CodeBuddy  +  WPS Office',34,WHITE)
text(d,960,1190,'Both recordings play at the same 12.8× speed.',30,WHITE)
text(d,960,1260,'Qwen rerun uses an improved partial-batch WPS writer.',30,MUTED)
text(d,960,1375,'Activity panels are reconstructed from timestamped agent and WPS events.',27,MUTED)
im.save(P/'intro.png')
im,d=base('WORKBUDDY OFFICE  /  RESULTS','Two WPS-edited attempts','Original task deterministic checks. Higher is better.')
for x,label,color,score,percent,t in [(100,'Clover',GREEN,'300 / 379','79.2%','2 min 43 sec'),(990,'Qwen3.6-Flash',BLUE,'305 / 379','80.5%','3 min 57 sec')]:
 box(d,x);text(d,x+415,500,label,52,color,True);text(d,x+415,650,score,76,WHITE,True);text(d,x+415,735,percent,48,color,True);text(d,x+415,850,'Agent elapsed time',30,MUTED);text(d,x+415,920,t,50,WHITE,True)
text(d,960,1190,'Times include deliberate WPS editing pauses; the runs made different edits.',30,WHITE)
text(d,960,1260,'Writer, provider and settings differ. One run each; not a controlled benchmark.',28,MUTED)
text(d,960,1375,'Source: recorded CodeBuddy runs and original deterministic verifier.',26,MUTED)
im.save(P/'outro.png')
for name,label in [('clover','CLOVER  |  300 / 379 checks'),('qwen','QWEN 3.6 FLASH  |  305 / 379 checks')]:
 im=Image.new('RGB',(1920,50),'#101923');ImageDraw.Draw(im).text((24,7),label,font=ImageFont.truetype(FONT,30),fill='white');im.save(P/(name+'-label.png'))
