"""AESOP/16 resource files (HACK.RES, OPEN.RES, EYE.RES) and the Dungeon Hack .TBL index.

Layouts verified against the GOG files in this folder:
  header   : char sig[16] ("AESOP/16 V1.00\0?"), u32 file_size, u32 lost_space,
             u32 first_dir_block (0x24), u32 create_time, u32 modify_time
  dir block: u32 next_block, u8 attrib[128], u32 entry_ptr[128]
  entry    : u32 timestamp, u32 attrib, u32 size, u8 data[size]
  .TBL     : u32 entry_ptr[n] for every directory slot, zero padded (DH only)
Entry 0 is the name->number dictionary.

Bitmaps in Dungeon Hack (and original EOB3) use the "old" AESOP/16 shape table
(see daesop convert.cpp); GOG EOB3 ships daesop-converted "1.10" VFX tables.
Palette resources: u16 ncolors, u16 offset[12], RGB[ncolors] (6-bit), 11 shade tables[ncolors].
"""
import re
import struct

HDR = struct.Struct('<16s5I')
ENTRY = struct.Struct('<3I')
SLOTS = 128


class ResFile:
    def __init__(self, path):
        self.path = path
        self.data = bytearray(open(path, 'rb').read())
        (self.sig, self.file_size, self.lost_space, self.fob,
         self.ctime, self.mtime) = HDR.unpack_from(self.data, 0)
        self.blocks = []            # offsets of directory blocks
        self.ptrs = []              # entry pointer per slot (0 = empty)
        blk = self.fob
        while blk:
            self.blocks.append(blk)
            nxt = struct.unpack_from('<I', self.data, blk)[0]
            self.ptrs += struct.unpack_from('<%dI' % SLOTS, self.data, blk + 4 + SLOTS)
            blk = nxt
        self._names = None

    # --- reading -----------------------------------------------------------
    def entry(self, idx):
        p = self.ptrs[idx]
        ts, attrib, size = ENTRY.unpack_from(self.data, p)
        return ts, attrib, bytes(self.data[p + 12:p + 12 + size])

    def indices(self):
        return [i for i, p in enumerate(self.ptrs) if p]

    def names(self):
        """name -> index, parsed from the entry-0 dictionary (string pairs key, decimal value)."""
        if self._names is None:
            toks = [t.decode('latin-1') for t in re.findall(rb'([\x20-\x7e]+)\x00', self.entry(0)[2])]
            valid = set(self.indices())
            self._names = {a: int(b) for a, b in zip(toks, toks[1:])
                           if b.isdigit() and not a.isdigit() and int(b) in valid}
        return self._names

    def index_names(self):
        out = {}
        for n, i in self.names().items():
            out.setdefault(i, n)
        return out

    # --- writing -----------------------------------------------------------
    def replace(self, idx, payload, attrib=None):
        """Append a new copy of entry idx and repoint its directory slot (old bytes become lost space)."""
        old = self.ptrs[idx]
        if old:
            ts, old_attrib, old_size = ENTRY.unpack_from(self.data, old)
            self.lost_space += old_size + ENTRY.size
        else:
            ts, old_attrib = 0, 0
        new = len(self.data)
        self.data += ENTRY.pack(ts, old_attrib if attrib is None else attrib, len(payload)) + payload
        self.ptrs[idx] = new
        blk = self.blocks[idx // SLOTS]
        struct.pack_into('<I', self.data, blk + 4 + SLOTS + 4 * (idx % SLOTS), new)

    def save(self, path):
        self.file_size = len(self.data)
        HDR.pack_into(self.data, 0, self.sig, self.file_size, self.lost_space,
                      self.fob, self.ctime, self.mtime)
        open(path, 'wb').write(self.data)

    def compact(self):
        """Rewrite with no lost space: header, directory blocks, then entries in slot order."""
        entries = [ENTRY.unpack_from(self.data, p) + (p,) if p else None for p in self.ptrs]
        out = bytearray(HDR.size)
        nblk = len(self.blocks)
        blk_size = 4 + SLOTS + 4 * SLOTS
        self.blocks = [HDR.size + k * blk_size for k in range(nblk)]
        out += bytes(blk_size * nblk)
        ptrs = []
        for e in entries:
            if e is None:
                ptrs.append(0); continue
            ts, attrib, size, p = e
            ptrs.append(len(out))
            out += self.data[p:p + 12 + size]
        for k, blk in enumerate(self.blocks):
            nxt = self.blocks[k + 1] if k + 1 < nblk else 0
            struct.pack_into('<I', out, blk, nxt)
            struct.pack_into('<%dI' % SLOTS, out, blk + 4 + SLOTS, *ptrs[k * SLOTS:(k + 1) * SLOTS])
        # carry the per-slot attribute bytes over from the original blocks
        for k, old_blk in enumerate(self._orig_blocks()):
            out[self.blocks[k] + 4:self.blocks[k] + 4 + SLOTS] = self.data[old_blk + 4:old_blk + 4 + SLOTS]
        self.data, self.ptrs, self.fob, self.lost_space = out, ptrs, self.blocks[0], 0

    def _orig_blocks(self):
        blks, blk = [], HDR.unpack_from(self.data, 0)[3]
        while blk:
            blks.append(blk)
            blk = struct.unpack_from('<I', self.data, blk)[0]
        return blks

    def tbl_bytes(self, min_len=0):
        raw = struct.pack('<%dI' % len(self.ptrs), *self.ptrs)
        return raw + b'\0' * max(0, min_len - len(raw))

    def check_tbl(self, tbl_path):
        tbl = open(tbl_path, 'rb').read()
        t = struct.unpack('<%dI' % (len(tbl) // 4), tbl)
        bad = [i for i, p in enumerate(self.ptrs) if i >= len(t) or t[i] != p]
        return bad, len(t)


# --- classification ---------------------------------------------------------
def kind(payload, name=''):
    if payload[:2] == b'S:':
        return 'string'
    if payload[:4] == b'FORM':
        return 'xmidi'
    if payload[:4] == b'1.10':
        return 'vfx110_shapes'
    if len(payload) >= 6 and struct.unpack_from('<I', payload)[0] == len(payload):
        return 'old_shapes'
    if 'palette' in name.lower() and len(payload) >= 26:
        n = struct.unpack_from('<H', payload)[0]
        if len(payload) == 26 + n * 3 + 11 * n:
            return 'palette'
    if name.endswith(('.IMPT', '.EXPT')):
        return 'code_table'
    if len(payload) > 256 and sum(0x70 <= b <= 0x90 for b in payload[:256]) > 200:
        return 'pcm_u8'
    return 'other'


# --- palettes ---------------------------------------------------------------
def decode_palette(payload):
    n = struct.unpack_from('<H', payload)[0]
    offs = struct.unpack_from('<12H', payload, 2)
    rgb6 = payload[offs[0]:offs[0] + 3 * n]
    shades = [payload[o:o + n] for o in offs[1:]]
    return n, [min(255, c * 255 // 63) for c in rgb6], shades


def encode_palette(rgb8, shades):
    n = len(rgb8) // 3
    offs = [26 + 0]
    body = bytes(min(63, (c * 63 + 127) // 255) for c in rgb8)
    for s in shades:
        offs.append(26 + len(body))
        body += bytes(s)
    return struct.pack('<13H', n, *offs) + body


# --- VFX "1.10" shape tables (GOG EOB3, daesop-converted) ------------------
def decode_vfx110(payload):
    """-> list of (w, h, pixels, mask, header) ; port of Thirdeye bitmap.cpp.

    "1.10", u32 count, {u32 offset, u32 colour}[count]; each shape has a 24-byte
    header (u16 h-1, u16 w-1, then origin / bounding-box words kept raw) followed
    by per-row tokens: 0 = end of row, 1 = skip n, even = run (n>>1) of next byte,
    odd = (n>>1) literal bytes.
    """
    assert payload[:4] == b'1.10'
    n = struct.unpack_from('<I', payload, 4)[0]
    out = []
    for i in range(n):
        o = struct.unpack_from('<I', payload, 8 + 8 * i)[0]
        hdr = struct.unpack_from('<12H', payload, o)
        h, w = hdr[0] + 1, hdr[1] + 1
        px, mask = bytearray(w * h), bytearray(w * h)
        pos = o + 24
        for y in range(h):
            x = 0
            while pos < len(payload):
                m = payload[pos]; pos += 1
                if m == 0:
                    break
                if m == 1:
                    x += payload[pos]; pos += 1
                    continue
                amt = m >> 1
                if m & 1:
                    vals = payload[pos:pos + amt]; pos += amt
                else:
                    vals = bytes([payload[pos]]) * amt; pos += 1
                for k, v in enumerate(vals):
                    if x + k < w:
                        px[y * w + x + k] = v; mask[y * w + x + k] = 1
                x += amt
        out.append((w, h, px, mask, hdr))
    return out


# --- old (AESOP/16, Dungeon Hack) shape tables -----------------------------
def decode_shapes(payload):
    """-> list of (w, h, pixels bytearray, mask bytearray)."""
    n = struct.unpack_from('<H', payload, 4)[0]
    offs = struct.unpack_from('<%dI' % n, payload, 6)
    out = []
    for o in offs:
        w, h = struct.unpack_from('<HH', payload, o)
        pos = o + 4
        px, mask = bytearray(w * h), bytearray(w * h)
        while payload[pos] != 0xFF:
            y = payload[pos]; pos += 1
            while True:
                x = payload[pos] | payload[pos + 1] << 8
                last = x & 0x8000; x &= 0x7FFF
                width = payload[pos + 2]; pos += 4          # u8 width, u8 packed byte count
                while width > 0:
                    b = payload[pos]; pos += 1
                    amt = (b >> 1) + 1
                    if b & 1:
                        px[y * w + x:y * w + x + amt] = bytes([payload[pos]]) * amt; pos += 1
                    else:
                        px[y * w + x:y * w + x + amt] = payload[pos:pos + amt]; pos += amt
                    mask[y * w + x:y * w + x + amt] = b'\1' * amt
                    x += amt; width -= amt
                if last:
                    break
        out.append((w, h, px, mask))
    return out


def _pack_span(vals):
    out, i = bytearray(), 0
    while i < len(vals):
        run = 1
        while i + run < len(vals) and run < 128 and vals[i + run] == vals[i]:
            run += 1
        if run >= 3:
            out += bytes([((run - 1) << 1) | 1, vals[i]]); i += run
            continue
        j = i
        while j < len(vals) and j - i < 128:
            if j + 2 < len(vals) and vals[j] == vals[j + 1] == vals[j + 2]:
                break
            j += 1
        out += bytes([((j - i - 1) << 1)]) + bytes(vals[i:j]); i = j
    return out


def encode_shapes(frames):
    """frames: list of (w, h, pixels, mask) -> old shape table bytes."""
    bodies = []
    for w, h, px, mask in frames:
        assert h <= 255, 'old shape rows are addressed with a u8'
        b = bytearray(struct.pack('<HH', w, h))
        for y in range(h):
            spans, x = [], 0
            while x < w:
                if mask[y * w + x]:
                    s = x
                    while x < w and mask[y * w + x] and x - s < 255:
                        x += 1
                    spans.append((s, x))
                else:
                    x += 1
            if not spans:
                continue
            b.append(y)
            for k, (s, e) in enumerate(spans):
                packed = _pack_span(px[y * w + s:y * w + e])
                assert len(packed) <= 255, 'span too large for u8 byte count'
                b += struct.pack('<HBB', s | (0x8000 if k == len(spans) - 1 else 0), e - s, len(packed))
                b += packed
        b.append(0xFF)
        bodies.append(bytes(b))
    head = 6 + 4 * len(bodies)
    offs, pos = [], head
    for body in bodies:
        offs.append(pos); pos += len(body)
    return struct.pack('<IH', pos, len(bodies)) + struct.pack('<%dI' % len(offs), *offs) + b''.join(bodies)
