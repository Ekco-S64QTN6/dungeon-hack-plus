"""Dungeon Hack's per-level graphics pairing rules (HACK.RES "kernel" code resource).

Decoded from the "randomize graphics" handler (daesop -j HACK.RES kernel):
  per level: wallnum  = rnd(0..6)
             floornum = rnd(0..7)  until table1062[floornum] & (1 << wallnum)
             floorpal = rnd(0..20) until table1091[floorpal] & (1 << floornum)
             wallpal  = rnd(0..20) until table1070[wallpal]  & (1 << wallnum)
                                    and table1112[wallpal]  & (1 << floorpal)
"setup level graphics" then uses table950[wallnum] (wallset 190-196),
table794[floornum] (Floor-0..7) and set_palette(1|2, table978[wallpal|floorpal]).
The loops retry forever, so an unsatisfiable rule hangs new-game creation.
Offsets are byte offsets into the kernel payload (match daesop's labels).
"""
import struct

T1062, T1070, T1091, T1112 = 1062, 1070, 1091, 1112   # ENG offsets (names follow daesop's labels)


KNOWN_KERNEL_SIZES = (15446, 15428)
DEFAULT_OFFSETS = {'palette': 978, 'floor_wall': 1062, 'wallpal_wall': 1070, 'floorpal_floor': 1091, 'wallpal_floorpal': 1112,
                   'wallset': 950, 'stairs': 922, 'floor': 794, 'door': 718}


def locate(kernel):
    """Find the graphics tables by content (FRE/GER kernels are 18 bytes shorter, so offsets shift).
    table978 = 21 longs 169..189 (palette resources); the four mask tables follow it contiguously
    (1062 = +84, 1070 = +92, 1091 = +113, 1112 = +134 in ENG)."""
    import struct as st
    pat = st.pack('<21I', *range(169, 190))
    p978 = kernel.find(pat)
    loads = {k: st.unpack_from('<H', kernel, _table_operand(kernel, pattern))[0]   # where the code reads them from
             for k, pattern in (('wallset', LOAD_WALLSET), ('stairs', LOAD_STAIRSET), ('floor', LOAD_FLOOR))}
    if p978 < 0:
        # anchor overwritten on purpose (test-only force_graphics): every known kernel (ENG, FRE, GER;
        # extensions only append) keeps these tables at the same offsets
        return dict(DEFAULT_OFFSETS, door=_door_table(kernel), **loads)
    assert p978 >= 0 and kernel.find(pat, p978 + 1) < 0, 'palette table not found uniquely'
    find = lambda vals: kernel.find(st.pack('<%dI' % len(vals), *vals))
    offs = {'palette': p978, 'floor_wall': p978 + 84, 'wallpal_wall': p978 + 92,
            'floorpal_floor': p978 + 113, 'wallpal_floorpal': p978 + 134,
            'wallset': loads['wallset'], 'stairs': loads['stairs'], 'floor': loads['floor'],
            'door': _door_table(kernel)}
    assert all(v >= 0 for v in offs.values()), offs
    return offs
WALLSETS = ['Marble', 'Wood', 'Stone', 'Foil', 'Ice', 'Mine', 'Rock', 'Eighth'] + ['W%02d' % i for i in range(8, 16)]
# slots 7+ exist only after add_wallsets(); their resources are "<name> Wallset" / "<name> Stairs"
N_FLOOR, N_PAL = 8, 21


# "randomize graphics": wallnum = rnd(0, 7 - 1) -> SHTC 7; PUSH; SHTC 1; SUB; CALL 2; SSBA "B:wallnum"
RND_WALL = bytes.fromhex('1d07041d010a21024254 01'.replace(' ', ''))
# "setup level graphics": LSBA "B:wallnum"; AIS 2; LTDA <table>; SXD "L:wallset" | "L:stairset"
LOAD_WALLSET = (bytes.fromhex('3f540127022a'), bytes.fromhex('4b0c00'))
LOAD_STAIRSET = (bytes.fromhex('3f540127022a'), bytes.fromhex('4b1200'))


def n_walls(kernel):
    """7 for the original kernel, 8 after add_wallset()."""
    i = kernel.find(RND_WALL[2:])
    assert i >= 2 and kernel.count(RND_WALL[2:]) == 1, 'wallset rnd() not found'
    return kernel[i - 1]


def _table_operand(kernel, pattern):
    pre, post = pattern
    pos = 0
    while True:
        i = kernel.find(pre, pos)
        assert i >= 0, 'table load not found'
        if kernel[i + len(pre) + 2:i + len(pre) + 5] == post:
            return i + len(pre)                       # offset of the u16 table address
        pos = i + 1


LOAD_FLOOR = (bytes.fromhex('3f3b0127022a'), bytes.fromhex('4b0e00'))     # LSBA floornum; AIS 2; LTDA; SXD "L:floorset"
LOAD_GROUND = (bytes.fromhex('3f3b0127022a'), bytes.fromhex('4b1400'))    # ... SXD "L:groundset"
# "randomize graphics" picks: rnd(0, n - 1) then SAW locVar_W:6; LAW locVar_W:6; <mask lookup>. The floor
# pick is the first such call (palette picks use n = 21).
RND_PICK_TAIL = bytes.fromhex('041d010a21023006002d0600')
MASK_IDS = {'floor_wall': 0, 'wallpal_wall': 1, 'floorpal_floor': 2}
MASK_ROWS = {'floor_wall': 16, 'wallpal_wall': 21, 'floorpal_floor': 21}   # word tables: room for 16 floors


def _pick_sites(kernel):
    out, pos = [], 0
    while True:
        i = kernel.find(RND_PICK_TAIL, pos)
        if i < 0:
            return out
        out.append(i); pos = i + 1


def n_floors(kernel):
    i = next(i for i in _pick_sites(kernel) if kernel[i - 1] != 21 and kernel[i - 2] == 0x1d)
    return kernel[i - 1]


def wide_masks(kernel):
    """{mask name: word-table offset} for masks widened by widen_masks() (found by their stub markers)."""
    out = {}
    for name, mid in MASK_IDS.items():
        j = kernel.find(b'DHW' + bytes([mid]))
        if j >= 0:
            out[name] = struct.unpack_from('<H', kernel, j + 4)[0]
    return out


def widen_masks(kernel):
    """Engine extension: the three 8-bit pairing masks (floor->wallsets, wall palette->wallsets,
    floor palette->floors) become 16-bit, so up to 16 wallsets and 16 floors. Each LTBA lookup site in
    "randomize graphics" is replaced by BRA to a stub: PUSH; SHTC 1; SHL (index*2); LTWA <word table>;
    BRA back. A marker 'DHW' + id + u16 table offset follows each stub (never executed)."""
    k = bytearray(kernel)
    if wide_masks(k):
        return bytes(k)
    o = locate(kernel)
    for name, mid in MASK_IDS.items():
        old = o[name]
        site_pat = b'\x28' + struct.pack('<H', old)
        site = k.find(site_pat)
        assert site >= 0 and k.find(site_pat, site + 1) < 0, 'mask lookup for %s not found uniquely' % name
        n_old = N_FLOOR if name == 'floor_wall' else N_PAL
        vals = list(k[old:old + n_old]) + [0] * (MASK_ROWS[name] - n_old)
        table = len(k); k += struct.pack('<%dH' % len(vals), *vals)
        stub = len(k)
        k += b'\x04\x1d\x01\x13\x29' + struct.pack('<H', table) + b'\x02' + struct.pack('<H', site + 3)
        k += b'DHW' + bytes([mid]) + struct.pack('<H', table)
        k[site:site + 3] = b'\x02' + struct.pack('<H', stub)
    assert len(k) < 0x10000
    return bytes(k)


def _extend_table(k, pattern, new_res):
    """Append a copy of the long table that `pattern`'s LTDA reads, plus new_res; repoint that load."""
    op = _table_operand(k, pattern)
    old = struct.unpack_from('<H', k, op)[0]
    return old, op


def add_wallsets(kernel, wallset_res, stairs_res):
    """Engine extension: more wallsets (8 fit the original 8-bit masks; up to 16 after widen_masks).
    Copies of the wallset/stairs tables with the new resources are appended to the kernel, the two loads
    in "setup level graphics" repointed, rnd(0..n-1) raised, and the debug "change wallset" wrap updated."""
    k = bytearray(kernel)
    n0 = n_walls(k); n = n0 + len(wallset_res)
    assert n <= 8 or wide_masks(k), 'more than 8 wallsets needs widen_masks() first'
    assert n <= 16
    for pattern, res in ((LOAD_WALLSET, wallset_res), (LOAD_STAIRSET, stairs_res)):
        op = _table_operand(k, pattern)
        old = struct.unpack_from('<H', k, op)[0]
        vals = list(struct.unpack_from('<%dI' % n0, k, old)) + list(res)
        new = len(k); k += struct.pack('<%dI' % n, *vals)
        struct.pack_into('<H', k, op, new)
    i = k.find(RND_WALL[2:]); k[i - 1] = n
    j = k.find(bytes.fromhex('3f5401041d%02x17' % n0))          # "change wallset": if (wallnum == n) wallnum = 0
    if j >= 0:
        k[j + 5] = n
    assert len(k) < 0x10000
    return bytes(k)


def add_floors(kernel, floor_res, ground_res):
    """Engine extension: more floors (needs widen_masks(); up to 16). Floor and ground-set tables are
    extended like the wallset ones, and the floor pick becomes rnd(0..n-1)."""
    k = bytearray(kernel)
    assert wide_masks(k), 'more floors needs widen_masks() first'
    n0 = n_floors(k); n = n0 + len(floor_res)
    assert n <= 16
    for pattern, res in ((LOAD_FLOOR, floor_res), (LOAD_GROUND, ground_res)):
        op = _table_operand(k, pattern)
        old = struct.unpack_from('<H', k, op)[0]
        vals = list(struct.unpack_from('<%dI' % n0, k, old)) + list(res)
        new = len(k); k += struct.pack('<%dI' % n, *vals)
        struct.pack_into('<H', k, op, new)
    i = next(i for i in _pick_sites(k) if k[i - 1] == n0 and k[i - 2] == 0x1d); k[i - 1] = n
    j = k.find(bytes.fromhex('3f3b01041d%02x17' % n0))           # "change floorset" wrap
    if j >= 0:
        k[j + 5] = n
    assert len(k) < 0x10000
    return bytes(k)


def extended_rules(kernel, n_walls_total, n_floors_total, wall_src='Rock', floor_src=2):
    """Rules as the pipeline's extra_wallset / extra_floors jobs leave them (new wallsets copy the
    pairing bits of `wall_src`, new floors those of Floor-`floor_src`), for validating a roll before
    building it. Resource numbers are placeholders."""
    k = kernel
    if n_walls_total > 8 or n_floors_total > 8:
        k = widen_masks(k)
    w0, f0 = n_walls(k), n_floors(k)
    if n_walls_total > w0:
        k = add_wallsets(k, [0] * (n_walls_total - w0), [0] * (n_walls_total - w0))
    if n_floors_total > f0:
        k = add_floors(k, [0] * (n_floors_total - f0), [0] * (n_floors_total - f0))
    rules = read(k)
    ws = WALLSETS.index(wall_src)
    for key, n in (('floor_ok_for_wall', f0), ('wallpal_ok_for_wall', N_PAL)):
        for i in range(n):
            if rules[key][i] >> ws & 1:
                for w in range(w0, n_walls_total):
                    rules[key][i] |= 1 << w
    for f in range(f0, n_floors_total):
        rules['floor_ok_for_wall'][f] = rules['floor_ok_for_wall'][floor_src]
        for p in range(N_PAL):
            if rules['floorpal_ok_for_floor'][p] >> floor_src & 1:
                rules['floorpal_ok_for_floor'][p] |= 1 << f
    return rules


def add_wallset(kernel, wallset_res, stairs_res):
    """The 8th wallset (fits the original 8-bit masks)."""
    assert n_walls(kernel) == 7, 'kernel already extended'
    return add_wallsets(kernel, [wallset_res], [stairs_res])


# "randomize graphics": doornum = rnd(0, 19 - 1) -> SHTC 0; PUSH; SHTC n; PUSH; SHTC 1; SUB; CALL 2; SSBA "B:doornum"
RND_DOOR_TAIL = bytes.fromhex('041d010a2102429f01')


def n_doors(kernel):
    i = kernel.find(RND_DOOR_TAIL)
    assert i >= 2 and kernel.count(RND_DOOR_TAIL) == 1 and kernel[i - 2] == 0x1d, 'door rnd() not found'
    return kernel[i - 1]


def add_doors(kernel, door_res):
    """Engine extension: more doors. The 19-entry door table (index = doornum, 0 = never picked) is
    copied to the end of the kernel with the new resources appended, all three LTDA loads (level
    setup, randomize's rejection check, debug "change doorset") are repointed, and the randomize
    bound rnd(0..18) becomes rnd(0..18+n). Door rules only test doornum 5-9, 11 and 18; the doors
    script only tests 3/7/14/17 (see-through types), so new numbers are plain blocking doors."""
    k = bytearray(kernel)
    n0 = n_doors(k)
    old = _door_table(k)
    vals = list(struct.unpack_from('<%dI' % n0, k, old)) + list(door_res)
    assert len(vals) < 256, 'doornum is a byte'
    new = len(k); k += struct.pack('<%dI' % len(vals), *vals)
    assert new + 4 * len(vals) < 0x10000
    pat = b'\x2a' + struct.pack('<H', old)
    sites = [i for i in range(len(k) - 2) if k[i:i + 3] == pat]
    assert len(sites) == 3, 'expected 3 door table loads, found %d' % len(sites)
    for i in sites:
        struct.pack_into('<H', k, i + 1, new)
    i = k.find(RND_DOOR_TAIL); k[i - 1] = len(vals)
    wrap = bytes.fromhex('3f9f01041d%02x17' % n0)          # "change doorset": if (doornum == 19) doornum = 0
    j = k.find(wrap)
    if j >= 0:
        k[j + 5] = len(vals)
    return bytes(k)


def _door_table(kernel):
    """Offset of the door table the code currently reads (content-found original, or the appended copy)."""
    i = kernel.find(bytes.fromhex('3f9f0127022a'))         # LSBA "B:doornum"; AIS 2; LTDA <table> (level setup)
    assert i >= 0
    return struct.unpack_from('<H', kernel, i + 6)[0]


def read(kernel):
    o = locate(kernel)
    wide = wide_masks(kernel)
    nf = n_floors(kernel)

    def mask(name, rows, off):
        if name in wide:
            return list(struct.unpack_from('<%dH' % rows, kernel, wide[name]))
        return list(kernel[off:off + rows])
    return {
        'n_walls': n_walls(kernel), 'n_floors': nf, 'wide': bool(wide),
        'floor_ok_for_wall': mask('floor_wall', nf, o['floor_wall']),            # [floor] -> wallset mask
        'wallpal_ok_for_wall': mask('wallpal_wall', N_PAL, o['wallpal_wall']),   # [pal] -> wallset mask
        'floorpal_ok_for_floor': mask('floorpal_floor', N_PAL, o['floorpal_floor']),  # [pal] -> floor mask
        'wallpal_ok_with_floorpal': list(struct.unpack_from('<%dI' % N_PAL, kernel, o['wallpal_floorpal'])),
    }


def write(kernel, rules):
    k = bytearray(kernel); o = locate(kernel)
    wide = wide_masks(kernel)
    for name, key, off in (('floor_wall', 'floor_ok_for_wall', o['floor_wall']), ('wallpal_wall', 'wallpal_ok_for_wall', o['wallpal_wall']),
                           ('floorpal_floor', 'floorpal_ok_for_floor', o['floorpal_floor'])):
        vals = rules[key]
        if name in wide:
            struct.pack_into('<%dH' % len(vals), k, wide[name], *[v & 0xFFFF for v in vals])
        else:
            k[off:off + len(vals)] = bytes(v & 0xFF for v in vals)
    struct.pack_into('<%dI' % N_PAL, k, o['wallpal_floorpal'], *rules['wallpal_ok_with_floorpal'])
    assert len(k) == len(kernel)
    return bytes(k)


def problems(rules):
    """Every reachable (wallset, floor, floorpal) must leave at least one choice at each step."""
    out = []
    for w in range(rules.get('n_walls', 7)):
        floors = [f for f in range(rules.get('n_floors', N_FLOOR)) if rules['floor_ok_for_wall'][f] >> w & 1]
        if not floors:
            out.append('wallset %s: no compatible floor' % WALLSETS[w])
        for f in floors:
            fpals = [p for p in range(N_PAL) if rules['floorpal_ok_for_floor'][p] >> f & 1]
            if not fpals:
                out.append('floor %d: no floor palette' % f)
            for fp in fpals:
                if not any(rules['wallpal_ok_for_wall'][p] >> w & 1 and rules['wallpal_ok_with_floorpal'][p] >> fp & 1
                           for p in range(N_PAL)):
                    out.append('wallset %s + floor %d + floorpal %d: no wall palette' % (WALLSETS[w], f, fp))
    return out


def describe(rules):
    lines = []
    for w, name in enumerate(WALLSETS[:rules.get('n_walls', 7)]):
        pals = [p for p in range(N_PAL) if rules['wallpal_ok_for_wall'][p] >> w & 1]
        floors = [f for f in range(rules.get('n_floors', N_FLOOR)) if rules['floor_ok_for_wall'][f] >> w & 1]
        lines.append('%-7s wall palettes %s  floors %s' % (name, pals, floors))
    return '\n'.join(lines)


def set_wall_palettes(rules, wallset, palettes):
    """Restrict which wall/floor palette ramps a wallset may be shown with."""
    w = WALLSETS.index(wallset.replace(' Wallset', ''))
    for p in range(N_PAL):
        if p in palettes:
            rules['wallpal_ok_for_wall'][p] |= 1 << w
        else:
            rules['wallpal_ok_for_wall'][p] &= ~(1 << w) & 0xFFFF
    return rules


# --- test-only: make level graphics deterministic for screenshot diffs -------
# "setup level graphics" resolves resources through these long tables; pointing
# every entry at one resource removes the time-seeded per-level randomization.
TABLES = {'wallset': (950, 7), 'stairs': (922, 7), 'floor': (794, 8), 'palette': (978, 21), 'door': (718, 19)}


def force(kernel, **resources):
    k = bytearray(kernel); o = locate(kernel)
    for key, res in resources.items():
        _, n = TABLES[key]; off = o[key]
        if key in ('wallset', 'stairs'):
            n = n_walls(kernel)
        elif key == 'door':
            n = n_doors(kernel)
        elif key == 'floor':
            n = n_floors(kernel)
        vals = list(struct.unpack_from('<%dI' % n, k, off))
        vals = [res if v else 0 for v in vals]          # keep the door table's rejected (0) slots
        struct.pack_into('<%dI' % n, k, off, *vals)
    return bytes(k)


# --- theme coherence: pair a wallset with its own floor and hue-matched palettes ----
def set_wall_floors(rules, wallset, floors):
    """table1062: which Floor-N may appear with this wallset."""
    w = WALLSETS.index(wallset.replace(' Wallset', ''))
    for f in range(rules.get('n_floors', N_FLOOR)):
        if f in floors:
            rules['floor_ok_for_wall'][f] |= 1 << w
        else:
            rules['floor_ok_for_wall'][f] &= ~(1 << w) & 0xFFFF
    return rules


def set_floor_palettes(rules, floor, palettes):
    """table1091: which wall/floor palettes may colour Floor-N."""
    for p in range(N_PAL):
        if p in palettes:
            rules['floorpal_ok_for_floor'][p] |= 1 << floor
        else:
            rules['floorpal_ok_for_floor'][p] &= ~(1 << floor) & 0xFFFF
    return rules


def allow_pairs(rules, wallpals, floorpals):
    """table1112: make every (wall palette, floor palette) pair legal (only adds bits)."""
    for p in wallpals:
        for fp in floorpals:
            rules['wallpal_ok_with_floorpal'][p] |= 1 << fp
    return rules


def match_palettes(src_rgb, palettes_rgb, k=3, candidates=range(15)):
    """Pick the k ramp palettes whose mid-tones best match the source art's hue.

    src_rgb: (N,3) array of the source art's pixels; palettes_rgb: {p: [r,g,b]*16}.
    Colours are compared after dividing out brightness (chromaticity), so a dark
    blue wall still matches a light blue ramp.
    """
    import numpy as np
    s = np.asarray(src_rgb, float).reshape(-1, 3)
    s = s[s.sum(1) > 30]
    chrom = lambda c: c / max(1.0, c.sum())
    target = chrom(s.mean(0))
    scored = []
    for p in candidates:
        mid = np.asarray(palettes_rgb[p], float).reshape(-1, 3)[3:10].mean(0)
        scored.append((float(((chrom(mid) - target) ** 2).sum()), p))
    return [p for _, p in sorted(scored)[:k]]
