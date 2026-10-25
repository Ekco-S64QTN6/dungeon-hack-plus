"""Phase-1 gate in one command.

  python3 -I mashup/smoke/gate.py [PLAN.json] [BUILD ...]      (defaults: smoke/gate_walk.json, smoke_demo2 smoke_demo3 smoke_stress)

Runs the closed-loop walk on the forced base twice (noise = pixels that differ
between two base runs: animated HUD bits, unpinned wall decorations) and on each
build, then checks, per checkpoint:
  * the walk reached it at the same map position and facing as base,
  * no pixel OUTSIDE the 3D view differs from base beyond base's own noise.
In-view differences are expected (that is the reskin); they are summarised and put
on a contact sheet (gate_report.png) for visual review. Writes gate_report.md.
"""
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import smoke    # noqa: E402
import walker   # noqa: E402

V = walker.VIEW
# DOSBox scales 320x200 to 640x480 (y x2.4), so the scaler blends the view's edge column into
# its neighbours; differences within 2 px of the view are scaler bleed, not outside changes.
# The parchment automap (game 52-110 x 140-190) shows cells glimpsed during turns, which depends on
# which key presses DH dropped on the way, so it is walk-path state, not build output.
AUTOMAP = (slice(int(140 * 2.4), int(190 * 2.4)), slice(52 * 2, 110 * 2))
VB = (slice(V[0].start - 2, V[0].stop + 2), slice(V[1].start - 2, V[1].stop + 2))


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(int)


def main():
    args = sys.argv[1:]
    base = 'smoke_base'
    if '--base' in args:
        i = args.index('--base'); base = args[i + 1]; del args[i:i + 2]
    plan_path = args.pop(0) if args and args[0].endswith('.json') else os.path.join(HERE, 'gate_walk.json')
    builds = args or ['smoke_demo2', 'smoke_demo3', 'smoke_stress']
    plan = json.load(open(plan_path))
    root = os.path.join(smoke.RUNS, 'gate' if base == 'smoke_base' else 'gate_' + base.replace('smokebase_', ''))
    shutil.rmtree(root, ignore_errors=True)
    x = subprocess.Popen(['Xvfb', smoke.DISPLAY, '-screen', '0', '1024x768x24'], stderr=subprocess.DEVNULL)
    env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy')
    env.pop('WAYLAND_DISPLAY', None)
    logs = {}
    try:
        time.sleep(1)
        logs['base'] = walker.run(plan, base, env, root)
        os.rename(os.path.join(root, base), os.path.join(root, 'base_a'))
        logs['base_b'] = walker.run(plan, base, env, root)
        os.rename(os.path.join(root, base), os.path.join(root, 'base_b'))
        for b in builds:
            logs[b] = walker.run(plan, b, env, root)
    finally:
        x.kill()

    shots = [cp['shot'] + '.png' for cp in plan['checkpoints'] if 'shot' in cp]
    lines = ['# Gate report', '', 'plan: `%s`' % os.path.relpath(plan_path, os.path.dirname(HERE)), '']
    ok = True
    if logs['base'] != logs['base_b']:
        ok = False; lines.append('**FAIL** base walks disagree: %s vs %s' % (logs['base'], logs['base_b']))
    noise = {}
    for f in shots:
        a, b = os.path.join(root, 'base_a', f), os.path.join(root, 'base_b', f)
        noise[f] = np.any(load(a) != load(b), 2) if os.path.exists(a) and os.path.exists(b) else None
    lines += ['| build | checkpoint | walk | outside-view diff (net of noise) | in-view diff |', '|---|---|---|---|---|']
    for b in builds:
        if logs[b] != logs['base']:
            ok = False
        for k, f in enumerate(shots):
            p = os.path.join(root, b, f)
            if not os.path.exists(p) or noise[f] is None:
                ok = False; lines.append('| %s | %s | **missing** | | |' % (b, f)); continue
            m = np.any(load(p) != load(os.path.join(root, 'base_a', f)), 2) & ~noise[f]
            out = m.copy(); out[VB] = False; out[AUTOMAP] = False
            walk = 'ok' if k < len(logs[b]) and k < len(logs['base']) and logs[b][k] == logs['base'][k] else '**differs**'
            if out.sum() or walk != 'ok':
                ok = False
            lines.append('| %s | %s | %s | %s | %.0f%% |' % (b, f[:-4], walk, '0 px' if not out.sum() else '**%d px**' % out.sum(),
                                                         100 * m[V].mean()))
    lines += ['', 'base noise per checkpoint: ' + ', '.join('%s %d px' % (f[:-4], n.sum()) for f, n in noise.items() if n is not None),
              '', '**GATE (mechanical): %s**. Visual review: `gate_report.png`.' % ('PASS' if ok else 'FAIL')]
    open(os.path.join(root, 'gate_report.md'), 'w').write('\n'.join(lines) + '\n')

    rows = ['base_a'] + builds
    sheet = Image.new('RGB', (len(shots) * 352, len(rows) * 301)); d = ImageDraw.Draw(sheet)
    for r, b in enumerate(rows):
        for c, f in enumerate(shots):
            p = os.path.join(root, b, f)
            if os.path.exists(p):
                sheet.paste(Image.open(p).convert('RGB').crop((276, 31, 628, 320)), (c * 352, r * 301 + 12))
            d.text((c * 352 + 2, r * 301), '%s %s' % (b, f[:-4]), fill=(255, 255, 0))
    sheet.save(os.path.join(root, 'gate_report.png'))
    print('\n'.join(lines))
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
