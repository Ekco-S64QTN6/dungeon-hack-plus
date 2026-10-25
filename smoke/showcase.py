"""Showcase image of Dungeon Hack+ matchups from real in-game captures (walker shots).

  python3 -I smoke/showcase.py SPEC.json OUT.png
SPEC: {"title": ..., "subtitle": ..., "note": ..., "cols": 4,
       "tiles": [{"shot": "smoke_runs/walks/<plan>/<build>/<shot>.png", "game": "eob1|eob2|eob3|menzo|dh",
                  "name": "Waterdeep sewers", "what": "its own pit"}, ...]}
Each tile is the 3D view (walker.VIEW) at 2x nearest-neighbour, framed, with a source-game badge.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
VIEW = (276, 31, 628, 320)                    # walker.VIEW as a PIL box
FONT = '/usr/share/fonts/noto/NotoSerif-%s.ttf'
GAMES = {'eob1': ('EYE OF THE BEHOLDER', (90, 140, 230)), 'eob2': ('EOB II: LEGEND OF DARKMOON', (80, 175, 110)),
         'eob3': ('EOB III: MYTH DRANNOR', (170, 110, 210)), 'menzo': ('MENZOBERRANZAN', (215, 85, 70)),
         'dh': ('DUNGEON HACK', (200, 170, 90))}
GOLD, INK, BG = (226, 186, 104), (230, 224, 210), (14, 11, 16)


def font(style, size):
    try:
        return ImageFont.truetype(FONT % style, size)
    except OSError:
        return ImageFont.load_default()


def main(spec_path, out):
    spec = json.load(open(spec_path))
    cols, scale, gap, pad = spec.get('cols', 4), 2, 36, 70
    tw, th = (VIEW[2] - VIEW[0]) * scale, (VIEW[3] - VIEW[1]) * scale
    cap = 96
    rows = (len(spec['tiles']) + cols - 1) // cols
    head = 300
    W = pad * 2 + cols * tw + (cols - 1) * gap
    H = head + rows * (th + cap) + (rows - 1) * gap + pad + 40
    img = Image.new('RGB', (W, H), BG)
    # soft warm glow behind the title
    glow = Image.new('L', (W, H), 0); ImageDraw.Draw(glow).ellipse((W * 0.2, -260, W * 0.8, 360), fill=70)
    img = Image.composite(Image.new('RGB', (W, H), (60, 38, 20)), img, glow.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    tf, sf, nf = font('Bold', 118), font('Italic', 40), font('Regular', 28)
    for dx, dy, col in ((5, 6, (0, 0, 0)), (0, 0, GOLD)):
        d.text((W // 2 + dx, 120 + dy), spec['title'], font=tf, fill=col, anchor='mm')
    d.text((W // 2, 210), spec['subtitle'], font=sf, fill=INK, anchor='mm')
    d.text((W // 2, 258), spec.get('note', ''), font=nf, fill=(160, 150, 140), anchor='mm')
    bf, nmf, wf = font('Bold', 22), font('Bold', 34), font('Italic', 28)
    for i, t in enumerate(spec['tiles']):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + gap), head + r * (th + cap + gap)
        shot = Image.open(os.path.join(ROOT, t['shot'])).convert('RGB').crop(VIEW).resize((tw, th), Image.NEAREST)
        d.rectangle((x - 6, y - 6, x + tw + 5, y + th + 5), fill=(0, 0, 0))
        d.rectangle((x - 4, y - 4, x + tw + 3, y + th + 3), outline=GOLD, width=2)
        img.paste(shot, (x, y))
        label, colour = GAMES[t['game']]
        bw = d.textlength(label, font=bf) + 24
        d.rounded_rectangle((x + 12, y + 12, x + 12 + bw, y + 46), radius=8, fill=colour)
        d.text((x + 24, y + 29), label, font=bf, fill=(255, 255, 255), anchor='lm')
        d.text((x, y + th + 16), t['name'], font=nmf, fill=GOLD)
        d.text((x, y + th + 58), t['what'], font=wf, fill=INK)
    foot = spec.get('footer')
    if foot:
        d.text((W // 2, H - 34), foot, font=font('Italic', 26), fill=(120, 112, 104), anchor='mm')
    img.save(out)
    print('%s: %dx%d' % (out, W, H))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
