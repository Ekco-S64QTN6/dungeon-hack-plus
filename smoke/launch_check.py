"""The player's path: `launch.py BUILD` (dosbox-dh.conf, HACK.BAT: checksys, intro, phase-one menu ...)
on a private Xvfb, with timed screenshots and optional input.

  python3 -I smoke/launch_check.py BUILD [--skip-intro] [--events "8:shot,9:key:Escape,12:click:640/480,15:shot"]
Events (seconds since launch): shot | key:<xdotool key> | click:<x>/<y> (window pixels) | type:<text>.
Shots go to smoke_runs/launch/<build>/. The build's savegame/ is used as is (back it up first if it matters).
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import smoke   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('build'); ap.add_argument('--skip-intro', action='store_true')
    ap.add_argument('--events', default='10:shot,25:shot,45:shot')
    ap.add_argument('--display', default=os.environ.get('SMOKE_DISPLAY', ':79'))
    a = ap.parse_args()
    out = os.path.join(smoke.RUNS, 'launch', a.build); os.makedirs(out, exist_ok=True)
    x = smoke.start_xvfb(a.display, screen='1600x1200x24')
    env = dict(os.environ, DISPLAY=a.display, SDL_AUDIODRIVER='dummy'); env.pop('WAYLAND_DISPLAY', None)
    # the player's dosbox-dh.conf, except mouse_capture: on_click swallows the first click and then moves
    # the pointer relatively, which absolute xdotool clicks can't drive
    conf = os.path.join(out, 'dosbox-seamless.conf')
    open(conf, 'w').write(open(os.path.join(ROOT, 'dosbox-dh.conf')).read().replace('mouse_capture       = on_click', 'mouse_capture       = seamless'))
    p = subprocess.Popen([sys.executable, '-I', os.path.join(ROOT, 'launch.py'), a.build, '--conf', conf] + (['--skip-intro'] if a.skip_intro else []),
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    smoke._CHILDREN.append(p)
    t0, n = time.time(), 0
    wid = None
    try:
        for ev in a.events.split(','):
            at, _, what = ev.partition(':')
            time.sleep(max(0.0, float(at) - (time.time() - t0)))
            if wid is None:
                r = subprocess.run(['xdotool', 'search', '--class', 'dosbox'], env=env, capture_output=True, text=True)
                wid = (r.stdout.split() or [None])[0]
            if wid is None:
                print('%5.1fs: no DOSBox window' % (time.time() - t0)); continue
            kind, _, arg = what.partition(':')
            if kind == 'shot':
                n += 1; path = os.path.join(out, '%02d_%03ds.png' % (n, int(float(at))))
                subprocess.run(['import', '-window', wid, path], env=env); print('shot', path)
            elif kind == 'key':
                subprocess.run(['xdotool', 'keydown', '--window', wid, arg], env=env); time.sleep(0.12)
                subprocess.run(['xdotool', 'keyup', '--window', wid, arg], env=env)
            elif kind == 'click':
                cx, cy = arg.split('/')
                subprocess.run(['xdotool', 'mousemove', '--window', wid, cx, cy], env=env); time.sleep(0.2)
                subprocess.run(['xdotool', 'mousedown', '--window', wid, '1'], env=env); time.sleep(0.12)
                subprocess.run(['xdotool', 'mouseup', '--window', wid, '1'], env=env)
            elif kind == 'type':
                subprocess.run(['xdotool', 'type', '--window', wid, '--delay', '120', arg], env=env)
        print('DOSBox still running:', p.poll() is None)
    finally:   # stop DOSBox first so launch.py runs its own cleanup (it restores OPEN.RES after --skip-intro)
        subprocess.run(['pkill', '-TERM', '-P', str(p.pid)], stderr=subprocess.DEVNULL)
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()
        x.kill()


if __name__ == '__main__':
    main()
