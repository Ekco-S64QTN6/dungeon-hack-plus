"""EOB1/EOB2 wall decorations (.DAT / .DEC + <set>.CPS) rendered exactly as EOB places them.

Format (ScummVM EoBCoreEngine::loadDecorations): u16 count; per decoration: u8 shapeIndex[10]
(0xFF = none), u8 next (chained decoration), u8 flags, i16 shapeX[10], i16 shapeY[10]; then
u16 nrects and rects (x/8, y, w/8, h) cut from the set's .CPS.
Placement (EoBCoreEngine::drawDecorations): for visible block b and slot s = 2b + i, the wall face
is _dscWallMapping[s] (front 'D', right-facing 'R', left-facing 'L'), the shape is
_dscShapeIndex[s] (1-based; negative = mirrored), and slot i == 0 is shifted by _dscShapeX[b].
Visible blocks: depth 3 = 0..6 (x -3..3), depth 2 = 7..11 (x -2..2), depth 1 = 12..14, party row 15..17.
"""
import struct

import numpy as np

# eobcommon.cpp DWM table (36 entries = 18 blocks x 2 slots)
WALL_MAPPING = [None, None, 'D', 'R', 'D', 'R', 'D', None, 'D', 'L', 'D', 'L',
                None, None, 'D', 'R', 'D', 'R', 'D', None, 'D', 'L', 'D', 'L',
                'D', 'R', 'D', None, 'D', 'L', None, 'R', 'D', None, None, 'L']
SHAPE_INDEX = {   # create_kyradat kEoB1/kEoB2DscShapeIndexDOS (signed)
    'eob1': [1, 1, 4, 10, 4, 8, 4, 1, 4, -8, 4, -10, 0, 0, 3, 9, 3, 7, 3, 1, 3, -7, 3, -9,
             2, 6, 2, 1, 2, -6, 1, 5, 1, 1, 1, -5],
}
SHAPE_INDEX['eob2'] = SHAPE_INDEX['eob1']     # kEoB2DscShapeIndexDOS is identical
DSC_X = {         # kEoB1DscXDOS (18 x i16)
    'eob1': [-144, -96, -48, 0, 48, 96, 144, -160, -80, 0, 80, 160, -128, 0, 128, 0, 0, 0],
    'eob2': [-144, -96, -48, 0, 48, 96, 144, -160, -80, 0, 80, 160, -128, 0, 128, 0, 0, 0],   # identical in EOB2
}
BLOCK_XY = [(x, -3) for x in range(-3, 4)] + [(x, -2) for x in range(-2, 3)] + [(x, -1) for x in range(-1, 2)] + [(-1, 0), (0, 0), (1, 0)]


def parse_dec(data):
    n = struct.unpack_from('<H', data)[0]; pos = 2; decs = []
    for _ in range(n):
        shp = list(data[pos:pos + 10]); nxt, flags = data[pos + 10], data[pos + 11]
        xs = list(struct.unpack_from('<10h', data, pos + 12)); ys = list(struct.unpack_from('<10h', data, pos + 32))
        decs.append({'shape': shp, 'next': nxt, 'flags': flags, 'x': xs, 'y': ys}); pos += 52
    nr = struct.unpack_from('<H', data, pos)[0]; pos += 2
    rects = [struct.unpack_from('<4H', data, pos + 8 * k) for k in range(nr)]
    return decs, rects


def shape_img(sheet_idx, rect):
    x8, y, w8, h = rect
    return sheet_idx[y:y + h, x8 * 8:(x8 + w8) * 8]


def render(decs, rects, sheet_idx, dec_index, block, face, game='eob1', view=(120, 176)):
    """-> (indices, mask) 120x176 view layer with decoration `dec_index` drawn on `face` of `block`."""
    out = np.zeros(view, np.uint8); mask = np.zeros(view, np.uint8)
    for i in (1, 0):
        s = block * 2 + i
        if WALL_MAPPING[s] != face:
            continue
        l = dec_index
        seen = 0
        while seen == 0 or (l not in (0, 0xFF) and seen < 8):   # next == 0 ends the chain
            d = decs[l]; seen += 1
            ix = SHAPE_INDEX[game][s]
            if ix == 0:
                break
            shp_ix = abs(ix) - 1
            flg = d['flags']
            if i == 0 and (flg & 1):
                ix = -ix
            sidx = d['shape'][shp_ix]
            if sidx != 0xFF and sidx < len(rects):
                img = shape_img(sheet_idx, rects[sidx]); h, w = img.shape
                x = (DSC_X[game][block] if i == 0 else 0) + (view[1] - 176) // 2
                if ix < 0:
                    x += 176 - d['x'][shp_ix] - w; img = img[:, ::-1]
                else:
                    x += d['x'][shp_ix]
                y = d['y'][shp_ix]
                for yy in range(h):
                    ty = y + yy
                    if not 0 <= ty < view[0]:
                        continue
                    for xx in range(w):
                        tx = x + xx
                        if 0 <= tx < view[1] and img[yy, xx]:
                            out[ty, tx] = img[yy, xx]; mask[ty, tx] = 1
            l = d['next']
    return out, mask


# DH draw_walls faces (AESOP.EXE tables via Thirdeye runtime/dh.cpp), party facing north
DH_DX = [-3, -2, -1, 1, 2, 3, -2, -1, 0, 1, 2, -2, -1, 1, 2, -1, 0, 1, -1, 1, -1, 0, 1, -1, 1]
DH_DY = [-3] * 11 + [-2] * 7 + [-1] * 5 + [0, 0]
DH_X = [-16, 16, 64, 104, 136, 168, -32, 16, 64, 112, 160, 0, 48, 112, 160, -32, 48, 128, 24, 128, -104, 24, 152, 0, 152]
DH_Y = [27] * 11 + [26, 20, 20, 26, 20, 20, 20] + [8] * 5 + [0, 0]
DH_MIRROR = [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
DH_PANEL = [[4, 4, 3, 3, 4, 4, 13, 13, 13, 13, 13, 5, 2, 2, 5, 16, 16, 16, 1, 1, 8, 8, 8, 0, 0],
            [10, 10, 9, 9, 10, 10, 14, 14, 14, 14, 14, 11, 12, 12, 11, 17, 17, 17, 7, 7, 15, 15, 15, 6, 6]]
FRONT_PANELS = {8, 13, 14, 15, 16, 17}
PAD = 160


def render_wide(decs, rects, sheet_idx, dec_index, block, face, game):
    """render() into a canvas padded by PAD on the left/right (DH faces start at x = -104)."""
    return render(decs, rects, sheet_idx, dec_index, block, face, game, view=(120, 176 + 2 * PAD))


def dh_panels(decs, rects, sheet_idx, dec_index, panel_sizes, game='eob1'):
    """-> {panel: (idx array h x w, mask)} for DH decoration panels 0..17 (unmirrored storage).
    panel_sizes: {panel: (w, h)} from the target resource. Each panel takes the face that shows
    the most decoration pixels; mirrored faces are flipped back."""
    best = {}
    for f in range(25):
        dx, dy = DH_DX[f], DH_DY[f]
        if (dx, dy) not in BLOCK_XY:
            continue
        block = BLOCK_XY.index((dx, dy))
        for variant in (0, 1):
            p = DH_PANEL[variant][f]
            if p in (14, 15, 17) or p not in panel_sizes:
                continue
            face = 'D' if p in FRONT_PANELS else ('R' if dx < 0 else 'L')
            lay, m = render_wide(decs, rects, sheet_idx, dec_index, block, face, game)
            w, h = panel_sizes[p]
            x0, y0 = DH_X[f] + PAD, DH_Y[f]
            crop = lay[y0:y0 + h, x0:x0 + w]; cm = m[y0:y0 + h, x0:x0 + w]
            if crop.shape != (h, w):
                continue
            if DH_MIRROR[f]:
                crop, cm = crop[:, ::-1], cm[:, ::-1]
            if p not in best or cm.sum() > best[p][1].sum():
                best[p] = (crop.copy(), cm.copy())
    return best
