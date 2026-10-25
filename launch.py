"""One-click launcher for Dungeon Hack builds with DOSBox-Staging.

Applies curated settings (1280x960 4:3 integer scaling, SB16, smooth CPU cycles),
supports build selection, optional intro skip, and recipe auto-building.

Usage:
  python3 -I mashup/launch.py [BUILD_NAME] [--skip-intro] [--recipe RECIPE_PATH]
Examples:
  python3 -I mashup/launch.py demo3 --skip-intro
  python3 -I mashup/launch.py stress
"""
import argparse
import os
import shutil
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import paths

HERE = os.path.dirname(os.path.abspath(__file__))
DOSBOX = os.path.join(HERE, 'third_party', 'dosbox-staging', 'dosbox')
if not os.path.exists(DOSBOX):
    DOSBOX = shutil.which('dosbox-staging') or shutil.which('dosbox') or DOSBOX
CONF = os.path.join(HERE, 'dosbox-dh.conf')


def main():
    parser = argparse.ArgumentParser(description='One-click launcher for Dungeon Hack+.')
    parser.add_argument('build', nargs='?', default='demo3', help='Name of the build under build/ (default: demo3)')
    parser.add_argument('--recipe', help='Optional path to recipe JSON to build prior to launching')
    parser.add_argument('--skip-intro', action='store_true', help='Skip OPEN.RES opening cinematic directly to title menu')
    parser.add_argument('--conf', default=CONF, help='DOSBox configuration file')
    args = parser.parse_args()

    if args.recipe:
        print(f'Building {args.recipe} -> {args.build}...')
        pipeline_py = os.path.join(HERE, 'pipeline.py')
        res = subprocess.run([sys.executable, '-I', pipeline_py, 'build', args.recipe, args.build])
        if res.returncode != 0:
            sys.exit(f'Build failed with code {res.returncode}')

    build_dir = os.path.join(HERE, 'build', args.build)
    if not os.path.isdir(build_dir):
        if args.build == 'base':
            build_dir = paths.get_dh_dir()
        else:
            sys.exit(f'Build not found: {build_dir}\nAvailable builds: {sorted(os.listdir(os.path.join(HERE, "build")))}')

    if build_dir != paths.get_dh_dir():           # never write into the base install
        for note in paths.seed_savegame(build_dir):
            print('savegame:', note)

    # Handle skip-intro by temporarily renaming OPEN.RES if needed
    open_res = os.path.join(build_dir, 'OPEN.RES')
    open_bak = os.path.join(build_dir, 'OPEN.RES.SKIP')
    if args.skip_intro and os.path.exists(open_res):
        os.rename(open_res, open_bak)
        print('Skipping opening cinematic (OPEN.RES temporarily disabled)')

    dosbox_args = [
        DOSBOX,
        '--conf', args.conf,
        '-c', f'mount c "{build_dir}"',
        '-c', 'c:',
        '-c', 'HACK.BAT',
        '-c', 'exit'
    ]

    print(f'Launching Dungeon Hack [{args.build}]...')
    print(f'DOSBox conf: {args.conf}')
    print('Press Ctrl+F10 or Middle Click to capture/release mouse in window.')

    try:
        subprocess.run(dosbox_args)
    finally:
        # Restore OPEN.RES if it was renamed
        if os.path.exists(open_bak):
            os.rename(open_bak, open_res)


if __name__ == '__main__':
    main()
