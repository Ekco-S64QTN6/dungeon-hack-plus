"""Authentic EOB1 / EOB2 theme recipes from hand-drawn Westwood wallsets.

  python3 -I tools/eob_classic.py      -> pool/recipe_eob2_darkmoon_classic.json, pool/recipe_eob1_waterdeep.json

Per EOB set: hand-drawn walls + door frame + stairs (`vmp_walls`), its own floor/ceiling
backdrop in one Floor-N slot, and kernel pairing rules so that DH wallset only appears
with that floor and with the 3 DH palettes whose hue best matches the set
(`kernel_rules.match_palettes`). Wallsets the theme leaves alone (Stone, Marble) are
restricted to the untouched original floors 5-7 so they never show an EOB floor.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import aesop, kernel_rules, westwood   # noqa: E402

# (EOB set, DH wallset, frame set, stairs set or None)
THEMES = {
    'eob2_darkmoon_classic': {
        'game': 'eob2',
        'comment': 'EOB2 Darkmoon (classic): hand-drawn Darkmoon dungeon, silver halls, crimson temple, '
                   'Mezz towers and forest, each with its own floor and hue-matched palettes',
        'sets': [('DUNG', 'Rock', 'DUNG', 'DUNG'), ('SILVER', 'Foil', 'SILVER', 'SILVER'),
                 ('CRIMSON', 'Mine', 'CRIMSON', 'CRIMSON'), ('MEZZ', 'Ice', 'MEZZ', 'MEZZ'),
                 ('FOREST', 'Wood', 'DUNG', 'DUNG')],
        'doors': ['e2_iron', 'e2_bars', 'e2_darkmoon', 'e2_vines', 'e2_cross', 'e2_silver', 'e2_wood', 'e2_mouth', 'e2_glyph'],
        # DH monster slot -> EOB2 monster (closest identity/role); guard1 excluded (bad slice)
        'monsters': {'Wererat': 'eob2_wolf', 'Goblin': 'eob2_ant', 'Hobgob': 'eob2_guard2', 'Cocatric': 'eob2_basilisk',
                     'Umberhul': 'eob2_bulette', 'Orc': 'eob2_cleric3', 'Bugbear': 'eob2_cleric2', 'Knight': 'eob2_cleric1',
                     'Ettin': 'eob2_frgiant', 'Ankheg': 'eob2_fsnake', 'Gargoyle': 'eob2_gargoyle', 'Otyugh': 'eob2_gasspore',
                     "Tanar'ri": 'eob2_guardian', 'Shadewiz': 'eob2_mage', 'Xill': 'eob2_mantis', 'Grmedusa': 'eob2_medusa',
                     'Carrion': 'eob2_spider', 'Gravmist': 'eob2_willowis', 'Ghost': 'eob2_aservant', 'Morph': 'eob2_mindflay',
                     'Darktent': 'eob2_beholder', 'Livmuck': 'eob2_cube', 'Wyvern': 'eob2_salamndr', 'Wight': 'eob2_skelwar',
                     'Mummy': 'eob2_guard1', 'Watchght': 'eob2_wasp'},
        # cosmetic EOB2 decorations for DH's generic slots 29-48: (sheet, .DEC, palette, decoration index)
        'wall_decos': [('BROWN2', 'BROWN', 'DUNG', 35), ('BROWN2', 'BROWN', 'DUNG', 36), ('BROWN2', 'BROWN', 'DUNG', 8),
                       ('BROWN1', 'BROWN', 'DUNG', 43), ('BROWN1', 'BROWN', 'DUNG', 32), ('AZURE1', 'AZURE', 'AZURE', 19),
                       ('AZURE1', 'AZURE', 'AZURE', 27), ('AZURE1', 'AZURE', 'AZURE', 49), ('MEZZ1', 'MEZZ', 'MEZZ', 2),
                       ('MEZZ1', 'MEZZ', 'MEZZ', 12), ('MEZZ1', 'MEZZ', 'MEZZ', 6), ('MEZZ2', 'MEZZ', 'MEZZ', 59),
                       ('MEZZ2', 'MEZZ', 'MEZZ', 44), ('SILVER1', 'SILVER', 'SILVER', 21), ('SILVER1', 'SILVER', 'SILVER', 7),
                       ('SILVER1', 'SILVER', 'SILVER', 27), ('CRIMSON', 'CRIMSON', 'CRIMSON', 24),
                       ('CRIMSON', 'CRIMSON', 'CRIMSON', 37), ('CRIMSON', 'CRIMSON', 'CRIMSON', 40),
                       ('AZURE1', 'AZURE', 'AZURE', 40)],   # not CRIMSON 52: a winged altar wider than the wall
    },
    'eob1_waterdeep': {
        'game': 'eob1',
        'comment': 'EOB1 Waterdeep (classic): hand-drawn sewers, dwarven ruins, drow halls, '
                   'green halls and Xanathar\'s lair, each with its own floor and hue-matched palettes',
        'sets': [('BLUE', 'Rock', 'BLUE', 'BLUE'), ('BRICK', 'Foil', 'BRICK', 'BLUE'),
                 ('DROW', 'Mine', 'DROW', 'DROW'), ('GREEN', 'Ice', 'GREEN', 'GREEN'),
                 ('XANATHA', 'Wood', 'XANATHA', 'BLUE')],
        'doors': ['iron', 'grate', 'slab', 'web', 'mouth', 'eye'],
        'monsters': {'Goblin': 'eob1_kobold', 'Ghoul': 'eob1_zombie', 'Wight': 'eob1_skeleton', 'Orc': 'eob1_kuotoa',
                     'Hobgob': 'eob1_kenku', 'Wererat': 'eob1_hellhound', 'Undbeast': 'eob1_disbeast', 'Bugbear': 'eob1_flind',
                     'Golem': 'eob1_golem', 'Carrion': 'eob1_leech', 'Xill': 'eob1_mantis', 'Knight': 'eob1_skelwar',
                     'Shadewar': 'eob1_drowelf', 'Shadewiz': 'eob1_shindia', 'Morph': 'eob1_mflayer', 'Troglody': 'eob1_dwarf',
                     'Spectre': 'eob1_mage'},
        # EOB1 has few purely cosmetic decorations (levers, keyholes, niches are left out); the rest of
        # slots 29-48 keep DH's own tapestries
        'wall_decos': [('BLUE', 'BLUE', 'BLUE', 7), ('BLUE', 'BLUE', 'BLUE', 8), ('BLUE', 'BLUE', 'BLUE', 10),
                       ('DROW', 'DROW', 'DROW', 14), ('DROW', 'DROW', 'DROW', 27),  # not XANATHA 11 (floor pedestal)
                       ('XANATHA', 'XANATHA', 'XANATHA', 17)],
    },
}
UNTOUCHED_FLOORS = {'Stone': [5, 6, 7], 'Marble': [5, 7]}
# every DH door resource the kernel's door table can pick (table718 non-zero entries)
DH_DOORS = ['Door-00', 'Door-02', 'Door-03', 'Door-04', 'Door-05', 'Door-06', 'Door-07', 'Door-08', 'Door-09',
            'Door-11', 'Door-12', 'Door-14', 'Door-15', 'Door-16', 'Door-17', 'Door-18']
# engine/data fixes every playable recipe carries (verified in game; see recipe_fixes.json). They run
# right after the palette rules: Ice Stairs frames must be in order before stairs art goes in.
FIX_JOBS = [{'type': 'fix_unlock_shape', 'target': 'items'}, {'type': 'fix_ice_stairs', 'target': 'Ice Stairs'}]


def reramp_jobs(slots):
    """Convert DH art the recipe leaves in these wallset slots to their new ramp shape (no-op if unchanged)."""
    return [{'type': 'reramp', 'target': s} for s in slots]


# DH monster slots used for the theme's monsters, in order (low-level dungeon dwellers first)
MONSTER_SLOTS = ['Goblin', 'Ghoul', 'Shghoul', 'Orc', 'Hobgob', 'Wight', 'Shadewiz', 'Wererat']


def set_colours(game, vset):
    d = os.path.join(ROOT, 'base_games', game)
    blocks, remap = westwood.vcn_blocks(os.path.join(d, vset + '.VCN'))
    ent = westwood.vmp(os.path.join(d, vset + '.VMP'))
    palf = os.path.join(d, vset + '.PAL')
    if not os.path.exists(palf):
        palf = os.path.join(d, 'EOBPAL.COL' if game == 'eob1' else 'DUNG.PAL')
    pal = np.array(westwood.read_pal(palf), np.uint8).reshape(-1, 3)
    w, h, px, m = westwood.render_position(blocks, ent, 0, 'front_d1')
    return pal[np.array([remap[16 + v] for v in px], np.uint8)][np.frombuffer(bytes(m), np.uint8) > 0]


def build(name, theme):
    dh = aesop.ResFile(os.path.join(ROOT, 'base_games', 'dungeon_hack', 'HACK.RES')); n = dh.names()
    pals = {p: aesop.decode_palette(dh.entry(n['wall/floor palette %02d' % p])[2])[1] for p in range(21)}
    game = theme['game']
    rules = {'type': 'palette_rules', 'target': 'kernel', 'wall_palettes': {}, 'wall_floors': {},
             'floor_palettes': {}, 'allow_pairs': []}
    jobs = []
    for floor, (vset, wall, frame_set, stairs_set) in enumerate(theme['sets']):
        match = kernel_rules.match_palettes(set_colours(game, vset), pals)
        rules['wall_palettes']['%s Wallset' % wall] = match
        rules['wall_floors']['%s Wallset' % wall] = [floor]
        rules['floor_palettes'][str(floor)] = match
        rules['allow_pairs'].append([match, match])
        has_stairs = stairs_set is not None
        jobs.append({'type': 'vmp_walls', 'target': '%s Wallset' % wall, 'game': game, 'set': vset,
                     'plain': [0, 1], 'frame': 2, 'frame_set': frame_set,
                     **({'stairs': '%s Stairs' % wall, 'stairs_set': stairs_set, 'stairs_down': 4, 'stairs_up': 3} if has_stairs else {})})
        jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/%s_backdrop.png' % vset})
    for floor, (vset, wall, frame_set, stairs_set) in enumerate(theme['sets']):
        if vset not in ('FOREST',):            # FOREST has no decorated wall type
            jobs.append({'type': 'vmp_deco', 'target': '%s decorations' % wall, 'wallset': '%s Wallset' % wall,
                         'game': game, 'set': vset, 'deco': 5, 'base': 0})
    for k, door in enumerate(DH_DOORS):
        jobs.append({'type': 'eob_door', 'target': door, 'kind': theme['doors'][k % len(theme['doors'])]})
    for k, (sheet, dec, epal, index) in enumerate(theme.get('wall_decos', [])):
        jobs.append({'type': 'eob_wall_deco', 'target': 'Wall Deco %02d' % (29 + k), 'game': game, 'sheet': sheet + '.CPS',
                     'dec': dec + ('.DAT' if game == 'eob1' else '.DEC'), 'pal': epal + '.PAL', 'index': index})
    for wall, floors in UNTOUCHED_FLOORS.items():
        rules['wall_floors']['%s Wallset' % wall] = floors
    mons = theme['monsters'] if isinstance(theme['monsters'], dict) else dict(zip(MONSTER_SLOTS, theme['monsters']))
    for slot, mon in mons.items():
        imgs = ['pool/monsters/%s/%d.png' % (mon, i) for i in range(6)]   # pool/monsters frames are already in DH order
        if all(os.path.exists(os.path.join(ROOT, p)) for p in imgs):
            jobs.append({'type': 'sprites', 'target': slot, 'images': imgs})
    recipe = {'comment': theme['comment'],
              'jobs': [rules] + FIX_JOBS + reramp_jobs([w for _, w, _, _ in theme['sets']]) + jobs}
    path = os.path.join(ROOT, 'pool', 'recipe_%s.json' % name)
    json.dump(recipe, open(path, 'w'), indent=1)
    print('%s: %d jobs; palettes %s' % (name, len(recipe['jobs']), rules['wall_palettes']))


# ---------------------------------------------------------------- EOB3 "Myth Drannor"
# DH already contains EOB3's Marble walls and 30 of its 31 monsters (identical silhouettes), so the
# new EOB3 content is: Mausoleum / Ruins / Forest walls, the doors and stairs (panels jobs from
# recipe_eob3_complete), the four 176x120 backdrops (19th frame of each wall object) as floors,
# and the Shadow Hound.
EOB3_SETS = [('Marble walls', 'Marble palette', 'Marble'), ('Mausoleum walls', 'Mausoleum palette', 'Wood'),
             ('Ruins walls', 'Ruins palette', 'Rock'), ('Forest walls', 'Forest palette', 'Stone')]
EOB3_UNTOUCHED_FLOORS = {'Foil': [5, 7], 'Ice': [6, 7], 'Mine': [6, 7]}


def eob3_colours(e3, wall, pal):
    en = e3.names()
    _, fx, _ = aesop.decode_palette(e3.entry(en['Fixed palette'])[2])
    _, rp, _ = aesop.decode_palette(e3.entry(en[pal])[2])
    P = np.array(fx, np.uint8).reshape(-1, 3).copy(); P[176:192] = np.array(rp, np.uint8).reshape(-1, 3)
    fr = aesop.decode_vfx110(e3.entry(en[wall])[2])
    w, h, px, m, _ = fr[18]                               # 176x120 floor/ceiling backdrop
    img = P[np.frombuffer(bytes(px), np.uint8)].reshape(h, w, 3)
    shape_two = kernel_rules_shape(rp)
    return img, shape_two


def eob3_front(e3, wall, pal):
    """EOB3 wall object panel 8 (near front wall, 128x96) in the set's colours: texture for slot 36."""
    en = e3.names()
    _, fx, _ = aesop.decode_palette(e3.entry(en['Fixed palette'])[2])
    _, rp, _ = aesop.decode_palette(e3.entry(en[pal])[2])
    P = np.array(fx, np.uint8).reshape(-1, 3).copy(); P[176:192] = np.array(rp, np.uint8).reshape(-1, 3)
    w, h, px, m, _ = aesop.decode_vfx110(e3.entry(en[wall])[2])[8]
    return P[np.frombuffer(bytes(px), np.uint8)].reshape(h, w, 3)


def kernel_rules_shape(rgb16):
    lum = [0.299 * rgb16[i] + 0.587 * rgb16[i + 1] + 0.114 * rgb16[i + 2] for i in range(0, 45, 3)]
    return any(b > a + 3 for a, b in zip(lum, lum[1:]))   # rises somewhere -> two-ramp


def build_eob3():
    from PIL import Image
    e3 = aesop.ResFile(os.path.join(ROOT, 'base_games', 'eob3', 'EYE.RES'))
    dh = aesop.ResFile(os.path.join(ROOT, 'base_games', 'dungeon_hack', 'HACK.RES')); n = dh.names()
    pals = {p: aesop.decode_palette(dh.entry(n['wall/floor palette %02d' % p])[2])[1] for p in range(21)}
    base_jobs = [j for j in json.load(open(os.path.join(ROOT, 'pool', 'recipe_eob3_complete.json')))['jobs']
                 if j['type'] != 'palette_rules']
    for j in base_jobs:      # Temple doors were given 'Fixed palette' as their PAL_WALLS ramp (its first 16 colours)
        if j.get('source_palette') == 'Fixed palette':
            j['source_palette'] = 'Marble palette'
    rules = {'type': 'palette_rules', 'target': 'kernel', 'wall_palettes': {}, 'wall_floors': {},
             'floor_palettes': {}, 'allow_pairs': []}
    jobs = []
    for floor, (wall, pal, dhw) in enumerate(EOB3_SETS):
        img, two = eob3_colours(e3, wall, pal)
        path = 'pool/floors/eob3_%s.png' % wall.split()[0].lower()
        Image.fromarray(img).save(os.path.join(ROOT, path))
        match = kernel_rules.match_palettes(img.reshape(-1, 3), pals, candidates=range(15, 21) if two else range(15))
        rules['wall_palettes']['%s Wallset' % dhw] = match
        rules['wall_floors']['%s Wallset' % dhw] = [floor]
        rules['floor_palettes'][str(floor)] = match
        rules['allow_pairs'].append([match, match])
        jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': path})
        front = 'pool/walls/eob3_%s_front.png' % wall.split()[0].lower()
        Image.fromarray(eob3_front(e3, wall, pal)).save(os.path.join(ROOT, front))
        jobs.append({'type': 'wallset', 'target': '%s Wallset' % dhw, 'texture': front, 'frames': '36,199-217'})
        if not any(j['target'] == '%s Stairs' % dhw for j in base_jobs):
            jobs.append({'type': 'stairs_from', 'target': '%s Stairs' % dhw, 'donor': {'Forest walls': 'Ice', 'Ruins walls': 'Stone'}.get(wall, dhw)})
    for wall, floors in EOB3_UNTOUCHED_FLOORS.items():
        rules['wall_floors']['%s Wallset' % wall] = floors
    jobs.append({'type': 'sprites', 'target': 'Wererat', 'images': ['pool/monsters/eob3_shadow_hound/%d.png' % i for i in range(6)]})
    recipe = {'comment': 'EOB3 Myth Drannor: Mausoleum/Ruins/Forest walls + EOB3 doors and stairs, each wallset with its own '
                         'EOB3 floor and hue-matched palettes, Shadow Hound. (DH already holds EOB3 Marble walls and 30/31 EOB3 monsters.)',
              'jobs': [rules] + FIX_JOBS + reramp_jobs([dhw for _, _, dhw in EOB3_SETS]) + base_jobs + jobs}
    json.dump(recipe, open(os.path.join(ROOT, 'pool', 'recipe_eob3_mythdrannor.json'), 'w'), indent=1)
    print('eob3_mythdrannor: %d jobs; palettes %s' % (len(recipe['jobs']), rules['wall_palettes']))


if __name__ == '__main__':
    for name, theme in THEMES.items():
        build(name, theme)
    build_eob3()
