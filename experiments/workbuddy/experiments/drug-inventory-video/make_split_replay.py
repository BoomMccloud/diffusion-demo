#!/usr/bin/env python3
"""20-second split-screen reconstruction from recorded calls and workbook."""
import io,json,subprocess,tarfile,textwrap
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import openpyxl
ROOT=Path(__file__).resolve().parent; SRC=ROOT/'source'; W,H,FPS=1280,720,24
F=lambda n:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',n)
M=lambda n:ImageFont.truetype('/System/Library/Fonts/Menlo.ttc',n)
BG='#0a1220'; WHITE='#edf3f8'; DIM='#9aafc1'; GREEN='#76e4b3'
records=[json.loads(l) for l in open(SRC/'cbc-output.txt')]; calls=[]; results={}
for rec in records:
 for c in rec.get('message',{}).get('content',[]):
  if c.get('type')=='tool_use': calls.append((c['id'],c['input']['description'],c['input']['command']))
  if c.get('type')=='tool_result': results[c['tool_use_id']]=c.get('_meta',{}).get('renderer',{}).get('value','')
assert len(calls)==5 and all(x[0] in results for x in calls)
with tarfile.open(SRC/'workspace.tar.gz') as z:
 member=next(m for m in z.getmembers() if m.name.endswith('.xlsx'))
 input_wb=openpyxl.load_workbook(io.BytesIO(z.extractfile(member).read()),data_only=True)
wb=openpyxl.load_workbook(SRC/'inventory_workbook.xlsx',data_only=True)
assert [s.max_row-1 for s in wb]==[60,200,40]
r=json.load(open(SRC/'result.json'))['verifier_result']['rewards']; assert r['tests_passed']==r['tests_total']==15
out=ROOT/'drug-inventory-split-view.mp4'
p=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
def text(d,xy,s,n=17,color=WHITE,mono=False):
 d.text(xy,str(s),font=M(n) if mono and all(ord(c)<128 for c in str(s)) else F(n),fill=color)
def lines(s,width):
 out=[]
 for line in s.split('\n'): out.extend(textwrap.wrap(line,width=width,replace_whitespace=False,drop_whitespace=False) or [''])
 return out
# Match each illustrated row to its original values and saved destination.
source_rows = list(input_wb.active.values)[1:]
output_rows = [list(sheet.values)[1:] for sheet in wb]
assert Counter(source_rows) == Counter(row for rows in output_rows for row in rows)
source_numbers = {row[0]: number for number, row in enumerate(source_rows, 2)}
counts = [len(rows) for rows in output_rows]
labels = ['Outbound / loss', 'Expiry warning', 'Other records']
colors = ['#ae5541', '#8f650b', '#23765b']
sample_rows = [rows[:5] for rows in output_rows]
command_lines = calls[3][2].splitlines()

def excerpt(*prefixes):
    return [next(line for line in command_lines if line.strip().startswith(prefix))
            for prefix in prefixes]

rule_lines = [
    excerpt('def is_outbound_loss', 'return row[4] <= 0', 'sheet1_data ='),
    excerpt('def is_warning', 'expiry =', 'if expiry >= 3', 'return False',
            'class_match =', "drug_class.startswith", 'vendor_match =', 'channel_match =',
            'return class_match', 'sheet2_data ='),
    excerpt('sheet3_data ='),
]
save_lines = [line for line in command_lines if line.startswith(('write_sheet(wb.', 'out_path =', 'wb.save('))]

write_output = results[calls[3][0]].splitlines()
write_output = [line for line in write_output if not line.startswith('Header:')]
stages = [
    (0, 0, 'Locate the workspace'),
    (1.45, 1, 'Locate the source workbook'),
    (2.9, 2, 'Read the source range'),
    (5.4, 3, 'Group zero and negative stock changes'),
    (7.8, 3, 'Group qualifying expiry warnings'),
    (10.6, 3, 'Group the remaining records'),
    (12.65, 3, 'Write all three sheets and save'),
    (15, 4, 'Reopen and verify the workbook'),
]
xs = [674, 711, 859, 921, 997, 1074, 1173]
headers = ['ROW', 'RECORD ID', 'CLASS', 'STOCK Δ', 'MONTHS', 'VENDOR', 'CHANNEL']
field_indexes = [0, 2, 4, 5, 6, 7]

def draw_grid(d, rows, source, fields=(), moved=0, accent='#23765b'):
    d.rectangle((665, 244, 1240, 275), fill='#35658e')
    for x, header in zip(xs, headers):
        text(d, (x, 251), header, 12)
    for i, row in enumerate(rows):
        y = 275 + i * 41
        fill = '#e8edf3' if i < moved else ('#ffffff' if i % 2 == 0 else '#f1f5f8')
        d.rectangle((665, y, 1240, y + 40), fill=fill)
        if i < moved:
            text(d, (711, y + 9), '✓ ' + row[0] + '   →   grouped', 16, accent)
            continue
        number = source_numbers[row[0]] if source else i + 2
        for j, (x, value) in enumerate(zip(xs, [number] + [row[k] for k in field_indexes])):
            if j in fields:
                right = xs[j + 1] - 3 if j + 1 < len(xs) else 1239
                d.rectangle((x - 3, y + 1, right, y + 39), fill='#ffedba')
            text(d, (x, y + 10), str(value)[:(7 if j >= 5 else 18)], 13, '#172e40')

for frame in range(20 * FPS):
    t = frame / FPS
    stage = max(i for i, (start, _, _) in enumerate(stages) if t >= start)
    start, call_index, caption = stages[stage]
    end = stages[stage + 1][0] if stage < len(stages) - 1 else 20
    progress = (t - start) / (end - start)
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    text(d, (30, 16), 'CLOVER  /  WORKBUDDY OFFICE', 17, GREEN)
    text(d, (30, 45), 'Drug inventory split', 26)
    text(d, (848, 27), 'SAVED RUN  •  EDITED TO 20 SECONDS', 15, DIM)
    d.rounded_rectangle((25, 91, 636, 650), 12, fill='#141e2d')
    d.rounded_rectangle((650, 91, 1255, 650), 12, fill='#e8edf3')
    d.rectangle((26, 92, 635, 130), fill='#26364a')
    d.rectangle((651, 92, 1254, 130), fill='#253b50')
    text(d, (42, 101), 'RECORDED CODEBUDDY CALLS', 15)
    text(d, (667, 101), 'WORKSHEET  •  RECONSTRUCTED EXECUTION', 15)
    selected = min(2, int((t - 15) / 1.35)) if stage == 7 else 0
    cid, desc, cmd = calls[call_index]
    text(d, (43, 149), f'{call_index + 1} / 5   {desc}', 17, GREEN)
    if 3 <= stage <= 5:
        code = ['…'] + rule_lines[stage - 3] + ['…']
    elif stage == 6:
        code = ['…'] + save_lines + ['…', '', 'Recorded stdout'] + write_output
    else:
        code = ['$ ' + cmd, '', 'Recorded stdout']
        code += results[cid].splitlines()[:3] if stage == 2 else results[cid].splitlines()
    y = 190
    for piece in lines('\n'.join(code), 57):
        active_result = stage == 7 and piece.startswith(wb.sheetnames[selected] + ':')
        if active_result:
            d.rounded_rectangle((36, y - 2, 625, y + 19), 4, fill='#23413e')
        text(d, (43, y), piece, 15, GREEN if active_result else WHITE, True)
        y += 20

    text(d, (666, 147), caption, 21, '#172e40')
    moved = 0
    moving_row = None
    if stage < 2:
        name = 'input/     output/' if stage == 0 else 'input/药品出入库明细.xlsx'
        d.rounded_rectangle((665, 209, 1240, 259), 6, fill='#ffffff')
        text(d, (681, 221), name, 19, '#172e40')
    else:
        if stage == 2:
            text(d, (666, 192), 'A1:J301  •  300 records, 10 columns', 17, '#415669')
            draw_grid(d, source_rows[:5], True)
        elif 3 <= stage <= 5:
            group = stage - 3
            transfer = max(0, min(5, (progress - .17) * 6.7))
            moved = int(transfer)
            if 0 < transfer < 5:
                moving_row = (sample_rows[group][moved][0], group, moved, transfer - moved)
            fields = [(3,), (2, 4, 5, 6), ()][group]
            text(d, (666, 192), 'Source worksheet  •  representative rows', 17, '#415669')
            draw_grid(d, sample_rows[group], True, fields, moved, colors[group])
            text(d, (669, 496), '→  ' + labels[group] + f'  •  {moved}/5 examples grouped', 18, colors[group])
        else:
            group = selected
            text(d, (666, 192), 'output/result.xlsx  •  ' + labels[group], 17, '#415669')
            draw_grid(d, sample_rows[group], False)

        if stage >= 6:
            d.rectangle((665, 526, 1240, 602), fill='#d4dfe9')
            text(d, (675, 531), 'SHEET TABS', 12, '#415669')
        for group, (label, count) in enumerate(zip(labels, counts)):
            x = 665 + group * 193
            if stage >= 6:
                current = group == selected
                accent = colors[group]
                d.rounded_rectangle((x + 4, 550, x + 185, 596), 5,
                                    fill='#ffffff' if current else '#e8edf3')
                if current:
                    d.rectangle((x + 6, 592, x + 183, 596), fill=accent)
                text(d, (x + 13, 556), wb.sheetnames[group], 17,
                     accent if current else '#586e7c')
                text(d, (x + 123, 560), str(count) + ' rows', 13, '#415669')
                continue
            active = stage >= 3 + group
            d.rounded_rectangle((x, 541, x + 186, 595), 6, fill='#ffffff' if active else '#d4dfe9')
            text(d, (x + 9, 547), label, 15, colors[group] if active else '#586e7c')
            tally = f'{count} rows' if stage > 3 + group or (active and moved == 5) else 'Grouping…' if active else 'Pending'
            text(d, (x + 9, 570), tally, 14, '#172e40')
        if moving_row:
            record_id, group, row_index, fraction = moving_row
            x = round(710 + (665 + group * 193 - 710) * fraction)
            y = round(280 + row_index * 41 + (512 - 280 - row_index * 41) * fraction)
            d.rounded_rectangle((x, y, x + 170, y + 26), 5, fill=colors[group])
            text(d, (x + 8, y + 4), record_id, 13)
        if t >= 18.5:
            text(d, (667, 612), '15 / 15 deterministic checks passed', 18, '#155b3b')
    text(d, (30, 677), 'RECORDED CODE AND OUTPUT  •  WORKSHEET ANIMATION ILLUSTRATES THE SAVED RUN', 14, DIM)
    p.stdin.write(im.tobytes())

p.stdin.close()
if p.wait():
    raise SystemExit('ffmpeg failed')
print(out)
