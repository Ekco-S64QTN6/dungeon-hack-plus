"""Menzoberranzan (DreamForge / Ravenloft engine) containers, verified against GOG files.

  RESn   : u32 count, u32 offset[count]; records are not stored in table order
  record : "EH", u8 type, u8 flags
           flags 0x05 -> u8 ?, u8 ?, u32 unpacked_size, LZSS stream      (10-byte header)
           flags 0x00 -> u8 ?, u32 size, raw data                         (9-byte header)
  LZSS   : classic Okumura (4 KB ring, flag byte LSB-first, 1 = literal, 12-bit pos / 4-bit len+3)
           -> consumed byte counts match record lengths exactly.
  COLORS : bytes 4..772 = 256-colour 6-bit palette (renders RES4 textures correctly);
           the rest is presumably light/shade tables.
Observed record types: RES4 05 = 64x192 column-major wall/floor textures (2-byte header),
RES3 06 = sprite frames (format still to be reversed), RES5 03 = XMIDI (FORM/XDIR),
RES6 04 = unsigned 8-bit PCM (one RIFF WAV). CD-only RES9/RES10 and CINE/CGEN *.DFA live in GAME.ISO.
"""
import struct


def lzss(src, out_size):
    ring = bytearray(4096); r = 0xFEE
    dst = bytearray(); i = 0; flags = 0
    while len(dst) < out_size and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00; i += 1
        if flags & 1:
            b = src[i]; i += 1
            dst.append(b); ring[r] = b; r = (r + 1) & 0xFFF
        else:
            b1, b2 = src[i], src[i + 1]; i += 2
            pos = b1 | ((b2 & 0xF0) << 4)
            for k in range((b2 & 0xF) + 3):
                b = ring[(pos + k) & 0xFFF]
                dst.append(b); ring[r] = b; r = (r + 1) & 0xFFF
    return bytes(dst), i


def records(path):
    """Yield (index, type, flags, payload) with LZSS records already unpacked."""
    d = open(path, 'rb').read()
    n = struct.unpack_from('<I', d)[0]
    offs = struct.unpack_from('<%dI' % n, d, 4)
    ends = {}
    srt = sorted(set(o for o in offs if 0 < o < len(d))) + [len(d)]
    for a, b in zip(srt, srt[1:]):
        ends[a] = b
    for k, o in enumerate(offs):
        if not 0 < o < len(d) or d[o:o + 2] != b'EH':
            yield k, None, None, b''
            continue
        typ, flags = d[o + 2], d[o + 3]
        if flags == 0x05:
            usize = struct.unpack_from('<I', d, o + 6)[0]
            payload, _ = lzss(d[o + 10:ends[o]], usize)
        elif flags == 0x00:
            size = struct.unpack_from('<I', d, o + 5)[0]
            payload = d[o + 9:o + 9 + size]
        else:
            payload = d[o:ends[o]]
        yield k, typ, flags, payload


def palette(colors_path):
    raw = open(colors_path, 'rb').read()[4:772]
    return [min(255, c * 255 // 63) for c in raw]


def texture(payload, w=64):
    """RES4 type-5 texture -> (w, h, row-major pixels). Stored column-major after a 2-byte header."""
    px = payload[2:]
    h = len(px) // w
    out = bytearray(w * h)
    for x in range(w):
        out[x::w] = px[x * h:(x + 1) * h]
    return w, h, out
