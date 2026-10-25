"""Level map and automap renderer for Dungeon Hack savegames.

Parses LEVELS.DAT (seed + 10x 32x32 grids) and FEA%02d.DAT (feature records:
party start, doors, stairs, illusionary walls, decorations, monsters) and
renders high-resolution maps with coordinate grids, statistics, and legends.

Usage:
  python3 -I mashup/tools/map_renderer.py [SAVEGAME_DIR] [LEVEL]
  python3 -I mashup/tools/map_renderer.py --all [SAVEGAME_DIR]
"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)

CELL_SIZE = 18
FEATURE_NAMES = {
    0: ('Start', (0, 230, 120), 'circle'),
    1: ('Door', (230, 140, 40), 'rect'),
    2: ('Door Button', (255, 200, 50), 'dot'),
    3: ('Illusion Wall', (80, 220, 240), 'dashed_rect'),
    4: ('Stairs Up', (60, 160, 255), 'triangle_up'),
    5: ('Stairs Down', (255, 60, 60), 'triangle_down'),
    6: ('Pit / Trap', (180, 40, 220), 'diamond'),
    8: ('Teleporter', (240, 100, 200), 'ring'),
    9: ('Spinner', (255, 180, 0), 'cross'),
    12: ('Monster', (220, 50, 80), 'dot'),
    16: ('Wall Deco', (160, 120, 200), 'small_dot'),
}


def load_dungeon(sg_dir):
    """Load dungeon seed, level grids, and features from a savegame directory."""
    levels_path = os.path.join(sg_dir, 'LEVELS.DAT')
    if not os.path.exists(levels_path):
        raise FileNotFoundError(f'Missing LEVELS.DAT in {sg_dir}')

    raw = open(levels_path, 'rb').read()
    seed = struct.unpack('<I', raw[:4])[0]
    num_levels = (len(raw) - 4) // 1024

    levels = []
    for lv in range(num_levels):
        grid = raw[4 + lv * 1024: 4 + (lv + 1) * 1024]
        fea_path = os.path.join(sg_dir, f'FEA{lv:02d}.DAT')
        recs = []
        if os.path.exists(fea_path):
            f_bytes = open(fea_path, 'rb').read()
            recs = [f_bytes[i:i + 8] for i in range(0, len(f_bytes), 8) if any(f_bytes[i:i + 8])]
        levels.append({'level': lv, 'grid': grid, 'features': recs})

    return seed, levels


def render_level(seed, level_data, out_path):
    """Render a single 32x32 dungeon level to PNG."""
    lv = level_data['level']
    grid = level_data['grid']
    recs = level_data['features']

    # Dimensions
    grid_px = 32 * CELL_SIZE
    offset_x = 36
    offset_y = 36
    sidebar_w = 200
    total_w = offset_x + grid_px + sidebar_w
    total_h = offset_y + grid_px + 36

    im = Image.new('RGB', (total_w, total_h), (18, 20, 24))
    draw = ImageDraw.Draw(im)

    # 1. Coordinate headers
    for i in range(32):
        # Top coordinate numbers
        draw.text((offset_x + i * CELL_SIZE + 4, 16), f'{i:02d}', fill=(120, 130, 140))
        # Left coordinate numbers
        draw.text((12, offset_y + i * CELL_SIZE + 4), f'{i:02d}', fill=(120, 130, 140))

    # 2. Tiles
    open_count = 0
    wall_count = 0
    for y in range(32):
        for x in range(32):
            tile = grid[y * 32 + x]
            rx = offset_x + x * CELL_SIZE
            ry = offset_y + y * CELL_SIZE
            if tile == 0xFF:
                open_count += 1
                draw.rectangle([rx, ry, rx + CELL_SIZE - 1, ry + CELL_SIZE - 1],
                               fill=(45, 50, 56), outline=(35, 40, 45))
            elif tile in (0, 1):
                wall_count += 1
                shade = (105, 100, 95) if tile == 0 else (118, 112, 106)
                draw.rectangle([rx, ry, rx + CELL_SIZE - 1, ry + CELL_SIZE - 1],
                               fill=shade, outline=(70, 66, 62))
            else:
                draw.rectangle([rx, ry, rx + CELL_SIZE - 1, ry + CELL_SIZE - 1], fill=(12, 14, 16))

    # Outer border around grid
    draw.rectangle([offset_x - 1, offset_y - 1, offset_x + grid_px, offset_y + grid_px], outline=(140, 150, 160))

    # 3. Features
    counts = {}
    for r in recs:
        typ = r[0]
        counts[typ] = counts.get(typ, 0) + 1
        fx = offset_x + r[1] * CELL_SIZE
        fy = offset_y + r[2] * CELL_SIZE
        info = FEATURE_NAMES.get(typ)
        if not info:
            continue
        name, color, shape = info

        if shape == 'circle':
            draw.ellipse([fx + 2, fy + 2, fx + CELL_SIZE - 3, fy + CELL_SIZE - 3], fill=color, outline=(255, 255, 255))
        elif shape == 'rect':
            draw.rectangle([fx + 3, fy + 3, fx + CELL_SIZE - 4, fy + CELL_SIZE - 4], fill=color, outline=(255, 220, 180))
        elif shape == 'dot':
            draw.ellipse([fx + 5, fy + 5, fx + CELL_SIZE - 6, fy + CELL_SIZE - 6], fill=color)
        elif shape == 'small_dot':
            draw.rectangle([fx + 7, fy + 7, fx + CELL_SIZE - 8, fy + CELL_SIZE - 8], fill=color)
        elif shape == 'dashed_rect':
            draw.rectangle([fx + 2, fy + 2, fx + CELL_SIZE - 3, fy + CELL_SIZE - 3], outline=color, fill=(30, 60, 70))
        elif shape == 'triangle_up':
            pts = [(fx + 2, fy + CELL_SIZE - 3), (fx + CELL_SIZE - 3, fy + CELL_SIZE - 3), (fx + CELL_SIZE // 2, fy + 2)]
            draw.polygon(pts, fill=color, outline=(200, 230, 255))
        elif shape == 'triangle_down':
            pts = [(fx + 2, fy + 2), (fx + CELL_SIZE - 3, fy + 2), (fx + CELL_SIZE // 2, fy + CELL_SIZE - 3)]
            draw.polygon(pts, fill=color, outline=(255, 200, 200))
        elif shape == 'diamond':
            pts = [(fx + CELL_SIZE // 2, fy + 2), (fx + CELL_SIZE - 3, fy + CELL_SIZE // 2),
                   (fx + CELL_SIZE // 2, fy + CELL_SIZE - 3), (fx + 2, fy + CELL_SIZE // 2)]
            draw.polygon(pts, fill=color)

    # 4. Sidebar Stats and Legend
    sx = offset_x + grid_px + 18
    sy = offset_y

    draw.text((sx, sy), 'DUNGEON HACK', fill=(255, 215, 0))
    draw.text((sx, sy + 18), f'Seed: 0x{seed:08X}', fill=(180, 200, 220))
    draw.text((sx, sy + 34), f'Level {lv:02d} / 09', fill=(240, 240, 240))
    draw.line([(sx, sy + 54), (sx + 170, sy + 54)], fill=(60, 70, 80))

    sy += 64
    draw.text((sx, sy), 'Statistics:', fill=(255, 255, 255))
    sy += 18
    draw.text((sx, sy), f'Corridors: {open_count} ({open_count*100//1024}%)', fill=(180, 180, 180)); sy += 16
    draw.text((sx, sy), f'Walls:     {wall_count} ({wall_count*100//1024}%)', fill=(180, 180, 180)); sy += 16
    draw.text((sx, sy), f'Doors:     {counts.get(1, 0)}', fill=(180, 180, 180)); sy += 16
    draw.text((sx, sy), f'Secrets:   {counts.get(3, 0)}', fill=(180, 180, 180)); sy += 16
    draw.text((sx, sy), f'Features:  {len(recs)}', fill=(180, 180, 180)); sy += 24

    draw.line([(sx, sy), (sx + 170, sy)], fill=(60, 70, 80)); sy += 10
    draw.text((sx, sy), 'Legend:', fill=(255, 255, 255)); sy += 20

    for typ in sorted(FEATURE_NAMES):
        if typ not in counts:
            continue
        name, color, _ = FEATURE_NAMES[typ]
        draw.rectangle([sx, sy + 2, sx + 10, sy + 12], fill=color)
        draw.text((sx + 16, sy), f'{name} ({counts[typ]})', fill=(200, 200, 200))
        sy += 18

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    im.save(out_path)
    return im


def render_all(sg_dir, out_dir=None):
    """Render all levels and produce a 10-level composite overview atlas."""
    if out_dir is None:
        out_dir = os.path.join(MASHUP, 'work', 'maps')
    os.makedirs(out_dir, exist_ok=True)

    seed, levels = load_dungeon(sg_dir)
    print(f'Rendering {len(levels)} levels for Seed 0x{seed:08X}...')

    rendered = []
    for ldata in levels:
        p = os.path.join(out_dir, f'level_{ldata["level"]:02d}.png')
        im = render_level(seed, ldata, p)
        rendered.append(im)
        print(f'  Level {ldata["level"]:02d} -> {p}')

    # Create 5x2 composite atlas
    cols, rows = 5, 2
    w, h = rendered[0].size
    atlas_w = cols * w
    atlas_h = rows * h
    atlas = Image.new('RGB', (atlas_w, atlas_h), (12, 14, 16))
    for i, im in enumerate(rendered):
        c, r = i % cols, i // cols
        atlas.paste(im, (c * w, r * h))

    atlas_path = os.path.join(out_dir, 'dungeon_atlas.png')
    atlas.save(atlas_path)
    print(f'Wrote full dungeon atlas: {atlas_path}')
    return atlas_path


if __name__ == '__main__':
    args = sys.argv[1:]
    target_sg = os.path.join(MASHUP, 'fixtures', 'savegame_nomon')
    if not os.path.exists(target_sg):
        target_sg = os.path.join(MASHUP, 'fixtures', 'savegame')

    if '--all' in args:
        args.remove('--all')
        sg = args[0] if args else target_sg
        render_all(sg)
    else:
        sg = args[0] if args and os.path.isdir(args[0]) else target_sg
        lv = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
        seed, levels = load_dungeon(sg)
        out = os.path.join(MASHUP, 'work', 'maps', f'level_{lv:02d}.png')
        render_level(seed, levels[lv], out)
        print(f'Saved {out}')
