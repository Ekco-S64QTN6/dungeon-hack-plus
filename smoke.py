#!/usr/bin/env python3
"""Smoke tests for mashup builds under DOSBox-Staging (mashup/third_party/dosbox-staging).

  python3 -I mashup/smoke.py boot  NAME [NAME...]      # headless: does phase-one start and keep running?
  python3 -I mashup/smoke.py fixture NAME              # keep build/NAME/savegame as the test fixture
  python3 -I mashup/smoke.py shots STEPS NAME [NAME..] # Xvfb + xdotool + import: scripted run, screenshots,
                                                       # pixel diff of every build against the base install

`boot` is a weak oracle: a build with 95 zeroed .TBL entries still reaches the
title menu, so it only catches hard start-up failures. Real verification is `shots`.
STEPS is JSON: {"seconds": 120, "dos": ["cd savegame", "..\\\\maze", "cd ..", "aesop hack phase-two"],
"autotype": "-w 25 -p 0.3 a enter", "steps": [{"at": 40, "shot": "view"}, {"at": 41, "key": "Up"},
{"at": 42, "click": [160, 100]}, ...]}  (click coordinates are in 320x200 game pixels).
"""
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DOSBOX = os.path.join(HERE, 'third_party', 'dosbox-staging', 'dosbox')
RUNS = os.path.join(HERE, 'smoke_runs')
FIXTURE = os.path.join(HERE, 'fixtures', 'savegame')
BASE_DIR = os.path.join(HERE, 'base_games', 'dungeon_hack')
DISPLAY = os.environ.get('SMOKE_DISPLAY', ':77')   # separate displays let runs go in parallel
WIN = (640, 400)


def stage(name):
    """Fresh copy of a build (or the base install) with the fixture savegame, outside build/."""
    src = BASE_DIR if name == 'base' else os.path.join(HERE, 'build', name)
    dst = os.path.join(RUNS, name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('DOSBOX', '*.pdf'))
    sg = os.path.join(dst, 'savegame')
    if os.path.isdir(FIXTURE):
        shutil.rmtree(sg, ignore_errors=True)
        shutil.copytree(FIXTURE, sg)
    os.makedirs(sg, exist_ok=True)
    return dst


def dosbox(dir_, commands, env, seconds, settings=()):
    args = [DOSBOX, '--noprimaryconf', '--nolocalconf', '--set', 'cpu_cycles=max',
            *[a for kv in settings for a in ('--set', kv)],
            '--set', 'window_size=%dx%d' % WIN, '--set', 'shader=none', '--set', 'mouse_capture=seamless', '--set', 'capture_dir=%s' % os.path.join(dir_, 'capture'),
            '-c', 'mount c "%s"' % dir_, '-c', 'c:']
    for c in commands:
        args += ['-c', c]
    args += ['-c', 'exit']
    log = open(os.path.join(dir_, 'SMOKE_DOSBOX.LOG'), 'w')
    p = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
    _CHILDREN.append(p)
    return p, seconds


def cmd_boot(*names):
    env = dict(os.environ, SDL_VIDEODRIVER='offscreen', SDL_AUDIODRIVER='dummy')
    for name in ('base',) + names:
        d = stage(name)
        p, secs = dosbox(d, ['aesop hack phase-one > SMOKE1.TXT', 'echo rc=%errorlevel% > SMOKE2.TXT'], env, 30)
        try:
            p.wait(secs); alive = False
        except subprocess.TimeoutExpired:
            p.kill(); alive = True
        out = open(os.path.join(d, 'SMOKE1.TXT'), errors='replace').read().strip() if os.path.exists(os.path.join(d, 'SMOKE1.TXT')) else ''
        verdict = 'running at timeout (pass, weak)' if alive and not out else 'EXITED/ERROR: %r' % out[:200]
        print('%-10s %s' % (name, verdict))


def cmd_fixture(name):
    src = os.path.join(HERE, 'build', name, 'savegame') if name != 'base' else os.path.join(BASE_DIR, 'savegame')
    if os.path.exists(FIXTURE):
        shutil.rmtree(FIXTURE)
    shutil.copytree(src, FIXTURE)
    print('fixture <-', src, os.listdir(FIXTURE))


def need(tool):
    if not shutil.which(tool):
        sys.exit('%s not found; install it first (Arch: sudo pacman -S xorg-server-xvfb xdotool imagemagick)' % tool)


def window_id(env, pid=None):
    """The DOSBox window to drive. With `pid`, only that process's window (never another
    harness's DOSBox); without, the class search must find exactly one."""
    for _ in range(50):
        cmd = ['xdotool', 'search', '--pid', str(pid)] if pid else ['xdotool', 'search', '--class', 'dosbox']
        ids = subprocess.run(cmd, env=env, capture_output=True, text=True).stdout.split()
        if pid and ids:
            # SDL creates helper windows too; keep the one with the dosbox class
            cls = set(subprocess.run(['xdotool', 'search', '--class', 'dosbox'], env=env, capture_output=True, text=True).stdout.split())
            ids = [i for i in ids if i in cls] or ids
            return ids[0]
        if not pid and ids:
            if len(ids) > 1:
                raise RuntimeError('%d DOSBox windows on %s: another run is using this display' % (len(ids), env.get('DISPLAY')))
            return ids[0]
        time.sleep(0.2)
    return None


# Cleanup: every DOSBox/Xvfb a harness starts is killed when it exits, also under `timeout`
# (SIGTERM would otherwise end Python without running finally blocks, leaving orphans that
# keep a build folder mounted and a window on the shared display).
import atexit, signal   # noqa: E402
_CHILDREN = []


def _cleanup():
    for p in _CHILDREN:
        if p.poll() is None:
            p.kill()


atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))


def start_xvfb(display=None, screen='1024x768x24'):
    """Start a private Xvfb; refuse if a live one already holds the display (another harness)."""
    display = display or DISPLAY
    lock = '/tmp/.X%s-lock' % display.lstrip(':')
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)
            raise RuntimeError('display %s is in use by Xvfb pid %d (another test run?)' % (display, pid))
        except (ProcessLookupError, ValueError):
            os.remove(lock)                                  # stale lock from a killed run
    x = subprocess.Popen(['Xvfb', display, '-screen', '0', screen], stderr=subprocess.DEVNULL)
    _CHILDREN.append(x)
    time.sleep(1)
    return x


def run_steps(name, spec, env):
    d = stage(name)
    shots = os.path.join(RUNS, 'shots', name); os.makedirs(shots, exist_ok=True)
    cmds = (['autotype ' + spec['autotype']] if spec.get('autotype') else []) + spec['dos']
    p, secs = dosbox(d, cmds, env, spec.get('seconds', 120))
    t0 = time.time(); wid = window_id(env, p.pid)
    for st in sorted(spec['steps'], key=lambda s: s['at']):
        time.sleep(max(0, st['at'] - (time.time() - t0)))
        if 'key' in st:                     # hold briefly: DH polls the keyboard and drops instant taps
            subprocess.run(['xdotool', 'keydown', '--window', wid, st['key']], env=env)
            time.sleep(st.get('hold', 0.12))
            subprocess.run(['xdotool', 'keyup', '--window', wid, st['key']], env=env)
        if 'click' in st:
            x, y = st['click']
            subprocess.run(['xdotool', 'mousemove', '--window', wid, str(x * WIN[0] // 320), str(y * WIN[1] // 200),
                            'click', '1'], env=env)
        if 'shot' in st:
            subprocess.run(['import', '-window', wid, os.path.join(shots, st['shot'] + '.png')], env=env)
    p.kill()
    return shots


def cmd_shots(steps_path, *names):
    for t in ('Xvfb', 'xdotool', 'import'):
        need(t)
    spec = json.load(open(steps_path))
    xvfb = start_xvfb()
    env = dict(os.environ, DISPLAY=DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy')
    env.pop('WAYLAND_DISPLAY', None)
    try:
        time.sleep(1)
        base = run_steps('base', spec, env)
        for name in names:
            got = run_steps(name, spec, env)
            for fn in sorted(os.listdir(base)):
                a = np.asarray(Image.open(os.path.join(base, fn)).convert('RGB'), dtype=np.int16)
                b_path = os.path.join(got, fn)
                if not os.path.exists(b_path):
                    print('%-10s %-12s MISSING' % (name, fn)); continue
                b = np.asarray(Image.open(b_path).convert('RGB'), dtype=np.int16)
                if a.shape != b.shape:
                    print('%-10s %-12s size differs %s vs %s' % (name, fn, a.shape, b.shape)); continue
                changed = np.any(a != b, axis=2)
                Image.fromarray((changed * 255).astype(np.uint8)).save(os.path.join(got, 'diff_' + fn))
                print('%-10s %-12s %.1f%% pixels differ from base' % (name, fn, 100 * changed.mean()))
    finally:
        xvfb.kill()


if __name__ == '__main__':
    cmd, *args = sys.argv[1:] or ['help']
    fn = {'boot': cmd_boot, 'fixture': cmd_fixture, 'shots': cmd_shots}.get(cmd)
    if not fn:
        sys.exit(__doc__)
    fn(*args)
