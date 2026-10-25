"""Run one step script against named builds under a private Xvfb (helper for exploration)."""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import smoke
spec = json.load(open(sys.argv[1]))
x = subprocess.Popen(['Xvfb', smoke.DISPLAY, '-screen', '0', '1024x768x24'], stderr=subprocess.DEVNULL)
env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy'); env.pop('WAYLAND_DISPLAY', None)
try:
    time.sleep(1)
    for name in sys.argv[2:]:
        out = smoke.run_steps(name, spec, env)
        os.rename(out, out + '_' + os.path.splitext(os.path.basename(sys.argv[1]))[0]) if not os.path.exists(out + '_' + os.path.splitext(os.path.basename(sys.argv[1]))[0]) else None
        print(name, 'done')
finally:
    x.kill()
