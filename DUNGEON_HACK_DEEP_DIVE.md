# Dungeon Hack internals: formats, engine and limits

Reverse-engineering notes for *Dungeon Hack* (1993, AESOP/16) and the data of its sister games
*Eye of the Beholder* I/II (Westwood), *EOB3* (AESOP/32) and *Menzoberranzan* (DreamForge),
as used by Dungeon Hack+. Everything here was checked against the GOG/Steam files, the script
bytecode (disassembled with `daesop -j`) or in game under DOSBox-Staging; the evidence is named
with each fact. Things that are not known are listed as such (§10).

(An earlier version of this file, written by another agent, contained claims that did not survive
checking: door frame counts, slot counts, file sizes, hashes, a memory map, monster counts. It was
replaced on 2026-10-25.)

---

## 1. Resource files (`HACK.RES`, `OPEN.RES`, `EYE.RES`)

All three use the same container (signature `AESOP/16 V1.00`, EOB3's too); `tools/aesop.py`:

```
header    : char sig[16], u32 file_size, u32 lost_space, u32 first_dir_block (0x24), u32 create_time, u32 modify_time
dir block : u32 next_block, u8 attrib[128], u32 entry_ptr[128]
entry     : u32 timestamp, u32 attrib, u32 size, u8 data[size]
```

* Resources are numbered by directory slot. `HACK.RES` has 24 blocks = **3,072 slots, 2,963 used,
  109 free**. Filling every slot still boots (`smoke_runs/slot_ceiling_report.md`); Dungeon Hack+
  adds its new resources (extra wallsets, floors, doors, music) in free slots.
* Entry 0 is the name → number dictionary. Code resources have import/export dictionaries
  (`<name>.IMPT`, `.EXPT`), hashed by byte sum mod table size with chaining (`tools/rtd.py`, round-trips
  all 702 byte-exactly).
* Dungeon Hack also reads `HACK.TBL` (u32 entry pointer per slot). It must match the RES exactly;
  the pipeline regenerates it (byte-identical to `daesop -create_tbl`).

**Shapes.** Dungeon Hack's bitmaps (and the original EOB3's) are AESOP "old shape" tables:
4 header bytes (vary; not needed for decoding), `u16 n, u32 offset[n]`; each frame `u16 w, u16 h`, then rows `u8 y`, spans
`u16 x (bit 15 = last span of the row), u8 width, u8 byte count`, and packets
(`b & 1`: run of `(b>>1)+1` copies of one byte, else that many literal bytes); `0xFF` ends the frame.
Pixels not covered by a span are transparent. GOG's `EYE.RES` ships daesop-converted "1.10" VFX
tables instead (`aesop.decode_vfx110`).

**Palettes.** `u16 ncolors, u16 offset[12], RGB[ncolors] (6-bit), 11 shade tables`.

## 2. The first-person view

* A view **object** is 18 panels: every position a wall face can occupy in the 3-deep view (front
  faces at depths 0-3, side faces left/right). The panel → position table is in Thirdeye's
  `draw_walls` (`third_party/disasm/thirdeye_dh.cpp`), confirmed in game by painting panels.
* **Wallset** resource = 13 objects × 18 panels + 2 specials. Identified in game: object 0 = walls
  (two variants), 1 = door frame (windows are drawn inside it), 2 panel 0 = the jamb post seen from
  inside a doorway, 4 = window grille, 11 = arch face. Objects 3, 5-10 and 12 are not identified.
* **Stairs** resource = down (frames 0-17) + up (18-35). **Doors** = 3 stages × 18 panels; only the
  front panels 8, 16 and 13 are drawn (`current door` script); stage = max state − state.
  (Original `Ice Stairs` has its depth-3 stairs-down picture in panel 12, so those stairs were
  invisible from three squares away; `fix_ice_stairs`.)
* **Floor** = 176×120 backdrop (floor + ceiling); **Ground** = pit/hole art for that floor.

## 3. Palettes and level graphics

* 256 colours: 0-223 fixed for every level, 224-239 floor ramp, 240-255 wall ramp. The kernel
  holds 21 palettes; 0-14 have one wall ramp, 15-20 two (two-tone masonry such as Stone).
  Wall art must be drawn for the ramp shape of the palettes it is paired with, or it shows wrong
  colours; everything that must look right on any level (doors, decorations, monsters, portraits)
  uses fixed colours only.
* Kernel tables (byte offsets inside the `kernel` code resource, same in ENG/FRE/GER):
  718 doors (19), 794 floors, 826 grounds, 858 levers, 922 stairsets, 950 wallsets, 978 palettes,
  1062 floor → allowed wallsets, 1070 wall palette → wallsets, 1091 floor palette → floors,
  1112 wall palette → floor palettes (`tools/kernel_rules.py` finds them by content).
* At new-game start, `randomize graphics` picks per level (time-seeded): a wallset, then floors,
  floor palettes and wall palettes until the masks allow them, a door, and decorations (wallset w
  owns decorations 4w..4w+3, plus generic ones 28-47). The retry loops never give up, so a rule set
  that cannot be satisfied hangs new-game creation; `kernel_rules.problems()` checks every rule set.

## 4. Script bytecode (SOP)

* Game logic is AESOP bytecode in code resources (334 in `HACK.RES`). Interpreter: `RT.ASM` in
  John Miles' AESOP/32 release. Tables are addressed by **absolute u16 operands** (`LTDA table950` =
  byte 950 of the resource) and the program header stores no code length, so tables and code can be
  appended and loads repointed. Branches are absolute too.
* Useful opcodes: BRF 01, BRA 02, PUSH 04, NOT 06, SHL 13, SHTC 1d, INTC 1e, RCRS 20, CALL 21,
  AIS 27, LTBA 28, LTWA 29, LTDA 2a. `AIS` adds the shifted top of stack into the entry below
  (so an indexed load is `SHTC 0; PUSH; index; AIS 2; LTDA table`); a call is
  `RCRS f; PUSH; arg; ...; CALL n`.
* Engine extensions in Dungeon Hack+ use this: 16 wallsets, 16 floors (16-bit pairing masks via
  word-table stubs), 35 doors, and in-game music (three runtime functions imported into the kernel,
  stubs hooked into "enter game", "setup level graphics" and "timer tick").

**Known bug:** `items` "unlock shape" called `lock_resource` instead of `unlock_resource`
(`fix_unlock_shape` imports the right function).

## 5. Sprites and portraits

* Monsters: 6 frames of 80×88 (front, back, two sides, two attacks), fixed colours only (two
  special monsters, Weird and Wraith2, use wall-ramp colours on purpose). DH has 57 monster slots.
* 30 of EOB3's 31 monsters are Dungeon Hack's own art (matching silhouettes); the Shadow Hound
  is the exception. Most EOB3 portraits are DH's too, and DH's Marble wallset is EOB3's Marble.
* EOB1/EOB2 monsters: CPS sheets cut with EOB's own frame rectangles (ScummVM's tables; each
  sheet's layout from the level scripts). Transparency is colour index 0 only.
  EOB1 colours come from `EOBPAL.COL` below 0xE0 plus the level palette band.
* Portraits: 31×32, 45 slots; the chooser shows men 0-31 and women 29-44.

## 6. Audio

* Sound effects are raw unsigned 8-bit mono PCM at **8,000 Hz**: measured from a DOSBox audio
  capture of a door opening (1.55 s, which only fits `DOOR 01` at 8 kHz;
  `smoke_runs/audio_rate_capture.md`), consistent with the 0x1F40 constant in `AESOP.EXE`.
* Music is XMIDI with separate MT-32/GM and AdLib versions. The original plays none in the dungeon:
  the runtime unloads the music driver during play "to conserve heap resources" (SOUND32.C).
  When re-enabled, `play_sequence` reads a track into a fixed buffer (tracks ≤ 8,112 bytes) and
  aborts the game if a track asks for a timbre the driver's library lacks.
* EOB2's music is Westwood AdLib programs (`.ADL`), not MIDI. EOB1 ships no music files.
  Menzoberranzan's music is XMIDI (RES5); its 386 sound effects (RES6) are unnamed PCM.

## 7. Dungeon generator and level data

* `MAZE.EXE` writes the levels from `SETTINGS.DAT` (fields in `tools/difficulty.py`, from Thirdeye).
  1,000 seeds × 5 settings profiles produced no hang (`smoke/maze_seeds.py`).
* `LEVELS.DAT`: u32 seed + one 32×32 map per level (0xFF open). `FEA*.DAT`: 8-byte feature
  records. Known types: 0 party start, 1 door, 2 door-frame button, 3 illusionary wall,
  4/5 stairs up/down, 12 creature, 16 wall decoration (byte 3 = faces N1 E2 S4 W8),
  19 floor pit (with its destination), 20 ceiling pit, 23 arch, 24 window, 25 pillar.

## 8. Memory and limits

* Start-up needs about 444 KB of free conventional memory (439 KB fails), with or without XMS,
  for the original, a fully reskinned build and the music build alike (`smoke/mem_margin.py`).
  This covers start-up and level 1 only; a worst-case deep level has not been measured.
* Resource slots: see §1 (the mix uses 3,032 of 3,072).

## 9. Other findings

* **Copy protection** is the `validity checker` script (manual-word questions); the GOG/Steam
  installs skip it on the normal path. Documented in `smoke_runs/copy_protection_report.md`;
  Dungeon Hack+ does not remove it.
* **Save/Continue** need a savegame template (`SAVEGAME\SAVEGAME.DIR` etc.) that GOG ships outside
  the game folder; without it the game aborts and DOSBox closes. Builds are seeded with it.
* The automap's Print button can only hang with a printer port configured; DOSBox-Staging has none.

## 10. Not known

* What wallset objects 3, 5-10 and 12 are.
* Several FEA record types (buttons, locks, shooters, teleporters: names from the script code,
  layouts not decoded).
* Whether the `unlock_resource` fix measurably reduces memory use over a long session.
* Menzoberranzan's sound effect names and sample rate.

## 11. Reference files

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `HACK.RES` (ENG, GOG/Steam) | 7,083,229 | `207eaf4081eee453c718fc8f761a707ab5c36bf974255185e2bc90ebe84cac66` |
| `OPEN.RES` (ENG, GOG/Steam) | 1,592,336 | `7bc61e506cbf3aa144acc1b6dd6992ba0e2267d1f7b29294e9eaac83dcf61486` |
| `EYE.RES` (EOB3, GOG) | 6,845,522 | `a11d5a2150ce65225af99655dab029788128af242eaa18ef5eb876a15e2cf767` |

## Credits

* `daesop` and Thirdeye (psi29a and contributors): AESOP formats, bytecode definitions, the
  `draw_walls` tables.
* John Miles: the AESOP/32 runtime and compiler release (`RT.ASM`, `SOUND32.C`).
* The ScummVM team: the Kyra engine's EOB1/EOB2 tables (view positions, decorations, monster frames,
  doors).
* The DOSBox-Staging team.
