"""Portrait extraction and management for Dungeon Hack.

Extracts 31x32 character portraits from:
  * EOB1: CHARGENA.CPS (44 portraits)
  * EOB2: CHARGENA.CPS (50 portraits)
  * EOB3: CHARPICS.BMP (90 portraits in AESOP old_shapes) and EYE.RES (82 portraits)

Maps them to Dungeon Hack's 45 portrait slots ('Portrait 0' .. 'Portrait 44')
using DH's fixed palette (0..223).
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
POOL_PORTRAITS = os.path.join(MASHUP, 'pool', 'portraits')


def extract_all():
    """Extract and quantize portraits from EOB1, EOB2, EOB3 to pool/portraits/."""
    os.makedirs(POOL_PORTRAITS, exist_ok=True)
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

    # 1. EOB1 portraits
    eob1_dir = paths.get_game_dir('eob1')
    eob1_cps = os.path.join(eob1_dir, 'CHARGENA.CPS')
    eob1_pal = westwood.read_pal(os.path.join(eob1_dir, cfg['games']['eob1'].get('default_pal', 'EOBPAL.COL')))
    if os.path.exists(eob1_cps):
        px, _ = westwood.unpack(eob1_cps)
        arr = np.asarray(Image.frombytes('P', (320, 200), bytes(px[:64000])))
        pal_rgb = np.array(eob1_pal, dtype=np.uint8).reshape(-1, 3)
        idx = 0
        for r in range(5):
            for c in range(10):
                x = 1 + c * 32
                y = r * 32
                cell = arr[y:y + 32, x:x + 31]
                if not np.any(cell != 0):
                    continue
                rgb = pal_rgb[cell]
                quant = normalize.quantize_fixed(rgb, dh_base, allowed)
                # Save as PNG
                im = Image.fromarray(quant, mode='P')
                im.putpalette(dh_base)
                fn = f'eob1_{idx:02d}.png'
                im.save(os.path.join(POOL_PORTRAITS, fn))
                catalog.append({'id': f'eob1_{idx:02d}', 'game': 'eob1', 'file': fn, 'size': [31, 32]})
                idx += 1
        print(f'Extracted {idx} EOB1 portraits')

    # 2. EOB2 portraits
    eob2_dir = paths.get_game_dir('eob2')
    eob2_cps = os.path.join(eob2_dir, 'CHARGENA.CPS')
    eob2_pal = westwood.read_pal(os.path.join(eob2_dir, cfg['games']['eob2'].get('default_pal', 'DUNG.PAL')))
    if os.path.exists(eob2_cps):
        px, _ = westwood.unpack(eob2_cps)
        arr = np.asarray(Image.frombytes('P', (320, 200), bytes(px[:64000])))
        pal_rgb = np.array(eob2_pal, dtype=np.uint8).reshape(-1, 3)
        idx = 0
        for r in range(5):
            for c in range(10):
                x = 1 + c * 32
                y = r * 32
                cell = arr[y:y + 32, x:x + 31]
                if not np.any(cell != 0):
                    continue
                rgb = pal_rgb[cell]
                quant = normalize.quantize_fixed(rgb, dh_base, allowed)
                im = Image.fromarray(quant, mode='P')
                im.putpalette(dh_base)
                fn = f'eob2_{idx:02d}.png'
                im.save(os.path.join(POOL_PORTRAITS, fn))
                catalog.append({'id': f'eob2_{idx:02d}', 'game': 'eob2', 'file': fn, 'size': [31, 32]})
                idx += 1
        print(f'Extracted {idx} EOB2 portraits')

    # 3. EOB3 portraits (CHARPICS.BMP)
    eob3_dir = paths.get_game_dir('eob3')
    eob3_charpics = os.path.join(eob3_dir, 'CHARGEN', 'CHARPICS.BMP')
    eob3_pal_file = os.path.join(eob3_dir, 'CHARGEN', 'PALETTE.COL')
    if os.path.exists(eob3_charpics) and os.path.exists(eob3_pal_file):
        e3_pal = westwood.read_pal(eob3_pal_file)
        pal_rgb = np.array(e3_pal, dtype=np.uint8).reshape(-1, 3)
        sh = aesop.decode_shapes(open(eob3_charpics, 'rb').read())
        idx = 0
        for w, h, px_bytes, mask_bytes in sh:
            if (w, h) != (31, 32):
                continue
            cell = np.frombuffer(px_bytes, dtype=np.uint8).reshape(h, w)
            rgb = pal_rgb[cell]
            quant = normalize.quantize_fixed(rgb, dh_base, allowed)
            im = Image.fromarray(quant, mode='P')
            im.putpalette(dh_base)
            fn = f'eob3_{idx:02d}.png'
            im.save(os.path.join(POOL_PORTRAITS, fn))
            catalog.append({'id': f'eob3_{idx:02d}', 'game': 'eob3', 'file': fn, 'size': [31, 32]})
            idx += 1
        print(f'Extracted {idx} EOB3 portraits')

    # Save catalog
    json.dump(catalog, open(os.path.join(POOL_PORTRAITS, 'catalog.json'), 'w'), indent=2)

    # Render contact sheet
    if catalog:
        cols = 15
        rows = (len(catalog) + cols - 1) // cols
        sheet_w = cols * 35
        sheet_h = rows * 44
        sheet = Image.new('RGB', (sheet_w, sheet_h), (32, 32, 32))
        draw = ImageDraw.Draw(sheet)
        for i, item in enumerate(catalog):
            c = i % cols
            r = i // cols
            p_im = Image.open(os.path.join(POOL_PORTRAITS, item['file'])).convert('RGB')
            sheet.paste(p_im, (c * 35 + 2, r * 44 + 10))
            draw.text((c * 35 + 2, r * 44), item['id'], fill=(200, 200, 200))
        sheet.save(os.path.join(POOL_PORTRAITS, 'portraits_sheet.png'))
        print(f'Saved contact sheet with {len(catalog)} portraits to {os.path.join(POOL_PORTRAITS, "portraits_sheet.png")}')

    return catalog


if __name__ == '__main__':
    extract_all()
