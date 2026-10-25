"""Plan a key route on a fixture level: start -> a cell N steps before a feature, facing it.

Map: LEVELS.DAT level chunk, 0/1 = wall, 0xFF = open. FEA type 0 = party start,
1 = door (byte 3: 0x05 = N/S passage, 0x0a = E/W), 4/5 = stairs up/down.
Keys: KP_8 forward, KP_7 turn left, KP_9 turn right (verified in DOSBox).
"""
import collections, json, sys
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]          # N E S W


def load(sg, level=0):
    lv = open(sg + '/LEVELS.DAT', 'rb').read()[4 + 1024 * level: 4 + 1024 * (level + 1)]
    f = open(sg + '/FEA%02d.DAT' % level, 'rb').read()
    recs = [f[i:i + 8] for i in range(0, len(f), 8) if any(f[i:i + 8])]
    return lv, recs


def plan(lv, recs, kind, back=2, facing=0):
    open_ = lambda x, y: 0 <= x < 32 and 0 <= y < 32 and lv[y * 32 + x] == 0xFF
    start = next((r[1], r[2]) for r in recs if r[0] == 0)
    blocked = {(r[1], r[2]) for r in recs if r[0] in (1, 4, 5)}
    goals = {}
    for r in recs:
        if r[0] != kind:
            continue
        axes = ([0, 2] if r[3] & 0x05 else [1, 3]) if kind == 1 else [0, 1, 2, 3]
        for d in axes:                                   # stand `back` cells away, looking at it
            dx, dy = DIRS[(d + 2) % 4]
            cells = [(r[1] + dx * k, r[2] + dy * k) for k in range(1, back + 1)]
            if all(open_(*c) and c not in blocked for c in cells):
                goals[cells[-1]] = (d, (r[1], r[2]))
    prev = {start: None}; q = collections.deque([start])
    while q:
        c = q.popleft()
        if c in goals:
            break
        for dx, dy in DIRS:
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and open_(*n) and n not in blocked:
                prev[n] = c; q.append(n)
    else:
        sys.exit('no route')
    path = []
    while c:
        path.append(c); c = prev[c]
    path.reverse()
    keys, f = [], facing
    def turn_to(d):
        nonlocal f
        diff = (d - f) % 4
        keys.extend({0: [], 1: ['KP_9'], 2: ['KP_9', 'KP_9'], 3: ['KP_7']}[diff]); f = d
    for a, b in zip(path, path[1:]):
        turn_to(DIRS.index((b[0] - a[0], b[1] - a[1]))); keys.append('KP_8')
    turn_to(goals[path[-1]][0])
    return start, path, goals[path[-1]][1], keys


if __name__ == '__main__':
    sg, kind, back = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    lv, recs = load(sg)
    start, path, target, keys = plan(lv, recs, kind, back)
    print(json.dumps({'start': start, 'target': target, 'steps': len(path) - 1, 'keys': keys}))
