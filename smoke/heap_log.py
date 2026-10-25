"""Heap use during a walk, from builds that carry the test-only `heap_probe` job (tools/heap_probe.py).

  python3 -I smoke/heap_log.py PLAN.json BUILD [BUILD...]
Runs smoke/walker.py PLAN on each build while polling the HEAP.LOG the game rewrites every tick:
(tick, heapfree, heapfree after flushing the cache, xmsfree, level). The flushed figure is what stays
locked, i.e. the working set the game needs at that moment; its minimum over a walk is the margin.
Writes smoke_runs/heap/<plan>__<build>.json and prints a summary.
"""
import json
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import smoke   # noqa: E402

FIELDS = ('tick', 'free', 'free_flushed', 'xms_free', 'level')


def run(plan, build, env=None):
    open(os.path.join(ROOT, 'build', build, 'HEAP.LOG'), 'wb').close()      # update_file needs it to exist
    log = os.path.join(smoke.RUNS, build, 'HEAP.LOG')
    if os.path.exists(log):
        os.remove(log)
    p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'walker.py'), plan, build], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    recs, last = [], None
    while True:
        done = p.poll() is not None
        try:
            d = open(log, 'rb').read(20)
        except OSError:
            d = b''
        if len(d) == 20 and d != last:
            last = d
            rec = dict(zip(FIELDS, struct.unpack('<5I', d)))
            if not recs or rec['tick'] != recs[-1]['tick']:
                recs.append(rec)
        if done:
            break
        time.sleep(0.2)
    return recs, p.stdout.read()


def main(plan, builds):
    out = os.path.join(smoke.RUNS, 'heap'); os.makedirs(out, exist_ok=True)
    tag = os.path.splitext(os.path.basename(plan))[0]
    for b in builds:
        recs, walk = run(plan, b)
        json.dump({'plan': plan, 'build': b, 'records': recs, 'walk': walk.strip().splitlines()[-1:]},
                  open(os.path.join(out, '%s__%s.json' % (tag, b)), 'w'), indent=1)
        if not recs:
            print('%s: no records (probe missing, or the game never reached the dungeon)' % b)
            continue
        f, ff = [r['free'] for r in recs], [r['free_flushed'] for r in recs]
        print('%s: %d records, ticks %d-%d, levels %s | free %d..%d | after flush %d..%d | xms free %d' % (
            b, len(recs), recs[0]['tick'], recs[-1]['tick'], sorted({r['level'] for r in recs}),
            min(f), max(f), min(ff), max(ff), min(r['xms_free'] for r in recs)))
        print('   walk: %s' % ' '.join(walk.strip().splitlines()[-1:]))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
