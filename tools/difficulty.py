"""Difficulty and dungeon generator preset manager for Dungeon Hack.

Reads, creates, and applies SETTINGS.DAT files that control MAZE.EXE's
dungeon generator parameters (documented in Thirdeye & DH disasm):
  * seed: 32-bit PRNG seed (0 = random)
  * depth: Dungeon depth (levels = depth + 10, e.g. 0 = 10 levels, 15 = 25 levels)
  * freq_monsters: Creature spawn frequency (0..7)
  * freq_treasure: Chest and item spawn frequency (0..7)
  * freq_food: Rations spawn frequency (0..7)
  * freq_illusions: Illusionary secret wall frequency (0..7)
  * freq_keys: Key and lock frequency (0..7)
  * freq_traps: Floor spike / dart trap frequency (0..7)
  * freq_pits: Floor / ceiling pit frequency (0..7)
  * hint_sheet_freq: Clue and parchment frequency (0..7)
  * zones_on: Themed dungeon zone divisions (0/1)
  * water_on: Flooded tile generation (0/1)
  * multi_level_puzzles_on: Inter-level activator puzzle generation (0/1)

Curated Presets:
  * classic: Shipped balanced dungeon (15 levels, moderate monsters and traps, zones & water on)
  * treasure_hunt: High loot, plentiful rations, minimal traps/pits, frequent hint sheets
  * iron_crawl: Deep 25-level gauntlet, high monster density, scarce food, deadly traps & pits
  * casual_explorer: 10 levels, light monster presence, abundant food & hints, no traps or pits
  * pacifist_labyrinth: Monster-free exploration maze with illusionary walls, water, and complex puzzles
"""
import argparse
import os
import struct
import sys

FIELDS = [
    ('depth', 'Dungeon Depth (Levels = depth + 10)', 0, 15),
    ('monsters', 'Monster Spawn Frequency', 0, 7),
    ('treasure', 'Treasure / Loot Frequency', 0, 7),
    ('food', 'Food / Rations Frequency', 0, 7),
    ('illusions', 'Illusionary Wall Frequency', 0, 7),
    ('keys', 'Key & Lock Frequency', 0, 7),
    ('traps', 'Trap Frequency', 0, 7),
    ('pits', 'Pit Frequency', 0, 7),
    ('hints', 'Hint Sheet Frequency', 0, 7),
    ('zones', 'Themed Zones Division', 0, 1),
    ('water', 'Flooded Dungeon Areas', 0, 1),
    ('puzzles', 'Multi-Level Puzzles', 0, 1),
]

PRESETS = {
    'classic': {
        'name': 'Classic Dungeon Hack',
        'desc': 'Balanced default adventure (15 levels, moderate spawns & traps, zones & water active)',
        'seed': 0, 'depth': 5, 'monsters': 4, 'treasure': 4, 'food': 4,
        'illusions': 4, 'keys': 4, 'traps': 4, 'pits': 4, 'hints': 4,
        'zones': 1, 'water': 1, 'puzzles': 0
    },
    'treasure_hunt': {
        'name': 'Treasure Hunt',
        'desc': 'Generous loot and provisions, reduced traps and pits, plentiful clues',
        'seed': 0, 'depth': 2, 'monsters': 2, 'treasure': 7, 'food': 7,
        'illusions': 3, 'keys': 5, 'traps': 1, 'pits': 1, 'hints': 7,
        'zones': 1, 'water': 1, 'puzzles': 0
    },
    'iron_crawl': {
        'name': 'Iron Crawl (Hardcore)',
        'desc': 'Brutal 25-level endurance test: dense monsters, scarce rations, deadly traps & multi-level puzzles',
        'seed': 0, 'depth': 15, 'monsters': 7, 'treasure': 5, 'food': 1,
        'illusions': 6, 'keys': 7, 'traps': 7, 'pits': 7, 'hints': 1,
        'zones': 1, 'water': 1, 'puzzles': 1
    },
    'casual_explorer': {
        'name': 'Casual Explorer',
        'desc': 'Relaxed 10-level dungeon: light monsters, maximum food & hint sheets, zero traps or pits',
        'seed': 0, 'depth': 0, 'monsters': 1, 'treasure': 6, 'food': 7,
        'illusions': 2, 'keys': 3, 'traps': 0, 'pits': 0, 'hints': 7,
        'zones': 0, 'water': 0, 'puzzles': 0
    },
    'pacifist_labyrinth': {
        'name': 'Pacifist Labyrinth',
        'desc': 'Zero monsters, high illusionary walls, water hazards, and complex inter-level puzzles',
        'seed': 0, 'depth': 8, 'monsters': 0, 'treasure': 4, 'food': 6,
        'illusions': 7, 'keys': 7, 'traps': 2, 'pits': 2, 'hints': 5,
        'zones': 1, 'water': 1, 'puzzles': 1
    },
}

# Shipped trailer bytes after offset 16
TRAILER = bytes.fromhex('0000000700000002000000')


def pack_settings(seed=0, depth=0, monsters=4, treasure=4, food=4, illusions=4,
                  keys=4, traps=4, pits=4, hints=4, zones=1, water=1, puzzles=0):
    buf = bytearray(27)
    struct.pack_into('<I', buf, 0, seed & 0xFFFFFFFF)
    buf[4] = depth & 0xFF
    buf[5] = monsters & 0xFF
    buf[6] = treasure & 0xFF
    buf[7] = food & 0xFF
    buf[8] = illusions & 0xFF
    buf[9] = keys & 0xFF
    buf[10] = traps & 0xFF
    buf[11] = pits & 0xFF
    buf[12] = hints & 0xFF
    buf[13] = 1 if zones else 0
    buf[14] = 1 if water else 0
    buf[15] = 1 if puzzles else 0
    buf[16:27] = TRAILER
    return bytes(buf)


def unpack_settings(data):
    if len(data) < 16:
        raise ValueError(f'SETTINGS.DAT too short ({len(data)} bytes, expected 27)')
    seed = struct.unpack_from('<I', data, 0)[0]
    vals = {'seed': seed}
    for i, (key, _, _, _) in enumerate(FIELDS):
        vals[key] = data[4 + i]
    return vals


def inspect_settings(path):
    if not os.path.exists(path):
        print(f'File not found: {path}')
        return None
    data = open(path, 'rb').read()
    vals = unpack_settings(data)
    print(f'=== Dungeon Settings: {path} ({len(data)} bytes) ===')
    seed_str = f'{vals["seed"]:#010x} ({vals["seed"]})' if vals["seed"] != 0 else '0 (Random)'
    print(f'  Seed               : {seed_str}')
    print(f'  Total Levels       : {vals["depth"] + 10} (depth setting: {vals["depth"]})')
    for key, desc, min_v, max_v in FIELDS[1:]:
        print(f'  {desc:<28}: {vals[key]} [{min_v}..{max_v}]')
    return vals


def apply_preset(preset_name, target_dir):
    if preset_name not in PRESETS:
        print(f'Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}')
        return False
    p = PRESETS[preset_name]
    save_dir = os.path.join(target_dir, 'savegame')
    if not os.path.exists(save_dir):
        # Case-insensitive search
        for c in os.listdir(target_dir):
            if c.lower() == 'savegame':
                save_dir = os.path.join(target_dir, c)
                break
    os.makedirs(save_dir, exist_ok=True)
    out_file = os.path.join(save_dir, 'SETTINGS.DAT')

    data = pack_settings(
        seed=p['seed'], depth=p['depth'], monsters=p['monsters'],
        treasure=p['treasure'], food=p['food'], illusions=p['illusions'],
        keys=p['keys'], traps=p['traps'], pits=p['pits'], hints=p['hints'],
        zones=p['zones'], water=p['water'], puzzles=p['puzzles']
    )
    with open(out_file, 'wb') as f:
        f.write(data)

    print(f'Applied preset "{p["name"]}" -> {out_file}')
    print(f'  Description: {p["desc"]}')
    print(f'  Levels: {p["depth"] + 10}, Monsters: {p["monsters"]}, Treasure: {p["treasure"]}, Food: {p["food"]}, Traps: {p["traps"]}')
    return True


def main():
    parser = argparse.ArgumentParser(description='Dungeon Hack difficulty preset manager')
    sub = parser.add_subparsers(dest='command')

    # list
    sub.add_parser('list', help='List available difficulty presets')

    # inspect
    p_ins = sub.add_parser('inspect', help='Inspect an existing SETTINGS.DAT')
    p_ins.add_argument('path', help='Path to SETTINGS.DAT')

    # apply
    p_app = sub.add_parser('apply', help='Apply a preset to a build/game folder')
    p_app.add_argument('preset', choices=list(PRESETS.keys()), help='Preset name')
    p_app.add_argument('target', default='Dungeon Hack', nargs='?', help='Target build or game directory')

    # custom
    p_cust = sub.add_parser('custom', help='Create custom settings')
    p_cust.add_argument('target', default='Dungeon Hack', nargs='?', help='Target build or game directory')
    p_cust.add_argument('--seed', type=int, default=0, help='PRNG seed (0=random)')
    p_cust.add_argument('--depth', type=int, default=5, help='Depth 0..15 (Levels = depth + 10)')
    p_cust.add_argument('--monsters', type=int, default=4, help='Monsters frequency 0..7')
    p_cust.add_argument('--treasure', type=int, default=4, help='Treasure frequency 0..7')
    p_cust.add_argument('--food', type=int, default=4, help='Food frequency 0..7')
    p_cust.add_argument('--illusions', type=int, default=4, help='Illusionary walls 0..7')
    p_cust.add_argument('--keys', type=int, default=4, help='Keys frequency 0..7')
    p_cust.add_argument('--traps', type=int, default=4, help='Traps frequency 0..7')
    p_cust.add_argument('--pits', type=int, default=4, help='Pits frequency 0..7')
    p_cust.add_argument('--hints', type=int, default=4, help='Hints frequency 0..7')
    p_cust.add_argument('--zones', type=int, default=1, help='Zones on (0/1)')
    p_cust.add_argument('--water', type=int, default=1, help='Water on (0/1)')
    p_cust.add_argument('--puzzles', type=int, default=0, help='Multi-level puzzles (0/1)')

    args = parser.parse_args()

    if args.command == 'list':
        print('=== Available Difficulty Presets ===')
        for k, v in PRESETS.items():
            print(f'  * {k:<20}: {v["name"]} - {v["desc"]}')
    elif args.command == 'inspect':
        inspect_settings(args.path)
    elif args.command == 'apply':
        apply_preset(args.preset, args.target)
    elif args.command == 'custom':
        save_dir = os.path.join(args.target, 'savegame')
        os.makedirs(save_dir, exist_ok=True)
        out_file = os.path.join(save_dir, 'SETTINGS.DAT')
        data = pack_settings(
            seed=args.seed, depth=args.depth, monsters=args.monsters,
            treasure=args.treasure, food=args.food, illusions=args.illusions,
            keys=args.keys, traps=args.traps, pits=args.pits, hints=args.hints,
            zones=args.zones, water=args.water, puzzles=args.puzzles
        )
        with open(out_file, 'wb') as f:
            f.write(data)
        print(f'Wrote custom settings to {out_file}')
        inspect_settings(out_file)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
