"""Item icon extraction and management for Dungeon Hack.

Extracts 16x16 item icons from:
  * EOB1: ITEMICN.CPS (89 icons)
  * EOB2: ITEMICN.CPS (110 icons)
  * EOB3: ITEMICN.CPS (110 icons)

Pads/centers each icon into 17x17 (matching DH's exact Icon 00..248 dimensions)
and quantizes to Dungeon Hack's fixed palette (0..223).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths
import aesop
import normalize
import westwood

MASHUP = os.path.dirname(HERE)
POOL_ICONS = os.path.join(MASHUP, 'pool', 'icons')


def extract_all():
    """Extract and quantize item icons from EOB1, EOB2, EOB3 to pool/icons/."""
    os.makedirs(POOL_ICONS, exist_ok=True)
    cfg = json.load(open(os.path.join(MASHUP, 'config.json')))
    root = os.path.normpath(os.path.join(MASHUP, cfg['root']))

    # Load DH base palette
    dh_res = aesop.ResFile(os.path.join(root, cfg['dh_install'], 'HACK.RES'))
    _, dh_base, _ = aesop.decode_palette(dh_res.entry(dh_res.names()['Main Base Palette'])[2])
    pal_json = os.path.join(MASHUP, 'work', 'aesop', 'dh_palette.json')
    if os.path.exists(pal_json):
        meta = json.load(open(pal_json))
        allowed = set(meta.get('monster_indices', range(1, 224)))
    else:
        allowed = set(range(1, 224))

    catalog = []

    sources = [
        ('eob1', 'Forgotten Realms The Archives - Collection One/games/Eye of the Beholder DE/GAME/EYE',
         'ITEMICN.CPS', 'EOBPAL.COL'),
        ('eob2', 'Forgotten Realms The Archives - Collection One/games/Eye of the Beholder II - EN/GAME/DARKMOON',
         'ITEMICN.CPS', 'DUNG.PAL'),
        ('eob3', 'Forgotten Realms The Archives - Collection One/games/Eye of the Beholder III/GAME/EOB3/CHARGEN',
         'ITEMICN.CPS', 'PALETTE.COL'),
    ]

    for game, rel_dir, cps_fn, pal_fn in sources:
        base_dir = os.path.join(root, rel_dir)
        cps_path = os.path.join(base_dir, cps_fn)
        pal_path = os.path.join(base_dir, pal_fn)
        if not os.path.exists(cps_path) or not os.path.exists(pal_path):
            continue

        pal = westwood.read_pal(pal_path)
        pal_rgb = np.array(pal, dtype=np.uint8).reshape(-1, 3)
        px, _ = westwood.unpack(cps_path)
        arr = np.frombuffer(px[:64000], dtype=np.uint8).reshape(200, 320)

        idx = 0
        for r in range(12):
            for c in range(20):
                cell = arr[r * 16:(r + 1) * 16, c * 16:(c + 1) * 16]
                if not np.any(cell != 0):
                    continue
                # 16x16 cell -> RGB
                rgb_16 = pal_rgb[cell]
                mask_16 = (cell != 0)

                # Quantize to DH fixed palette
                quant_16 = normalize.quantize_fixed(rgb_16, dh_base, allowed)

                # Place into 17x17 canvas (index 0 = transparent)
                canvas = np.zeros((17, 17), dtype=np.uint8)
                canvas[0:16, 0:16] = np.where(mask_16, quant_16, 0)

                # Save as indexed PNG with transparency on index 0
                im = Image.fromarray(canvas, mode='P')
                im.putpalette(dh_base)
                im.info['transparency'] = 0

                fn = f'{game}_icon_{idx:03d}.png'
                im.save(os.path.join(POOL_ICONS, fn))
                catalog.append({'id': f'{game}_{idx:03d}', 'game': game, 'file': fn, 'size': [17, 17]})
                idx += 1

        print(f'Extracted {idx} {game} icons (17x17)')

    json.dump(catalog, open(os.path.join(POOL_ICONS, 'catalog.json'), 'w'), indent=2)

    # Render contact sheet
    if catalog:
        cols = 20
        rows = (len(catalog) + cols - 1) // cols
        sheet_w = cols * 24
        sheet_h = rows * 28
        sheet = Image.new('RGB', (sheet_w, sheet_h), (24, 24, 28))
        draw = ImageDraw.Draw(sheet)
        for i, item in enumerate(catalog):
            c = i % cols
            r = i // cols
            p_im = Image.open(os.path.join(POOL_ICONS, item['file'])).convert('RGB')
            sheet.paste(p_im, (c * 24 + 3, r * 28 + 2))
            draw.text((c * 24 + 1, r * 28 + 19), f'{i:03d}', fill=(140, 140, 140))
        sheet_path = os.path.join(POOL_ICONS, 'icons_sheet.png')
        sheet.save(sheet_path)
        print(f'Saved contact sheet with {len(catalog)} icons to {sheet_path}')

    return catalog


if __name__ == '__main__':
    extract_all()
