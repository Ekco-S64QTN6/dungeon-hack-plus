"""Save -> quit -> title menu -> Continue -> restore, driven headlessly like a player would.

  python3 -I smoke/save_restore.py BUILD [--fixture savegame] [--no-template]

Session 1 starts the game (phase-two), opens CAMP, Save Game, slot 1, types SMOKE + Enter,
then checks the files: SAVEGAME.DIR's first slot reads SMOKE and SAVE_01.BIN exists.
Session 2 runs the HACK.BAT menu loop, clicks Continue and slot 1, and checks the restored
game is on screen (a crash leaves DOS's text screen, which is almost all black).
--no-template skips seeding GOG's savegame files: the negative control, which must FAIL with
"Couldn't open savegame directory for reading" (the bug users hit on GOG installs).
Coordinates are for a 1280x960 window.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import smoke   # noqa: E402
import paths   # noqa: E402

CAMP, SAVE_GAME, SLOT1, CONTINUE = (70, 920), (890, 435), (680, 172), (630, 452)
MENU_BAT = """@echo off
:MENU
aesop hack phase-one
if ERRORLEVEL 3 goto MENU
if ERRORLEVEL 1 goto STOP
aesop hack phase-two
:STOP
echo STOPPED
"""


class Session:
    def __init__(self, d, out, command, env):
        self.out, self.env = out, env
        args = [smoke.DOSBOX, '--noprimaryconf', '--nolocalconf', '--set', 'window_size=1280x960',
                '--set', 'cpu_cycles=max', '--set', 'mouse_capture=seamless', '--set', 'capture_dir=%s' % out,
                '-c', 'mount c "%s"' % d, '-c', 'c:', '-c', command]
        self.p = subprocess.Popen(args, env=env, stdout=open(os.path.join(out, 'dosbox.log'), 'a'), stderr=subprocess.STDOUT)
        self.wid = smoke.window_id(env, self.p.pid)

    def shot(self, name):
        path = os.path.join(self.out, name + '.png')
        subprocess.run(['import', '-window', self.wid, path], env=self.env, timeout=20)
        return np.asarray(Image.open(path).convert('RGB'))

    def click(self, xy, wait):
        for args in (['mousemove', '--window', self.wid, str(xy[0]), str(xy[1])], ['mousedown', '--window', self.wid, '1'],
                     ['mouseup', '--window', self.wid, '1']):
            subprocess.run(['xdotool'] + args, env=self.env, timeout=10); time.sleep(0.15)
        time.sleep(wait)

    def type(self, text, wait):
        subprocess.run(['xdotool', 'type', '--delay', '150', '--window', self.wid, text], env=self.env, timeout=20)
        subprocess.run(['xdotool', 'key', '--window', self.wid, 'Return'], env=self.env, timeout=10)
        time.sleep(wait)

    def close(self):
        self.p.kill(); self.p.wait()


def looks_like_game(img):
    return (img.max(axis=2) > 40).mean() > 0.2     # game screens ~0.5-0.7 lit; the DOS crash screen ~0.01


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('build'); ap.add_argument('--fixture', default='savegame'); ap.add_argument('--no-template', action='store_true')
    a = ap.parse_args()
    smoke.FIXTURE = os.path.join(ROOT, 'fixtures', a.fixture)
    d = smoke.stage(a.build)
    sg = os.path.join(d, 'savegame')
    for fn in os.listdir(sg):                          # start without any slot saves
        if fn.upper() in paths.SAVE_TEMPLATE_FILES or fn.upper().startswith(('SAVE_', 'ITEMS_')):
            os.remove(os.path.join(sg, fn))
    if not a.no_template:
        paths.seed_savegame(d)
    if os.path.exists(os.path.join(d, 'OPEN.RES')):
        os.remove(os.path.join(d, 'OPEN.RES'))
    open(os.path.join(d, 'MENU.BAT'), 'w').write(MENU_BAT.replace('\n', '\r\n'))
    out = os.path.join(smoke.RUNS, 'save_restore', a.build + ('_notemplate' if a.no_template else ''))
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    x = smoke.start_xvfb(screen='1600x1200x24')
    env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy'); env.pop('WAYLAND_DISPLAY', None)
    results = []
    try:
        time.sleep(1)
        s = Session(d, out, 'aesop hack phase-two', env)
        time.sleep(25)
        s.shot('1_ingame')
        s.click(CAMP, 4); s.click(SAVE_GAME, 4)
        img = s.shot('2_save_screen')
        s.click(SLOT1, 3); s.type('SMOKE', 8)
        img = s.shot('3_after_save')
        s.close()
        sgdir = open(os.path.join(sg, 'SAVEGAME.DIR'), 'rb').read() if os.path.exists(os.path.join(sg, 'SAVEGAME.DIR')) else b''
        results.append(('save: SAVEGAME.DIR slot 1 = SMOKE', sgdir.split(b'\r\n')[0] == b'SMOKE'))
        results.append(('save: SAVE_01.BIN written', os.path.exists(os.path.join(sg, 'SAVE_01.BIN'))))
        results.append(('save: game still running after save', looks_like_game(img)))

        s = Session(d, out, 'MENU.BAT', env)
        time.sleep(14)
        s.shot('4_menu')
        s.click(CONTINUE, 15)
        img = s.shot('5_restore_list')
        results.append(('continue: restore list shown', looks_like_game(img)))
        s.click(SLOT1, 15)
        img = s.shot('6_restored')
        results.append(('restore: back in the game', looks_like_game(img)))
        s.close()
    finally:
        x.kill()
    ok = all(r for _, r in results)
    report = ['# save -> Continue -> restore: %s%s' % (a.build, ' (no template: negative control)' if a.no_template else ''), '']
    report += ['- %s: %s' % (n, 'ok' if r else '**FAIL**') for n, r in results]
    report += ['', '**%s**' % ('PASS' if ok else 'FAIL')]
    open(os.path.join(out, 'report.md'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
