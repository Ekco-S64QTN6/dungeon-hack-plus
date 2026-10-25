"""Closed-loop walker for Dungeon Hack under DOSBox-Staging + Xvfb.

Unlike a fixed key script, every action is verified from the screen:
  * facing  = compass letter at the top, template-matched (smoke/compass_*.png)
  * a step  = the 3D view changed after KP_8 (retried; "blocked" if it never changes)
DH drops some key presses (even held ones), so turns are repeated until the compass agrees.

  python3 -I mashup/smoke/walker.py PLAN.json NAME [NAME...]
PLAN: {"fixture": "fixtures/savegame_nomon", "level": 0, "checkpoints": [
        {"shot": "start"}, {"face": "S", "shot": "stairs_up"},
        {"goto": [25, 4], "face": "S", "shot": "door_d2"}, ...]}
"""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import smoke   # noqa: E402
import route   # noqa: E402

VIEW = (slice(31, 320), slice(276, 628))          # 3D view in 640x480 screenshots
COMPASS = (slice(328, 366), slice(450, 492))      # top letter of the compass rose
DIRS = 'NESW'


class Game:
    def __init__(self, name, fixture, env):
        self.env = env
        smoke.FIXTURE = os.path.join(os.path.dirname(HERE), fixture)
        self.dir = smoke.stage(name)
        self.proc, _ = smoke.dosbox(self.dir, ['aesop hack phase-two'], env, 0)
        self.wid = smoke.window_id(env, self.proc.pid)
        self.tmp = tempfile.mkdtemp()
        self.templates = {d: np.asarray(Image.open(os.path.join(HERE, 'compass_%s.png' % d)).convert('L'), float)
                          for d in DIRS if os.path.exists(os.path.join(HERE, 'compass_%s.png' % d))}

    def shot(self):
        p = os.path.join(self.tmp, 's.png')
        subprocess.run(['import', '-window', self.wid, p], env=self.env)
        return np.asarray(Image.open(p).convert('RGB'))

    def save(self, img, path):
        Image.fromarray(img).save(path)

    def key(self, k, hold=0.12, settle=1.1):
        subprocess.run(['xdotool', 'keydown', '--window', self.wid, k], env=self.env)
        time.sleep(hold)
        subprocess.run(['xdotool', 'keyup', '--window', self.wid, k], env=self.env)
        time.sleep(settle)

    def facing(self, img=None):
        img = self.shot() if img is None else img
        g = np.asarray(Image.fromarray(img).convert('L'), float)[COMPASS]
        scores = {d: ((g - t) ** 2).mean() for d, t in self.templates.items()}
        return min(scores, key=scores.get), scores

    def turn_to(self, want):
        for _ in range(12):
            f, _ = self.facing()
            if f == want:
                return True
            diff = (DIRS.index(want) - DIRS.index(f)) % 4
            self.key('KP_7' if diff == 3 else 'KP_9')
        return False

    def forward(self):
        before = self.shot()[VIEW].astype(int)
        for attempt in range(4):
            self.key('KP_8')
            after = self.shot()[VIEW].astype(int)
            if np.any(before != after, axis=2).mean() > 0.05:
                return True
        return False

    def close(self):
        self.proc.kill()
        shutil.rmtree(self.tmp, ignore_errors=True)


def path_to(lv, recs, start, goal, through_doors=False):
    open_ = lambda x, y: 0 <= x < 32 and 0 <= y < 32 and lv[y * 32 + x] == 0xFF
    blocked = {(r[1], r[2]) for r in recs if r[0] in ((4, 5, 25) if through_doors else (1, 4, 5, 25))} - {goal}   # 25 = pillar
    prev = {start: None}; q = collections.deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        for dx, dy in route.DIRS:
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and open_(*n) and n not in blocked:
                prev[n] = c; q.append(n)
    if goal not in prev:
        return None
    out = []
    while c:
        out.append(c); c = prev[c]
    return out[::-1]


def run(plan, name, env, outroot):
    fixture = plan.get('fixture', 'fixtures/savegame')
    lv, recs = route.load(os.path.join(os.path.dirname(HERE), fixture), plan.get('level', 0))
    pos = next((r[1], r[2]) for r in recs if r[0] == 0)
    g = Game(name, fixture, env)
    out = os.path.join(outroot, name); os.makedirs(out, exist_ok=True)
    log = []
    try:
        time.sleep(plan.get('boot', 5))
        for cp in plan['checkpoints']:
            if 'goto' in cp:
                doors = {(r[1], r[2]) for r in recs if r[0] == 1}
                path = path_to(lv, recs, pos, tuple(cp['goto']), cp.get('through_doors', False))
                if path is None:
                    log.append('no path to %s' % cp['goto']); break
                for a, b in zip(path, path[1:]):
                    d = DIRS[route.DIRS.index((b[0] - a[0], b[1] - a[1]))]
                    if not g.turn_to(d):
                        log.append('turn to %s failed at %s' % (d, a)); raise RuntimeError
                    if b in doors:                     # open it: click the door face ahead
                        subprocess.run(['xdotool', 'mousemove', '--window', g.wid, '452', '175'], env=env); time.sleep(0.2)
                        subprocess.run(['xdotool', 'mousedown', '--window', g.wid, '1'], env=env); time.sleep(0.12)
                        subprocess.run(['xdotool', 'mouseup', '--window', g.wid, '1'], env=env); time.sleep(1.5)
                        log.append('opened door %s' % (b,))
                    if not g.forward():
                        log.append('blocked stepping %s -> %s' % (a, b)); raise RuntimeError
                    pos = b
            if 'forward' in cp:
                for _ in range(cp['forward']):
                    if g.forward():
                        pos = (pos[0] + route.DIRS[DIRS.index(g.facing()[0])][0], pos[1] + route.DIRS[DIRS.index(g.facing()[0])][1])
            if 'face' in cp and not g.turn_to(cp['face']):
                log.append('could not face %s' % cp['face']); raise RuntimeError
            if 'click' in cp:
                x, y = cp['click']
                subprocess.run(['xdotool', 'mousemove', '--window', g.wid, str(x * 2), str(int(y * 2.4))], env=env)
                time.sleep(0.2)
                subprocess.run(['xdotool', 'mousedown', '--window', g.wid, '1'], env=env); time.sleep(0.12)
                subprocess.run(['xdotool', 'mouseup', '--window', g.wid, '1'], env=env)
                time.sleep(cp.get('settle', 0.0))
            if 'hotkey' in cp:                  # DOSBox hotkeys, e.g. ctrl+F6 = start/stop audio capture
                subprocess.run(['xdotool', 'key', '--window', g.wid, cp['hotkey']], env=env)
                time.sleep(cp.get('settle', 0.5))
            if 'burst' in cp:                   # n shots, `every` seconds apart (animations)
                for i in range(cp['burst']):
                    g.save(g.shot(), os.path.join(out, '%s_%02d.png' % (cp['prefix'], i)))
                    time.sleep(cp.get('every', 0.2))
                log.append('%s burst x%d at %s' % (cp['prefix'], cp['burst'], pos))
            if 'wait' in cp:
                time.sleep(cp['wait'])
            if 'shot' in cp:
                img = g.shot(); g.save(img, os.path.join(out, cp['shot'] + '.png'))
                log.append('%s at %s facing %s' % (cp['shot'], pos, g.facing(img)[0]))
    except RuntimeError:
        g.save(g.shot(), os.path.join(out, 'FAILED.png'))
    finally:
        g.close()
    open(os.path.join(out, 'walk.log'), 'w').write('\n'.join(log) + '\n')
    return log


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    x = smoke.start_xvfb()
    env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy')
    env.pop('WAYLAND_DISPLAY', None)
    outroot = os.path.join(smoke.RUNS, 'walks', os.path.splitext(os.path.basename(sys.argv[1]))[0])
    try:
        time.sleep(1)
        for name in sys.argv[2:]:
            print(name, run(plan, name, env, outroot))
    finally:
        x.kill()
