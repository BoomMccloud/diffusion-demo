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


from functools import lru_cache

source = list(input_wb.active.values)[1:]
outputs = [list(sheet.values)[1:] for sheet in wb]
assert Counter(source) == Counter(row for rows in outputs for row in rows)
sheets = [source] + outputs
counts = [len(rows) for rows in sheets]
source_index = {row: i for i, row in enumerate(source)}
names = ['Source inventory', *wb.sheetnames]
english = ['Original workbook', 'Outbound / loss', 'Expiry warning', 'Other records']
accents = ['#3b6481', '#a74d3b', '#8b6511', '#22715a']
paper_width, paper_height = 510, 420
positions = [(25, 0), (600, 0), (25, 474), (600, 474)]
final_positions = [(37 + 335 * i, 177) for i in range(3)]
font = lru_cache(maxsize=None)(F)

def label(d, xy, value, size, color):
    d.text(xy, str(value), font=font(size), fill=color)

def smooth(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)

def mix(a, b, amount):
    return a + (b - a) * amount

@lru_cache(maxsize=None)
def make_paper(sheet, count, closeup=False):
    image = Image.new('RGB', (paper_width, paper_height), '#fffdf6')
    d = ImageDraw.Draw(image)
    accent = accents[sheet]
    d.rectangle((0, 0, paper_width, 7), fill=accent)
    label(d, (19, 16), names[sheet], 28, '#152f3f')
    label(d, (20, 52), english[sheet], 16, accent)
    label(d, (365, 23), f'{count} rows', 23, '#152f3f')
    d.rectangle((19, 83, 491, 110), fill='#e8edf0')
    columns = [(24, 0, 'RECORD ID'), (178, 2, 'CLASS'), (270, 4, 'STOCK Δ'), (378, 5, 'EXPIRY (MO)')]
    if sheet == 0:
        for block in range(3):
            label(d, (24 + block * 158, 87), f'Records {block * 100 + 1}–{(block + 1) * 100}',
                  14, '#2e4654')
    else:
        for x, _, title in columns:
            label(d, (x, 87), title, 14, '#2e4654')
    if sheet == 0:
        # Lay out all 300 actual records across three blocks of 100 lines.
        micro = M(4)
        for block in range(3):
            x = 23 + block * 158
            d.rectangle((x - 3, 113, x + 147, 399), outline='#dce6e9')
            for local, row in enumerate(sheets[0][block * 100:(block + 1) * 100]):
                y = 118 + int(local * 2.77)
                if local % 2 == 0:
                    d.rectangle((x, y, x + 143, y + 1), fill='#e7ecec')
                d.text((x + 2, y - 2), f'{row[0]}   {row[2]}   {row[4]}   {row[5]}',
                       font=micro, fill='#405b6a')
        label(d, (22, 402), 'All 300 source rows  ·  10 columns in the workbook', 11, accent)
    elif closeup:
        for i, row in enumerate(sheets[sheet][:9]):
            y = 113 + 29 * i
            if i % 2 == 0:
                d.rectangle((19, y, 491, y + 28), fill='#f1f4f3')
            for x, k, _ in columns:
                label(d, (x, y + 4), row[k], 19, '#152f3f')
        label(d, (20, 386), f'{count} rows  ×  10 columns verified', 18, accent)
    else:
        # Each data record occupies one line in the overview. At this scale the
        # full data is seen as a dense sheet; the closing inserts show readable rows.
        pitch = 286 / counts[sheet]
        for i in range(counts[sheet]):
            y = 114 + int(i * pitch)
            if i < count:
                row = sheets[sheet][i]
                if i % 2 == 0 and pitch > 2:
                    d.rectangle((19, y, 491, y + int(pitch) - 1), fill='#e8efef')
                for x, k, _ in columns:
                    length = len(str(row[k])) * 4
                    d.line((x, y, x + length, y), fill=accent)
            elif pitch > 3:
                d.line((19, y, 491, y), fill='#e9ebe8')
        for x in (160, 251, 360):
            d.line((x, 112, x, 400), fill='#e4e7e6')
    return image

def place(canvas, sheet, count, box, closeup=False):
    x, y, scale = box
    image = make_paper(sheet, count, closeup)
    dimensions = (round(paper_width * scale), round(paper_height * scale))
    shadow = ImageDraw.Draw(canvas)
    shadow.rectangle((round(x) + 5, round(y) + 7,
                      round(x) + dimensions[0] + 5, round(y) + dimensions[1] + 7), fill='#11222c')
    canvas.paste(image.resize(dimensions, Image.Resampling.LANCZOS), (round(x), round(y)))

grid = [(208 + x * .54, 104 + y * .54, .54) for x, y in positions]
opening = (206, 106, 1.24)
opening_focus = (opening[0] + paper_width * opening[2] / 2, opening[1])
grid_focus = (grid[0][0] + paper_width * grid[0][2] / 2, grid[0][1])
assert len(set(source)) == 300
codes = [
    ['ws = wb.active'],
    ['return row[4] <= 0'],
    ['if expiry >= 3:', '    return False', '…', 'return class_match or', '       vendor_match or', '       channel_match'],
    ['sheet3_data = [r for r in', '    data_rows if not', '    is_outbound_loss(r) and', '    not is_warning(r)]'],
]
# Check the display's code fragments against the stored call.
assert ' '.join(codes[2][-3:]).replace('  ', ' ').split() == (
    'return class_match or vendor_match or channel_match'.split())
assert all(' '.join(codes[3]).split()[i] == word for i, word in enumerate(
    next(line for line in calls[3][2].splitlines() if line.startswith('sheet3_data =')).split()))

def side(d, headline, lines):
    d.rounded_rectangle((1051, 104, 1254, 625), 10, fill='#132531')
    label(d, (1064, 121), 'RECORDED CODE', 14, '#8dd8b9')
    label(d, (1064, 155), headline, 17, '#f1f5f5')
    mono = M(12)
    y = 192
    for line in lines:
        for piece in textwrap.wrap(line, 24) or ['']:
            d.text((1064, y), piece, font=mono if piece.isascii() else font(13), fill='#e7f0f2')
            y += 21

out = ROOT / 'drug-inventory-paper-replay.mp4'
args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]

with subprocess.Popen(args, stdin=subprocess.PIPE) as encoder:
    for frame in range(20 * FPS):
        t = frame / FPS
        canvas = Image.new('RGB', (W, H), '#203541')
        d = ImageDraw.Draw(canvas)
        label(d, (27, 15), 'CLOVER / WORKBUDDY OFFICE', 15, '#8dd8b9')
        label(d, (27, 40), 'Drug inventory split', 31, '#f1f5f5')
        tallies = counts.copy() if t >= 14 else [300, 0, 0, 0]
        head, code = 'Read the workbook', codes[0]

        if t < 4:
            amount = smooth((t - 1.8) / 1.7)
            scale = mix(opening[2], grid[0][2], amount)
            for i, (x, y) in enumerate(positions):
                box = (mix(opening_focus[0], grid_focus[0], amount)
                       + (x - positions[0][0] - paper_width / 2) * scale,
                       mix(opening_focus[1], grid_focus[1], amount)
                       + (y - positions[0][1]) * scale, scale)
                if i == 0 or amount > .02:
                    place(canvas, i, tallies[i], box)
        elif t < 14:
            group = min(2, int((t - 4) / (10 / 3)))
            elapsed = t - (4 + group * (10 / 3))
            dest = group + 1
            total = counts[dest]
            limits = [0, 1, 1 + (total - 1) // 2, total]
            wave_time = elapsed / 1.06
            wave = min(3, int(wave_time))
            phase = wave_time % 1
            batch = sheets[dest][limits[wave]:limits[wave + 1]] if wave < 3 else []
            arrived = phase >= .72
            landed = limits[wave + 1] if batch and arrived else limits[wave]
            tallies = [300] + [n if i < dest else landed if i == dest else 0
                              for i, n in enumerate(counts[1:], 1)]
            for i, box in enumerate(grid):
                place(canvas, i, tallies[i], box)
            head, code = english[dest], ['…'] + codes[dest] + ['…']
            if batch:
                sx, sy, scale = grid[0]
                dx, dy, _ = grid[dest]
                accent = accents[dest]
                # Color every source record in this batch at its actual paper position.
                highlights = Image.new('RGBA', canvas.size)
                marker = ImageDraw.Draw(highlights)
                for row in batch:
                    block, offset = divmod(source_index[row], 100)
                    left = sx + (23 + block * 158) * scale
                    top = sy + (118 + offset * 2.77) * scale
                    marker.rectangle((left, top - .5, left + 143 * scale, top + 1.5),
                                     fill=(244, 179, 53, 115))
                target_top = dy + (114 + 286 * limits[wave] / total) * scale
                target_bottom = dy + (114 + 286 * limits[wave + 1] / total) * scale
                if arrived:
                    marker.rectangle((dx + 19 * scale, target_top, dx + 491 * scale,
                                      max(target_top + 4, target_bottom)),
                                     fill=(113, 204, 155, 115), outline=accent)
                canvas.paste(highlights, (0, 0), highlights)

                # Keep real IDs readable at desk scale. The same slip holds at
                # the source, travels as a unit, and holds again over the landing range.
                progress = smooth((phase - .25) / .47)
                block, offset = divmod(source_index[batch[0]], 100)
                origin_x = sx + (23 + block * 158) * scale
                origin_y = sy + (118 + offset * 2.77) * scale
                tip_x = mix(origin_x, dx + 19 * scale, progress)
                tip_y = mix(origin_y, target_top, progress)
                x = mix(sx + 9, dx + 9, progress)
                y = mix(origin_y + 19, target_top + 19, progress)
                y = min(y, 544) - 28 * (4 * progress * (1 - progress))
                if progress in (0, 1):
                    d.line((tip_x, tip_y, x + 15, y), fill=accent, width=2)
                    d.ellipse((tip_x - 3, tip_y - 3, tip_x + 3, tip_y + 3), fill=accent)
                d.rounded_rectangle((x, y, x + 252, y + 57), 5,
                                    fill='#e4f5ea' if arrived else '#fff8df', outline=accent, width=2)
                phase_label = 'Landed' if arrived else 'Selected' if progress == 0 else 'Copying'
                label(d, (x + 8, y + 5), f'{phase_label}  ·  {len(batch)} ' +
                      ('row' if len(batch) == 1 else 'rows'), 13, accent)
                ids = batch[0][0] if len(batch) == 1 else f'{batch[0][0]}  …  {batch[-1][0]}'
                label(d, (x + 8, y + 28), ids, 13, '#172e40')
        else:
            amount = smooth((t - 14) / 1.65)
            if amount < 1:
                x, y, scale = grid[0]
                place(canvas, 0, 300, (x - 520 * amount, y - 350 * amount, scale))
            for i, (x, y) in enumerate(final_positions, 1):
                gx, gy, scale = grid[i]
                place(canvas, i, counts[i], (mix(gx, x, amount), mix(gy, y, amount),
                      mix(scale, .62, amount)), closeup=t >= 14.75)
            head = 'Reopen and verify'
            code = ['wb.save(out_path)', '', *results[calls[4][0]].splitlines()[1:]]
            if t >= 15.65:
                label(d, (38, 472), '60 + 200 + 40 = 300 records', 29, '#f1f5f5')
                label(d, (38, 516), '15 / 15 verifier checks passed', 23, '#8dd8b9')

        side(d, head, code)
        label(d, (27, 673), 'Saved WorkBuddy run  •  Paper layout, copy motion and timing reconstructed',
              15, '#bbcad2')
        encoder.stdin.write(canvas.tobytes())
    encoder.stdin.close()
    if encoder.wait():
        raise SystemExit('ffmpeg failed')
print(out)
