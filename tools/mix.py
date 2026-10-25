"""The Dungeon Hack+ mix: one build whose graphics slots are filled from every source game.

  python3 -I tools/mix.py [SEED] [OUT.json]       -> pool/recipe_mix.json (default seed 1)

DH picks per level, at new-game start, one of 7 wallsets (each with its own stairs, door frame
and 4 decorations), one of 8 floors, one of 21 palettes, one of 16 doors, decorations from the
20 generic slots, and monsters from its fixed list. The mix fills those slots from DH, EOB1,
EOB2 and EOB3 by a seed, so within one game every level can come from a different game, and a
new seed (`dhplus.py roll`) reshuffles which sets are in the 7 slots.

Every piece is a job type that passed the in-game gate (vmp_walls, vmp_deco, eob_door,
eob_wall_deco, EOB3 panels, floors, sprites). Each external wallset gets its own floor slot and
hue-matched palettes; DH wallsets that stay keep their original floor/palette rules on the
floors left over. Rule sets are checked with kernel_rules.problems() (a bad set would hang
new-game creation) and re-rolled until valid.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import aesop, kernel_rules   # noqa: E402
import eob_classic as ec     # noqa: E402
import menzo_walls          # noqa: E402

SLOTS = ['Marble', 'Wood', 'Stone', 'Foil', 'Ice', 'Mine', 'Rock']        # kernel wallnum order

# external wallsets: (id, game, set, frame set, stairs set)
WESTWOOD_SETS = [('eob1_' + s.lower(), 'eob1', s, f, st) for s, _, f, st in ec.THEMES['eob1_waterdeep']['sets']] + \
                [('eob2_' + s.lower(), 'eob2', s, f, st) for s, _, f, st in ec.THEMES['eob2_darkmoon_classic']['sets']]
# EOB3: (id, wall object, palette, DH slot its jobs target in recipe_eob3_complete)
EOB3_SETS = [('eob3_mausoleum', 'Mausoleum walls', 'Mausoleum palette', 'Wood'),
             ('eob3_ruins', 'Ruins walls', 'Ruins palette', 'Rock'),
             ('eob3_forest', 'Forest walls', 'Forest palette', 'Stone')]
EOB3_STAIR_DONOR = {'eob3_forest': 'Ice', 'eob3_ruins': 'Stone', 'eob3_mausoleum': 'Wood'}   # DH style, if no EOB3 stairs
# DH style whose window, shelf and pillars (incl. the rubble/table/crate second state) each imported set
# borrows; no source game has these features. By material: rough stone -> Stone, smooth/drow stone ->
# Marble, carved panels -> Foil, forest -> Ice (bark), cave -> Rock, planks -> Wood.
FURNITURE_DONOR = {'eob1_blue': 'Stone', 'eob1_brick': 'Stone', 'eob1_green': 'Stone', 'eob1_drow': 'Marble',
                   'eob1_xanatha': 'Foil', 'eob2_dung': 'Stone', 'eob2_mezz': 'Marble', 'eob2_silver': 'Foil',
                   'eob2_crimson': 'Foil', 'eob2_forest': 'Ice', 'eob3_mausoleum': 'Marble', 'eob3_ruins': 'Stone',
                   'eob3_forest': 'Ice', 'menzo_blue': 'Marble', 'menzo_purple': 'Marble', 'menzo_red': 'Marble',
                   'menzo_gold': 'Marble', 'menzo_cave': 'Rock', 'menzo_wood': 'Wood'}
EOB3_DECOS = {'Wood': ['Wall Deco 09', 'Wall Deco 10', 'Wall Deco 11'], 'Rock': ['Wall Deco 12', 'Wall Deco 13', 'Wall Deco 14']}
EOB3_DOORS = ['Door-05', 'Door-06', 'Door-07', 'Door-08', 'Door-09', 'Door-11', 'Door-18']


def eob3_jobs():
    jobs = [j for j in json.load(open(os.path.join(ROOT, 'pool', 'recipe_eob3_complete.json')))['jobs'] if j['type'] == 'panels']
    for j in jobs:
        if j.get('source_palette') == 'Fixed palette':     # Temple art: see eob_classic.build_eob3
            j['source_palette'] = 'Marble palette'
    return jobs


def retarget(job, old_stem, new_stem):
    j = dict(job)
    j['target'] = j['target'].replace(old_stem + ' ', new_stem + ' ')
    if 'ramp_of' in j:
        j['ramp_of'] = j['ramp_of'].replace(old_stem + ' ', new_stem + ' ')
    return j


NEW_SLOTS = kernel_rules.WALLSETS[7:16]          # Eighth, W08..W15 (engine extension)
SEE_THROUGH_DOORS = {'grate', 'web', 'e2_bars'}
# Character portraits. DH's chooser pages 16 at a time: men get 0-31, women 29 + box (29-44); 29-31 are
# shared (helmeted/hooded). Candidates labelled by eye from the extracted sheets, minus EOB2 0-43 (= EOB1)
# and EOB3 faces that are already DH's own (DH reused EOB3's portraits; matched by image distance).
PORTRAITS = {
    'male': ['eob1_%02d' % i for i in list(range(0, 14)) + list(range(15, 26)) + [28]] + ['eob2_49'] +
            ['eob3_%02d' % i for i in (50, 51, 52, 65)],
    'female': ['eob1_%02d' % i for i in range(29, 44)] + ['eob2_%02d' % i for i in (44, 46, 47, 48)] +
              ['eob3_%02d' % i for i in (54, 59, 62, 64)],
    'shared': ['eob1_14', 'eob1_26', 'eob1_27', 'eob2_45', 'eob3_55', 'eob3_73', 'eob3_74'],
}
PORTRAIT_SLOTS = {'male': range(0, 29), 'shared': range(29, 32), 'female': range(32, 45)}
EXTRA_DOORS = 16


N_WALLS, N_FLOORS = 16, 16          # engine extension: 16 wallsets and 16 floors per game (DH: 7 and 8)


def roll(seed=1, external=4, picks=None, eighth=True, extra_doors=True):
    """picks: optional {slot: source id} to pin (tests); the rest of the roll is unchanged.
    With eighth (the engine extension, now 16 wallsets / 16 floors) every new slot (Eighth, W08-W15)
    takes an external set, and `external` of DH's own 7 slots do too; the others keep DH art."""
    rng = random.Random(seed)
    dh = aesop.ResFile(os.path.join(ROOT, 'base_games', 'dungeon_hack', 'HACK.RES')); n = dh.names()
    kernel = dh.entry(n['kernel'])[2]
    pals = {p: aesop.decode_palette(dh.entry(n['wall/floor palette %02d' % p])[2])[1] for p in range(21)}
    e3 = aesop.ResFile(os.path.join(ROOT, 'base_games', 'eob3', 'EYE.RES'))
    e3jobs = eob3_jobs()
    summary = {'seed': seed}

    # ---- wallsets: which DH slots get external sets, and which sets
    sources = [s[0] for s in WESTWOOD_SETS] + [s[0] for s in EOB3_SETS] + list(menzo_walls.SETS)
    pinned = dict(picks or {})
    for attempt in range(500):
        if pinned:
            picks = dict(pinned)
        else:
            ext_slots = (NEW_SLOTS if eighth else []) + rng.sample(SLOTS, external)
            picks = dict(zip(ext_slots, rng.sample(sources, len(ext_slots))))
        n_ext = len(picks)
        ext = any(sl in NEW_SLOTS for sl in picks)
        nf = N_FLOORS if ext else 8
        floors = rng.sample(range(nf), n_ext)
        rules = kernel_rules.extended_rules(kernel, N_WALLS, N_FLOORS) if ext else kernel_rules.read(kernel)
        job = {'type': 'palette_rules', 'target': 'kernel', 'wall_palettes': {}, 'wall_floors': {},
               'floor_palettes': {}, 'allow_pairs': []}
        for (slot, src), floor in zip(picks.items(), floors):
            if src.startswith('menzo'):
                match = kernel_rules.match_palettes(menzo_walls.colours(src), pals)
            elif src.startswith('eob3'):
                _, wall, pal, _ = next(s for s in EOB3_SETS if s[0] == src)
                img, two = ec.eob3_colours(e3, wall, pal)
                match = kernel_rules.match_palettes(img.reshape(-1, 3), pals, candidates=range(15, 21) if two else range(15))
            else:
                _, game, vset, _, _ = next(s for s in WESTWOOD_SETS if s[0] == src)
                match = kernel_rules.match_palettes(ec.set_colours(game, vset), pals)
            job['wall_palettes'][slot + ' Wallset'] = match
            job['wall_floors'][slot + ' Wallset'] = [floor]
            job['floor_palettes'][str(floor)] = match
            job['allow_pairs'].append([match, match])
        free = [f for f in range(8) if f not in floors]          # DH's own sets keep original floors
        ok = True
        for slot in SLOTS:
            if slot in picks:
                continue
            w = SLOTS.index(slot)
            mine = [f for f in free if rules['floor_ok_for_wall'][f] >> w & 1]
            if not mine:
                ok = False; break
            job['wall_floors'][slot + ' Wallset'] = mine
        if not ok:
            continue
        for k, v in job['wall_palettes'].items():
            kernel_rules.set_wall_palettes(rules, k, v)
        for k, v in job['wall_floors'].items():
            kernel_rules.set_wall_floors(rules, k, v)
        for k, v in job['floor_palettes'].items():
            kernel_rules.set_floor_palettes(rules, int(k), v)
        for a, b in job['allow_pairs']:
            kernel_rules.allow_pairs(rules, a, b)
        if not kernel_rules.problems(rules):
            break
    else:
        raise SystemExit('no valid wallset/floor assignment found')
    ext_jobs = [{'type': 'extra_wallset', 'copy': 'Rock', 'count': N_WALLS - 7},
                {'type': 'extra_floors', 'copy': 'Floor-2', 'count': N_FLOORS - 8}] if any(sl in NEW_SLOTS for sl in picks) else []
    jobs = ext_jobs + [job] + \
        [dict(j) for j in ec.FIX_JOBS] + ec.reramp_jobs(list(picks))   # before any art goes in
    summary['wallsets'] = {slot: picks.get(slot, 'dh_' + slot.lower()) for slot in SLOTS + NEW_SLOTS if slot in SLOTS or slot in picks}
    summary['floors'] = {}
    for (slot, src), floor in zip(picks.items(), floors):
        summary['floors'][floor] = src
        if src.startswith('menzo'):
            jobs += menzo_walls.jobs(src, slot, floor)
        elif src.startswith('eob3'):
            _, wall, pal, old = next(s for s in EOB3_SETS if s[0] == src)
            for j in e3jobs:
                if j['target'] in ('%s Wallset' % old, '%s Stairs' % old):
                    jobs.append(retarget(j, old, slot))
            for target, deco in zip(ec_deco_slots(slot), EOB3_DECOS.get(old, [])):
                src_job = next(j for j in e3jobs if j['target'] == deco)
                jobs.append(dict(src_job, target=target, ramp_of=slot + ' Wallset'))
            jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/eob3_%s.png' % wall.split()[0].lower()})
            jobs.append({'type': 'wallset', 'target': '%s Wallset' % slot, 'texture': 'pool/walls/eob3_%s_front.png' % wall.split()[0].lower(), 'frames': '36,199-217'})
            if not any(j['target'] == '%s Stairs' % old for j in e3jobs):      # EOB3 Forest/Ruins have no stairs
                jobs.append({'type': 'stairs_from', 'target': '%s Stairs' % slot, 'donor': EOB3_STAIR_DONOR[src]})
        else:
            _, game, vset, frame_set, stairs_set = next(s for s in WESTWOOD_SETS if s[0] == src)
            jobs.append({'type': 'vmp_walls', 'target': '%s Wallset' % slot, 'game': game, 'set': vset,
                         'plain': [0, 1], 'frame': 2, 'frame_set': frame_set,
                         **({'stairs': '%s Stairs' % slot, 'stairs_set': stairs_set, 'stairs_down': 4, 'stairs_up': 3} if stairs_set else {})})
            if vset != 'FOREST' and slot in SLOTS:      # wallsets 8+ use generic decoration slots
                jobs.append({'type': 'vmp_deco', 'target': '%s decorations' % slot, 'wallset': '%s Wallset' % slot,
                             'game': game, 'set': vset, 'deco': 5, 'base': 0})
            jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/%s_backdrop.png' % vset})
        jobs.append({'type': 'furniture_from', 'target': '%s Wallset' % slot, 'donor': FURNITURE_DONOR[src]})

    # ---- doors (with extra_doors: 16 more door numbers). Every EOB door gets a slot: see-through
    # kinds go to DH's see-through door numbers 3/7/14/17 (the doors script only lets those show
    # what is behind them), the rest fill the new slots first; DH keeps its other original slots.
    door_pool = [('eob1', k) for k in ec.THEMES['eob1_waterdeep']['doors']] + \
                [('eob2', k) for k in ec.THEMES['eob2_darkmoon_classic']['doors']] + [('eob3', d) for d in EOB3_DOORS]
    rng.shuffle(door_pool)
    see_through = [d for d in door_pool if d[1] in SEE_THROUGH_DOORS]
    solid = [d for d in door_pool if d[1] not in SEE_THROUGH_DOORS]
    extra = ['Extra Door %02d' % n for n in range(EXTRA_DOORS)] if extra_doors else []
    if extra:
        jobs.insert(0, {'type': 'extra_doors', 'count': EXTRA_DOORS, 'copy': 'Door-05'})
    assign = {}
    for slot, d in zip(['Door-03', 'Door-07', 'Door-14', 'Door-17'], see_through):
        assign[slot] = d
    solid += see_through[4:]
    for slot in extra + [s_ for s_ in ec.DH_DOORS if s_ not in assign]:
        if not solid:
            break
        if slot in ec.DH_DOORS and not extra and rng.random() < 0.25:
            continue                           # without extra slots, DH keeps about a quarter of its doors
        assign[slot] = solid.pop()
    summary['doors'] = {}
    for slot in ec.DH_DOORS + extra:
        if slot not in assign:
            summary['doors'][slot] = 'dh'; continue
        game, what = assign[slot]
        summary['doors'][slot] = '%s %s' % (game, what)
        if game == 'eob3':
            jobs.append(dict(next(j for j in e3jobs if j['target'] == what), target=slot))
        else:
            jobs.append({'type': 'eob_door', 'target': slot, 'kind': what})

    # ---- generic decorations 29-48: DH tapestries (3 in 10) or EOB1/EOB2 pieces
    deco_pool = [('eob1', d) for d in ec.THEMES['eob1_waterdeep']['wall_decos']] + \
                [('eob2', d) for d in ec.THEMES['eob2_darkmoon_classic']['wall_decos']]
    rng.shuffle(deco_pool)
    summary['generic_decos'] = {}
    for k in range(20):
        target = 'Wall Deco %02d' % (29 + k)
        if rng.random() < 0.3 or not deco_pool:
            summary['generic_decos'][target] = 'dh'; continue
        game, (sheet, dec, epal, index) = deco_pool.pop()
        summary['generic_decos'][target] = '%s %s #%d' % (game, sheet, index)
        jobs.append({'type': 'eob_wall_deco', 'target': target, 'game': game, 'sheet': sheet + '.CPS',
                     'dec': dec + ('.DAT' if game == 'eob1' else '.DEC'), 'pal': epal + '.PAL', 'index': index})

    # ---- wallset decorations: an imported set in one of DH's own 7 slots inherits that slot's 4 decoration
    # resources. EOB1/EOB2 sets replace them (vmp_deco), EOB3 Mausoleum/Ruins 3 of them; Menzo sets, EOB3
    # Forest and EOB2's forest have none, so DH's carvings for that slot would sit on foreign walls. Those
    # get cosmetic EOB decorations (fixed colours, so they suit any wall) instead.
    full = [('eob1', d) for d in ec.THEMES['eob1_waterdeep']['wall_decos']] + \
           [('eob2', d) for d in ec.THEMES['eob2_darkmoon_classic']['wall_decos']]
    rng.shuffle(full)
    summary['slot_decos'] = {}
    k = 0
    for slot, src in picks.items():
        if slot not in SLOTS:
            continue
        if src.startswith('eob3'):
            own = len(EOB3_DECOS.get(next(s3 for s3 in EOB3_SETS if s3[0] == src)[3], []))
        elif src.startswith('menzo'):
            own = 0
        else:
            own = 0 if next(s2 for s2 in WESTWOOD_SETS if s2[0] == src)[2] == 'FOREST' else 4
        for target in ec_deco_slots(slot)[own:]:
            game, (sheet, dec, epal, index) = full[k % len(full)]; k += 1
            summary['slot_decos'][target] = '%s %s #%d' % (game, sheet, index)
            jobs.append({'type': 'eob_wall_deco', 'target': target, 'game': game, 'sheet': sheet + '.CPS',
                         'dec': dec + ('.DAT' if game == 'eob1' else '.DEC'), 'pal': epal + '.PAL', 'index': index})

    # ---- monsters: each DH monster with an EOB counterpart keeps its art or takes one of them
    cands = {}
    for theme in ('eob1_waterdeep', 'eob2_darkmoon_classic'):
        for slot, mon in ec.THEMES[theme]['monsters'].items():
            cands.setdefault(slot, []).append(mon)
    cands.setdefault('Wererat', []).append('eob3_shadow_hound')
    summary['monsters'] = {}
    used = set()
    for slot in sorted(cands):
        choice = rng.choice([None] + [m for m in cands[slot] if m not in used])
        imgs = ['pool/monsters/%s/%d.png' % (choice, i) for i in range(6)] if choice else []
        if choice and all(os.path.exists(os.path.join(ROOT, p)) for p in imgs):
            used.add(choice); summary['monsters'][slot] = choice
            jobs.append({'type': 'sprites', 'target': slot, 'images': imgs})
        else:
            summary['monsters'][slot] = 'dh'

    # ---- in-game music (tools/game_music.py): one track per wallset, looping. MT-32/GM versions come
    # from every source whose tracks passed smoke/music_tracks.py (fits the buffer, no missing timbres,
    # sounds); the AdLib version is always one of DH's own, the only tracks DH's timbre library covers
    summary['music'] = {}
    good = music_pool()
    if good:
        dh_ad = {'dh:Music Scene One Roland': 'dh:Music Scene One Adlib', 'dh:Music Scene Two Roland': 'dh:Music Scene Two Adlib/Pc',
                 'dh:Music End Roland': 'dh:Music End Adlib/Pc'}
        tracks = {}
        for slot in SLOTS + [sl for sl in NEW_SLOTS if sl in picks]:
            src = picks.get(slot, 'dh')
            own = [t for t in good if t.split(':')[0] == src.split('_')[0]]
            fresh = [t for t in own if t not in summary['music'].values()] or \
                    [t for t in good if t not in summary['music'].values()] or own or good   # distinct while the pool lasts
            la = rng.choice(fresh)
            tracks[slot] = {'la': la, 'ad': dh_ad.get(la) or rng.choice(sorted(dh_ad.values()))}
            summary['music'][slot] = la
        jobs.append({'type': 'game_music', 'tracks': tracks})

    # ---- character portraits: about half of DH's, same group (men / women / helmeted-hooded)
    summary['portraits'] = {}
    for group, slots in PORTRAIT_SLOTS.items():
        pool = list(PORTRAITS[group]); rng.shuffle(pool)
        for slot in slots:
            if pool and rng.random() < 0.5:
                face = pool.pop()
                summary['portraits']['Portrait %d' % slot] = face
                jobs.append({'type': 'sprites', 'target': 'Portrait %d' % slot, 'images': ['pool/portraits/%s.png' % face]})

    # ---- audio: EOB3 sound effects and music (fixed, not rolled)
    for rec in ('recipe_sounds.json', 'recipe_music.json'):
        jobs += json.load(open(os.path.join(ROOT, 'pool', rec)))['jobs']
    return {'comment': 'Dungeon Hack+ mix, seed %d: graphics slots filled from DH, EOB1, EOB2, EOB3 (see "mix")' % seed,
            'mix': summary, 'jobs': jobs}


def music_pool():
    """Track specs that passed the in-game track test (tools/music_tracks.json, from smoke/music_tracks.py)."""
    path = os.path.join(HERE, 'music_tracks.json')
    res = json.load(open(path)) if os.path.exists(path) else {}
    return sorted(t for t, v in res.items() if isinstance(v, float) and v >= 0.5)


def ec_deco_slots(slot):
    sys.path.insert(0, ROOT)
    from pipeline import WALL_DECOS        # wallset -> its decoration resources (decoration object's table14)
    return WALL_DECOS.get(slot, [])        # 'Eighth' has none of its own


def describe(summary):
    lines = ['Dungeon Hack+ mix, seed %s' % summary['seed'], '', 'Wallsets (each level picks one):']
    lines += ['  %-7s %s' % (k, v) for k, v in summary['wallsets'].items()]
    lines += ['', 'Doors:'] + ['  %s  %s' % (k, v) for k, v in summary['doors'].items()]
    lines += ['', 'Generic decorations:'] + ['  %s  %s' % (k, v) for k, v in summary['generic_decos'].items()]
    lines += ['', 'Monsters:'] + ['  %-9s %s' % (k, v) for k, v in summary['monsters'].items()]
    if summary.get('music'):
        lines += ['', 'In-game music (per wallset):'] + ['  %-7s %s' % (k, v) for k, v in summary['music'].items()]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'pool', 'recipe_mix.json')
    recipe = roll(seed)
    json.dump(recipe, open(out, 'w'), indent=1)
    print(describe(recipe['mix']))
    print('%d jobs -> %s' % (len(recipe['jobs']), out))
