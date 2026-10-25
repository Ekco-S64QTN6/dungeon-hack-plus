"""EOB1 and EOB2 monster extractor and pool manager for Dungeon Hack.

Extracts classic D&D monsters from Westwood .CPS sheets:
  * eob1_kobold    (KOBOLD.CPS)
  * eob1_skeleton  (SKELETON.CPS)
  * eob1_zombie    (ZOMBIE.CPS)
  * eob1_kuotoa    (KUOTOA.CPS)
  * eob1_kenku     (KENKU.CPS)
  * eob1_disbeast  (DISBEAST.CPS)
  * eob1_mflayer   (MFLAYER.CPS)
  * eob1_hellhound (HELLHND.CPS)
  * eob2_wolf      (WOLF.CPS)

Applies authentic per-level palettes, extracts the 6 standard poses
[front, back, side_left, side_right, atk1, atk2], and saves ready-to-use
RGBA PNG frames into pool/monsters/<name>/0.png..5.png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
import westwood
import normalize

POOL_MONSTERS = os.path.join(MASHUP, 'pool', 'monsters')


# EOB monster frame rectangles (x, y, w, h), identical in EOB1 and EOB2 (ScummVM create_kyradat
# kEoB1/kEoB2EncodeMonsterDefsDOS, layouts at entries 0/18/36). EOB order: front, side, side, back, atk, atk.
EOB_LAYOUTS = [
    [(0, 0, 56, 96), (56, 40, 96, 56), (152, 40, 96, 56), (248, 0, 56, 96), (0, 96, 56, 96), (56, 96, 56, 96)],
    [(0, 0, 56, 96), (56, 0, 56, 96), (112, 0, 56, 96), (168, 0, 56, 96), (224, 0, 56, 96), (0, 96, 56, 96)],
    [(0, 0, 80, 88), (80, 0, 80, 88), (160, 0, 80, 88), (240, 0, 80, 88), (0, 88, 80, 88), (80, 88, 80, 88)],
]
DH_FROM_EOB = [0, 3, 1, 2, 4, 5]      # DH [front, back, side, side, atk1, atk2] <- EOB frame index


LAYOUTS_FILE = os.path.join(HERE, 'eob_monster_layouts.json')   # from LEVEL*.INF / *.ELO (authoritative)


def exact_frames(im_rgb, layout=None):
    """Cut the 6 frames with EOB's own rectangles. The layout is the one whose rectangles cover the
    most sprite pixels (ties -> fewest rectangles left empty). Frames are scaled by ONE factor (so a
    crouch stays smaller than a stand) and anchored bottom-centre in 80x88, DH's monster frame."""
    arr = np.asarray(im_rgb.convert('RGB'))
    fg = np.any(arr != 0, axis=2)
    best = None
    for L, rects in enumerate(EOB_LAYOUTS):
        cover = np.zeros_like(fg)
        filled = 0
        for x, y, w, h in rects:
            cover[y:y + h, x:x + w] = True
            filled += fg[y:y + h, x:x + w].any()
        score = (fg & cover).sum() / max(1, fg.sum()) + 0.01 * filled
        if best is None or score > best[0]:
            best = (score, L, rects)
    _, L, rects = best
    if layout is not None:                  # authoritative layout from the level scripts
        L, rects = layout, EOB_LAYOUTS[layout]
    sc = min(80 / max(w for _, _, w, _ in rects), 88 / max(h for _, _, _, h in rects), 1.0)
    out = []
    for k in DH_FROM_EOB:
        x, y, w, h = rects[k]
        a = arr[y:y + h, x:x + w]
        alpha = (np.any(a != 0, axis=2) * 255).astype(np.uint8)
        fr = Image.fromarray(np.dstack([a, alpha]), 'RGBA')
        if sc < 1.0:
            fr = fr.resize((max(1, round(w * sc)), max(1, round(h * sc))), Image.LANCZOS)
        canvas = Image.new('RGBA', (80, 88), (0, 0, 0, 0))
        canvas.alpha_composite(fr, ((80 - fr.width) // 2, 88 - fr.height))
        out.append(canvas)
    return out, L


def slice_monster_sheet(im, reach=1):
    """Find the 6 standard monster sprite boxes ordered by [front, back, side_l, side_r, atk1, atk2]."""
    arr = np.asarray(im.convert('RGB'))
    fg = np.any(arr != 0, axis=2)
    seen = np.zeros_like(fg)
    boxes = []

    for y0 in range(200):
        for x0 in range(320):
            if fg[y0, x0] and not seen[y0, x0]:
                stack = [(y0, x0)]
                seen[y0, x0] = True
                ys, xs = [], []
                while stack:
                    y, x = stack.pop()
                    ys.append(y); xs.append(x)
                    for dy in range(-reach, reach + 1):
                        for dx in range(-reach, reach + 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < 200 and 0 <= nx < 320 and fg[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((ny, nx))
                if len(ys) >= 150:
                    boxes.append((min(ys), max(ys), min(xs), max(xs)))

    # Drop small extras (spell icons, eye rays) and keep the 6 largest pose sprites
    if boxes:
        area = lambda b: (b[1] - b[0] + 1) * (b[3] - b[2] + 1)
        big = max(area(b) for b in boxes)
        boxes = [b for b in boxes if area(b) >= 0.2 * big]
        if len(boxes) > 6:
            boxes = sorted(boxes, key=area, reverse=True)[:6]

    # Sort into top row (5 boxes) and bottom row (attack frame)
    # y // 100 separates row 0 and row 1
    boxes.sort(key=lambda b: (b[0] // 100, b[2]))

    crops = []
    for y0, y1, x0, x1 in boxes:
        sub = im.crop((x0, y0, x1 + 1, y1 + 1)).convert('RGBA')
        # Mask out black background
        data = np.asarray(sub)
        rgb = data[..., :3]
        alpha = np.where(np.any(rgb != 0, axis=2), 255, 0).astype(np.uint8)
        crops.append(Image.fromarray(np.dstack([rgb, alpha]), mode='RGBA'))

    # Top row has 5 poses: Front (0), SideL (1), SideR (2), Back (3), Atk1 (4)
    # Bottom row has Atk2 (5)
    # Map to DH: [front, back, side_l, side_r, atk1, atk2]
    # Corresponding box indices: [0, 3, 1, 2, 4, 5]
    if len(crops) >= 6:
        dh_order = [crops[0], crops[3], crops[1], crops[2], crops[4], crops[5]]
        return dh_order

    return crops


def extract_all():
    os.makedirs(POOL_MONSTERS, exist_ok=True)
    eob1_dir = paths.get_game_dir('eob1')
    eob2_dir = paths.get_game_dir('eob2')

    # EOB1: global EOBPAL.COL below 0xE0 + the level band (level .PALs hold saturated junk below 0xE0)
    pal1_blue = westwood.eob1_palette(eob1_dir, 'BLUE.PAL')
    pal1_green = westwood.eob1_palette(eob1_dir, 'GREEN.PAL')
    pal1_drow = westwood.eob1_palette(eob1_dir, 'DROW.PAL')
    pal1_brick = westwood.eob1_palette(eob1_dir, 'BRICK.PAL')
    pal2_dung = westwood.read_pal(os.path.join(eob2_dir, 'DUNG.PAL'))

    monsters = [
        ('eob1_kobold',   eob1_dir, 'KOBOLD.CPS',   pal1_blue),
        ('eob1_skeleton', eob1_dir, 'SKELETON.CPS', pal1_blue),
        ('eob1_zombie',   eob1_dir, 'ZOMBIE.CPS',   pal1_blue),
        ('eob1_kuotoa',   eob1_dir, 'KUOTOA.CPS',   pal1_blue),
        ('eob1_kenku',    eob1_dir, 'KENKU.CPS',    pal1_green),
        ('eob1_disbeast', eob1_dir, 'DISBEAST.CPS', pal1_drow),
        ('eob1_mflayer',  eob1_dir, 'MFLAYER.CPS',  pal1_brick),
        ('eob1_hellhound',eob1_dir, 'HELLHND.CPS',  pal1_brick),
        ('eob2_wolf',     eob2_dir, 'WOLF.CPS',     pal2_dung),
    ] + [('eob1_' + nm.lower(), eob1_dir, nm + '.CPS', pal1_blue) for nm in (
        'DROWELF', 'DWARF', 'FLIND', 'GOLEM', 'LEECH', 'MAGE', 'MANTIS', 'SHINDIA', 'SKELWAR')
    ] + [('eob2_' + nm.lower(), eob2_dir, nm + '.CPS', pal2_dung) for nm in (
        'ANT', 'ASERVANT', 'BASILISK', 'BEHOLDER', 'BULETTE', 'CLERIC1', 'CLERIC2', 'CLERIC3', 'FRGIANT',
        'FSNAKE', 'GARGOYLE', 'GASSPORE', 'GUARD1', 'GUARD2', 'GUARDIAN', 'MAGE', 'MANTIS', 'MEDUSA',
        'MINDFLAY', 'SPIDER', 'WASP', 'WILLOWIS', 'CUBE', 'SALAMNDR', 'SKELWAR', 'HELLHND')]
    layouts = json.load(open(LAYOUTS_FILE)) if os.path.exists(LAYOUTS_FILE) else {}

    manifest = []
    all_frames = []

    for name, d, fn, pal in monsters:
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            continue
        px, _ = westwood.unpack(p)
        im = Image.frombytes('P', (320, 200), bytes(px[:64000]))
        im.putpalette(pal)

        key = name.split('_')[0] + '_' + fn[:-4].lower()        # e.g. eob1_hellhound -> eob1_hellhnd
        frames, layout = exact_frames(im, layouts.get(key))
        if len(frames) != 6:
            print(f'Warning: {name} produced {len(frames)} frames instead of 6; skipping')
            continue

        out_dir = os.path.join(POOL_MONSTERS, name)
        os.makedirs(out_dir, exist_ok=True)
        img_paths = []
        for i, f in enumerate(frames):
            fp = os.path.join(out_dir, f'{i}.png')
            f.save(fp)
            rel_p = os.path.relpath(fp, MASHUP)
            img_paths.append(rel_p)

        manifest.append({'name': name, 'images': img_paths})
        all_frames.append((name, frames))
        print(f'Extracted {name}: 6 frames saved to {out_dir}')

    # Update pool.json with the new monsters
    pool_path = os.path.join(MASHUP, 'pool', 'pool.json')
    if os.path.exists(pool_path):
        pool = json.load(open(pool_path))
        existing_names = {m['name'] for m in pool.get('monsters', [])}
        for m in manifest:
            if m['name'] not in existing_names:
                pool['monsters'].append(m)
        json.dump(pool, open(pool_path, 'w'), indent=1)
        print(f'Updated {pool_path} (total monsters in pool: {len(pool["monsters"])})')

    # Build review contact sheet
    if all_frames:
        sheet_w = 6 * 85 + 140
        sheet_h = len(all_frames) * 100 + 20
        sheet = Image.new('RGB', (sheet_w, sheet_h), (25, 28, 32))
        draw = ImageDraw.Draw(sheet)
        poses = ['Front', 'Back', 'Side L', 'Side R', 'Atk 1', 'Atk 2']

        # Header
        for c, p in enumerate(poses):
            draw.text((140 + c * 85 + 10, 5), p, fill=(220, 220, 100))

        for r, (name, frames) in enumerate(all_frames):
            y = 25 + r * 100
            draw.text((10, y + 35), name, fill=(240, 240, 240))
            for c, f in enumerate(frames):
                x = 140 + c * 85
                draw.rectangle([x, y, x + 80, y + 90], outline=(45, 50, 55))
                # Centre sprite at bottom
                cw, ch = f.size
                px = x + (80 - cw) // 2
                py = y + (90 - ch)
                sheet.paste(f, (px, py), f)

        sheet_path = os.path.join(POOL_MONSTERS, 'monsters_sheet.png')
        sheet.save(sheet_path)
        print(f'Saved monster review sheet to {sheet_path}')

    return manifest


if __name__ == '__main__':
    extract_all()
