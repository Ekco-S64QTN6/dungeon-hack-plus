"""Menzoberranzan wallsets for Dungeon Hack.

Menzo (DreamForge's texture-mapped engine) stores walls as 64x192 vertical strips (RES4 type 05)
and floors/ceilings as 64x64 flats. A DH wall face is 4:3, so four adjacent strips (256x192)
make one face; `wallset` jobs then warp it onto every DH panel with perspective foreshortening
(normalize.warp_to_mask). Variant 1 uses a decorated strip pair (carvings, braces).

Floors: DH Floor-N is a 176x120 backdrop (ceiling, dark horizon, floor). The flats are
projected onto a floor and a ceiling plane fitted to DH's own view geometry: wall faces sit
at depth z = n + 0.59 squares (front panels 96/59/38 px tall), horizon y = 39.2, floor line
y = 39.2 + 103/z, ceiling line y = 39.2 - 49.6/z, one square = 128 * 1.59 / z px wide.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dreamforge   # noqa: E402
import paths        # noqa: E402

# set -> plain strips (variant 0), decorated strips (variant 1), floor flat, ceiling flat (RES4 record ids)
# DH stair style each set borrows (Menzo has no stair art): drow stone -> Marble, planks -> Wood, cave -> Rock
STAIR_DONOR = {'menzo_blue': 'Marble', 'menzo_purple': 'Marble', 'menzo_red': 'Marble', 'menzo_gold': 'Marble',
               'menzo_wood': 'Wood', 'menzo_cave': 'Rock'}
SETS = {
    'menzo_blue':   {'v0': [237, 238, 239, 240], 'v1': [236, 241, 242, 239], 'floor': 1036, 'ceiling': 1034},
    'menzo_purple': {'v0': [517, 518, 519, 520], 'v1': [518, 534, 535, 519], 'floor': 1042, 'ceiling': 1041},
    'menzo_red':    {'v0': [836, 837, 838, 839], 'v1': [836, 841, 842, 839], 'floor': 1035, 'ceiling': 1047},
    'menzo_gold':   {'v0': [819, 820, 821, 822], 'v1': [819, 824, 825, 822], 'floor': 980, 'ceiling': 997},
    'menzo_cave':   {'v0': [177, 178, 179, 180], 'v1': [183, 184, 185, 186], 'floor': 993, 'ceiling': 994},
    'menzo_wood':   {'v0': [0, 1, 2, 3], 'v1': [10, 11, 12, 13], 'floor': 995, 'ceiling': 996},
}
YH, B, T, Z1, FACE1 = 39.2, 103.0, 49.6, 1.59, 128.0


def load_res4():
    """RES4 textures by record id -> RGB array (64x192 strips, 64x64 flats)."""
    base = paths.get_game_dir('menzo')
    pal = np.array(dreamforge.palette(os.path.join(base, 'COLORS')), np.uint8).reshape(-1, 3)
    out = {}
    for k, typ, flags, payload in dreamforge.records(os.path.join(base, 'RES4')):
        if typ == 0x05 and len(payload) in (12290, 4096):
            w, h, px = dreamforge.texture(payload if len(payload) == 12290 else b'\0\0' + payload)
            out[k] = pal[np.frombuffer(bytes(px), np.uint8)].reshape(h, w, 3)
    return out


def face(tex, ids):
    return np.concatenate([tex[i] for i in ids], axis=1)            # 4 strips -> 256x192


def backdrop(floor, ceiling, w=176, h=120, ss=3):
    """Project two 64x64 flats onto DH's floor and ceiling planes, darkening with distance."""
    out = np.zeros((h, w, 3), np.float32)
    for sy in range(ss):
        for sx in range(ss):
            y = np.arange(h)[:, None] + (sy + 0.5) / ss
            x = np.arange(w)[None, :] + (sx + 0.5) / ss
            below = y > YH
            dy = np.where(below, y - YH, YH - y)
            z = np.where(below, B, T) / np.maximum(dy, 1e-3)
            u = (x - w / 2) * z / (FACE1 * Z1) + 0.5
            v = z - (Z1 - 1)
            tu = (np.mod(u, 1) * 64).astype(int) % 64
            tv = (np.mod(v, 1) * 64).astype(int) % 64
            img = np.where(below[..., None], floor[tv, tu], ceiling[tv, tu]).astype(np.float32)
            fog = np.clip(1.0 - (z - 1.0) / 7.0, 0, 1)[..., None]       # DH floors: narrow dark band at the horizon
            out += img * fog
    return (out / (ss * ss)).astype(np.uint8)


def export():
    tex = load_res4()
    os.makedirs(os.path.join(ROOT, 'pool', 'walls'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'pool', 'floors'), exist_ok=True)
    for name, s in SETS.items():
        for v in ('v0', 'v1'):
            Image.fromarray(face(tex, s[v])).save(os.path.join(ROOT, 'pool', 'walls', '%s_%s.png' % (name, v)))
        Image.fromarray(backdrop(tex[s['floor']], tex[s['ceiling']])).save(os.path.join(ROOT, 'pool', 'floors', name + '.png'))
    print('menzo wallsets -> pool/walls, pool/floors:', ', '.join(SETS))


def colours(name):
    """RGB samples of a set's plain wall, for kernel_rules.match_palettes."""
    return np.asarray(Image.open(os.path.join(ROOT, 'pool', 'walls', name + '_v0.png')).convert('RGB')).reshape(-1, 3)


def jobs(name, slot, floor):
    """Recipe jobs putting Menzo set `name` into DH wallset slot `slot` with its backdrop in Floor-`floor`."""
    w = 'pool/walls/%s_%%s.png' % name
    return [{'type': 'wallset', 'target': '%s Wallset' % slot, 'texture': w % 'v0', 'frames': '0-5,8,13,16'},
            {'type': 'wallset', 'target': '%s Wallset' % slot, 'texture': w % 'v1', 'frames': '6,7,9-12'},
            {'type': 'wallset', 'target': '%s Wallset' % slot, 'texture': w % 'v0', 'frames': '18-36,199-217'},   # + arch
            {'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/%s.png' % name},
            {'type': 'stairs_from', 'target': '%s Stairs' % slot, 'donor': STAIR_DONOR[name]}]


if __name__ == '__main__':
    export()
