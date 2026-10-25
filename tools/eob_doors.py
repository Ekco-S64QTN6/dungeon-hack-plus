"""EOB1 doors -> Dungeon Hack 3-stage door resources.

EOB draws a door as one shape (3 sizes: near/mid/far) cut from DOOR.CPS and animates
it procedurally (slides it, splits it). DH instead stores 3 stages x 18 panels and only
uses the front panels 8 (depth 1), 16 (depth 2), 13 (depth 3); stage block 0 = nearly
open, 1 = half, 2 = closed (doors.render: block = maxstate - state - 1).

Cut boxes: ScummVM devtools/create_kyradat/resources/eob1_dos.h kEoB1DoorShapeDefsDOS
(8 types x 3 sizes x (x/8, y, w/8, h)); index 0 = near, 2 = far.
"""
import numpy as np
from PIL import Image

EOB1_DOOR_DEFS = [0x00, 0x00, 0x0A, 0x48, 0x11, 0x98, 0x07, 0x2F, 0x19, 0x48, 0x04, 0x1D, 0x0A, 0x00, 0x0A, 0x48,
                  0x1D, 0x48, 0x07, 0x2F, 0x19, 0x68, 0x04, 0x1D, 0x14, 0x00, 0x06, 0x48, 0x24, 0x48, 0x04, 0x2F,
                  0x1E, 0x78, 0x03, 0x1D, 0x1A, 0x00, 0x0C, 0x48, 0x00, 0x90, 0x07, 0x29, 0x21, 0x78, 0x04, 0x1B,
                  0x00, 0xBC, 0x0A, 0x0C, 0x0A, 0xBC, 0x06, 0x08, 0x0A, 0xC4, 0x04, 0x02, 0x07, 0x4A, 0x09, 0x37,
                  0x00, 0x4A, 0x07, 0x25, 0x07, 0xA0, 0x05, 0x17, 0x07, 0x82, 0x09, 0x1C, 0x00, 0x70, 0x07, 0x13,
                  0x0C, 0xA0, 0x05, 0x0B, 0x10, 0x48, 0x09, 0x4B, 0x18, 0x98, 0x07, 0x2E, 0x1F, 0x98, 0x04, 0x1D]
# Indices 0xF0-0xFF are EOB's per-level wall/floor slot. Iron door and grate use them only for the
# floor seen between spikes/bars (-> transparent, DH draws its own floor); slab/mouth/eye are
# *painted* in level colours, so those keep them and match the surrounding walls.
# web: strands are the per-level band 228-235 (a mauve ramp in DROW.PAL, the spider levels that
# use webs); 236-238 are near-black there = the corridor seen through the web -> transparent.
SEE_THROUGH = {'iron': set(range(0xF0, 0x100)), 'grate': set(range(0xF0, 0x100)), 'web': {236, 237, 238}}
# EOB2 door cut boxes (x/8, y, w/8, h) x (near, mid, far), read from the door blocks of
# DARKMOON/LEVEL*.INF (LCW-packed; marker 0xEC/0xEA, sheet name, wall, type, switch, 3 x u16[4]).
EOB2_DOOR_BOXES = {
    'e2_iron':     ('door1', [((0, 0, 9, 71), (9, 0, 7, 47), (16, 0, 4, 28))]),            # L1-2
    'e2_bars':     ('door1', [((0, 71, 9, 71), (9, 48, 7, 47), (16, 29, 4, 28))]),         # L1-2
    'e2_mouth':    ('door1', [((0, 142, 9, 55), (9, 94, 7, 37), (16, 58, 4, 23)),          # L3 upper jaw
                              ((20, 0, 9, 28), (9, 131, 7, 19), (16, 81, 4, 11))]),        #    lower jaw
    'e2_darkmoon': ('door1', [((20, 46, 9, 70), (9, 150, 7, 47), (16, 92, 4, 29))]),       # L5-6 emblem door
    'e2_vines':    ('door2', [((0, 71, 9, 69), (9, 48, 7, 47), (16, 29, 4, 28))]),         # L7-9
    'e2_cross':    ('door2', [((0, 0, 9, 70), (9, 0, 7, 47), (16, 0, 4, 28))]),            # L8-9
    'e2_silver':   ('door2', [((20, 71, 9, 70), (9, 143, 7, 47), (16, 88, 4, 29))]),       # L10-14
    'e2_wood':     ('door2', [((20, 0, 9, 70), (9, 95, 7, 47), (16, 58, 4, 29))]),         # L13
    'e2_glyph':    ('door2', [((29, 0, 9, 69), (29, 71, 7, 47), (16, 119, 4, 28))]),       # L15-16
}
EOB2_MOTION = {'e2_mouth': 'split'}
# level palette of the levels each EOB2 door appears on (sets per level from DARKMOON/LEVEL*.INF):
# L1-3 DUNG (brown), L5-6 MEZZ, L7-9 SILVER, L10-14 AZURE, L15-16 CRIMSON. The glyph door's runes
# use indices that only CRIMSON.PAL defines (DUNG.PAL makes them white).
EOB2_DOOR_PAL = {'e2_iron': 'DUNG.PAL', 'e2_bars': 'DUNG.PAL', 'e2_mouth': 'DUNG.PAL', 'e2_darkmoon': 'MEZZ.PAL',
                 'e2_vines': 'SILVER.PAL', 'e2_cross': 'SILVER.PAL', 'e2_silver': 'AZURE.PAL', 'e2_wood': 'AZURE.PAL',
                 'e2_glyph': 'CRIMSON.PAL'}

# door "kinds" built from the 8 EOB1 types: (types, motion)
EOB1_DOORS = {
    'iron':   ((0,), 'up'),     # studded iron door
    'grate':  ((1,), 'up'),     # barred grate
    'slab':   ((2,), 'up'),     # stone slab
    'web':    ((3,), 'fade'),   # spider web
    'mouth':  ((5, 6), 'split'),  # upper + lower jaw
    'eye':    ((7,), 'up'),     # Xanathar's eye door
}
DH_FRONT = {0: 8, 1: 16, 2: 13}          # EOB size index -> DH front panel


def door_spec(kind):
    """-> (game, sheet file, [part boxes (near, mid, far) in (x/8, y, w/8, h)], motion)."""
    if kind in EOB2_DOOR_BOXES:
        sheet, parts = EOB2_DOOR_BOXES[kind]
        return 'eob2', sheet.upper() + '.CPS', parts, EOB2_MOTION.get(kind, 'up')
    types, motion = EOB1_DOORS[kind]
    parts = [tuple(tuple(EOB1_DOOR_DEFS[(t * 3 + i) * 4:(t * 3 + i) * 4 + 4]) for i in range(3)) for t in types]
    return 'eob1', 'DOOR.CPS', parts, motion


def cut_box(sheet_idx, pal, box, see_through=()):
    x8, y, w8, h = box
    i = sheet_idx[y:y + h, x8 * 8:(x8 + w8) * 8]
    a = pal[i]
    alpha = (((i != 0) & ~np.isin(i, list(see_through))) * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a, alpha]), 'RGBA')


def cut(sheet_idx, pal, t, size, see_through=()):
    """-> RGBA crop of EOB1 door type t at size index (0 near .. 2 far); index 0 and the
    indices in `see_through` are transparent."""
    x8, y, w8, h = EOB1_DOOR_DEFS[(t * 3 + size) * 4:(t * 3 + size) * 4 + 4]
    i = sheet_idx[y:y + h, x8 * 8:(x8 + w8) * 8]
    a = pal[i]
    alpha = (((i != 0) & ~np.isin(i, list(see_through))) * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a, alpha]), 'RGBA')


def stage(kind_parts, motion, box_w, box_h, frac, seed=0):
    """Compose one stage (frac = visible fraction, 1.0 = closed) in a box_w x box_h RGBA image."""
    out = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
    if motion == 'split':
        top, bot = kind_parts
        half = box_h // 2
        t = top.resize((box_w, half), Image.LANCZOS); b = bot.resize((box_w, box_h - half), Image.LANCZOS)
        shift = int(round((1 - frac) * half))
        out.alpha_composite(t, (0, -shift)) if shift < half else None
        out.alpha_composite(b, (0, half + shift)) if shift < box_h - half else None
        return out
    door = kind_parts[0].resize((box_w, box_h), Image.LANCZOS)
    if motion == 'up':
        shift = int(round((1 - frac) * box_h))
        if shift < box_h:
            out.alpha_composite(door, (0, -shift))
        return out
    if motion == 'fade':
        a = np.asarray(door).copy()
        keep = np.random.default_rng(seed).random(a.shape[:2]) < frac
        a[..., 3] = np.where(keep, a[..., 3], 0)
        return Image.fromarray(a, 'RGBA')
    raise ValueError(motion)
