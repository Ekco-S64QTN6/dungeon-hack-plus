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

SLOTS = ['Marble', 'Wood', 'Stone', 'Foil', 'Ice', 'Mine', 'Rock']        # kernel wallnum order

# external wallsets: (id, game, set, frame set, stairs set)
WESTWOOD_SETS = [('eob1_' + s.lower(), 'eob1', s, f, st) for s, _, f, st in ec.THEMES['eob1_waterdeep']['sets']] + \
                [('eob2_' + s.lower(), 'eob2', s, f, st) for s, _, f, st in ec.THEMES['eob2_darkmoon_classic']['sets']]
# EOB3: (id, wall object, palette, DH slot its jobs target in recipe_eob3_complete)
EOB3_SETS = [('eob3_mausoleum', 'Mausoleum walls', 'Mausoleum palette', 'Wood'),
             ('eob3_ruins', 'Ruins walls', 'Ruins palette', 'Rock'),
             ('eob3_forest', 'Forest walls', 'Forest palette', 'Stone')]
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


def roll(seed=1, external=5):
    rng = random.Random(seed)
    dh = aesop.ResFile(os.path.join(ROOT, 'base_games', 'dungeon_hack', 'HACK.RES')); n = dh.names()
    kernel = dh.entry(n['kernel'])[2]
    pals = {p: aesop.decode_palette(dh.entry(n['wall/floor palette %02d' % p])[2])[1] for p in range(21)}
    e3 = aesop.ResFile(os.path.join(ROOT, 'base_games', 'eob3', 'EYE.RES'))
    e3jobs = eob3_jobs()
    summary = {'seed': seed}

    # ---- wallsets: which DH slots get external sets, and which sets
    sources = [s[0] for s in WESTWOOD_SETS] + [s[0] for s in EOB3_SETS]
    for attempt in range(500):
        ext_slots = rng.sample(SLOTS, external)
        picks = dict(zip(ext_slots, rng.sample(sources, external)))
        floors = rng.sample(range(8), external)
        rules = kernel_rules.read(kernel)
        job = {'type': 'palette_rules', 'target': 'kernel', 'wall_palettes': {}, 'wall_floors': {},
               'floor_palettes': {}, 'allow_pairs': []}
        for (slot, src), floor in zip(picks.items(), floors):
            if src.startswith('eob3'):
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
        free = [f for f in range(8) if f not in floors]
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
    jobs = [job] + [dict(j) for j in ec.FIX_JOBS] + ec.reramp_jobs(list(picks))   # before any art goes in
    summary['wallsets'] = {slot: picks.get(slot, 'dh_' + slot.lower()) for slot in SLOTS}
    summary['floors'] = {}
    for (slot, src), floor in zip(picks.items(), floors):
        summary['floors'][floor] = src
        if src.startswith('eob3'):
            _, wall, pal, old = next(s for s in EOB3_SETS if s[0] == src)
            for j in e3jobs:
                if j['target'] in ('%s Wallset' % old, '%s Stairs' % old):
                    jobs.append(retarget(j, old, slot))
            for target, deco in zip(ec_deco_slots(slot), EOB3_DECOS.get(old, [])):
                src_job = next(j for j in e3jobs if j['target'] == deco)
                jobs.append(dict(src_job, target=target, ramp_of=slot + ' Wallset'))
            jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/eob3_%s.png' % wall.split()[0].lower()})
        else:
            _, game, vset, frame_set, stairs_set = next(s for s in WESTWOOD_SETS if s[0] == src)
            jobs.append({'type': 'vmp_walls', 'target': '%s Wallset' % slot, 'game': game, 'set': vset,
                         'plain': [0, 1], 'frame': 2, 'frame_set': frame_set,
                         **({'stairs': '%s Stairs' % slot, 'stairs_set': stairs_set, 'stairs_down': 4, 'stairs_up': 3} if stairs_set else {})})
            if vset != 'FOREST':
                jobs.append({'type': 'vmp_deco', 'target': '%s decorations' % slot, 'wallset': '%s Wallset' % slot,
                             'game': game, 'set': vset, 'deco': 5, 'base': 0})
            jobs.append({'type': 'floor', 'target': 'Floor-%d' % floor, 'image': 'pool/floors/%s_backdrop.png' % vset})

    # ---- doors: each of the 16 door slots keeps DH art (1 in 4) or takes an EOB door
    door_pool = [('eob1', k) for k in ec.THEMES['eob1_waterdeep']['doors']] + \
                [('eob2', k) for k in ec.THEMES['eob2_darkmoon_classic']['doors']] + [('eob3', d) for d in EOB3_DOORS]
    rng.shuffle(door_pool)
    summary['doors'] = {}
    for slot in ec.DH_DOORS:
        if rng.random() < 0.25 or not door_pool:
            summary['doors'][slot] = 'dh'; continue
        game, what = door_pool.pop()
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

    # ---- audio: EOB3 sound effects and music (fixed, not rolled)
    for rec in ('recipe_sounds.json', 'recipe_music.json'):
        jobs += json.load(open(os.path.join(ROOT, 'pool', rec)))['jobs']
    return {'comment': 'Dungeon Hack+ mix, seed %d: graphics slots filled from DH, EOB1, EOB2, EOB3 (see "mix")' % seed,
            'mix': summary, 'jobs': jobs}


def ec_deco_slots(slot):
    sys.path.insert(0, ROOT)
    from pipeline import WALL_DECOS        # wallset -> its decoration resources (decoration object's table14)
    return WALL_DECOS[slot]


def describe(summary):
    lines = ['Dungeon Hack+ mix, seed %s' % summary['seed'], '', 'Wallsets (each level picks one):']
    lines += ['  %-7s %s' % (k, v) for k, v in summary['wallsets'].items()]
    lines += ['', 'Doors:'] + ['  %s  %s' % (k, v) for k, v in summary['doors'].items()]
    lines += ['', 'Generic decorations:'] + ['  %s  %s' % (k, v) for k, v in summary['generic_decos'].items()]
    lines += ['', 'Monsters:'] + ['  %-9s %s' % (k, v) for k, v in summary['monsters'].items()]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'pool', 'recipe_mix.json')
    recipe = roll(seed)
    json.dump(recipe, open(out, 'w'), indent=1)
    print(describe(recipe['mix']))
    print('%d jobs -> %s' % (len(recipe['jobs']), out))
