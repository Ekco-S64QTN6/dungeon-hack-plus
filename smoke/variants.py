"""Forced-graphics smoke variants per preset x wallset, for the in-game gate.

  python3 -I smoke/variants.py PRESET [WALLSET ...]     (PRESET = pool/recipe_PRESET.json; build/PRESET must exist)
For each wallset W the preset reskins (or the ones given), writes and builds
  pool/smoke/PRESET__W.json   preset jobs + force_graphics(W, its stairs, a reskinned door, a floor,
                              a palette the BUILT kernel rules allow for W)
  pool/smoke/base__PRESET__W.json  the same force_graphics alone (comparable base)
and prints the pairs for smoke/gate.py --base.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import aesop, kernel_rules   # noqa: E402


def main(preset, wallsets=None):
    jobs = json.load(open(os.path.join(ROOT, 'pool', 'recipe_%s.json' % preset)))['jobs']
    targets = [j.get('target', '') for j in jobs]
    walls = wallsets or [t for t in dict.fromkeys(targets) if t.endswith('Wallset')] or ['Stone Wallset']
    doors = [t for t in dict.fromkeys(targets) if t.startswith('Door-')] or ['Door-05']
    floors = [t for t in dict.fromkeys(targets) if t.startswith('Floor-')] or ['Floor-0']
    r = aesop.ResFile(os.path.join(ROOT, 'build', preset, 'HACK.RES'))
    rules = kernel_rules.read(r.entry(r.names()['kernel'])[2])
    os.makedirs(os.path.join(ROOT, 'pool', 'smoke'), exist_ok=True)
    pairs = []
    for k, w in enumerate(walls):
        stem = w.split()[0]; widx = kernel_rules.WALLSETS.index(stem)
        pal = next(p for p in range(21) if rules['wallpal_ok_for_wall'][p] >> widx & 1)
        allowed = ['Floor-%d' % f for f in range(rules['n_floors']) if rules['floor_ok_for_wall'][f] >> widx & 1]
        floor = next((f for f in allowed if f in floors), allowed[0] if allowed else floors[0])
        force = {"type": "force_graphics", "target": "kernel (TEST ONLY)", "wallset": w, "stairs": "%s Stairs" % stem,
                 "floor": floor, "ground": floor.replace('Floor', 'Ground'), "palette": "wall/floor palette %02d" % pal,
                 "door": doors[k % len(doors)]}
        tag = '%s__%s' % (preset, stem.lower())
        engine = [j for j in jobs if j['type'] in ('extra_wallset', 'extra_floors', 'extra_doors')]   # base = same engine, DH art
        for name, js in (('smoke_' + tag, jobs + [force]), ('smokebase_' + tag, engine + [force])):
            path = os.path.join(ROOT, 'pool', 'smoke', name + '.json')
            json.dump({"comment": "SMOKE VARIANT (test only)", "jobs": js}, open(path, 'w'), indent=1)
            out = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'pipeline.py'), 'build', path, name],
                                 capture_output=True, text=True).stdout
            if 'VERIFY OK' not in out:
                sys.exit('build failed: %s\n%s' % (name, out[-800:]))
        pairs.append(('smokebase_' + tag, 'smoke_' + tag, force))
        print('%s  wallset=%s palette=%02d door=%s stairs=%s floor=%s' % (tag, w, pal, force['door'], force['stairs'], force['floor']))
    return pairs


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or None)
