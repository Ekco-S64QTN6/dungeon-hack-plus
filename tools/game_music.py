"""In-game music for Dungeon Hack (the original only plays music in OPEN.RES's intro/ending).

The AESOP runtime has the calls (the intro uses them): load_music() loads the XMIDI driver from
SOUND.CFG and reserves a fixed sequence buffer; play_sequence(LA, AD, PC) reads the resource
for the active device (MT-32/GM, AdLib, PC speaker) into that buffer and starts it;
sequence_playing() polls. DreamForge called unload_music() during play "to conserve heap
resources", so this costs conventional memory (driver + buffer + state + timbre cache, all
fixed): measure with smoke/mem_margin.py. Tracks must fit the buffer: DH's own intro plays an
8,112-byte track, so tracks are limited to that size.

Kernel patch (all hook points found by byte pattern, so FRE/GER kernels work too):
  "enter game"           : load_music() once                 (stub replaces RCRS set_palette)
  "setup level graphics" : play this level's track           (stub replaces INTC 2001)
  "timer tick"           : if not playing, play it again     (stub replaces LAD param 0)
Each stub is appended to the kernel, runs, re-executes the 3-byte instruction it displaced,
and branches back. Track tables (LA and AD resource numbers per wallset) are appended too.
"""
import struct

MAX_TRACK = 8112


def single_sequence(data):
    """XMIDI with several sequences -> one holding only the largest. play_sequence() always plays
    sequence 0; Menzo files put a tiny instrument-less stub there and the song second."""
    if data[8:12] != b'XDIR' or struct.unpack_from('<H', data, 20)[0] < 2:
        return data
    cat = 22 + (22 & 1)
    assert data[cat:cat + 4] == b'CAT ' and data[cat + 8:cat + 12] == b'XMID', 'unexpected XMIDI layout'
    pos, end, forms = cat + 12, cat + 8 + struct.unpack_from('>I', data, cat + 4)[0], []
    while pos + 8 <= end:
        n = struct.unpack_from('>I', data, pos + 4)[0]
        forms.append(data[pos:pos + 8 + n]); pos += 8 + n + (n & 1)
    song = max(forms, key=len)
    return (b'FORM' + struct.pack('>I', 14) + b'XDIR' + b'INFO' + struct.pack('>I', 2) + struct.pack('<H', 1) +
            b'CAT ' + struct.pack('>I', 4 + len(song)) + b'XMID' + song)

ENTER_GAME = bytes.fromhex('200801041d00041dcc2102')          # RCRS set_palette; PUSH; SHTC 0; PUSH; SHTC 204; CALL 2
SETUP_LEVEL = bytes.fromhex('1ed107041d00043958043f540127022a')  # INTC 2001; ...; LSB party_lvl; LSBA wallnum; AIS 2; LTDA
TIMER_TICK = bytes.fromhex('2e00003e6104396004')               # LAD param 0; SSD L:tick; LSB B:plr_update
# SHTC 0; PUSH (base 0); LSB "B:party_lvl"; LSBA "B:wallnum"; AIS 2. AIS (RT.ASM do_AIS) shifts the
# index and ADDS it into the stack entry below (popping), so the 0 base must be pushed first; without
# it the index lands on whatever was pushed before (here the play_sequence pointer: hang)
LEVEL_INDEX = bytes.fromhex('1d00043958043f54012702')


def _find(code, pattern):
    i = code.find(pattern)
    assert i >= 0 and code.find(pattern, i + 1) < 0, 'hook pattern not unique: %s' % pattern.hex()
    return i


def patch_kernel(kernel, slots, la_table, ad_table, hooks=('enter', 'setup', 'tick')):
    """slots: {'load_music', 'play_sequence', 'sequence_playing'} -> kernel import offsets.
    la_table / ad_table: per-wallset track resource numbers (len = number of wallsets)."""
    k = bytearray(kernel)
    rcrs = lambda f: b'\x20' + struct.pack('<H', slots[f])
    bra = lambda a: b'\x02' + struct.pack('<H', a)
    brf = lambda a: b'\x01' + struct.pack('<H', a)
    la_at = len(k); k += struct.pack('<%dI' % len(la_table), *la_table)
    ad_at = len(k); k += struct.pack('<%dI' % len(ad_table), *ad_table)
    load = lambda t: LEVEL_INDEX + b'\x2a' + struct.pack('<H', t)          # acc = table[wallnum[party_lvl]]
    play = rcrs('play_sequence') + b'\x04' + load(la_at) + b'\x04' + load(ad_at) + b'\x04' + load(ad_at) + b'\x21\x03'
    if 'const' in hooks:          # debugging: constant resource numbers, exactly like the intro's call
        intc = lambda v: b'\x1e' + struct.pack('<H', v)
        play = rcrs('play_sequence') + b'\x04' + intc(la_table[0]) + b'\x04' + intc(ad_table[0]) + b'\x04' + intc(ad_table[0]) + b'\x21\x03'

    def hook(at, body):
        """Overwrite the 3-byte instruction at `at` with BRA stub; stub = body + displaced + BRA back."""
        displaced = bytes(k[at:at + 3])
        stub = len(k)
        k.extend(body + displaced + bra(at + 3))
        k[at:at + 3] = bra(stub)
        assert len(k) < 0x10000

    if 'enter' in hooks:
        hook(_find(k, ENTER_GAME), rcrs('load_music') + b'\x21\x00' + (play if 'enter_play' in hooks else b''))
    setup = k.find(SETUP_LEVEL)                    # handler start = first of its two table loads (wallset)
    assert setup >= 0 and k[setup + len(SETUP_LEVEL) + 2:setup + len(SETUP_LEVEL) + 5] == bytes.fromhex('4b0c00')
    if 'setup' in hooks:
        hook(setup, play)
    if 'tick' not in hooks:
        return bytes(k)
    tick = _find(k, TIMER_TICK)
    # if (!sequence_playing()) play;  -- the BRF target is the displaced LAD inside the stub
    stub = len(k)
    pre = rcrs('sequence_playing') + b'\x21\x00' + b'\x06'
    skip = stub + len(pre) + 3 + len(play)
    hook(tick, pre + brf(skip) + play)
    return bytes(k)
