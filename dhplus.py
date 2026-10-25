#!/usr/bin/env python3
"""Dungeon Hack+ (dhplus) — Unified patcher, preset manager, and launcher.

Non-destructive modding tool and patcher for Dungeon Hack:
  * Detects legally acquired base games in base_games/ and validates SHA-256 hashes.
  * Backs up pristine files before any modification.
  * Builds verified cross-engine mashups from recipes (EOB1, EOB2, EOB3, Menzo).
  * Applies difficulty/generator presets (depth, monster frequency, loot, traps).
  * Launches playable builds with curated DOSBox-Staging settings.
  * Provides rollback and full automated regression testing.

Zero proprietary game files are distributed with this software.
Never modifies original game files; all builds live under build/<name>/.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tools'))
import difficulty
import paths

# Known clean SHA256 hashes for GOG / Retail English Dungeon Hack & expansions
KNOWN_HASHES = {
    'HACK.RES': ('207eaf4081eee453c718fc8f761a707ab5c36bf974255185e2bc90ebe84cac66', 'Dungeon Hack main archive'),
    'OPEN.RES': ('7bc61e506cbf3aa144acc1b6dd6992ba0e2267d1f7b29294e9eaac83dcf61486', 'Dungeon Hack intro cinematic'),
    'EYE.RES':  ('dfdb3fcb089c2c62c3e414c81062b08a0d783a37ba772ee6b5f4c4cbe9e0fc02', 'Eye of the Beholder III archive'),
}

PRESET_RECIPES = {
    'eob3_complete': 'pool/recipe_eob3_complete.json',
    'eob3_marble': 'pool/recipe_eob3_marble.json',
    'eob3_mausoleum': 'pool/recipe_eob3_mausoleum.json',
    'eob3_ruins': 'pool/recipe_eob3_ruins.json',
    'eob3_forest': 'pool/recipe_eob3_forest.json',
    'eob3_decorations': 'pool/recipe_eob3_decorations.json',
    'eob1_sewers': 'pool/recipe_eob1_sewers.json',
    'eob2_darkmoon': 'pool/recipe_eob2_darkmoon.json',
    'mixed': 'pool/recipe_mixed.json',
    'sounds': 'pool/recipe_sounds.json',
    'music': 'pool/recipe_music.json',
    'demo2': 'pool/recipe_demo2.json',
    'demo3': 'pool/recipe_demo3.json',
    'stress': 'pool/recipe_stress.json',
    'eob2_darkmoon_classic': 'pool/recipe_eob2_darkmoon_classic.json',
    'eob1_waterdeep': 'pool/recipe_eob1_waterdeep.json',
    'mix': 'pool/recipe_mix.json',
    'eob3_mythdrannor': 'pool/recipe_eob3_mythdrannor.json',
    'fixes': 'pool/recipe_fixes.json',
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def detect_install():
    print('======================================================')
    print('          Dungeon Hack+ — Base Game Detection         ')
    print('======================================================')

    # 1. Base Game: Dungeon Hack (Required)
    dh_dir = paths.get_dh_dir()
    print(f'\n[1] Dungeon Hack (Required Target)')
    print(f'    Path: {dh_dir}')
    if not os.path.exists(dh_dir):
        print('    Status: NOT FOUND')
        print('    Action: Drop your Dungeon Hack files into base_games/dungeon_hack/')
    else:
        all_dh_matched = True
        for fn in ['HACK.RES', 'OPEN.RES']:
            expected, desc = KNOWN_HASHES[fn]
            fp = os.path.join(dh_dir, fn)
            if not os.path.exists(fp):
                print(f'    * {fn:<10}: MISSING')
                all_dh_matched = False
                continue
            actual = sha256_file(fp)
            match = actual.lower() == expected.lower()
            if not match:
                all_dh_matched = False
            status = "MATCH (Pristine Retail/GOG)" if match else "MISMATCH / MODIFIED"
            print(f'    * {fn:<10}: {status} ({actual[:12]}...)')
        print(f'    Readiness: {"READY (Pristine Clean)" if all_dh_matched else "READY (Custom / Non-Standard)"}')

    # 2. Eye of the Beholder III (Optional - Wallsets, Doors, Monsters)
    eob3_dir = paths.get_game_dir('eob3')
    print(f'\n[2] Eye of the Beholder III (Optional - Wallsets, Doors, Monsters)')
    print(f'    Path: {eob3_dir}')
    eye_res = os.path.join(eob3_dir, 'EYE.RES')
    if os.path.exists(eye_res):
        actual = sha256_file(eye_res)
        expected, desc = KNOWN_HASHES['EYE.RES']
        match = actual.lower() == expected.lower()
        status = "MATCH (Pristine Retail/GOG)" if match else "MODIFIED / CUSTOM"
        print(f'    * EYE.RES   : {status} ({actual[:12]}...)')
        print('    Readiness: READY')
    else:
        print('    * EYE.RES   : NOT FOUND')
        print('    Readiness: OPTIONAL (Drop EYE.RES into base_games/eob3/ for EOB3 content)')

    # 3. Eye of the Beholder I (Optional - Classic Monsters, Icons)
    eob1_dir = paths.get_game_dir('eob1')
    print(f'\n[3] Eye of the Beholder I (Optional - Classic Monsters, Icons)')
    print(f'    Path: {eob1_dir}')
    pal1 = os.path.join(eob1_dir, 'EOBPAL.COL')
    if os.path.exists(pal1):
        cps_count = len([f for f in os.listdir(eob1_dir) if f.upper().endswith('.CPS')])
        print(f'    * EOBPAL.COL: FOUND ({cps_count} CPS sprites available)')
        print('    Readiness: READY')
    else:
        print('    * EOBPAL.COL: NOT FOUND')
        print('    Readiness: OPTIONAL (Drop files into base_games/eob1/)')

    # 4. Eye of the Beholder II (Optional - Darkmoon Palettes & Portraits)
    eob2_dir = paths.get_game_dir('eob2')
    print(f'\n[4] Eye of the Beholder II (Optional - Darkmoon Palettes & Portraits)')
    print(f'    Path: {eob2_dir}')
    pal2 = os.path.join(eob2_dir, 'DUNG.PAL')
    if os.path.exists(pal2):
        print(f'    * DUNG.PAL  : FOUND')
        print('    Readiness: READY')
    else:
        print('    * DUNG.PAL  : NOT FOUND')
        print('    Readiness: OPTIONAL (Drop files into base_games/eob2/)')

    # 5. Menzoberranzan (Optional - Underdark Caverns, Audio)
    menzo_dir = paths.get_game_dir('menzo')
    print(f'\n[5] Menzoberranzan (Optional - Underdark Caverns, Audio)')
    print(f'    Path: {menzo_dir}')
    res0 = os.path.join(menzo_dir, 'RES0')
    if os.path.exists(res0):
        print(f'    * RES0-8    : FOUND')
        print('    Readiness: READY')
    else:
        print('    * RES0-8    : NOT FOUND')
        print('    Readiness: OPTIONAL (Drop files into base_games/menzo/)')

    print('\n======================================================')
    return dh_dir


def list_presets():
    print('=== Available Mashup Presets ===')
    for k, rel_path in PRESET_RECIPES.items():
        fp = os.path.join(HERE, rel_path)
        desc = ''
        if os.path.exists(fp):
            try:
                rec = json.load(open(fp))
                desc = rec.get('comment', '')
                job_count = len(rec.get('jobs', []))
                desc = f'({job_count} jobs) {desc}'
            except Exception:
                pass
        print(f'  * {k:<18}: {desc}')

    print('\n=== Available Generator Difficulty Presets ===')
    for k, v in difficulty.PRESETS.items():
        print(f'  * {k:<18}: {v["name"]} - {v["desc"]}')


def build_preset(preset_key, build_name=None):
    if preset_key not in PRESET_RECIPES:
        print(f'Unknown preset: {preset_key}. Available: {list(PRESET_RECIPES.keys())}')
        return False
    rec_path = os.path.join(HERE, PRESET_RECIPES[preset_key])
    out_name = build_name or preset_key

    print(f'Building preset "{preset_key}" -> build/{out_name}...')
    cmd = [sys.executable, '-I', os.path.join(HERE, 'pipeline.py'), 'build', rec_path, out_name]
    ret = subprocess.run(cmd)
    return ret.returncode == 0


def roll_mix(seed=None, name='mix'):
    """New mix recipe (tools/mix.py) -> build/<name>/, with MIX.TXT listing what went where."""
    import random
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import mix
    seed = random.randrange(1, 10 ** 6) if seed is None else seed
    recipe = mix.roll(seed)
    path = os.path.join(HERE, 'pool', 'recipe_%s_rolled.json' % name)
    json.dump(recipe, open(path, 'w'), indent=1)
    print(mix.describe(recipe['mix']))
    ret = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pipeline.py'), 'build', path, name])
    if ret.returncode == 0:
        open(os.path.join(HERE, 'build', name, 'MIX.TXT'), 'w').write(mix.describe(recipe['mix']))
        print('Rolled mix seed %d -> build/%s (see MIX.TXT)' % (seed, name))
    return ret.returncode == 0


def rollback_build(build_name):
    """Safely remove a synthesized build directory."""
    build_dir = os.path.join(HERE, 'build', build_name)
    if not os.path.exists(build_dir):
        print(f'Build "{build_name}" does not exist under build/. Nothing to rollback.')
        return True
    shutil.rmtree(build_dir)
    print(f'Rolled back build "{build_name}". Target removed cleanly.')
    # Verify base game remains pristine
    detect_install()
    return True


def run_regression_suite():
    """CI-style test runner: builds and verifies all registered presets."""
    print('======================================================')
    print('       Dungeon Hack+ — Regression Test Suite          ')
    print('======================================================\n')
    results = {}
    for preset in PRESET_RECIPES.keys():
        test_name = f'_ci_test_{preset}'
        rec_path = os.path.join(HERE, PRESET_RECIPES[preset])
        print(f'>> Testing preset: {preset}...')
        cmd_build = [sys.executable, '-I', os.path.join(HERE, 'pipeline.py'), 'build', rec_path, test_name]
        ret_build = subprocess.run(cmd_build, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if ret_build.returncode != 0:
            results[preset] = ('FAIL (build)', ret_build.stderr.decode()[:120])
            continue

        cmd_verify = [sys.executable, '-I', os.path.join(HERE, 'pipeline.py'), 'verify', test_name]
        ret_verify = subprocess.run(cmd_verify, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_verify = ret_verify.stdout.decode()
        if ret_verify.returncode == 0 and 'VERIFY OK' in out_verify:
            results[preset] = ('PASS', 'Clean build & verification')
        else:
            results[preset] = ('FAIL (verify)', out_verify[:120])

        # Cleanup
        shutil.rmtree(os.path.join(HERE, 'build', test_name), ignore_errors=True)

    print('\n======================================================')
    print('                 Test Results Summary                 ')
    print('======================================================')
    all_passed = True
    for preset, (status, detail) in results.items():
        if status != 'PASS':
            all_passed = False
        print(f'  {preset:<18}: {status:<15} ({detail})')
    print('======================================================')
    print(f'Final Result: {"ALL TESTS PASSED ✔" if all_passed else "SOME TESTS FAILED ✖"}')
    return all_passed


def launch_build(preset_or_build, skip_intro=False):
    build_dir = os.path.join(HERE, 'build', preset_or_build)
    if not os.path.exists(build_dir):
        if preset_or_build in PRESET_RECIPES:
            print(f'Build {preset_or_build} does not exist yet. Building now...')
            if not build_preset(preset_or_build):
                return False
        else:
            print(f'Build directory not found: {build_dir}')
            return False

    cmd = [sys.executable, '-I', os.path.join(HERE, 'launch.py'), preset_or_build]
    if skip_intro:
        cmd.append('--skip-intro')
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='Dungeon Hack+ (dhplus) non-destructive patcher and manager')
    parser.add_argument('--lang', choices=['eng', 'fre', 'ger'], default='eng',
                        help='Dungeon Hack language install to build from (base_games/dungeon_hack[_fre|_ger])')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('detect', help='Detect and verify legally acquired base games')
    sub.add_parser('assets', help='Regenerate pool/ art and sounds from your own games (run once after cloning)')
    sub.add_parser('list', help='List available mashup and difficulty presets')
    sub.add_parser('test', help='Run CI regression suite building and verifying all presets')

    p_build = sub.add_parser('build', help='Build a preset into build/<name>/')
    p_build.add_argument('preset', choices=list(PRESET_RECIPES.keys()), help='Preset name')
    p_build.add_argument('name', nargs='?', help='Target build directory name')

    p_rollback = sub.add_parser('rollback', help='Rollback / remove a build from build/<name>/')
    p_rollback.add_argument('name', help='Build name to remove')

    p_launch = sub.add_parser('launch', help='Launch a build in DOSBox-Staging')
    p_launch.add_argument('target', help='Build name or preset')
    p_launch.add_argument('--skip-intro', action='store_true', help='Skip OPEN.RES intro cutscene')
    p_launch.add_argument('--reroll', action='store_true', help='Roll a new mix into this build first (saves are kept)')

    p_diff = sub.add_parser('difficulty', help='Apply difficulty preset to a build')
    p_diff.add_argument('preset', choices=list(difficulty.PRESETS.keys()), help='Difficulty preset')
    p_diff.add_argument('build', help='Build directory name under build/')

    p_roll = sub.add_parser('roll', help='Roll a new mix (DH + EOB1 + EOB2 + EOB3 in one build) and build it; saves are kept')
    p_roll.add_argument('seed', type=int, nargs='?', help='Seed (default: random)')
    p_roll.add_argument('name', nargs='?', default='mix', help='Build directory name (default: mix)')

    args = parser.parse_args()
    if args.lang != 'eng':     # read by tools/paths.get_game_dir and inherited by the pipeline subprocesses
        os.environ['DHPLUS_DH_DIR'] = 'base_games/dungeon_hack_' + args.lang

    if args.command == 'detect':
        detect_install()
    elif args.command == 'list':
        list_presets()
    elif args.command == 'test':
        run_regression_suite()
    elif args.command == 'build':
        build_preset(args.preset, args.name)
    elif args.command == 'rollback':
        rollback_build(args.name)
    elif args.command == 'launch':
        if args.reroll and not roll_mix(None, args.target):
            sys.exit('reroll failed')
        launch_build(args.target, args.skip_intro)
    elif args.command == 'difficulty':
        target = os.path.join(HERE, 'build', args.build)
        difficulty.apply_preset(args.preset, target)
    elif args.command == 'assets':
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'tools', 'pool_assets.py')], check=True)
    elif args.command == 'roll':
        roll_mix(args.seed, args.name)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
