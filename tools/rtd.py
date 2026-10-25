"""AESOP runtime dictionaries (RTD): IMPT/EXPT tables, entry 0 name table, ...

Format (arun/asm/RT.ASM RTD_lookup/RTD_first/RTD_iterate):
  u16 H; u32 chain_off[H] (byte offset of chain h from dict start, 0 = empty);
  chains: { u16 tag_len, tag\\0, u16 def_len, def\\0 }* u16 0
  hash(tag) = sum(tag bytes) mod H; lengths include the terminating NUL.
"""
import struct


def parse(d):
    """-> (H, [(hash, [(tag, def), ...]) in file order])"""
    H = struct.unpack_from('<H', d)[0]
    offs = struct.unpack_from('<%dI' % H, d, 2)
    chains = []
    for h, o in sorted(((h, o) for h, o in enumerate(offs) if o), key=lambda x: x[1]):
        pos, items = o, []
        while True:
            tl = struct.unpack_from('<H', d, pos)[0]; pos += 2
            if tl == 0:
                break
            tag = d[pos:pos + tl - 1]; pos += tl
            dl = struct.unpack_from('<H', d, pos)[0]; pos += 2
            dfn = d[pos:pos + dl - 1]; pos += dl
            items.append((tag, dfn))
        chains.append((h, items))
    return H, chains


def hash_of(tag, H):
    return sum(tag) % H


def build(H, chains):
    by_hash = dict(chains)
    order = [h for h, _ in chains]
    body = bytearray(); offs = [0] * H
    base = 2 + 4 * H
    for h in order:
        offs[h] = base + len(body)
        for tag, dfn in by_hash[h]:
            body += struct.pack('<H', len(tag) + 1) + tag + b'\0' + struct.pack('<H', len(dfn) + 1) + dfn + b'\0'
        body += b'\0\0'
    return struct.pack('<H', H) + struct.pack('<%dI' % H, *offs) + bytes(body) + b'\0\0'   # end of dictionary


def add(H, chains, tag, dfn):
    """Append (tag, def) to the chain its hash selects (creating the chain at the end if new)."""
    h = hash_of(tag, H)
    for hh, items in chains:
        if hh == h:
            items.append((tag, dfn)); return chains
    chains.append((h, [(tag, dfn)]))
    return chains
