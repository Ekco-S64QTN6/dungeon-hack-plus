"""Comprehensive build-time randomizer for Dungeon Hack+.

Generates randomized, rule-consistent cross-engine mashup recipes covering:
- Wallsets (EOB3 1:1 panel copies + Westwood flat textures)
- Palette pairing rules (ensuring single-ramp vs two-ramp consistency)
- Animated doors (72-frame doors mapped to Door-05..Door-18)
- Stairways (Marble and Mausoleum)
- Wall decorations, keyholes, and levers
- 57 monster targets reskinned from 40 authentic creature frames
- Restored 8 kHz sound effects (doors, mechanisms, creatures)
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eob3_mapping


def roll_recipe(pool_path, seed, name):
    rng = random.Random(int(seed))
    with open(pool_path) as f:
        pool = json.load(f)

    jobs = []
    wall_pal_rules = {}

    # 1. Wallsets & Doors
    # 7 native DH wallsets:
    # Marble Wallset, Wood Wallset, Rock Wallset, Stone Wallset, Foil Wallset, Ice Wallset, Mine Wallset
    available_eob3_sets = ['marble', 'mausoleum', 'ruins', 'forest']
    dh_wallsets = list(pool.get('wall_targets', [
        'Marble Wallset', 'Wood Wallset', 'Rock Wallset',
        'Stone Wallset', 'Foil Wallset', 'Ice Wallset', 'Mine Wallset'
    ]))

    # Pick 2-4 wallsets to receive full EOB3 panel-level overhauls
    num_eob3 = rng.randint(2, 4)
    chosen_eob3_keys = rng.sample(available_eob3_sets, min(num_eob3, len(available_eob3_sets)))

    used_dh_wallsets = set()
    for eob3_key in chosen_eob3_keys:
        info = eob3_mapping.EOB3_WALL_SETS[eob3_key]
        default_target = info['dh_wallset']
        if default_target and default_target in dh_wallsets and default_target not in used_dh_wallsets:
            target_wallset = default_target
        else:
            candidates = [w for w in dh_wallsets if w not in used_dh_wallsets]
            target_wallset = rng.choice(candidates) if candidates else dh_wallsets[0]

        used_dh_wallsets.add(target_wallset)

        # Palette rule consistency: two-ramp vs single-ramp
        if info['ramp'] == 'double':
            wall_pal_rules[target_wallset] = [15, 16, 17, 18, 19, 20]
        else:
            wall_pal_rules[target_wallset] = [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]

        # Copy wall panels (0..17)
        if info['wall']:
            jobs.append({
                'type': 'panels',
                'target': target_wallset,
                'target_first': 0,
                'count': 18,
                'source': info['wall'],
                'source_first': 0,
                'source_palette': info['palette']
            })

        # Doors for this set
        for door_src, dh_door, total_shapes in info['doors']:
            # Door frame into wallset object 1 (18..35)
            jobs.append({
                'type': 'panels',
                'target': target_wallset,
                'target_first': 18,
                'count': 18,
                'source': door_src,
                'source_first': 0,
                'source_palette': info['palette']
            })
            # Door animated stages into Door-xx (0..53)
            # 5-stage doors (90 frames) truncate 5th stage (frames 72..89)
            jobs.append({
                'type': 'panels',
                'target': dh_door,
                'target_first': 0,
                'count': 54,
                'source': door_src,
                'source_first': 18,
                'source_palette': info['palette']
            })

        # Stairs if available
        if info.get('stairs_down') and info.get('dh_stairs'):
            jobs.append({
                'type': 'panels',
                'target': info['dh_stairs'],
                'target_first': 0,
                'count': 18,
                'source': info['stairs_down'],
                'source_first': 0,
                'source_palette': info['palette']
            })
        if info.get('stairs_up') and info.get('dh_stairs'):
            jobs.append({
                'type': 'panels',
                'target': info['dh_stairs'],
                'target_first': 18,
                'count': 18,
                'source': info['stairs_up'],
                'source_first': 0,
                'source_palette': info['palette']
            })

    # Remaining wallsets: optionally texture from Westwood pool
    remaining_wallsets = [w for w in dh_wallsets if w not in used_dh_wallsets]
    for w in remaining_wallsets:
        if pool.get('walls') and rng.random() > 0.2:
            tex = rng.choice(pool['walls'])
            jobs.append({
                'type': 'wallset',
                'target': w,
                'frames': '0-35',   # wall object 0 + door frame (object 1)
                'texture': tex
            })

    # Add palette_rules job if any wallset modified its ramp type
    if wall_pal_rules:
        jobs.insert(0, {
            'type': 'palette_rules',
            'target': 'kernel',
            'wall_palettes': wall_pal_rules
        })

    # 2. Decorations, Keyholes & Levers (Pick 10-15 random decorations)
    decos = list(eob3_mapping.EOB3_DECORATIONS)
    keyholes = list(eob3_mapping.EOB3_KEYHOLES)
    levers = list(eob3_mapping.EOB3_LEVERS)

    num_decos = rng.randint(8, 14)
    for src_name, dh_target, pal, default_wallset in rng.sample(decos, min(num_decos, len(decos))):
        jobs.append({
            'type': 'panels',
            'target': dh_target,
            'target_first': 0,
            'count': 18,
            'source': src_name,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': default_wallset
        })

    num_keys = rng.randint(4, 8)
    for src_name, dh_target, pal, default_wallset in rng.sample(keyholes, min(num_keys, len(keyholes))):
        jobs.append({
            'type': 'panels',
            'target': dh_target,
            'target_first': 0,
            'count': 18,
            'source': src_name,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': default_wallset
        })

    num_levs = rng.randint(4, 6)
    for src_name, dh_target, pal, default_wallset in rng.sample(levers, min(num_levs, len(levers))):
        jobs.append({
            'type': 'panels',
            'target': dh_target,
            'target_first': 0,
            'count': 18,
            'source': src_name,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': default_wallset
        })

    # 3. Floors & Ceilings
    if pool.get('floors'):
        for f_target in pool.get('floor_targets', []):
            if rng.random() > 0.3:
                jobs.append({
                    'type': 'floor',
                    'target': f_target,
                    'image': rng.choice(pool['floors'])
                })

    # 4. Monsters (All 57 DH slots covered from 40 monster pool)
    monster_pool = list(pool.get('monsters', []))
    targets = list(pool.get('monster_targets', []))
    rng.shuffle(monster_pool)

    # Distribute monster skins across targets
    for i, target in enumerate(targets):
        if rng.random() > 0.15:  # 85% chance to reskin each monster slot
            mon = monster_pool[i % len(monster_pool)]
            jobs.append({
                'type': 'sprites',
                'target': target,
                'images': mon['images']
            })

    # 5. Sounds
    sound_rec_path = os.path.join(PROJECT_ROOT, 'pool', 'recipe_sounds.json')
    if os.path.exists(sound_rec_path):
        with open(sound_rec_path) as sf:
            s_rec = json.load(sf)
        # Include door/mechanism sounds + sample of monster sounds
        for sj in s_rec.get('jobs', []):
            if sj['target'].startswith(('DOOR', 'S-')) or rng.random() > 0.4:
                jobs.append(sj)

    recipe_data = {
        'comment': f'Procedural Rolled Mashup (Seed: {seed}) with ramp-consistent wallsets, doors, 57-monster pool, and 8 kHz audio',
        'seed': int(seed),
        'jobs': jobs
    }

    out_recipe_path = os.path.join(PROJECT_ROOT, 'pool', f'rolled_{name}_{seed}.json')
    with open(out_recipe_path, 'w') as f:
        json.dump(recipe_data, f, indent=2)

    return out_recipe_path
