"""EOB3 to Dungeon Hack asset mapping and recipe generator.

Maps all 4 EOB3 wallsets, stairs, and doors to DH slots:
  * Marble: walls (idx 297), stairs up/down (331/330), door (298) -> Marble Wallset / Marble Stairs / Door-05
  * Mausoleum: walls (idx 253), stairs up/down (266/267), skull door (257) -> Wood Wallset / Wood Stairs / Door-06
  * Ruins: walls (idx 236), wooden door (238, 90 frames -> drop 5th block), crystal door (240) -> Rock Wallset / Door-07
  * Forest: walls (idx 228) -> Stone Wallset (native 2-ramp)
  * Temple: gold door (277), mask door (282) -> Door-08, Door-09

Generates validated recipe jobs and pool presets.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, MASHUP)
import aesop
import kernel_rules
import normalize

EOB3_WALL_SETS = {
    'marble': {
        'name': 'EOB3 Marble',
        'wall': 'Marble walls',
        'palette': 'Marble palette',
        'ramp': 'single',
        'stairs_down': 'Marble stairs down',
        'stairs_up': 'Marble stairs up',
        'doors': [('Marble door', 'Door-05', 72)],
        'dh_wallset': 'Marble Wallset',
        'dh_stairs': 'Marble Stairs',
    },
    'mausoleum': {
        'name': 'EOB3 Mausoleum',
        'wall': 'Mausoleum walls',
        'palette': 'Mausoleum palette',
        'ramp': 'double',
        'stairs_down': 'Mausoleum stairs down',
        'stairs_up': 'Mausoleum stairs up',
        'doors': [
            ('Mausoleum skull door', 'Door-06', 72),
            ('Mausoleum Star Trek(TM) door', 'Door-07', 72),
        ],
        'dh_wallset': 'Wood Wallset',
        'dh_stairs': 'Wood Stairs',
    },
    'ruins': {
        'name': 'EOB3 Ruins',
        'wall': 'Ruins walls',
        'palette': 'Ruins palette',
        'ramp': 'double',
        'stairs_down': None,
        'stairs_up': None,
        'doors': [
            ('Ruins wooden door', 'Door-08', 90),
            ('Ruins crystal door', 'Door-09', 72),
        ],
        'dh_wallset': 'Rock Wallset',
        'dh_stairs': None,
    },
    'forest': {
        'name': 'EOB3 Forest',
        'wall': 'Forest walls',
        'palette': 'Forest palette',
        'ramp': 'double',
        'stairs_down': None,
        'stairs_up': None,
        'doors': [],
        'dh_wallset': 'Stone Wallset',
        'dh_stairs': None,
    },
    'temple': {
        'name': 'EOB3 Temple (Doors Only)',
        'wall': None,
        'palette': 'Fixed palette',
        'ramp': 'single',
        'stairs_down': None,
        'stairs_up': None,
        'doors': [
            ('Temple gold door', 'Door-11', 72),
            ('Temple mask door', 'Door-18', 90),
        ],
        'dh_wallset': None,
        'dh_stairs': None,
    },
}

EOB3_DECORATIONS = [
    ('Marble elven tapestry', 'Wall Deco 00', 'Marble palette', 'Marble Wallset'),
    ('Marble air tapestry', 'Wall Deco 01', 'Marble palette', 'Marble Wallset'),
    ('Marble fire tapestry', 'Wall Deco 02', 'Marble palette', 'Marble Wallset'),
    ('Marble water tapestry', 'Wall Deco 03', 'Marble palette', 'Marble Wallset'),
    ('Marble earth tapestry', 'Wall Deco 04', 'Marble palette', 'Marble Wallset'),
    ('Marble niche', 'Wall Deco 05', 'Marble palette', 'Marble Wallset'),
    ('Marble plaque', 'Wall Deco 06', 'Marble palette', 'Marble Wallset'),
    ('Marble valve', 'Wall Deco 07', 'Marble palette', 'Marble Wallset'),
    ('Marble censer', 'Wall Deco 08', 'Marble palette', 'Marble Wallset'),
    ('Mausoleum plaque', 'Wall Deco 09', 'Mausoleum palette', 'Wood Wallset'),
    ('Mausoleum wall spikes', 'Wall Deco 10', 'Mausoleum palette', 'Wood Wallset'),
    ('Mausoleum nameplate', 'Wall Deco 11', 'Mausoleum palette', 'Wood Wallset'),
    ('Ruins plaque', 'Wall Deco 12', 'Ruins palette', 'Rock Wallset'),
    ('Ruins niche', 'Wall Deco 13', 'Ruins palette', 'Rock Wallset'),
    ('Ruins square niche', 'Wall Deco 14', 'Ruins palette', 'Rock Wallset'),
    ('Temple censer', 'Wall Deco 15', 'Fixed palette', 'Marble Wallset'),
    ('Temple font', 'Wall Deco 16', 'Fixed palette', 'Marble Wallset'),
    ('Temple niche', 'Wall Deco 17', 'Fixed palette', 'Marble Wallset'),
]

EOB3_KEYHOLES = [
    ('Marble brass keyhole', 'Keyhole 00', 'Marble palette', 'Marble Wallset'),
    ('Marble copper keyhole', 'Keyhole 01', 'Marble palette', 'Marble Wallset'),
    ('Marble silver keyhole', 'Keyhole 02', 'Marble palette', 'Marble Wallset'),
    ('Marble crystal keyhole', 'Keyhole 03', 'Marble palette', 'Marble Wallset'),
    ('Ruins keyhole', 'Keyhole 04', 'Ruins palette', 'Rock Wallset'),
    ('Temple copper lock', 'Keyhole 05', 'Fixed palette', 'Marble Wallset'),
    ('Temple iron lock', 'Keyhole 06', 'Fixed palette', 'Marble Wallset'),
    ('Temple gold lock', 'Keyhole 07', 'Fixed palette', 'Marble Wallset'),
    ('Temple crystal lock', 'Keyhole 08', 'Fixed palette', 'Marble Wallset'),
    ('Temple fire lock', 'Keyhole 09', 'Fixed palette', 'Marble Wallset'),
    ('Temple frost lock', 'Keyhole 10', 'Fixed palette', 'Marble Wallset'),
    ('Mausoleum holy lock', 'Keyhole 11', 'Mausoleum palette', 'Wood Wallset'),
]

EOB3_LEVERS = [
    ('Marble lever', 'Lever 00', 'Marble palette', 'Marble Wallset'),
    ('Marble magic lever', 'Lever 01', 'Marble palette', 'Marble Wallset'),
    ('Marble rusted lever', 'Lever 02', 'Marble palette', 'Marble Wallset'),
    ('Marble button', 'Lever 03', 'Marble palette', 'Marble Wallset'),
    ('Temple gold lever', 'Lever 04', 'Fixed palette', 'Marble Wallset'),
    ('Temple secret handle', 'Lever 05', 'Fixed palette', 'Marble Wallset'),
    ('Mausoleum button', 'Lever 06', 'Mausoleum palette', 'Wood Wallset'),
    ('Mausoleum drawers', 'Lever 07', 'Mausoleum palette', 'Wood Wallset'),
]


def build_set_recipe(set_key):
    """Generate pipeline recipe jobs for an EOB3 theme set."""
    info = EOB3_WALL_SETS[set_key]
    jobs = []

    # 1. Palette rules if needed
    if info['ramp'] == 'double' and info['dh_wallset']:
        # If targeting a wallset that originally used single ramp, update rules to 2-ramp (15..20)
        stem = info['dh_wallset'].split()[0]
        if stem != 'Stone':
            jobs.append({
                'type': 'palette_rules',
                'target': 'kernel',
                'wall_palettes': {info['dh_wallset']: [15, 16, 17, 18, 19, 20]},
            })

    # 2. Wallset jobs
    if info['wall'] and info['dh_wallset']:
        # Copy plain wall panels (0..17)
        jobs.append({
            'type': 'panels',
            'target': info['dh_wallset'],
            'target_first': 0,
            'count': 18,
            'source': info['wall'],
            'source_first': 0,
            'source_palette': info['palette'],
        })

    # 3. Doors (frame -> wallset object 1 slots 18..35, stages -> Door-xx slots 0..53)
    for door_src, dh_door, total_shapes in info['doors']:
        if info['dh_wallset']:
            # Door frame into wallset object 1
            jobs.append({
                'type': 'panels',
                'target': info['dh_wallset'],
                'target_first': 18,
                'count': 18,
                'source': door_src,
                'source_first': 0,
                'source_palette': info['palette'],
            })
        # 3 stages into Door-xx
        jobs.append({
            'type': 'panels',
            'target': dh_door,
            'target_first': 0,
            'count': 54,
            'source': door_src,
            'source_first': 18,
            'source_palette': info['palette'],
        })

    # 4. Stairs (down 0..17, up 18..35)
    if info['stairs_down'] and info['stairs_up'] and info['dh_stairs']:
        jobs.append({
            'type': 'panels',
            'target': info['dh_stairs'],
            'target_first': 0,
            'count': 18,
            'source': info['stairs_down'],
            'source_first': 0,
            'source_palette': info['palette'],
        })
        jobs.append({
            'type': 'panels',
            'target': info['dh_stairs'],
            'target_first': 18,
            'count': 18,
            'source': info['stairs_up'],
            'source_first': 0,
            'source_palette': info['palette'],
        })

    return {'comment': f'{info["name"]} complete port to Dungeon Hack', 'jobs': jobs}


def build_decorations_recipe():
    """Generate pipeline recipe jobs for EOB3 decorations, keyholes, and levers."""
    jobs = []

    # Wall Decorations (18 panels)
    for src, dst, pal, ramp_of in EOB3_DECORATIONS:
        jobs.append({
            'type': 'panels',
            'target': dst,
            'target_first': 0,
            'count': 18,
            'source': src,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': ramp_of,
        })

    # Keyholes (18 panels)
    for src, dst, pal, ramp_of in EOB3_KEYHOLES:
        jobs.append({
            'type': 'panels',
            'target': dst,
            'target_first': 0,
            'count': 18,
            'source': src,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': ramp_of,
        })

    # Levers & Buttons (36 panels = 2 positions x 18)
    for src, dst, pal, ramp_of in EOB3_LEVERS:
        jobs.append({
            'type': 'panels',
            'target': dst,
            'target_first': 0,
            'count': 36,
            'source': src,
            'source_first': 0,
            'source_palette': pal,
            'ramp_of': ramp_of,
        })

    return {'comment': 'EOB3 wall decorations, keyholes, and levers port to Dungeon Hack', 'jobs': jobs}


def export_all_recipes():
    out_dir = os.path.join(MASHUP, 'pool')
    os.makedirs(out_dir, exist_ok=True)

    generated = {}
    for key in EOB3_WALL_SETS:
        rec = build_set_recipe(key)
        fn = f'recipe_eob3_{key}.json'
        fp = os.path.join(out_dir, fn)
        with open(fp, 'w') as f:
            json.dump(rec, f, indent=1)
        generated[key] = fp
        print(f'Generated {fn} ({len(rec["jobs"])} jobs)')

    # Standalone decorations recipe
    deco_rec = build_decorations_recipe()
    deco_fp = os.path.join(out_dir, 'recipe_eob3_decorations.json')
    with open(deco_fp, 'w') as f:
        json.dump(deco_rec, f, indent=1)
    generated['decorations'] = deco_fp
    print(f'Generated recipe_eob3_decorations.json ({len(deco_rec["jobs"])} jobs)')

    # Composite complete EOB3 mashup recipe
    composite_jobs = []
    seen_targets = set()
    for key in ['marble', 'mausoleum', 'ruins', 'forest', 'temple']:
        rec = build_set_recipe(key)
        for j in rec['jobs']:
            tag = (j['type'], j.get('target'), j.get('target_first'))
            if tag not in seen_targets:
                seen_targets.add(tag)
                composite_jobs.append(j)

    for j in deco_rec['jobs']:
        tag = (j['type'], j.get('target'), j.get('target_first'))
        if tag not in seen_targets:
            seen_targets.add(tag)
            composite_jobs.append(j)

    comp_rec = {
        'comment': 'Complete EOB3 Mega-Mashup: 4 wallsets, 2 stairsets, 6 doors, 18 decorations, 12 keyholes, 8 levers with rule-consistent palettes',
        'jobs': composite_jobs,
    }
    comp_path = os.path.join(out_dir, 'recipe_eob3_complete.json')
    with open(comp_path, 'w') as f:
        json.dump(comp_rec, f, indent=1)
    print(f'Generated recipe_eob3_complete.json ({len(composite_jobs)} jobs)')

    return generated


if __name__ == '__main__':
    export_all_recipes()
