"""EOB3 monster extractor and pool manager for Dungeon Hack.

Extracts all 31 monsters from EOB3 EYE.RES VFX "1.10" shape tables:
  * Sword wraith, Undead beast, Feyr, Minotaur, Steel shadow, Scaladar,
  * Shadow, Hag, Chimera, Watch ghost, Ogre slug, Wyvern, Troll,
  * Grey pudding, Shadow wizard, Shadow warrior, Bone naga, Shambling mound,
  * Spirit naga, Groaning spirit, Death knight, Shadow hound, Water weird,
  * Earth elemental, Water elemental, Slithermorph, Grave mist, Lich,
  * Flar, Wight, Big evil bad guy.

Applies authentic per-monster palettes from EYE.RES, maps to DH pose order
[front, back, side_1, side_2, atk_1, atk_2] (indices [0, 3, 1, 2, 4, 5]),
and saves RGBA PNG frames (80x88) into pool/monsters/<name>/0.png..5.png.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
import aesop

POOL_MONSTERS = os.path.join(MASHUP, 'pool', 'monsters')

# Monster name -> (palette resource name, base offset)
PALETTE_MAP = {
    'Sword wraith': ('Sword wraith palette', 192),
    'Undead beast': ('Undead beast palette', 224),
    'Feyr': ('Feyr palette', 192),
    'Minotaur': ('Minotaur palette', 224),
    'Steel shadow': ('Steel shadow palette', 192),
    'Scaladar': ('Scaladar palette', 224),
    'Shadow': ('Shadow palette', 224),
    'Hag': ('Hag palette', 192),
    'Chimera': ('Chimera palette', 224),
    'Watch ghost': ('Watch ghost palette', 192),
    'Ogre slug': ('Ogre slug palette', 224),
    'Wyvern': ('Wyvern palette', 224),
    'Troll': ('Troll palette', 192),
    'Grey pudding': ('Grey pudding palette', 192),
    'Shadow wizard': ('Shadow palette', 224),
    'Shadow warrior': ('Shadow warrior palette', 224),
    'Bone naga': ('Bone naga palette', 192),
    'Shambling mound': ('Shambling mound palette', 224),
    'Spirit naga': ('Spirit naga palette', 192),
    'Groaning spirit': ('Groaning spirit palette', 224),
    'Death knight': ('Knights palette', 192),
    'Shadow hound': ('Shadow hound palette', 224),
    'Water weird': ('Water weird palette', 192),
    'Earth elemental': ('Slithermorph palette', 192),
    'Water elemental': ('Water elemental palette', 224),
    'Slithermorph': ('Slithermorph palette', 192),
    'Grave mist': ('Grave mist palette', 192),
    'Lich': ('Lich palette', 224),
    'Flar': ('Wight/Flar palette', 192),
    'Wight': ('Wight/Flar palette', 192),
    'Big evil bad guy': ('Big evil bad guy palette', 192),
}


def slugify(name):
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
    return f'eob3_{clean}'


def extract_all():
    os.makedirs(POOL_MONSTERS, exist_ok=True)
    eye_res_path = paths.get_game_file('eob3', 'EYE.RES')

    res = aesop.ResFile(eye_res_path)
    names = res.names()

    # Fixed base palette for fallback
    _, _, fpdata = res.entry(names['Fixed palette'])
    fn, frgb8, _ = aesop.decode_palette(fpdata)

    manifest = []
    all_frames = []

    for mon_name, (pal_name, base_off) in PALETTE_MAP.items():
        if mon_name not in names:
            print(f'Warning: {mon_name} not found in EYE.RES; skipping')
            continue
        if pal_name not in names:
            print(f'Warning: palette {pal_name} not found in EYE.RES; skipping')
            continue

        _, _, pdata = res.entry(names[pal_name])
        pn, prgb8, _ = aesop.decode_palette(pdata)

        _, _, mdata = res.entry(names[mon_name])
        shapes = aesop.decode_vfx110(mdata)
        if len(shapes) != 6:
            print(f'Warning: {mon_name} has {len(shapes)} frames instead of 6; skipping')
            continue

        raw_frames = []
        for w, h, px, mask, hdr in shapes:
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            for y in range(h):
                for x in range(w):
                    pos = y * w + x
                    if mask[pos]:
                        p = px[pos]
                        if p != 0:
                            idx = p - base_off
                            if 0 <= idx < pn:
                                rgba[y, x] = [prgb8[idx * 3], prgb8[idx * 3 + 1], prgb8[idx * 3 + 2], 255]
                            elif p < fn:
                                rgba[y, x] = [frgb8[p * 3], frgb8[p * 3 + 1], frgb8[p * 3 + 2], 255]
                            else:
                                rgba[y, x] = [200, 200, 200, 255]
            raw_frames.append(Image.fromarray(rgba, 'RGBA'))

        # Map EOB3 shape order [0:Front, 1:Side1, 2:Side2, 3:Back, 4:Atk1, 5:Atk2]
        # to DH order [0:Front, 1:Back, 2:Side1, 3:Side2, 4:Atk1, 5:Atk2]
        # Mapping indices: [0, 3, 1, 2, 4, 5]
        dh_frames = [raw_frames[0], raw_frames[3], raw_frames[1], raw_frames[2], raw_frames[4], raw_frames[5]]

        slug = slugify(mon_name)
        out_dir = os.path.join(POOL_MONSTERS, slug)
        os.makedirs(out_dir, exist_ok=True)
        img_paths = []
        for i, f in enumerate(dh_frames):
            fp = os.path.join(out_dir, f'{i}.png')
            f.save(fp)
            rel_p = os.path.relpath(fp, MASHUP)
            img_paths.append(rel_p)

        manifest.append({'name': slug, 'display_name': mon_name, 'images': img_paths})
        all_frames.append((slug, dh_frames))
        print(f'Extracted {mon_name} -> {slug}: 6 frames saved to {out_dir}')

    # Update pool.json
    pool_path = os.path.join(MASHUP, 'pool', 'pool.json')
    if os.path.exists(pool_path):
        pool = json.load(open(pool_path))
        existing_names = {m['name'] for m in pool.get('monsters', [])}
        added = 0
        for m in manifest:
            if m['name'] not in existing_names:
                pool['monsters'].append({'name': m['name'], 'images': m['images']})
                added += 1
        json.dump(pool, open(pool_path, 'w'), indent=1)
        print(f'Updated {pool_path} (+{added} EOB3 monsters, total in pool: {len(pool["monsters"])})')

    # Build master review contact sheet
    if all_frames:
        sheet_w = 6 * 85 + 160
        sheet_h = len(all_frames) * 96 + 30
        sheet = Image.new('RGB', (sheet_w, sheet_h), (25, 28, 32))
        draw = ImageDraw.Draw(sheet)
        poses = ['Front', 'Back', 'Side 1', 'Side 2', 'Atk 1', 'Atk 2']

        # Header
        for c, p in enumerate(poses):
            draw.text((160 + c * 85 + 15, 8), p, fill=(220, 220, 100))

        for r, (slug, frames) in enumerate(all_frames):
            y = 30 + r * 96
            # Label
            draw.text((8, y + 35), slug.replace('eob3_', ''), fill=(240, 240, 240))
            for c, f in enumerate(frames):
                x = 160 + c * 85
                draw.rectangle([x, y, x + 80, y + 88], outline=(45, 50, 55))
                # Paste sprite
                sheet.paste(f, (x, y), f)

        sheet_path = os.path.join(POOL_MONSTERS, 'eob3_monsters_sheet.png')
        sheet.save(sheet_path)
        print(f'Saved EOB3 monsters contact sheet to {sheet_path}')

    return manifest


if __name__ == '__main__':
    extract_all()
