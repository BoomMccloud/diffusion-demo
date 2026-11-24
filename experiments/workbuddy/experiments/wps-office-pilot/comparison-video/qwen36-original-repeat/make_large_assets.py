from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;W,H=1920,1540
BG='#0b1220';PANEL='#152235';WHITE='#edf4f7';MUTED='#aabccc';GREEN='#70e3b1';BLUE='#76aefa';RED='#ff6b70';LINE='#304257';FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(d,x,y,s,size,color=WHITE,b=False,anchor='mm'):d.text((x,y),s,font=ImageFont.truetype(BOLD if b else FONT,size),fill=color,anchor=anchor)
def base(kicker,title,subtitle):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);text(d,110,90,kicker,36,GREEN,True,'lm');text(d,110,200,title,84,WHITE,True,'lm');text(d,112,290,subtitle,46,MUTED,False,'lm');d.line((110,360,1810,360),fill=LINE,width=3);return im,d
def box(d,x):d.rounded_rectangle((x,445,x+830,1115),radius=24,fill=PANEL,outline=LINE,width=2)
im,d=base('WPS OFFICE','Updating a board presentation','Clover and Qwen3.6 Flash in WPS Office')
for x,label,color in [(100,'Clover',GREEN),(990,'Qwen3.6 Flash',BLUE)]:
 box(d,x);text(d,x+415,650,label,76,color,True);text(d,x+415,790,'CodeBuddy + WPS',45,WHITE)
text(d,960,1245,'Same task and WPS writer',44,WHITE);text(d,960,1325,'Playback: 14.5× speed',37,MUTED);text(d,960,1430,'Agent panels reconstructed from recorded events',32,MUTED);im.save(P/'intro-large.png')
im,d=base('WPS OFFICE','Results','Original task deterministic checks')
box(d,100);box(d,990)
text(d,515,515,'Clover',70,GREEN,True);text(d,515,625,'WPS output: Produced',48,GREEN,True);text(d,515,740,'300 / 379',82,WHITE,True);text(d,515,850,'Elapsed time: 2:43',49);text(d,515,960,'Stream rate: ~1,217 tok/s',40)
text(d,1405,515,'Qwen3.6 Flash',65,BLUE,True);text(d,1405,625,'WPS output: Not produced',43,RED,True);text(d,1405,740,'251 / 379*',82,WHITE,True);text(d,1405,850,'Elapsed time: 4:29',49);text(d,1405,960,'Stream rate: ~218 tok/s',40)
text(d,960,1190,'*Qwen’s score is for a Python-generated file.',35,WHITE)
text(d,960,1265,'Stream rates measured at the proxy, not pure model TPS.',33,MUTED)
text(d,960,1340,'One attempt per model. Agent times include paced WPS edits.',33,MUTED)
im.save(P/'outro-large.png')
for name,label in [('clover','CLOVER'),('qwen','QWEN 3.6 FLASH')]:
 im=Image.new('RGB',(1920,50),'#101923');ImageDraw.Draw(im).text((24,1),label,font=ImageFont.truetype(BOLD,39),fill='white');im.save(P/(name+'-label-large.png'))
im=Image.new('RGBA',(490,165),(10,15,25,235));d=ImageDraw.Draw(im);d.rounded_rectangle((1,1,488,163),radius=16,outline=RED,width=4,fill=(10,15,25,240));d.line((24,35,94,105),fill=RED,width=13);d.line((94,35,24,105),fill=RED,width=13);text(d,125,80,'Edit rejected',43,WHITE,True,'lm');im.save(P/'rejected-large.png')
