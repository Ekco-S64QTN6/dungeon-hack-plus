#!/usr/bin/env python3
"""Cross-engine asset pipeline for a Dungeon Hack mashup.

  python3 -I mashup/pipeline.py inventory          # what is in every game folder
  python3 -I mashup/pipeline.py snapshot           # read-only backup of the DH install + hashes
  python3 -I mashup/pipeline.py extract            # AESOP / Westwood / DreamForge -> work/
  python3 -I mashup/pipeline.py build RECIPE NAME  # recipe.json -> build/NAME (a patched copy of DH)
  python3 -I mashup/pipeline.py verify NAME        # structural checks on build/NAME
  python3 -I mashup/pipeline.py roll POOL SEED NAME  # randomized reskin build from pool.json

Nothing is ever written inside the game folders.
"""
import hashlib
import json
import os
import shutil
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import paths
import aesop        # noqa: E402
import dreamforge   # noqa: E402
import kernel_rules  # noqa: E402
import rtd           # noqa: E402
import eob_decos     # noqa: E402
import game_music    # noqa: E402
import eob_doors     # noqa: E402
import normalize    # noqa: E402
import westwood     # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

CFG = json.load(open(os.path.join(HERE, 'config.json')))
ROOT = os.path.normpath(os.path.join(HERE, CFG['root']))
WORK = os.path.join(HERE, 'work')
SIGS = [(b'AESOP/16', 'aesop_res'), (b'GFFI', 'gff'), (b'FORM', 'iff/xmidi'), (b'RIFF', 'riff'),
        (b'MZ', 'dos_exe'), (b'%PDF', 'pdf')]


def gpath(game, *p):
    return paths.get_game_file(game, *p)


def sha(path, n=None):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:n]


def sniff(path):
    head = open(path, 'rb').read(16)
    for sig, name in SIGS:
        if head.startswith(sig):
            return name
    if len(head) >= 10 and struct.unpack_from('<H', head, 2)[0] in (0, 4) \
            and struct.unpack_from('<H', head)[0] + 2 == os.path.getsize(path):
        return 'westwood_lcw'
    return ''


# --------------------------------------------------------------------------- inventory
def cmd_inventory():
    os.makedirs(WORK, exist_ok=True)
    inv, lines = {}, ['# Asset inventory', '']
    for game, g in CFG['games'].items():
        base = gpath(game)
        files = []
        for dp, _, fns in os.walk(base):
            for fn in fns:
                p = os.path.join(dp, fn)
                ext = os.path.splitext(fn)[1].upper().lstrip('.') or '(none)'
                files.append({'path': os.path.relpath(p, base), 'ext': ext,
                              'size': os.path.getsize(p), 'sig': sniff(p)})
        if game == 'menzo':
            for n in range(11):
                p = os.path.join(base, 'RES%d' % n)
                if os.path.exists(p):
                    f = next(x for x in files if x['path'] == 'RES%d' % n)
                    f['sig'] = 'dreamforge_res'
        inv[game] = files
        by = {}
        for f in files:
            by.setdefault(f['ext'], [0, 0])
            by[f['ext']][0] += 1; by[f['ext']][1] += f['size']
        lines += ['## %s (%s) — %d files' % (game, g['engine'], len(files)), '',
                  '| ext | count | bytes |', '|---|---|---|']
        lines += ['| %s | %d | %d |' % (e, c, s) for e, (c, s) in sorted(by.items(), key=lambda x: -x[1][1])]
        lines.append('')
    json.dump(inv, open(os.path.join(WORK, 'inventory.json'), 'w'), indent=1)
    open(os.path.join(WORK, 'inventory.md'), 'w').write('\n'.join(lines))
    print('wrote', os.path.join(WORK, 'inventory.md'))


# --------------------------------------------------------------------------- snapshot
def cmd_snapshot():
    src = paths.get_dh_dir()
    tag = sha(os.path.join(src, 'HACK.RES'), 10)
    dst = os.path.join(HERE, 'backup', 'DH-' + tag)
    if os.path.exists(dst):
        print('snapshot exists:', dst)
    else:
        shutil.copytree(src, dst)
        with open(os.path.join(dst, 'SHA256SUMS'), 'w') as f:
            for dp, _, fns in os.walk(dst):
                for fn in sorted(fns):
                    if fn != 'SHA256SUMS':
                        p = os.path.join(dp, fn)
                        f.write('%s  %s\n' % (sha(p), os.path.relpath(p, dst)))
        print('snapshot written:', dst)


# --------------------------------------------------------------------------- extract
def save_indexed(path, w, h, px, pal, mask=None):
    im = Image.frombytes('P', (w, h), bytes(px))
    im.putpalette(list(pal) + [0] * (768 - len(pal)))
    if mask is not None:
        im.info['transparency'] = 0
        px2 = bytes(v if m else 0 for v, m in zip(px, mask))
        im = Image.frombytes('P', (w, h), px2); im.putpalette(list(pal)); im.info['transparency'] = 0
    im.save(path)


def atlas(frames, pal, path, cols=12):
    W = max(f[0] for f in frames) + 4; H = max(f[1] for f in frames) + 14
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W, rows * H), (48, 0, 48))
    d = ImageDraw.Draw(sheet)
    for k, (w, h, px, m) in enumerate(frames):
        rgb = np.array(pal, dtype=np.uint8).reshape(-1, 3)[np.frombuffer(bytes(px), np.uint8)].reshape(h, w, 3)
        a = np.frombuffer(bytes(m), np.uint8).reshape(h, w)
        tile = np.where(a[..., None] > 0, rgb, np.array([48, 0, 48], np.uint8))
        x, y = (k % cols) * W, (k // cols) * H
        sheet.paste(Image.fromarray(tile.astype(np.uint8)), (x + 2, y + 12))
        d.text((x + 2, y), str(k), fill=(255, 255, 0))
    sheet.save(path)


def write_wav(path, pcm, rate):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(rate); w.writeframes(pcm)


def extract_aesop():
    out = os.path.join(WORK, 'aesop'); os.makedirs(out, exist_ok=True)
    dh = aesop.ResFile(gpath('dh', 'HACK.RES'))
    _, base, _ = aesop.decode_palette(dh.entry(dh.names()['Main Base Palette'])[2])
    _, wall, _ = aesop.decode_palette(dh.entry(dh.names()['wall/floor palette 03'])[2])
    preview = base[:224 * 3] + wall + wall          # floor + wall ramps for previews
    monster_idx = set()
    for game, resname in [('dh', 'HACK.RES'), ('dh', 'OPEN.RES'), ('eob3', 'EYE.RES')]:
        r = aesop.ResFile(gpath(game, resname))
        tag = os.path.splitext(resname)[0].lower()
        d = os.path.join(out, tag); os.makedirs(os.path.join(d, 'raw'), exist_ok=True)
        names = r.index_names(); manifest = []
        if game == 'eob3':
            en = r.names()
            _, fx, _ = aesop.decode_palette(r.entry(en['Fixed palette'])[2])
            _, mp, _ = aesop.decode_palette(r.entry(en['Marble palette'])[2])
            eob3_preview = fx[:176 * 3] + mp + fx[192 * 3:]   # PAL_WALLS region = 0xB0
        for i in r.indices():
            ts, attrib, p = r.entry(i)
            nm = names.get(i, '')
            k = aesop.kind(p, nm)
            manifest.append({'index': i, 'name': nm, 'kind': k, 'size': len(p), 'attrib': attrib})
            safe = '%04d_%s' % (i, ''.join(c if c.isalnum() else '_' for c in nm)[:40])
            if k in ('xmidi', 'pcm_u8', 'vfx110_shapes', 'palette'):
                open(os.path.join(d, 'raw', safe + '.bin'), 'wb').write(p)
            if k == 'pcm_u8':
                write_wav(os.path.join(d, 'raw', safe + '.wav'), p, CFG['pcm_rate_guess'])
            if k == 'vfx110_shapes':
                fr = [f[:4] for f in aesop.decode_vfx110(p)]
                atlas(fr, eob3_preview, os.path.join(d, safe + '.png'), cols=18 if len(fr) % 18 in (0, 1) else 12)
            if k == 'old_shapes' and game == 'dh':
                fr = aesop.decode_shapes(p)
                atlas(fr, preview, os.path.join(d, safe + '.png'), cols=9 if len(fr) == 236 else 12)
                if len(fr) == 6 and fr[0][:2] == (80, 88):
                    for w, h, px, m in fr:
                        monster_idx.update(v for v, mm in zip(px, m) if mm)
        json.dump(manifest, open(os.path.join(d, 'manifest.json'), 'w'), indent=0)
        print(tag, len(manifest), 'entries')
    json.dump({'base_palette': base, 'monster_indices': sorted(monster_idx)},
              open(os.path.join(out, 'dh_palette.json'), 'w'))


def extract_westwood():
    for game in ('eob1', 'eob2'):
        base = gpath(game); out = os.path.join(WORK, 'westwood', game); os.makedirs(out, exist_ok=True)
        files = os.listdir(base)
        default = westwood.read_pal(os.path.join(base, CFG['games'][game]['default_pal']))
        for fn in sorted(files):
            stem, ext = os.path.splitext(fn)
            if ext.upper() == '.CPS':
                try:
                    px, emb = westwood.unpack(os.path.join(base, fn))
                except Exception as e:
                    print('skip', fn, e); continue
                pal = default
                if stem + '.PAL' in files:
                    pal = westwood.read_pal(os.path.join(base, stem + '.PAL'))
                if len(px) >= 64000:
                    save_indexed(os.path.join(out, stem + '.png'), 320, 200, px[:64000], pal)
            if ext.upper() == '.VCN' and stem + '.VMP' in files:
                blocks, remap = westwood.vcn_blocks(os.path.join(base, fn))
                ent = westwood.vmp(os.path.join(base, stem + '.VMP'))
                pal = westwood.read_pal(os.path.join(base, stem + '.PAL')) if stem + '.PAL' in files else default
                w, h, px = westwood.render_blocks(ent[:330], blocks, 22)       # 176x120 backdrop
                save_indexed(os.path.join(out, stem + '_backdrop.png'), w, h, bytes(remap[v] for v in px), pal)
                for t in range((len(ent) - 330) // 431):
                    wt = ent[330 + 431 * t:330 + 431 * (t + 1)]
                    w, h, px = westwood.render_blocks(wt[239:], blocks, 16)     # near front wall 128x96
                    save_indexed(os.path.join(out, '%s_wt%d_front.png' % (stem, t)), w, h,
                                 bytes(remap[16 + v] for v in px), pal)
        print(game, 'done ->', out)


def extract_dreamforge():
    base = gpath('menzo'); out = os.path.join(WORK, 'dreamforge'); os.makedirs(out, exist_ok=True)
    pal = dreamforge.palette(os.path.join(base, 'COLORS'))
    counts = {}
    for n in range(9):
        p = os.path.join(base, 'RES%d' % n)
        d = os.path.join(out, 'RES%d' % n); os.makedirs(d, exist_ok=True)
        for k, typ, flags, payload in dreamforge.records(p):
            if typ is None:
                continue
            counts[(n, typ)] = counts.get((n, typ), 0) + 1
            stem = os.path.join(d, '%04d_t%02x' % (k, typ))
            if typ == 0x05 and len(payload) == 12290:
                w, h, px = dreamforge.texture(payload)
                save_indexed(stem + '.png', w, h, px, pal)
            elif typ == 0x05 and len(payload) == 4096:
                w, h, px = dreamforge.texture(b'\0\0' + payload)
                save_indexed(stem + '_64.png', w, h, px, pal)
            elif payload[:4] == b'FORM':
                open(stem + '.xmi', 'wb').write(payload)
            elif payload[:4] == b'RIFF':
                open(stem + '.wav', 'wb').write(payload)
            elif typ == 0x04:
                write_wav(stem + '.wav', payload, CFG['pcm_rate_guess'])
            else:
                open(stem + '.bin', 'wb').write(payload)
    print('menzo records:', {'RES%d/type%02x' % k: v for k, v in sorted(counts.items())})


def cmd_extract():
    extract_aesop(); extract_westwood(); extract_dreamforge()


# --------------------------------------------------------------------------- build
def frange(spec, n):
    out = set()
    for part in str(spec).split(','):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return sorted(i for i in out if i < n)


def load_rgb(path):
    return np.asarray(Image.open(os.path.join(HERE, path)).convert('RGB'))


def palette_lums(r, p):
    _, rgb, _ = aesop.decode_palette(r.entry(r.names()['wall/floor palette %02d' % p])[2])
    return [0.299 * rgb[i] + 0.587 * rgb[i + 1] + 0.114 * rgb[i + 2] for i in range(0, 48, 3)]


BUILT_SHAPES = {}     # target -> ramp shapes its art was posterized for (saved in MASHUP_BUILD.json)


def ramp_profile(r, target):
    """Mean ramp luminance over the palettes the kernel rules allow for `target`."""
    rules = kernel_rules.read(r.entry(r.names()['kernel'])[2])
    stem = target.split()[0]
    if target.startswith('Floor-'):
        n = int(target.split('-')[1])
        pals = [p for p in range(21) if rules['floorpal_ok_for_floor'][p] >> n & 1]
    elif stem in kernel_rules.WALLSETS:                    # "<X> Wallset" / "<X> Stairs"
        w = kernel_rules.WALLSETS.index(stem)
        pals = [p for p in range(21) if rules['wallpal_ok_for_wall'][p] >> w & 1]
    else:                       # doors, decos: whatever wall palette the level has
        pals = sorted({p for p in range(21) for w in range(7) if rules['wallpal_ok_for_wall'][p] >> w & 1})
    lums = [palette_lums(r, p) for p in pals]
    shapes = {normalize.ramp_shape(l) for l in lums}
    BUILT_SHAPES[target] = sorted(shapes)
    if len(shapes) > 1:
        print('    WARNING: %s is paired with both single- and two-ramp palettes %s; '
              'consider a palette_rules job' % (target, pals))
    return list(np.mean(lums, axis=0)), pals


def job_palette_rules(r, job, pal):
    """Same-size byte patch of the kernel's wallset<->palette pairing tables."""
    idx = r.names()['kernel']
    k = r.entry(idx)[2]
    rules = kernel_rules.read(k)
    for wallset, pals in job.get('wall_palettes', {}).items():
        kernel_rules.set_wall_palettes(rules, wallset, pals)
    for wallset, floors in job.get('wall_floors', {}).items():
        kernel_rules.set_wall_floors(rules, wallset, floors)
    for floor, pals in job.get('floor_palettes', {}).items():
        kernel_rules.set_floor_palettes(rules, int(floor), pals)
    for wallpals, floorpals in job.get('allow_pairs', []):
        kernel_rules.allow_pairs(rules, wallpals, floorpals)
    bad = kernel_rules.problems(rules)
    if bad:
        raise SystemExit('palette_rules would hang new-game creation: %s' % bad[:5])
    r.replace(idx, kernel_rules.write(k, rules))
    print('    ' + kernel_rules.describe(rules).replace('\n', '\n    '))


def job_force_graphics(r, job, pal):
    """TEST ONLY: every level uses the same wallset/stairs/floor/palette/door, for screenshot diffs."""
    names = r.names(); idx = names['kernel']
    res = {k: names[v] for k, v in job.items() if k in kernel_rules.TABLES}
    r.replace(idx, kernel_rules.force(r.entry(idx)[2], **res))
    if 'doornum' in job:            # same for the door pick (SHTC min; PUSH; SHTC count; ...)
        k = bytearray(r.entry(idx)[2]); i = k.find(kernel_rules.RND_DOOR_TAIL)
        assert k[i - 5:i - 3] == b'\x1d\x00' and k[i - 2] == 0x1d
        k[i - 4] = job['doornum']; k[i - 1] = job['doornum'] + 1
        r.replace(idx, bytes(k))
    if 'wallnum' in job:            # pin "randomize graphics" to rnd(n, n): exercises the real per-level path
        k = bytearray(r.entry(idx)[2]); i = k.find(kernel_rules.RND_WALL[2:])
        assert k[i - 5:i - 3] == b'\x1d\x00' and k[i - 2] == 0x1d     # SHTC 0; PUSH; SHTC n (min, count)
        k[i - 4] = job['wallnum']; k[i - 1] = job['wallnum'] + 1
        r.replace(idx, bytes(k))
    if 'wall_deco' in job:          # decoration object's table14 (deco index -> resource), 48 longs at 14
        di = names['decoration']; d = bytearray(r.entry(di)[2])
        vals = struct.unpack_from('<48I', d, 14)
        assert vals[:4] == (229, 230, 231, 232), 'decoration table14 not where expected'
        struct.pack_into('<48I', d, 14, *[names[job['wall_deco']] if v else 0 for v in vals])
        r.replace(di, bytes(d))


EOB3 = {}


def eob3_res():
    if 'r' not in EOB3:
        EOB3['r'] = aesop.ResFile(gpath('eob3', 'EYE.RES'))
    return EOB3['r']


def job_panels(r, job, pal):
    """Copy EOB3 view-position panels (18 per wall object) 1:1 into a DH resource.

    EOB3 PAL_WALLS indices 0xB0-0xBF are re-ranked onto the ramp profile of the DH
    target; EOB3 fixed colours go to the nearest DH fixed colour.
    """
    e3 = eob3_res(); en = e3.names()
    src = aesop.decode_vfx110(e3.entry(en[job['source']])[2])
    idx = r.names()[job['target']]
    dst = aesop.decode_shapes(r.entry(idx)[2])
    _, fixed3, _ = aesop.decode_palette(e3.entry(en['Fixed palette'])[2])
    _, ramp3, _ = aesop.decode_palette(e3.entry(en[job['source_palette']])[2])
    _, dhbase, _ = aesop.decode_palette(r.entry(r.names()['Main Base Palette'])[2])
    lut = np.zeros(256, np.uint8)
    fx = np.array(fixed3, np.uint8).reshape(-1, 3)
    lut[1:176] = normalize.quantize_fixed(fx[None, 1:176], dhbase, range(1, 224))[0]
    src_l = [0.299 * ramp3[i] + 0.587 * ramp3[i + 1] + 0.114 * ramp3[i + 2] for i in range(0, 48, 3)]
    swatch = np.array(ramp3[:45], np.uint8).reshape(1, 15, 3)
    if job.get('colors', 'fixed' if job['target'].startswith('Door-') else 'ramp') == 'fixed':
        # doors appear on every wallset (single- and two-ramp levels): use DH fixed colours instead
        rp = np.array(ramp3, np.uint8).reshape(-1, 3)
        lut[176:192] = normalize.quantize_fixed(rp[None, :16], dhbase, range(1, 224))[0]
    else:
        profile, pals = ramp_profile(r, job.get('ramp_of', job['target']))
        lut[176:191] = normalize.to_ramp_target(swatch, profile, 240, dither=False, stretch=(0, 100))[0]
        lut[191] = 255
    lut[192:] = normalize.quantize_fixed(fx[None, 192:], dhbase, range(1, 224))[0]
    count = job.get('count', 18)
    for k in range(count):
        s = src[job.get('source_first', 0) + k]
        t = job.get('target_first', 0) + k
        w, h, _, m = dst[t]
        spx, smask = bytes(s[2]), bytes(s[3])
        if s[0] == w and 0 < h - s[1] <= 2:     # Ice Stairs' depth-3 panel is 48x38, the rest 48x37: pad rows
            spx += bytes((h - s[1]) * w); smask += bytes((h - s[1]) * w)
        else:
            assert s[:2] == (w, h), 'panel %d: source %s vs target %s' % (k, s[:2], (w, h))
        if job.get('keep_empty', True) and not any(m):
            continue
        dst[t] = (w, h, bytearray(lut[np.frombuffer(spx, np.uint8)].tobytes()), bytearray(smask))
    r.replace(idx, aesop.encode_shapes(dst))


def add_runtime_import(r, code_name, func):
    """Make runtime function `func` (e.g. 'C:load_music') callable from code resource `code_name`:
    adds it to <code>.IMPT at the next free external-reference offset (the runtime sizes the
    thunk from the IMPT entries; C entries are 4 bytes, variables 2) and returns that offset,
    which is the RCRS operand. Returns the existing offset if it is already imported."""
    impt_i = r.names()['%s.IMPT' % code_name]
    H, chains = rtd.parse(r.entry(impt_i)[2])
    ents = {t.decode(): v.decode() for _, c in chains for t, v in c}
    if func in ents:
        return int(ents[func].split(',')[0])
    slot = sum(4 if t[0] == 'C' else 2 for t in ents if t[0] in 'CBWL')
    assert slot == max(int(v.split(',')[0]) + (4 if t[0] == 'C' else 2) for t, v in ents.items() if t[0] in 'CBWL')
    rtd.add(H, chains, func.encode(), str(slot).encode())
    r.replace(impt_i, rtd.build(H, chains))
    return slot


def job_extra_doors(r, job, pal):
    """ENGINE EXTENSION (kernel_rules.add_doors): more door types per game.

    {"count": 16, "copy": "Door-05"}   (runs with the other engine extensions, before the art jobs)
    Adds "Extra Door NN" resources (copies of `copy`, which later eob_door/panels jobs reskin) in free
    directory slots and appends them to the kernel's door table; randomize then picks rnd(0..18+n).
    New door numbers are ordinary blocking doors (see-through types are only 3/7/14/17).
    """
    names = r.names()
    if 'Extra Door 00' in names:
        return
    src = names[job.get('copy', 'Door-05')]
    _, attrib, payload = r.entry(src)
    free = [i for i, p in enumerate(r.ptrs) if not p]
    H, chains = rtd.parse(r.entry(0)[2])
    added = []
    for n, idx in enumerate(free[:job.get('count', 16)]):
        r.replace(idx, payload, attrib=attrib)
        r.data[r.blocks[idx // aesop.SLOTS] + 4 + idx % aesop.SLOTS] = r.data[r.blocks[src // aesop.SLOTS] + 4 + src % aesop.SLOTS]
        name = 'Extra Door %02d' % n
        rtd.add(H, chains, name.encode(), str(idx).encode())
        ADDED[name] = job.get('copy', 'Door-05'); added.append(idx)
    r.replace(0, rtd.build(H, chains)); r._names = None
    ki = r.names()['kernel']
    r.replace(ki, kernel_rules.add_doors(r.entry(ki)[2], added))
    print('    added %d doors (%s ... %s); kernel picks rnd(0..%d)' % (len(added), added[0], added[-1], 18 + len(added)))


def job_game_music(r, job, pal):
    """In-game music (tools/game_music.py): each wallset plays its own track, looping.

    {"tracks": {"Marble": {"la": "dh:Music Scene Two Roland", "ad": "dh:Music Scene Two Adlib/Pc"},
                "Eighth": {"la": "menzo:31", "ad": "menzo:83"}, ...},
     "default": {"la": ..., "ad": ...}}
    Sources: "dh:<OPEN.RES name>", "menzo:<RES5 record>" or "eob3:<EYE.RES name>". la = MT-32/GM version,
    ad = AdLib (also used for PC speaker). Runs after extra_wallset (tables cover every wallset).
    """
    n = r.names()
    ki = n['kernel']
    nw = kernel_rules.n_walls(r.entry(ki)[2])
    menzo = {}

    def load(spec):
        kind, _, key = spec.partition(':')
        if kind == 'dh':
            o = aesop.ResFile(os.path.join(paths.get_dh_dir(), 'OPEN.RES'))
            data = o.entry(o.names()[key])[2]
        elif kind == 'eob3':
            e3 = aesop.ResFile(os.path.join(gpath('eob3'), 'EYE.RES'))
            data = e3.entry(e3.names()[key])[2]
        elif kind == 'menzo':
            if not menzo:
                for rec, typ, flags, payload in dreamforge.records(os.path.join(gpath('menzo'), 'RES5')):
                    if typ == 0x03:
                        menzo[rec] = payload
            data = menzo[int(key)]
        else:
            raise ValueError(spec)
        data = game_music.single_sequence(data)
        assert data[:4] == b'FORM' and len(data) <= game_music.MAX_TRACK, '%s: not an XMIDI track that fits the %d-byte buffer' % (spec, game_music.MAX_TRACK)
        return data
    added, free = {}, [i for i, p in enumerate(r.ptrs) if not p]
    H, chains = rtd.parse(r.entry(0)[2])

    def resource(spec):
        if spec not in added:
            idx = free.pop(0)
            r.replace(idx, load(spec), attrib=r.entry(n['Music Scene One Roland'])[1] if 'Music Scene One Roland' in n else 0x10)
            name = 'Game Music %d' % len(added)
            rtd.add(H, chains, name.encode(), str(idx).encode())
            ADDED[name] = None                    # new data, not a copy of an original resource
            added[spec] = idx
        return added[spec]
    la, ad = [], []
    for w in kernel_rules.WALLSETS[:nw]:
        t = job['tracks'].get(w, job.get('default'))
        la.append(resource(t['la'])); ad.append(resource(t['ad']))
    r.replace(0, rtd.build(H, chains)); r._names = None
    slots = {f: add_runtime_import(r, 'kernel', 'C:' + f) for f in ('load_music', 'play_sequence', 'sequence_playing')}
    r.replace(ki, game_music.patch_kernel(r.entry(ki)[2], slots, la, ad, job.get('hooks', ('enter', 'setup', 'tick'))))
    print('    in-game music: %d tracks for %d wallsets; imports %s' % (len(added), nw, slots))


def job_fix_unlock_shape(r, job, pal):
    """FIX (Bug 1): `items` "unlock shape" calls C:lock_resource instead of C:unlock_resource.

    Both handlers are identical (RCRS 0x0036 = import slot 54 = C:lock_resource), so item
    shapes are never unlocked and stay pinned in the resource cache. Adds C:unlock_resource
    to items.IMPT at the next free external-reference slot (the runtime sizes the thunk from
    the IMPT entries; C entries are 4 bytes) and retargets the unlock handler's RCRS operand.
    Same-size code patch; RTR_unlock never underflows (arun/src/RTRES.C).
    """
    n = r.names()
    code_i, impt_i = n['items'], n['items.IMPT']
    code = bytearray(r.entry(code_i)[2])
    H, chains = rtd.parse(r.entry(impt_i)[2])
    ents = {t.decode(): v.decode() for _, c in chains for t, v in c}
    LOCK, UNLOCK = 1019 + 1, 1053 + 1            # operand of RCRS in "lock shape" / "unlock shape"
    assert code[1019] == code[1053] == 0x20, 'items: RCRS not where expected'
    lock_slot = int(ents['C:lock_resource'])
    assert struct.unpack_from('<H', code, LOCK)[0] == lock_slot == struct.unpack_from('<H', code, UNLOCK)[0], 'items: unexpected operands'
    if 'C:unlock_resource' in ents:
        new_slot = int(ents['C:unlock_resource'])
    else:
        new_slot = sum(4 if t[0] == 'C' else 2 for t in ents if t[0] in 'CBWL')
        assert new_slot == max(int(v.split(',')[0]) + (4 if t[0] == 'C' else 2) for t, v in ents.items() if t[0] in 'CBWL')
        rtd.add(H, chains, b'C:unlock_resource', str(new_slot).encode())
        r.replace(impt_i, rtd.build(H, chains))
    struct.pack_into('<H', code, UNLOCK, new_slot)
    r.replace(code_i, bytes(code))
    print('    items "unlock shape": RCRS slot %d (C:lock_resource) -> %d (C:unlock_resource)' % (lock_slot, new_slot))


LAYOUT_FIXES = []    # resources whose frame ORDER a fix job changes on purpose (verify accepts permutations)
ADDED = {}           # resources an engine extension added: new name -> original it was copied from


def job_extra_wallset(r, job, pal):
    """ENGINE EXTENSION: an 8th wallset (+ stairs) that "randomize graphics" can pick per level.

    {"copy": "Rock"}   (runs before palette_rules; later jobs fill "Eighth Wallset"/"Eighth Stairs")
    Adds two resources in free directory slots (copies of the source wallset/stairs) with their
    names, extends the kernel (kernel_rules.add_wallset: tables appended, loads repointed,
    rnd(0..7)), gives wallset 7 the source's floor/palette pairing bits (otherwise new-game
    creation would loop forever looking for a floor), and appends an 8-entry copy of
    "current pillar"'s per-wallset pillar table (its 7-entry table would be read past the end).
    """
    names = r.names()
    if 'Eighth Wallset' in names:
        return
    src = job.get('copy', 'Rock')
    free = [i for i, p in enumerate(r.ptrs) if not p]
    added = {}
    for idx, kind in zip(free[:2], ('Wallset', 'Stairs')):
        orig = names['%s %s' % (src, kind)]
        _, attrib, payload = r.entry(orig)
        r.replace(idx, payload, attrib=attrib)
        r.data[r.blocks[idx // aesop.SLOTS] + 4 + idx % aesop.SLOTS] = r.data[r.blocks[orig // aesop.SLOTS] + 4 + orig % aesop.SLOTS]
        added['Eighth ' + kind] = idx
        ADDED['Eighth ' + kind] = '%s %s' % (src, kind)
    H, chains = rtd.parse(r.entry(0)[2])
    for tag, idx in added.items():
        rtd.add(H, chains, tag.encode(), str(idx).encode())
    r.replace(0, rtd.build(H, chains)); r._names = None
    ki = r.names()['kernel']
    k = kernel_rules.add_wallset(r.entry(ki)[2], added['Eighth Wallset'], added['Eighth Stairs'])
    rules = kernel_rules.read(k)
    w = kernel_rules.WALLSETS.index(src)
    for key, n in (('floor_ok_for_wall', kernel_rules.N_FLOOR), ('wallpal_ok_for_wall', kernel_rules.N_PAL)):
        for i in range(n):
            if rules[key][i] >> w & 1:
                rules[key][i] |= 1 << 7
    r.replace(ki, kernel_rules.write(k, rules))
    pi = r.names()['current pillar']
    p = bytearray(r.entry(pi)[2])
    op = p.find(bytes.fromhex('2a0e00')) + 1                  # LTDA "L:table14" (pillar art per wallset)
    vals = struct.unpack_from('<7I', p, 14)
    struct.pack_into('<H', p, op, len(p))
    p += struct.pack('<8I', *vals, vals[w])
    r.replace(pi, bytes(p))
    print('    added Eighth Wallset (%d) + Eighth Stairs (%d) as copies of %s; kernel picks rnd(0..7)'
          % (added['Eighth Wallset'], added['Eighth Stairs'], src))


def job_fix_ice_stairs(r, job, pal):
    """FIX: original `Ice Stairs` has its depth-3 front stairs-down art (48x38) in panel 12 (a variant-1
    depth-2 side slot) and an empty 16x59 frame in panel 13, so the stairs vanish when seen 3 squares
    ahead. Every other stairset has 12 = 16x59 (empty), 13 = 48x37 (art). Swap 12 and 13."""
    idx = r.names()['Ice Stairs']
    fr = aesop.decode_shapes(r.entry(idx)[2])
    assert fr[12][:2] == (48, 38) and fr[13][:2] == (16, 59) and not any(fr[13][3]), 'Ice Stairs: unexpected layout'
    fr[12], fr[13] = fr[13], fr[12]
    r.replace(idx, aesop.encode_shapes(fr))
    LAYOUT_FIXES.append('Ice Stairs')


def job_eob_door(r, job, pal):
    """EOB1/EOB2 door -> DH Door-xx: 3 synthesized stages (EOB slides/splits/dissolves doors procedurally).

    {"target": "Door-05", "kind": "iron", "palette": "BLUE.PAL"}  (kinds: tools/eob_doors.EOB1_DOORS)
    Each stage is fitted into the doorway box of the target's own closed door at that depth and
    posterized through the ramp profile the door can be drawn with.
    """
    game, sheet_file, part_boxes, motion = eob_doors.door_spec(job['kind'])
    base = gpath(game)
    px, _ = westwood.unpack(os.path.join(base, sheet_file))
    if game == 'eob1':
        pal = np.array(westwood.eob1_palette(base, job.get('palette', 'BLUE.PAL')), np.uint8).reshape(-1, 3)
    else:
        pal = np.array(westwood.read_pal(os.path.join(base, job.get('palette', eob_doors.EOB2_DOOR_PAL.get(job['kind'], 'DUNG.PAL')))), np.uint8).reshape(-1, 3)
    sheet = np.frombuffer(px[:64000], np.uint8).reshape(200, 320)
    see = eob_doors.SEE_THROUGH.get(job['kind'], ())
    idx = r.names()[job['target']]
    frames = aesop.decode_shapes(r.entry(idx)[2])
    # colours: 'fixed' (default) = DH fixed palette 1-223 like monsters, independent of the level's
    # wall ramp (doors appear on every wallset, incl. two-ramp Stone); 'ramp' = recoloured per level
    fixed = job.get('colors', 'fixed') == 'fixed'
    if fixed:
        _, dhbase, _ = aesop.decode_palette(r.entry(r.names()['Main Base Palette'])[2])
    else:
        profile, _ = ramp_profile(r, job['target'])
    for size, panel in eob_doors.DH_FRONT.items():
        w, h, cpx, cm = frames[36 + panel]                       # closed stage = block 2
        m = np.frombuffer(bytes(cm), np.uint8).reshape(h, w)
        if not m.any():
            continue
        ys, xs = np.nonzero(m); x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        parts = [eob_doors.cut_box(sheet, pal, boxes[size], see) for boxes in part_boxes]
        for block, frac in ((0, 1 / 3), (1, 2 / 3), (2, 1.0)):
            st = np.asarray(eob_doors.stage(parts, motion, x1 - x0, y1 - y0, frac, seed=size))
            rgb = np.zeros((h, w, 3), np.uint8); alpha = np.zeros((h, w), np.uint8)
            rgb[y0:y1, x0:x1] = st[..., :3]; alpha[y0:y1, x0:x1] = st[..., 3] > 127
            if fixed:
                ramp = normalize.quantize_fixed(rgb, dhbase, range(1, 224))
            else:
                lum = normalize.luminance(st[..., :3])[st[..., 3] > 127]
                lohi = tuple(np.percentile(lum, (2, 98))) if lum.size else (0, 255)
                ramp = normalize.to_ramp_target(rgb, profile, 240, dither=False, lohi=lohi)
            k = block * 18 + panel
            frames[k] = (w, h, bytearray((ramp * alpha).tobytes()), bytearray(alpha.tobytes()))
    r.replace(idx, aesop.encode_shapes(frames))


# decoration object's table14: deco index -> resource; indices 0-27 are 4 per wallset (wallnum*4 + 0..3)
WALL_DECOS = {'Marble': ['Wall Deco 00', 'Wall Deco 01', 'Wall Deco 02', 'Wall Deco 03'],
              'Wood': ['Wall Deco 08', 'Wall Deco 09', 'Wall Deco 10', 'Wall Deco 11'],
              'Stone': ['Wall Deco 04', 'Wall Deco 05', 'Wall Deco 06', 'Wall Deco 07'],
              'Foil': ['Wall Deco 24', 'Wall Deco 25', 'Wall Deco 26'],
              'Ice': ['Wall Deco 12', 'Wall Deco 13', 'Wall Deco 14', 'Wall Deco 15'],
              'Mine': ['Wall Deco 16', 'Wall Deco 17', 'Wall Deco 18', 'Wall Deco 19'],
              'Rock': ['Wall Deco 20', 'Wall Deco 21', 'Wall Deco 22', 'Wall Deco 23']}


def job_vmp_deco(r, job, pal):
    """EOB1/2 decorated wall (wt5) as a DH wall decoration overlay for one wallset.

    {"wallset": "Rock Wallset", "game": "eob2", "set": "DUNG", "deco": 5, "base": 0}
    Overlay = pixels where the decorated wall type differs from the plain one, per view position;
    written to every decoration slot that wallset owns (kernel wdeco: wallnum*4 + 0..3, resolved
    through the decoration object's table14) and coloured with that wallset's ramp profile.
    """
    base_dir = gpath(job['game']); vset = job['set']
    blocks, remap = westwood.vcn_blocks(os.path.join(base_dir, vset + '.VCN'))
    ent = westwood.vmp(os.path.join(base_dir, vset + '.VMP'))
    palfile = os.path.join(base_dir, vset + '.PAL')
    palx = np.array(westwood.read_pal(palfile if os.path.exists(palfile) else
                                      os.path.join(base_dir, CFG['games'][job['game']]['default_pal'])), np.uint8).reshape(-1, 3)
    profile, _ = ramp_profile(r, job['wallset'])
    stem = job['wallset'].split()[0]
    for target in WALL_DECOS[stem]:
        idx = r.names()[target]
        frames = aesop.decode_shapes(r.entry(idx)[2])
        got = []
        for pos, ((p0, p1), _) in westwood.DH_PANEL.items():
            for k in (p0, p1):
                if k is None:
                    continue
                w, h = frames[k][:2]
                d_px, d_m = westwood.dh_panel(blocks, ent, job.get('deco', 5), pos, w, h)
                b_px, _ = westwood.dh_panel(blocks, ent, job.get('base', 0), pos, w, h)
                m = np.frombuffer(bytes(d_m), np.uint8) & (np.frombuffer(bytes(d_px), np.uint8) != np.frombuffer(bytes(b_px), np.uint8))
                got.append((k, w, h, palx[np.array([remap[16 + v] for v in d_px], np.uint8)], m.astype(np.uint8)))
        lum = np.concatenate([normalize.luminance(c)[mk > 0] for *_, c, mk in got]) if got else np.array([0])
        lohi = tuple(np.percentile(lum, (2, 98))) if lum.size > 1 else (0, 255)
        for k, w, h, c, mk in got:
            ramp = normalize.to_ramp_target(c.reshape(h, w, 3), profile, 240, False, lohi=lohi)
            frames[k] = (w, h, bytearray((ramp.reshape(-1) * mk).tobytes()), bytearray(mk.tobytes()))
        r.replace(idx, aesop.encode_shapes(frames))


def job_reramp(r, job, pal):
    """Convert the DH art left in a wallset slot to the slot's new ramp shape.

    {"target": "Marble"}   (run after palette_rules, before the jobs that replace parts of the slot)
    A slot whose palettes change between single- and two-ramp (e.g. an EOB3 set in a DH slot)
    still shows DH art that no job replaces: the wallset's other objects (arches, windows,
    pillars...), its stairs, and its decorations. Their wall-ramp indices (240-254) are mapped by
    luminance from the slot's original palettes to the new ones, like imported art is.
    No-op when the shape is unchanged.
    """
    stem = job['target']
    w = kernel_rules.WALLSETS.index(ADDED['%s Wallset' % stem].split()[0]) if '%s Wallset' % stem in ADDED \
        else kernel_rules.WALLSETS.index(stem)                      # the 8th wallset starts as a copy
    src = aesop.ResFile(os.path.join(paths.get_dh_dir(), 'HACK.RES'))
    old_rules = kernel_rules.read(src.entry(src.names()['kernel'])[2])
    old_lums = [palette_lums(src, p) for p in range(21) if old_rules['wallpal_ok_for_wall'][p] >> w & 1]
    new_prof, new_pals = ramp_profile(r, '%s Wallset' % stem)
    new_lums = [palette_lums(r, p) for p in new_pals]
    old_shape = {normalize.ramp_shape(l) for l in old_lums}; new_shape = {normalize.ramp_shape(l) for l in new_lums}
    if old_shape == new_shape:
        print('    %s: ramp shape unchanged %s, nothing to do' % (stem, sorted(new_shape)))
        return
    old_prof = np.mean(old_lums, axis=0)[:15]
    gray = np.repeat(old_prof[None, :, None], 3, axis=2)           # each old ramp index as a grey pixel
    lut = np.arange(256, dtype=np.uint8)
    lut[240:255] = normalize.to_ramp_target(gray, new_prof, 240, dither=False, lohi=(old_prof.min(), old_prof.max()))[0]
    targets = ['%s Wallset' % stem, '%s Stairs' % stem] + WALL_DECOS.get(stem, [])
    for t in targets:
        idx = r.names()[t]
        frames = aesop.decode_shapes(r.entry(idx)[2])
        frames = [(fw, fh, bytearray(lut[np.frombuffer(bytes(px), np.uint8)].tobytes()), m) for fw, fh, px, m in frames]
        r.replace(idx, aesop.encode_shapes(frames))
        ramp_profile(r, t if t.endswith(('Wallset', 'Stairs')) else '%s Wallset' % stem)
        BUILT_SHAPES[t] = sorted(new_shape)
    print('    %s: %s -> %s ramps, re-ramped %s' % (stem, sorted(old_shape), sorted(new_shape), targets))


def job_eob_wall_deco(r, job, pal):
    """One EOB1/2 decoration (.DAT/.DEC + sheet .CPS) as a DH wall decoration, placed per view
    position exactly as EOB draws it (tools/eob_decos.py). Coloured with DH fixed colours 1-223,
    because generic decoration slots (29-48) appear on every wallset.

    {"target": "Wall Deco 31", "game": "eob2", "sheet": "BROWN2.CPS", "dec": "BROWN.DEC",
     "pal": "DUNG.PAL", "index": 35}
    Panels where EOB has no shape for that view stay empty (EOB doesn't show it there either).
    """
    base = gpath(job['game'])
    decs, rects = eob_decos.parse_dec(open(os.path.join(base, job['dec']), 'rb').read())
    sheet = np.frombuffer(bytes(westwood.unpack(os.path.join(base, job['sheet']))[0][:64000]), np.uint8).reshape(200, 320)
    epal = np.array(westwood.eob1_palette(base, job['pal']) if job['game'] == 'eob1'
                    else westwood.read_pal(os.path.join(base, job['pal'])), np.uint8).reshape(-1, 3)
    _, dhbase, _ = aesop.decode_palette(r.entry(r.names()['Main Base Palette'])[2])
    idx = r.names()[job['target']]
    frames = aesop.decode_shapes(r.entry(idx)[2])
    sizes = {k: frames[k][:2] for k in range(len(frames))}
    got = eob_decos.dh_panels(decs, rects, sheet, job['index'], sizes, job['game'])
    assert got, 'decoration %d draws nothing' % job['index']
    lut = np.zeros(256, np.uint8)
    used = sorted(set(np.concatenate([c[m > 0] for c, m in got.values()]).tolist()))
    lut[used] = normalize.quantize_fixed(epal[used][None], dhbase, range(1, 224))[0]
    for k, (w, h) in sizes.items():
        if k in got:
            c, m = got[k]
            frames[k] = (w, h, bytearray((lut[c] * (m > 0)).astype(np.uint8).tobytes()), bytearray((m > 0).astype(np.uint8).tobytes()))
        else:
            frames[k] = (w, h, bytearray(w * h), bytearray(w * h))
    r.replace(idx, aesop.encode_shapes(frames))


def job_vmp_walls(r, job, pal):
    """EOB1/2 hand-drawn walls copied 1:1 from VMP view positions (ScummVM kyra tables).

    {"target": "Rock Wallset", "game": "eob1", "set": "BRICK", "plain": [0, 1], "frame": 2,
     "stairs": "Rock Stairs", "stairs_down": 4, "stairs_up": 3}
    Plain wall types fill DH wall object 0 (variant 0 / 1 side panels; fronts from variant 0),
    the frame type fills object 1 (door frame), stairs types fill the stairset [down][up].
    Colours go through the target's real ramp profile with ONE brightness stretch for the
    whole set, so EOB's own depth shading between near and far panels is kept.
    """
    base = gpath(job['game'])

    def load_set(vset):
        blocks, remap = westwood.vcn_blocks(os.path.join(base, vset + '.VCN'))
        ent = westwood.vmp(os.path.join(base, vset + '.VMP'))
        palfile = os.path.join(base, vset + '.PAL')
        pal = np.array(westwood.read_pal(palfile if os.path.exists(palfile) else
                                         os.path.join(base, CFG['games'][job['game']]['default_pal'])), np.uint8).reshape(-1, 3)
        return blocks, ent, lambda px: pal[np.array([remap[16 + v] for v in px], np.uint8)]
    sets = {name: load_set(name) for name in {job['set'], job.get('frame_set', job['set']), job.get('stairs_set', job['set'])}}

    def fill(target, plan):            # plan: [(dh_panel_index, set, walltype, pos)]
        idx = r.names()[target]
        frames = aesop.decode_shapes(r.entry(idx)[2])
        got = []
        for k, vset, wt, pos in plan:
            blocks, ent, rgb_of = sets[vset]
            w, h = frames[k][:2]
            try:
                px, m = westwood.dh_panel(blocks, ent, wt, pos, w, h)
            except AssertionError:      # DH data quirk, e.g. Ice Stairs has panels 12/13 swapped
                print('    note: %s panel %d is %dx%d, not a %s panel; kept DH art' % (target, k, w, h, pos))
                continue
            got.append((k, w, h, rgb_of(px), np.frombuffer(bytes(m), np.uint8)))
        lum = np.concatenate([normalize.luminance(c)[mk > 0] for _, _, _, c, mk in got])
        lohi = np.percentile(lum, (2, 98))
        profile, _ = ramp_profile(r, target)
        for k, w, h, c, mk in got:
            if job.get('keep_empty', True) and not any(frames[k][3]):
                continue
            ramp = normalize.to_ramp_target(c.reshape(h, w, 3), profile, 240, job.get('dither', False), lohi=tuple(lohi))
            frames[k] = (w, h, bytearray((ramp.reshape(-1) * mk).tobytes()), bytearray(mk.tobytes()))
        r.replace(idx, aesop.encode_shapes(frames))

    wall_plan, frame_plan = [], []
    vs, fs, ss = job['set'], job.get('frame_set', job['set']), job.get('stairs_set', job['set'])
    v0, v1 = (job.get('plain', [0, 1]) + [job.get('plain', [0])[0]])[:2]
    for pos, ((p0, p1), _) in westwood.DH_PANEL.items():
        wall_plan.append((p0, vs, v0, pos))
        if p1 is not None:
            wall_plan.append((p1, vs, v1, pos))
        if job.get('frame') is not None:
            frame_plan += [(18 + p0, fs, job['frame'], pos)] + ([(18 + p1, fs, job['frame'], pos)] if p1 is not None else [])
    fill(job['target'], wall_plan + frame_plan)
    if job.get('stairs'):
        st = []
        for base_k, wt in ((0, job.get('stairs_down')), (18, job.get('stairs_up'))):
            if wt is None:
                continue
            for pos, ((p0, p1), _) in westwood.DH_PANEL.items():
                st.append((base_k + p0, ss, wt, pos))
                if p1 is not None:
                    st.append((base_k + p1, ss, wt, pos))
        fill(job['stairs'], st)


def job_wallset(r, job, pal):
    idx = r.names()[job['target']]
    frames = aesop.decode_shapes(r.entry(idx)[2])
    profile, _ = ramp_profile(r, job['target'])
    tex = normalize.to_ramp_target(load_rgb(job['texture']), profile, 240, dither=job.get('dither', True))
    for k in frange(job.get('frames', '0-35'), len(frames)):   # objects 0 (walls) + 1 (door frame)
        w, h, px, m = frames[k]
        if not any(m):
            continue
        new, mask = normalize.warp_to_mask(tex, m, w, h)
        frames[k] = (w, h, bytearray(new.tobytes()), m)
    r.replace(idx, aesop.encode_shapes(frames))


def job_floor(r, job, pal):
    idx = r.names()[job['target']]
    (w, h, px, m), = aesop.decode_shapes(r.entry(idx)[2])
    img = Image.fromarray(load_rgb(job['image'])).resize((w, h), Image.LANCZOS)
    profile, _ = ramp_profile(r, job['target'])
    ramp = normalize.to_ramp_target(np.asarray(img), profile, 224, dither=job.get('dither', True))
    r.replace(idx, aesop.encode_shapes([(w, h, bytearray(ramp.tobytes()), m)]))


def job_sprites(r, job, pal):
    """Monsters (6 x 80x88), portraits (31x32), icons ...: RGBA PNGs -> fixed-palette indices."""
    pal_file = os.path.join(HERE, 'pool', 'dh_palette.json')
    if not os.path.exists(pal_file):
        pal_file = os.path.join(WORK, 'aesop', 'dh_palette.json')
    meta = json.load(open(pal_file))
    allowed = set(meta['monster_indices']) - {0}
    idx = r.names()[job['target']]
    old = aesop.decode_shapes(r.entry(idx)[2])
    assert len(job['images']) == len(old), '%s needs %d frames' % (job['target'], len(old))
    frames = []
    for (w, h, _, _), path in zip(old, job['images']):
        im = Image.open(os.path.join(HERE, path)).convert('RGBA')
        if im.size != (w, h):           # pre-composed frames (exact EOB cuts) are used as-is
            im = normalize.fit_sprite(im, w, h)
        a = np.asarray(im)
        px = normalize.quantize_fixed(a[..., :3], meta['base_palette'], allowed)
        mask = (a[..., 3] > 127).astype(np.uint8)
        frames.append((w, h, bytearray((px * mask).tobytes()), bytearray(mask.tobytes())))
    r.replace(idx, aesop.encode_shapes(frames))



def job_xmidi(r, job, pal):
    """Swap XMIDI music tracks from EOB3 or Menzoberranzan into DH (e.g. OPEN.RES intro/ending music)."""
    src = str(job['source'])
    if src.startswith('menzo:'):
        idx = int(src.split(':')[1])
        res5_path = paths.get_game_file('menzo', 'RES5')
        with open(res5_path, 'rb') as f:
            count = struct.unpack('<I', f.read(4))[0]
            offsets = struct.unpack(f'<{count + 1}I', f.read((count + 1) * 4))
            f.seek(offsets[idx])
            data = f.read(offsets[idx + 1] - offsets[idx])
            track_bytes = data[9:]  # Strip 9-byte EH header
    else:
        e3 = eob3_res()
        track_bytes = e3.entry(e3.names()[job['source']])[2]
    r.replace(r.names()[job['target']], track_bytes)

def job_raw(r, job, pal):
    """Same-format payload swap, e.g. Menzoberranzan XMIDI -> DH music, u8 PCM -> DH sound."""
    r.replace(r.names()[job['target']], open(os.path.join(HERE, job['file']), 'rb').read())


JOBS = {'wallset': job_wallset, 'floor': job_floor, 'sprites': job_sprites, 'raw': job_raw,
        'panels': job_panels, 'xmidi': job_xmidi, 'palette_rules': job_palette_rules, 'force_graphics': job_force_graphics,
        'vmp_walls': job_vmp_walls, 'fix_unlock_shape': job_fix_unlock_shape, 'fix_ice_stairs': job_fix_ice_stairs,
        'eob_door': job_eob_door, 'vmp_deco': job_vmp_deco,
        'eob_wall_deco': job_eob_wall_deco, 'reramp': job_reramp, 'extra_wallset': job_extra_wallset,
        'game_music': job_game_music, 'extra_doors': job_extra_doors}


def cmd_build(recipe_path, name):
    recipe = json.load(open(recipe_path))
    src = paths.get_dh_dir()
    dst = os.path.join(HERE, 'build', name)
    kept = None
    if os.path.exists(dst):
        sg = os.path.join(dst, 'savegame')
        if os.path.isdir(sg) and os.listdir(sg):      # a rebuild must not delete the player's saves
            kept = os.path.join(HERE, 'build', '.%s.savegame.keep' % name)
            shutil.rmtree(kept, ignore_errors=True); shutil.move(sg, kept)
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    if kept:
        shutil.rmtree(os.path.join(dst, 'savegame'), ignore_errors=True); shutil.move(kept, os.path.join(dst, 'savegame'))
        print('  kept existing savegame/')
    for note in paths.seed_savegame(dst):
        print('  savegame:', note)
    for resname in ('HACK.RES', 'OPEN.RES'):
        jobs = [j for j in recipe['jobs'] if j.get('res', 'HACK.RES') == resname]
        jobs.sort(key=lambda j: (j['type'] not in ('extra_wallset', 'extra_doors'), j['type'] != 'palette_rules', j['type'] == 'force_graphics'))  # engine extensions, rules first; force last
        if resname == 'HACK.RES':   # every wallset whose palette rules change gets its leftover DH art re-ramped
            have = {j['target'] for j in jobs if j['type'] == 'reramp'}
            ruled = [w.split()[0] for j in jobs if j['type'] == 'palette_rules' for w in j.get('wall_palettes', {})]
            n_rules = sum(j['type'] in ('palette_rules', 'extra_wallset', 'extra_doors') for j in jobs)
            jobs[n_rules:n_rules] = [{'type': 'reramp', 'target': w} for w in dict.fromkeys(ruled) if w not in have]
        if not jobs:
            continue
        r = aesop.ResFile(os.path.join(src, resname))
        for j in jobs:
            print('  %-13s %s' % (j['type'], j.get('target', '')))
            JOBS[j['type']](r, j, None)
        if recipe.get('compact', True):
            r.compact()
        r.save(os.path.join(dst, resname))
        tbl = os.path.join(src, resname.replace('.RES', '.TBL'))
        open(os.path.join(dst, os.path.basename(tbl)), 'wb').write(r.tbl_bytes(os.path.getsize(tbl)))
    json.dump({'recipe': recipe, 'recipe_sha': sha(recipe_path, 12), 'ramp_shapes': BUILT_SHAPES, 'layout_fixes': LAYOUT_FIXES, 'added': ADDED},
              open(os.path.join(dst, 'MASHUP_BUILD.json'), 'w'), indent=1)
    print('built', dst)
    cmd_verify(name)


def check_ramps(name):
    """Ramp-shape regression check (palette ladders, not pixels).

    Fails if a wallset's allowed palettes mix single/two-ramp shapes, or if the
    rules changed a wallset's ramp shape while its original art (designed for the
    old shape) was left in place.
    """
    src = aesop.ResFile(os.path.join(paths.get_dh_dir(), 'HACK.RES'))
    dst = aesop.ResFile(os.path.join(HERE, 'build', name, 'HACK.RES'))
    old = kernel_rules.read(src.entry(src.names()['kernel'])[2])
    new = kernel_rules.read(dst.entry(dst.names()['kernel'])[2])
    shape = {p: normalize.ramp_shape(palette_lums(dst, p)) for p in range(21)}
    mpath = os.path.join(HERE, 'build', name, 'MASHUP_BUILD.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    ok = True
    copied = manifest.get('added', {})
    for w, stem in enumerate(kernel_rules.WALLSETS[:new['n_walls']]):
        w_old = kernel_rules.WALLSETS.index(copied['%s Wallset' % stem].split()[0]) if '%s Wallset' % stem in copied else w
        before = {shape[p] for p in range(21) if old['wallpal_ok_for_wall'][p] >> w_old & 1}
        after = {shape[p] for p in range(21) if new['wallpal_ok_for_wall'][p] >> w & 1}
        idx = dst.names()['%s Wallset' % stem]
        src_idx = src.names()[copied.get('%s Wallset' % stem, '%s Wallset' % stem)]
        reskinned = dst.entry(idx)[2] != src.entry(src_idx)[2]
        if len(after) > 1:
            print('  ramp check: %s Wallset pairs with mixed ramp shapes %s' % (stem, after)); ok = False
        built = manifest.get('ramp_shapes', {}).get('%s Wallset' % stem)
        if reskinned and built is None:
            print('  ramp check: %s Wallset reskinned without a recorded ramp shape (pre-check build; rebuild it)' % stem); ok = False
        elif reskinned and set(built) != after:
            print('  ramp check: %s Wallset art built for %s ramps but pairs with %s' % (stem, built, after)); ok = False
        if after != before and not reskinned:
            print('  ramp check: %s Wallset ramp shape changed %s -> %s but its original art was kept'
                  % (stem, before, after)); ok = False
        stairs_built = manifest.get('ramp_shapes', {}).get('%s Stairs' % stem)
        if after != before and (stairs_built is None or set(stairs_built) != after):
            print('  ramp check: %s ramp shape changed %s -> %s but %s Stairs kept its original art (add a reramp job)'
                  % (stem, before, after, stem)); ok = False
    print('  ramp check:', 'OK' if ok else 'FAILED')
    return ok


def cmd_verify(name):
    dst = os.path.join(HERE, 'build', name)
    src = paths.get_dh_dir()
    ok = True
    for resname in ('HACK.RES', 'OPEN.RES'):
        r = aesop.ResFile(os.path.join(dst, resname))
        o = aesop.ResFile(os.path.join(src, resname))
        bad, n = r.check_tbl(os.path.join(dst, resname.replace('.RES', '.TBL')))
        names_r = r.index_names()
        mpath = os.path.join(dst, 'MASHUP_BUILD.json')
        manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
        fixes = set(manifest.get('layout_fixes', []))
        recorded = manifest.get('added', {})
        new_idx = [i for i in r.indices() if i >= len(o.ptrs) or not o.ptrs[i]]
        shape_err = [(i, 'added resource not recorded in the manifest') for i in new_idx if names_r.get(i) not in recorded]
        added = {i: o.names()[recorded[names_r[i]]] for i in new_idx if recorded.get(names_r.get(i))}   # copies
        fresh = {i for i in new_idx if names_r.get(i) in recorded and not recorded[names_r[i]]}        # new data
        changed = [i for i in r.indices() if i in new_idx or r.entry(i)[2] != o.entry(i)[2]]
        for i in changed:
            p = r.entry(i)[2]
            if i in fresh:
                continue
            if aesop.kind(p) == 'old_shapes':
                try:
                    new = aesop.decode_shapes(p); old = aesop.decode_shapes(o.entry(added.get(i, i))[2])
                    dn, do = [f[:2] for f in new], [f[:2] for f in old]
                    if dn != do and not (names_r.get(i) in fixes and sorted(dn) == sorted(do)):
                        shape_err.append((i, 'frame count/size differs'))
                except Exception as e:
                    shape_err.append((i, repr(e)))
        grow = sum(len(r.entry(i)[2]) - (0 if i in fresh else len(o.entry(added.get(i, i))[2])) for i in changed)
        print('%s: %d changed, tbl mismatches %d, shape errors %s, payload growth %+d bytes, size %d'
              % (resname, len(changed), len(bad), shape_err or 'none', grow, len(r.data)))
        ok &= not bad and not shape_err
    ok &= check_ramps(name)
    print('VERIFY', 'OK' if ok else 'FAILED')
    return ok


# --------------------------------------------------------------------------- roll
def cmd_roll(pool_path, seed, name):
    """Comprehensive build-time randomizer: draws a rule-consistent cross-engine skin

    Covers wallsets, ramp rules, animated doors, stairs, decos, levers, 57 monster slots,
    and 8 kHz sound effects while strictly respecting the 444 KB memory cliff.
    """
    import randomizer
    recipe = randomizer.roll_recipe(pool_path, seed, name)
    print(f'Rolled recipe {recipe} for build "{name}" (seed {seed})')
    cmd_build(recipe, name)


if __name__ == '__main__':
    cmd, *args = sys.argv[1:] or ['help']
    fn = {'inventory': cmd_inventory, 'snapshot': cmd_snapshot, 'extract': cmd_extract,
          'build': cmd_build, 'verify': cmd_verify, 'roll': cmd_roll}.get(cmd)
    if not fn:
        sys.exit(__doc__)
    fn(*args)
