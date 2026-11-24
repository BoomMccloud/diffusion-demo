from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;W,H=1920,1540
BG='#0b1220';PANEL='#152235';WHITE='#edf4f7';MUTED='#aabccc';GREEN='#70e3b1';BLUE='#76aefa';RED='#ff6b70';LINE='#304257';FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(d,x,y,s,size,color=WHITE,b=False,anchor='mm'):d.text((x,y),s,font=ImageFont.truetype(BOLD if b else FONT,size),fill=color,anchor=anchor)
def base(kicker,title,subtitle):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);text(d,100,82,kicker,27,GREEN,True,'lm');text(d,100,175,title,69,WHITE,True,'lm');text(d,102,250,subtitle,31,MUTED,False,'lm');d.line((100,310,1820,310),fill=LINE,width=3);return im,d
def box(d,x):d.rounded_rectangle((x,410,x+830,1080),radius=24,fill=PANEL,outline=LINE,width=2)
im,d=base('WORKBUDDY OFFICE  /  WPS DEMO','Can both agents update WPS?','Same board task and original all-or-nothing WPS writer.')
for x,label,color,kind in [(100,'Clover',GREEN,'Diffusion language model'),(990,'Qwen3.6-Flash',BLUE,'Autoregressive language model')]:
 box(d,x);text(d,x+415,545,label,57,color,True);text(d,x+415,650,kind,33,MUTED);text(d,x+415,755,'CodeBuddy  +  WPS Office',34,WHITE)
text(d,960,1190,'Both recordings play at the same 14.5× speed.',30,WHITE)
text(d,960,1260,'An X marks each rejected Qwen WPS update batch.',30,MUTED)
text(d,960,1375,'Activity panels are reconstructed from timestamped agent and WPS events.',27,MUTED);im.save(P/'intro.png')
im,d=base('WORKBUDDY OFFICE  /  RESULTS','One WPS completion. One fallback.','Original task deterministic checks; one attempt per model.')
box(d,100);box(d,990)
text(d,515,488,'Clover',52,GREEN,True);text(d,515,600,'WPS EDITED',38,GREEN,True);text(d,515,690,'300 / 379',70,WHITE,True);text(d,515,790,'Agent time   2 min 43 sec',36);text(d,515,890,'~1,217 output tokens/sec',36)
text(d,1405,488,'Qwen3.6-Flash',52,BLUE,True);text(d,1405,600,'WPS FAILED',38,RED,True);text(d,1405,680,'251 / 379 via Python',56,WHITE,True);text(d,1405,790,'Agent time   4 min 29 sec',36);text(d,1405,890,'~218 output tokens/sec',36)
text(d,960,1180,'Streaming rates are provider-reported output tokens divided by proxy output intervals.',27,WHITE)
text(d,960,1240,'Rates are not pure model TPS; agent time includes paced WPS edits. Providers differ.',27,MUTED)
text(d,960,1300,'Qwen made no WPS edits; its score is for the Python-generated fallback.',28,MUTED)
text(d,960,1375,'Source: CodeBuddy trajectories, proxy usage and original deterministic verifier.',25,MUTED);im.save(P/'outro.png')
for name,label in [('clover','CLOVER  |  WPS-edited deck'),('qwen','QWEN 3.6 FLASH  |  original WPS writer')]:
 im=Image.new('RGB',(1920,50),'#101923');ImageDraw.Draw(im).text((24,7),label,font=ImageFont.truetype(FONT,30),fill='white');im.save(P/(name+'-label.png'))
for i in range(1,5):
 im=Image.new('RGBA',(370,150),(10,15,25,225));d=ImageDraw.Draw(im);d.rounded_rectangle((1,1,368,148),radius=16,outline=RED,width=4,fill=(10,15,25,235));d.line((23,32,75,84),fill=RED,width=11);d.line((75,32,23,84),fill=RED,width=11);text(d,95,49,'WPS BATCH',27,WHITE,True,'lm');text(d,95,89,f'REJECTED  {i} / 4',26,RED,True,'lm');im.save(P/f'rejected-{i}.png')
