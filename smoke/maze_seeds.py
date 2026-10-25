"""Hunt for MAZE.EXE seeds that never finish ("Generating..." forever).

  python3 -I smoke/maze_seeds.py FIRST COUNT [--settings HEX24] [--timeout S] [--jobs N]

Runs the original MAZE.EXE headlessly (DOSBox, offscreen SDL) once per seed: SETTINGS.DAT =
u32 seed + the 12 settings bytes (+ the rest of the fixture's file); success = SEED.TXT reports
that seed and LEVELS.DAT was rewritten. Results go to smoke_runs/maze_seeds/results.json
(seed -> seconds, or "HANG"/"ERROR").
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import queue
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import smoke   # noqa: E402

OUT = os.path.join(smoke.RUNS, 'maze_seeds')


def run_seed(seed, settings, timeout, slot):
    d = os.path.join(OUT, 'work%d' % slot)
    if not os.path.isdir(d):
        shutil.copytree(smoke.BASE_DIR, d, ignore=shutil.ignore_patterns('DOSBOX', '*.pdf', 'OPEN.RES', 'savegame'))
    sg = os.path.join(d, 'savegame')
    shutil.rmtree(sg, ignore_errors=True); os.makedirs(sg)
    tail = open(os.path.join(ROOT, 'fixtures', 'savegame', 'SETTINGS.DAT'), 'rb').read()[16:]
    open(os.path.join(sg, 'SETTINGS.DAT'), 'wb').write(struct.pack('<I', seed) + settings + tail)
    env = dict(os.environ, SDL_VIDEODRIVER='offscreen', SDL_AUDIODRIVER='dummy')
    args = [smoke.DOSBOX, '--noprimaryconf', '--nolocalconf', '--set', 'cpu_cycles=max',
            '-c', 'mount c "%s"' % d, '-c', 'c:', '-c', 'cd savegame', '-c', '..\\maze > MAZEOUT.TXT', '-c', 'exit']
    t0 = time.time()
    p = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p.wait(timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()
        return seed, 'HANG'
    dt = round(time.time() - t0, 1)
    txt = open(os.path.join(sg, 'SEED.TXT'), errors='replace').read() if os.path.exists(os.path.join(sg, 'SEED.TXT')) else ''
    ok = ('Seed=%08X' % seed) in txt and os.path.exists(os.path.join(sg, 'LEVELS.DAT'))
    return seed, dt if ok else 'ERROR'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('first', type=int); ap.add_argument('count', type=int)
    ap.add_argument('--settings', default='000107070101010107000000', help='12 settings bytes (hex); default = fixture')
    ap.add_argument('--timeout', type=float, default=60); ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rpath = os.path.join(OUT, 'results.json')
    results = json.load(open(rpath)) if os.path.exists(rpath) else {}
    key = a.settings
    done = results.setdefault(key, {})
    seeds = [s for s in range(a.first, a.first + a.count) if str(s) not in done]
    settings = bytes.fromhex(a.settings)
    slots = queue.Queue()
    for k in range(a.jobs):
        slots.put(k)

    def one(seed):                      # each run gets a work folder no other running seed is using
        slot = slots.get()
        try:
            return run_seed(seed, settings, a.timeout, slot)
        finally:
            slots.put(slot)
    with ThreadPoolExecutor(a.jobs) as ex:
        futs = [ex.submit(one, s) for s in seeds]
        for f in futs:
            seed, res = f.result()
            done[str(seed)] = res
            if res in ('HANG', 'ERROR'):
                print('seed %d: %s' % (seed, res), flush=True)
            json.dump(results, open(rpath, 'w'), indent=0)
    times = [v for v in done.values() if isinstance(v, float)]
    bad = {k: v for k, v in done.items() if not isinstance(v, float)}
    print('settings %s: %d seeds, %d ok (max %.1fs), problems: %s' % (key, len(done), len(times), max(times or [0]), bad))


if __name__ == '__main__':
    main()
