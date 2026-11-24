#!/usr/bin/env python3
"""Animate representative source rows into their verified output sheets."""
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

source = list(input_wb.active.values)[1:]
destinations = [list(sheet.values)[1:] for sheet in wb]
assert Counter(source) == Counter(row for rows in destinations for row in rows)
counts = [len(rows) for rows in destinations]
labels = ['Outbound / loss', 'Expiry warning', 'Other records']
source_positions = {values: index + 2 for index, values in enumerate(source)}
colors = ['#a64533', '#826009', '#17694d']
command = calls[3][2].splitlines()

def recorded(*prefixes):
    return [next(line.strip() for line in command if line.strip().startswith(prefix))
            for prefix in prefixes]

snippets = [
    recorded('def is_outbound_loss', 'return row[4] <= 0', 'sheet1_data ='),
    (recorded('def is_warning', 'expiry =', 'if expiry >= 3', 'return False')
     + ['…'] + recorded('sheet2_data =')),
    recorded('sheet3_data ='),
]
save_lines = recorded('wb.save(out_path)')
columns = [(46, 'ROW'), (101, 'RECORD ID'), (285, 'DRUG'), (510, 'CLASS'),
           (610, 'STOCK CHANGE'), (745, 'EXPIRY (MONTHS)')]
FONT_CACHE = {size: F(size) for size in (12, 14, 15, 16, 17, 18, 20, 21, 23, 31, 38)}
CODE_FONT = M(14)

def draw_text(draw, xy, value, size=17, color=WHITE):
    draw.text(xy, str(value), font=FONT_CACHE[size], fill=color)

def header(draw, y):
    draw.rectangle((38, y, 924, y + 30), fill='#336084')
    for x, label in columns:
        draw_text(draw, (x, y + 6), label, 12)

def row(draw, y, values, number, accent=None, fields=(), fill='#ffffff'):
    draw.rectangle((38, y, 924, y + 31), fill=fill)
    data = [number, values[0], values[1], values[2], values[4], values[5]]
    for i, ((x, _), value) in enumerate(zip(columns, data)):
        right = columns[i + 1][0] if i + 1 < len(columns) else 924
        if i in fields:
            draw.rectangle((x - 4, y + 1, right - 4, y + 30), fill='#ffedba')
        draw_text(draw, (x, y + 4), value, 17, '#172e40')
    if accent:
        draw.rectangle((38, y, 924, y + 31), outline=accent, width=2)

def code_panel(draw, title, code):
    draw.rounded_rectangle((951, 95, 1254, 644), 10, fill='#141e2d')
    draw_text(draw, (967, 112), 'RECORDED CODE', 14, GREEN)
    draw_text(draw, (967, 146), title, 18)
    y = 188
    for line in code:
        pieces = textwrap.wrap(line, 30) or ['']
        for piece in pieces:
            font = CODE_FONT if piece.isascii() else FONT_CACHE[14]
            draw.text((967, y), piece, font=font, fill=WHITE)
            y += 22

def tabs(draw, selected, tallies):
    names = ['Source'] + wb.sheetnames
    for i, (name, count) in enumerate(zip(names, [len(source)] + tallies)):
        x = 38 + i * 222
        active = i == selected
        color = '#336084' if i == 0 else colors[i - 1]
        draw.rounded_rectangle((x, 570, x + 213, 618), 6,
                               fill='#ffffff' if active else '#d9e2ea')
        draw_text(draw, (x + 12, 581), name, 18, color)
        draw_text(draw, (x + 123, 583), f'{count} rows', 16, '#324d63')
        if active:
            draw.rectangle((x + 2, 614, x + 211, 618), fill=color)


def smooth(fraction):
    return fraction * fraction * (3 - 2 * fraction)


out = ROOT / 'drug-inventory-row-copy.mp4'
ffmpeg = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
          '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]

with subprocess.Popen(ffmpeg, stdin=subprocess.PIPE) as encoder:
    for frame in range(20 * FPS):
        t = frame / FPS
        im = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(im)
        draw_text(d, (27, 17), 'CLOVER / WORKBUDDY OFFICE', 15, GREEN)
        draw_text(d, (27, 41), 'Drug inventory split', 31)
        d.rounded_rectangle((25, 95, 938, 644), 10, fill='#e8edf3')

        if t < 2.25:
            draw_text(d, (39, 111), 'SOURCE WORKBOOK', 14, '#415669')
            draw_text(d, (39, 141), '药品出入库明细.xlsx', 23, '#172e40')
            draw_text(d, (39, 183), '300 inventory records across 10 columns', 18, '#324d63')
            header(d, 226)
            for i, values in enumerate(source[:8]):
                row(d, 257 + 33 * i, values, i + 2, fill='#ffffff' if i % 2 == 0 else '#f4f7fa')
            tabs(d, 0, [0, 0, 0])
            code_panel(d, 'Read the workbook', [line for line in calls[2][2].splitlines()
                                              if 'load_workbook' in line or 'active' in line])
        elif t < 13.5:
            group = int((t - 2.25) / 3.75)
            elapsed = t - (2.25 + group * 3.75)
            saved_rows = destinations[group]
            # One visible row lands first. Five batch animations then represent all remaining rows.
            bounds = [0, 1] + [1 + (len(saved_rows) - 1) * i // 5 for i in range(1, 6)]
            wave_time = max(0, elapsed - .24) / .52
            wave = min(6, int(wave_time))
            landed = bounds[wave]
            moving = saved_rows[landed:bounds[wave + 1]] if wave < 6 else []
            selected = moving[:3] if moving else saved_rows[-3:]
            tallies = [n if i < group else landed if i == group else 0
                       for i, n in enumerate(counts)]
            color = colors[group]

            draw_text(d, (39, 115), 'Source workbook  /  300 rows', 21, '#172e40')
            header(d, 152)
            for i, values in enumerate(selected):
                row(d, 184 + 33 * i, values, source_positions[values], color,
                    [(4,), (3, 5), (4, 5)][group])
            draw_text(d, (39, 327), f'Output workbook  /  {labels[group]}', 21, '#172e40')
            draw_text(d, (700, 330), f'{landed} of {counts[group]} copied', 17, color)
            header(d, 365)
            for i in range(3):
                y = 397 + 33 * i
                d.rectangle((38, y, 924, y + 31), fill='#f7fafc')
            for i in range(max(0, landed - 3), landed):
                y = 397 + 33 * (i - max(0, landed - 3))
                row(d, y, saved_rows[i], i + 2, fill='#e2f3eb')
            if moving:
                fraction = smooth(min(1, (wave_time % 1) / .83))
                if fraction > 0:
                    # Show up to three actual batch records crossing from source to destination.
                    for i, values in enumerate(selected):
                        y = round(184 + 33 * i + 213 * fraction)
                        row(d, y, values, '↳', color, fill='#e2f3eb')
                draw_text(d, (42, 514), f'Copying {len(moving)} ' +
                          ('row' if len(moving) == 1 else 'rows in this batch'), 17, color)
            else:
                draw_text(d, (42, 514), f'All {landed} rows copied', 17, color)

            tabs(d, group + 1, tallies)
            code_panel(d, labels[group], ['…'] + snippets[group] + ['…'])
        elif t < 18:
            group = int((t - 13.5) / 1.5)
            elapsed = t - (13.5 + group * 1.5)
            draw_text(d, (39, 111), 'VALIDATE SAVED OUTPUT  /  result.xlsx', 14, '#415669')
            draw_text(d, (39, 144), wb.sheetnames[group] + f'   ·   {counts[group]} rows', 31, colors[group])
            header(d, 210)
            for i, values in enumerate(destinations[group][:7]):
                row(d, 242 + 35 * i, values, i + 2,
                    fill='#ffffff' if i % 2 == 0 else '#f4f7fa')
            # Push in on the populated grid, leaving the tab strip and code anchored.
            zoom = smooth(min(1, elapsed / .48))
            crop = (38, 210, 925 - round(29 * zoom), 487 - round(40 * zoom))
            grid = im.crop(crop).resize((887, 277), Image.Resampling.LANCZOS)
            im.paste(grid, (38, 210))
            draw_text(d, (40, 513), f'{counts[group]} rows  ×  10 columns confirmed', 18, colors[group])
            tabs(d, group + 1, counts)
            stdout = results[calls[4][0]].splitlines()
            code_panel(d, 'Reopen and verify', [line for line in calls[4][2].splitlines()
                       if 'load_workbook' in line] + ['', 'Recorded output', stdout[group + 1]])
        else:
            draw_text(d, (39, 118), 'SAVED OUTPUT WORKBOOK', 14, '#415669')
            draw_text(d, (39, 151), 'result.xlsx', 31, '#172e40')
            draw_text(d, (42, 252), '60 + 200 + 40 = 300 records', 38, '#172e40')
            draw_text(d, (42, 329), '15 / 15 verifier checks passed', 31, '#17694d')
            tabs(d, -1, counts)
            code_panel(d, 'Save and verify', save_lines + ['', 'Recorded output'] +
                       results[calls[4][0]].splitlines()[1:])
        draw_text(d, (27, 673),
                  'Saved WorkBuddy run  •  Row movement and timing are reconstructed', 15, DIM)
        encoder.stdin.write(im.tobytes())
    encoder.stdin.close()
    if encoder.wait():
        raise SystemExit('ffmpeg failed')
print(out)
