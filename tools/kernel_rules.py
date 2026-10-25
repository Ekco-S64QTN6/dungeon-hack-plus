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
    if p978 < 0 and len(kernel) in KNOWN_KERNEL_SIZES:
        # anchor overwritten on purpose (test-only force_graphics); all known kernels (ENG 15446,
        # FRE/GER 15428 bytes) keep these tables at the same offsets
        return dict(DEFAULT_OFFSETS)
    assert p978 >= 0 and kernel.find(pat, p978 + 1) < 0, 'palette table not found uniquely'
    find = lambda vals: kernel.find(st.pack('<%dI' % len(vals), *vals))
    offs = {'palette': p978, 'floor_wall': p978 + 84, 'wallpal_wall': p978 + 92,
            'floorpal_floor': p978 + 113, 'wallpal_floorpal': p978 + 134,
            'wallset': find(range(190, 197)), 'stairs': find(range(197, 204)), 'floor': find(range(153, 161)),
            'door': find([122, 0, 123, 124, 125, 126])}
    assert all(v >= 0 for v in offs.values()), offs
    return offs
WALLSETS = ['Marble', 'Wood', 'Stone', 'Foil', 'Ice', 'Mine', 'Rock']
N_FLOOR, N_PAL = 8, 21


def read(kernel):
    o = locate(kernel)
    return {
        'floor_ok_for_wall': list(kernel[o['floor_wall']:o['floor_wall'] + N_FLOOR]),           # [floor] -> wallset mask
        'wallpal_ok_for_wall': list(kernel[o['wallpal_wall']:o['wallpal_wall'] + N_PAL]),       # [pal] -> wallset mask
        'floorpal_ok_for_floor': list(kernel[o['floorpal_floor']:o['floorpal_floor'] + N_PAL]),  # [pal] -> floor mask
        'wallpal_ok_with_floorpal': list(struct.unpack_from('<%dI' % N_PAL, kernel, o['wallpal_floorpal'])),
    }


def write(kernel, rules):
    k = bytearray(kernel); o = locate(kernel)
    k[o['floor_wall']:o['floor_wall'] + N_FLOOR] = bytes(rules['floor_ok_for_wall'])
    k[o['wallpal_wall']:o['wallpal_wall'] + N_PAL] = bytes(rules['wallpal_ok_for_wall'])
    k[o['floorpal_floor']:o['floorpal_floor'] + N_PAL] = bytes(rules['floorpal_ok_for_floor'])
    struct.pack_into('<%dI' % N_PAL, k, o['wallpal_floorpal'], *rules['wallpal_ok_with_floorpal'])
    assert len(k) == len(kernel)
    return bytes(k)


def problems(rules):
    """Every reachable (wallset, floor, floorpal) must leave at least one choice at each step."""
    out = []
    for w in range(7):
        floors = [f for f in range(N_FLOOR) if rules['floor_ok_for_wall'][f] >> w & 1]
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
    for w, name in enumerate(WALLSETS):
        pals = [p for p in range(N_PAL) if rules['wallpal_ok_for_wall'][p] >> w & 1]
        floors = [f for f in range(N_FLOOR) if rules['floor_ok_for_wall'][f] >> w & 1]
        lines.append('%-7s wall palettes %s  floors %s' % (name, pals, floors))
    return '\n'.join(lines)


def set_wall_palettes(rules, wallset, palettes):
    """Restrict which wall/floor palette ramps a wallset may be shown with."""
    w = WALLSETS.index(wallset.replace(' Wallset', ''))
    for p in range(N_PAL):
        if p in palettes:
            rules['wallpal_ok_for_wall'][p] |= 1 << w
        else:
            rules['wallpal_ok_for_wall'][p] &= ~(1 << w) & 0xFF
    return rules


# --- test-only: make level graphics deterministic for screenshot diffs -------
# "setup level graphics" resolves resources through these long tables; pointing
# every entry at one resource removes the time-seeded per-level randomization.
TABLES = {'wallset': (950, 7), 'stairs': (922, 7), 'floor': (794, 8), 'palette': (978, 21), 'door': (718, 19)}


def force(kernel, **resources):
    k = bytearray(kernel); o = locate(kernel)
    for key, res in resources.items():
        _, n = TABLES[key]; off = o[key]
        vals = list(struct.unpack_from('<%dI' % n, k, off))
        vals = [res if v else 0 for v in vals]          # keep the door table's rejected (0) slots
        struct.pack_into('<%dI' % n, k, off, *vals)
    return bytes(k)


# --- theme coherence: pair a wallset with its own floor and hue-matched palettes ----
def set_wall_floors(rules, wallset, floors):
    """table1062: which Floor-N may appear with this wallset."""
    w = WALLSETS.index(wallset.replace(' Wallset', ''))
    for f in range(N_FLOOR):
        if f in floors:
            rules['floor_ok_for_wall'][f] |= 1 << w
        else:
            rules['floor_ok_for_wall'][f] &= ~(1 << w) & 0xFF
    return rules


def set_floor_palettes(rules, floor, palettes):
    """table1091: which wall/floor palettes may colour Floor-N."""
    for p in range(N_PAL):
        if p in palettes:
            rules['floorpal_ok_for_floor'][p] |= 1 << floor
        else:
            rules['floorpal_ok_for_floor'][p] &= ~(1 << floor) & 0xFF
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
