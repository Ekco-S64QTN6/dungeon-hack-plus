"""Westwood EOB1/EOB2 formats (verified against the GOG files in this folder).

  .CPS/.VCN : u16 size-2, u16 method (4 = LCW/Format80), u32 unpacked size, u16 palette size, data
  .PAL      : 768 bytes, 6-bit VGA RGB
  .VCN      : (after LCW) u16 nblocks, u8 remap[32] (EOB1 VGA), nblocks * 32-byte 8x8 4bpp blocks
  .VMP      : u16 count, u16 entry[count]; 330 backdrop entries + 431 per wall type
              entry bit 0x4000 = horizontal flip, low 14 bits = block number
  .PAK      : u32 offset, char name[]\0 ... (EOB1 ENG ships EOBDATA*.PAK; EOB1 DE ships loose files)
Reference decoders: ScummVM engines/kyra (EOB support), OpenRA (C&C CPS/LCW).
"""
import struct


def lcw(src, out_size):
    dst = bytearray(); i = 0
    while len(dst) < out_size and i < len(src):
        c = src[i]; i += 1
        if not c & 0x80:                                   # relative copy
            cnt = ((c >> 4) & 7) + 3; pos = ((c & 0xF) << 8) | src[i]; i += 1
            for _ in range(cnt):
                dst.append(dst[-pos])
        elif not c & 0x40:                                 # literal run
            cnt = c & 0x3F
            if cnt == 0:
                break
            dst += src[i:i + cnt]; i += cnt
        else:
            cnt = c & 0x3F
            if cnt == 0x3E:                                # fill
                n, v = struct.unpack_from('<HB', src, i); i += 3
                dst += bytes([v]) * n
            else:                                          # absolute copy
                if cnt == 0x3F:
                    n, pos = struct.unpack_from('<HH', src, i); i += 4
                else:
                    n = cnt + 3; pos = struct.unpack_from('<H', src, i)[0]; i += 2
                for k in range(n):
                    dst.append(dst[pos + k])
    return bytes(dst)


def rle3(src, out_size):
    """Westwood compression method 3 (ScummVM Screen::decodeFrame3): signed control byte;
    0 = u16 BE count + fill byte, < 0 = fill -n, > 0 = copy n literals."""
    dst = bytearray(); i = 0
    while len(dst) < out_size and i < len(src):
        c = src[i] - 256 if src[i] > 127 else src[i]; i += 1
        if c == 0:
            n = (src[i] << 8) | src[i + 1]; dst += bytes([src[i + 2]]) * n; i += 3
        elif c < 0:
            dst += bytes([src[i]]) * -c; i += 1
        else:
            dst += src[i:i + c]; i += c
    return bytes(dst[:out_size])


def unpack(path_or_bytes):
    """CPS/VCN container -> (pixels/bytes, embedded palette or None)."""
    d = open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes
    _, method, usize, palsz = struct.unpack_from('<HHIH', d)
    pal = d[10:10 + palsz] or None
    body = d[10 + palsz:]
    if method == 4:
        return lcw(body, usize), pal
    if method == 0:
        return body[:usize], pal
    if method == 3:
        return rle3(body, usize), pal
    raise ValueError('unsupported Westwood compression %d' % method)


def read_pal(path):
    return [min(255, c * 255 // 63) for c in open(path, 'rb').read()[:768]]


def vcn_blocks(path):
    raw, _ = unpack(path)
    n = struct.unpack_from('<H', raw)[0]
    remap = raw[2:34]
    blocks = []
    for b in range(n):
        blk = raw[34 + 32 * b:66 + 32 * b]
        px = bytearray()
        for byte in blk:
            px += bytes([byte >> 4, byte & 0xF])
        blocks.append(px)          # 64 nibble indices, row-major 8x8
    return blocks, remap


def vmp(path):
    d = open(path, 'rb').read()
    n = struct.unpack_from('<H', d)[0]
    return list(struct.unpack_from('<%dH' % n, d, 2))


def render_blocks(entries, blocks, cols):
    """VMP entries -> (w, h, nibble pixels) laid out `cols` blocks wide."""
    rows = (len(entries) + cols - 1) // cols
    w, h = cols * 8, rows * 8
    out = bytearray(w * h)
    for k, e in enumerate(entries):
        blk = blocks[e & 0x3FFF] if (e & 0x3FFF) < len(blocks) else bytes(64)
        bx, by = (k % cols) * 8, (k // cols) * 8
        for y in range(8):
            row = blk[y * 8:y * 8 + 8]
            if e & 0x4000:
                row = row[::-1]
            out[(by + y) * w + bx:(by + y) * w + bx + 8] = row
    return w, h, out


def unpak(path):
    d = open(path, 'rb').read()
    entries, pos = [], 0
    while True:
        off = struct.unpack_from('<I', d, pos)[0]
        if off == 0 or off >= len(d) + 1:
            break
        end = d.index(b'\0', pos + 4)
        name = d[pos + 4:end].decode('latin-1'); pos = end + 1
        if not name:
            break
        entries.append((name, off))
        if pos >= entries[0][1]:
            break
    out = {}
    for k, (name, off) in enumerate(entries):
        nxt = entries[k + 1][1] if k + 1 < len(entries) else len(d)
        out[name] = d[off:nxt]
    return out


# --- EOB view positions (ScummVM kyra scene_rpg.cpp, _vmpOffsetsDefault) ----
# Each wall type = 431 VMP entries after the 330 backdrop entries, split into 9
# view positions: (offset, blocks wide, blocks high, block row the view draws it at).
VMP_POS = {
    'side_d3_outer': (102, 3, 5, 3), 'side_d3_inner': (97, 1, 5, 3), 'front_d3': (129, 6, 5, 3),
    'side_d2_outer': (117, 2, 6, 3), 'side_d2_inner': (81, 2, 8, 2), 'front_d2': (159, 10, 8, 2),
    'side_d1': (45, 3, 12, 1), 'front_d1': (239, 16, 12, 1), 'side_d0': (0, 3, 15, 0),
}
# DH panel (draw_walls kCellPanel, variant 0 / variant 1) for each EOB position, and the
# DH face's view y (kCellY); DH crops the EOB block rows to y_dh .. y_dh + height.
DH_PANEL = {
    'side_d0': ((0, 6), 0), 'side_d1': ((1, 7), 8), 'side_d2_inner': ((2, 12), 20), 'side_d3_inner': ((3, 9), 27),
    'side_d3_outer': ((4, 10), 27), 'side_d2_outer': ((5, 11), 26), 'front_d1': ((8, None), 8),
    'front_d3': ((13, None), 27), 'front_d2': ((16, None), 20),
}


def render_position(blocks, entries, walltype, pos):
    """-> (w, h, nibbles, mask) of one EOB wall position, left-side (unflipped) orientation.
    Entry 0 = no block; nibble 0 = transparent (ScummVM vcnDraw_*_trans_4bit)."""
    off, bw, bh, _ = VMP_POS[pos]
    base = 330 + 431 * walltype + off
    w, h = bw * 8, bh * 8
    px, mask = bytearray(w * h), bytearray(w * h)
    for by in range(bh):
        for bx in range(bw):
            e = entries[base + by * bw + bx]
            if not e:
                continue
            blk = blocks[e & 0x3FFF] if (e & 0x3FFF) < len(blocks) else bytes(64)
            for y in range(8):
                row = blk[y * 8:y * 8 + 8]
                if e & 0x4000:
                    row = row[::-1]
                for x in range(8):
                    i = (by * 8 + y) * w + bx * 8 + x
                    px[i] = row[x]; mask[i] = 1 if row[x] else 0
    return w, h, px, mask


def dh_panel(blocks, entries, walltype, pos, dh_w, dh_h):
    """EOB position cropped to the DH panel box (same width; rows from the DH face's y)."""
    w, h, px, mask = render_position(blocks, entries, walltype, pos)
    top = DH_PANEL[pos][1] - VMP_POS[pos][3] * 8
    extra = top + dh_h - h          # Ice Stairs' depth-3 panel is 48x38 where the rest are 48x37
    assert w == dh_w and 0 <= top and extra <= 2, (pos, w, h, dh_w, dh_h, top)
    rows = slice(top * w, (top + dh_h - max(0, extra)) * w)
    pad = bytes(max(0, extra) * w)  # transparent rows below
    return bytes(px[rows]) + pad, bytes(mask[rows]) + pad


def eob1_palette(base_dir, level_pal=None):
    """EOB1 colours as the game shows them: the global EOBPAL.COL for indices < 0xE0 (level .PAL
    files hold saturated junk there) plus the level palette's own band 0xE0-0xFF."""
    import os
    pal = read_pal(os.path.join(base_dir, 'EOBPAL.COL'))
    if level_pal:
        lp = read_pal(os.path.join(base_dir, level_pal))
        pal[0xE0 * 3:] = lp[0xE0 * 3:]
    return pal
