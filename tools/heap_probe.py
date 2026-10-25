"""TEST ONLY: log the AESOP heap from inside a running game.

The runtime has heapfree() and xmsfree() (HACK.RES resource 3, the runtime function table) but no
script calls them, and dprint goes to a debug console DOSBox doesn't show. This kernel patch makes
the game append records to HEAP.LOG in its own folder (the harness creates it empty before launch;
game_music already hooks "enter game"), which the host polls while a walk runs (smoke/heap_log.py):
  "timer tick" : every `every` ticks: update_file("HEAP.LOG") (opens at offset 0; seek_in_file is unused
                 by DH and does not append), write_long_to_file: tick, heapfree(), heapfree() after
                 flush_cache(16 MB) (= what stays locked: the working set), xmsfree(), party level; close_file()
L:tick is game time (about one per second while playing, continued from the save).
Hooks follow game_music: a 3-byte instruction becomes BRA to an appended stub. The tick hook takes
"SSD L:tick" (game_music takes the LAD before it, so both patches can coexist); the stub runs the
displaced store first, then the probe (the next instruction reloads the accumulator).
"""
import struct

import game_music

LOG = b'HEAP.LOG\0'
TICK_STORE = bytes.fromhex('3e6104396004')       # SSD "L:tick"; LSB "B:plr_update"
L_TICK, B_PARTY_LVL = 0x461, 0x458


def patch_kernel(kernel, slots, every=1):
    """slots: {'update_file', 'close_file', 'write_long_to_file', 'heapfree',
    'flush_cache', 'xmsfree'} -> kernel import offsets (RCRS operands)."""
    k = bytearray(kernel)
    w16 = lambda v: struct.pack('<H', v)
    rcrs = lambda f: b'\x20' + w16(slots[f])
    call = lambda n: b'\x21' + bytes([n])
    bra = lambda a: b'\x02' + w16(a)

    def with_name(at, body):
        """body(addr of the inline file name) placed after a BRA that jumps over the name."""
        name_at = at + 3
        return bra(name_at + len(LOG)) + LOG + body(name_at)

    def write(value):                                   # write_long_to_file(value)
        return rcrs('write_long_to_file') + b'\x04' + value + call(1)

    # "timer tick": displaced SSD L:tick first, then the probe every `every` ticks
    tick = game_music._find(k, TICK_STORE)
    stub = len(k)
    pre = bytes(k[tick:tick + 3]) + b'\x3b' + w16(L_TICK) + b'\x04\x1d' + bytes([every - 1]) + b'\x0f'  # LSD tick; PUSH; SHTC; BAND
    brt_at = stub + len(pre)
    probe = with_name(brt_at + 3, lambda a: rcrs('update_file') + b'\x04' + b'\x54' + w16(a) + call(1) +
                      write(b'\x3b' + w16(L_TICK)) +
                      write(rcrs('heapfree') + call(0)) +
                      rcrs('flush_cache') + b'\x04\x1f' + struct.pack('<I', 0xFFFFFF) + call(1) +   # drop all unlocked
                      write(rcrs('heapfree') + call(0)) +
                      write(rcrs('xmsfree') + call(0)) +
                      write(b'\x39' + w16(B_PARTY_LVL)) +
                      rcrs('close_file') + call(0))
    end = brt_at + 3 + len(probe)
    k.extend(pre + b'\x00' + w16(end) + probe + bra(tick + 3))     # BRT end (skip unless tick % every == 0)
    k[tick:tick + 3] = bra(stub)
    assert len(k) < 0x10000
    return bytes(k)
