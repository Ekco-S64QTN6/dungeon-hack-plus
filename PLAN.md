# Dungeon Hack Cross-Engine Mashup — Plan & Findings

> **Historical design document (written 2026-10-24, before any in-game testing).** Kept for its
> format specs, compatibility matrix and palette model, which still hold. Superseded since:
> * "Replace in place, never add slots" (§4): the engine now has 16 wallsets, 16 floors and 35
>   doors, added in free resource slots (3,072 slots, 2,963 used; not 3,081). See `CLAUDE.md`.
> * `pipeline.py roll` + `pool/pool.json`: replaced by the mix (`tools/mix.py`, `dhplus.py roll`).
> * "Not verified yet / Xvfb not installed" (§5, §8, §10): the in-game gate is closed; DOSBox-Staging,
>   Xvfb and the walker harness run every check in game (`smoke/`).
> * EOB1/2 walls are copied 1:1 from EOB's hand-drawn view positions, not warped (§4 Path C);
>   Menzo floors are projected (Path B); `SKELWAR.CPS` (RLE method 3) is supported (§7).
> * The project moved from `` to the repository root; paths below are updated.
>
> Current status: `ROADMAP.md`. Working notes and engine facts: `CLAUDE.md`.

Everything marked **✔ measured** was checked against the actual files in this folder
(GOG *Forgotten Realms: The Archives* Collections One and Three) on 2026-10-24.
Everything marked **◐ inferred** is a strong hypothesis still to be confirmed in game.

## 0. Corrections to the starting assumptions

| Assumption | What the files show |
|---|---|
| A Ravenloft game is in the folder | **No.** Collection Three contains only Dungeon Hack (ENG/FRE/GER) and Menzoberranzan. The top-level `Dungeon Hack/` is byte-identical to `Dungeon Hack-ENG` (`HACK.RES` cmp equal). |
| Menzoberranzan ships `.CINE`, `.CGEN`, `.RAW` files | `CINE/` and `CGEN/` are **directories inside `GAME.ISO`** holding `*.DFA` animations. There are no `.RAW` files. On disk: `RES0`–`RES8`, `COLORS`, `LEVELS.DAT`, `OBJECTS.DAT`, `NPCS.DAT`. The ISO also has `RES3`, `RES6`, `RES9`, `RES10` (55 MB) and `DATA.A00/A01` (ARJ). |
| LoftRES is the community tool | I found **no trace of LoftRES** online. The plan does not depend on it: `tools/dreamforge.py` reads the RES container and LZSS directly. If you have LoftRES, use it as a cross-check. |
| XWE 1.11 / Game Extractor handle AESOP | Not verified. The tool that is verified and maintained is **daesop**, bundled with **Thirdeye** (GPLv3, github.com/psi29a/thirdeye). It extracts, replaces, converts bitmaps and creates DH `.TBL` files. |
| EOB3 assets are directly portable to DH | **Different bitmap encoding, identical art layout.** ✔ GOG EOB3 runs **AESOP/32** with VFX **"1.10"** shape tables (312; decoder ported to `aesop.decode_vfx110`, all 312 decode). ✔ DH runs **AESOP/16 V1.00** with the old shape format plus a `.TBL`. ✔ Both use the **same 18-panel view-position unit in the same order** (EOB3 "19 shapes" = 18 panels + backdrop). ✔ EOB3 wall ramps (PAL_WALLS 0xB0–0xBF) follow DH's ramp convention. So EOB3 walls, stairs and doors copy 1:1 with an index remap (`panels` job). |
| AESOP palettes are flat 768-byte blocks | ✔ They are structured resources: `u16 n, u16 off[12], RGB6[n], 11 shade tables[n]`. The base palette is 3610 B with n=256; the wall/floor palettes are 250 B with n=16. |
| Westwood is the hardest tier | For **walls, floors, and monsters** it is the *easiest* tier. DH copied the EOB1/2 view layout: a 176×120 viewport, a 128×96 near front wall, and wall colours in indices 240–255 (✔ EOB1 VCN remap points at 0xF0–0xFE). |

## 1. Asset inventory (what is actually here)

Run `python3 -I pipeline.py inventory`. It writes `work/inventory.md` and `inventory.json`.

| Game | Path used | Engine | Key containers ✔ |
|---|---|---|---|
| Dungeon Hack | `Dungeon Hack/` | AESOP/16 runtime (`AESOP.EXE` 151,968 B, Borland 16-bit) + `MAZE.EXE` generator | `HACK.RES` (2,963 entries) + `HACK.TBL`, `OPEN.RES` (194) + `OPEN.TBL`, `*.ADV` Miles drivers, `STDPATCH.AD` (222 B) |
| EOB3 | `…Collection One/games/Eye of the Beholder III/GAME/EOB3` | AESOP/32 runtime (DOS/4GW; GOG adds DOS32A) | `EYE.RES` (2,449), `*.GFF` (GFFI cine files: `INTRO/LICH/DARK/FINALE`), `CHARGEN/` (**a Westwood-format chargen**: `.CPS`, `ITEM.DAT`, `CHARPICS.BMP`) |
| EOB1 | `…/Eye of the Beholder DE/GAME/EYE` (loose files); ENG ships `EOBDATA1-6.PAK` + `EYE.PAK` | Westwood | `.CPS` (48), `.VCN/.VMP/.PAL` ×5 sets (BLUE, BRICK, DROW, GREEN, …), `.DAT` decorations, `.MAZ/.INF` levels, `.EGA/.ECN/.EMP` (EGA variants), `.CMP` |
| EOB2 | `…/Eye of the Beholder II - EN/GAME/DARKMOON` | Westwood | `.CPS` (116), `.VCN/.VMP` ×5 (CRIMSON, DUNG, FOREST, MEZZ, SILVER), `.PAL` (19), `.DEC`, `.DCR`, `.ADL` music, `.SND` |
| Menzoberranzan | `…Collection Three/games/Menzoberranzan/GAME/MENZO` + `GAME.ISO` | DreamForge (Ravenloft engine) | `RES0-8` on disk, plus `RES3/6/9/10`, `CINE/*.DFA`, `CGEN/*.DFA` on ISO. `COLORS` palette and shade tables. Miles `A32*.DLL` drivers |

### Format reference

| Ext / container | Engine | Contents | Status |
|---|---|---|---|
| `.RES` "AESOP/16 V1.00" | AESOP (DH, EOB3) | Directory blocks of 128 slots. Entry 0 = name dictionary. Holds compiled SOP code (`.IMPT/.EXPT` tables), strings (`S:`), shape tables, palettes, raw PCM, XMIDI | **Shared container**, ✔ parsed by `tools/aesop.py` |
| `.TBL` | AESOP/16 (DH only) | `u32` pointer per directory slot, zero-padded (✔ 2,963/2,963 match) | Engine-locked; **must be regenerated** after any RES change |
| Old shape table | AESOP/16 (DH) | `u32 size, u16 n, u32 off[n]`; per shape `u16 w,h` + row RLE (`u8 y`, spans `u16 x | 0x8000 last, u8 width, u8 bytes`, packets `b&1` fill / copy `(b>>1)+1`, `0xFF` end) | ✔ decode+encode round-trip on all 632 DH tables |
| VFX "1.10" shapes | AESOP/32 (GOG EOB3) | Newer VFX shape tables | Decoder exists in Thirdeye `apps/thirdeye/graphics/bitmap.cpp`; not yet ported to `tools/` |
| `.GFF` (GFFI) | EOB3 cine player | Miles GFF animation | Engine-locked (cutscenes) |
| `.CPS` | Westwood | 320×200 image, LCW/Format80 (method 4) | ✔ `tools/westwood.py`. One file (`SKELWAR.CPS`, method 3) is unsupported |
| `.PAL` / `.COL` | Westwood | 768 B, 6-bit RGB | ✔ |
| `.VCN` | Westwood | LCW-packed: `u16 nblocks`, 32 B remap (16 backdrop, 16 wall), 8×8 4bpp blocks | ✔ BLUE: 1512 blocks |
| `.VMP` | Westwood | `u16 n` + block refs (bit 14 = flip). 330 backdrop (22×15 blocks = **176×120**), then 431 per wall type; entries 239–430 = **128×96 near front wall** | ✔ |
| `.DAT/.DEC/.DCR` | Westwood | Decoration shapes and coordinates | Engine-locked layout; art is on `.CPS` sheets |
| `.ADL`, `.SND` | Westwood | AdLib (OPL) music and SFX programs | Engine-locked |
| `.MAZ/.INF` | Westwood | Level maps and scripts | Not used (DH generates levels) |
| `RESn` | DreamForge | `u32 count, u32 off[count]`, records `"EH" type flags`. flags 0x05 = LZSS (10 B hdr, u32 usize @6). flags 0x00 = raw (9 B hdr, u32 size @5) | ✔ LZSS consumption matches record lengths exactly |
| RES4 type 05 | DreamForge | 559 textures: 12,290 B = 2 B hdr + **64×192 column-major** walls, 4,096 B = 64×64 | ✔ render correctly with `COLORS[4:772]` |
| RES3 type 06 (3,167), RES4 type 06 (502) | DreamForge | Sprite / object frames ◐ | Format **not yet reversed** |
| RES5 type 03 (104) | DreamForge | **XMIDI** (`FORM…XDIR`) | Same Miles format as AESOP |
| RES6 type 04 (386) | DreamForge | Unsigned 8-bit PCM (plus 1 RIFF WAV) | Rate not stored ◐ |
| `*.DFA` | DreamForge | Cutscene animations (CINE/CGEN) | Not worth porting |

## 2. Three-tier compatibility matrix

Legend: **N** = native (byte format DH accepts), **C** = convertible (method given), **X** = not worth it / incompatible.

| Category | EOB1 (Westwood) | EOB2 (Westwood) | EOB3 (AESOP/32) | Dungeon Hack | Menzoberranzan (DreamForge) | Other DreamForge |
|---|---|---|---|---|---|---|
| **Walls / stairs / doors** | **C** VMP front wall 128×96 → target-ramp posterize → mask-warp into DH panels. (Using ScummVM's VMP position tables would let EOB's hand-drawn side walls be copied directly) | **C** same | **≈N** 1:1 panel copy + index remap, ✔ demo2 (Marble walls → Stone) | N (7 wallsets × [13 objects × 18 panels + 2]; stairs 2×18; doors 3×18) | **C** RES4 64×192 textures → ramp → mask-warp (true texture-mapped source, so perspective comes from warp) | absent |
| **Floors/ceilings** | **C** VMP backdrop is exactly 176×120 → ramp 224–238 | **C** same | **C** decode → ramp | N (`Floor-0..7`, 176×120) | **C** 64×64 floor textures need a floor projection (not yet implemented) | absent |
| **Monsters** | **C** CPS sheet → `slice_sheet` → 6 frames 80×88 → fixed palette 0–223 (✔ demo) | **C** same | **C** "1.10" decode → same | N (57 tables × 6 × 80×88) | **C, blocked** RES3 sprite format not reversed yet. Expect 8-direction frames, use front/back/side/attack | absent |
| **Items (icons / floor items)** | **C** ITEMICN/ITEMS1/ITEML1 sheets → fixed palette | **C** | **C** | N (`Icon xx`, small shapes) | X (3D object sprites, low value) | — |
| **Portraits** | **C** CHARGENA/CHARPICS → 31×32 → fixed palette | **C** | **C** (EOB3 has 40 `Portrait n`; the EOB3 chargen is Westwood CPS) | N (`Portrait 0..`, 31×32) | **C** downscale CGEN/portrait art (source TBD) | — |
| **UI frames / screens** | X SOP code hard-codes coordinates. Full-screen art (320×200) could be swapped as "C" but you gain nothing structurally | X | X same reasoning | N | X | — |
| **Sounds** | X (OPL SFX programs) | X (`.SND` = OPL) | **N** raw u8 PCM (90 entries) → `raw` job; check rate | N (119 + 34 voice) | **C** strip `EH` header (done), resample to DH rate | — |
| **Music** | X (`.ADL` driver bytecode; ADL→XMIDI is not realistic) | X | **N** XMIDI (66), but AdLib needs a matching timbre bank | N (only 7 in `OPEN.RES`: intro/ending. **No in-dungeon music**) | **N** XMIDI (104). Same timbre caveat | — |
| **Palettes** | **C** only via ramp re-mapping. Do not import raw palettes | C | C | N (base 256 + 21 wall/floor ramps) | C (ramp/quantize) | — |

### Per-level pairing rules: data, not EXE ✔
The `kernel` SOP resource in `HACK.RES` decides this, in its "randomize graphics" and "setup level graphics" handlers (from `daesop -j HACK.RES kernel`). For each of the 25 levels:
`wallnum = rnd(0..6)`. `floornum = rnd(0..7)` until `table1062[floornum] & 1<<wallnum`. `floorpal = rnd(0..20)` until `table1091[floorpal] & 1<<floornum`. `wallpal = rnd(0..20)` until `table1070[wallpal] & 1<<wallnum` **and** `table1112[wallpal] & 1<<floorpal`.
Rendering then uses `table950[wallnum]` (resources 190–196), `table794[floornum]`, and `set_palette(1|2, table978[wallpal|floorpal])`. All four mask tables are fixed-size byte arrays at known offsets (`tools/kernel_rules.py`), so retargeting ramps is a **same-size byte patch** (`palette_rules` job). The loops retry forever, so `kernel_rules.problems()` refuses any rule set that would hang new-game creation. The choice is made when a game is created, so rule edits only affect new games.
Original rules: Marble, Wood, Foil, Ice, Mine and Rock pair with single-ramp palettes (00–14). **Stone pairs only with two-ramp palettes 15–20.**

### Palettes (the deciding constraint) ✔
Slot usage across all 632 DH shape tables:
* **240–255** (wall ramp): wallsets, stairs, doors 05–09/11/18, keyholes, wall and special decorations, `Main Screen`, `Healer`, and two monsters (**Weird**, **Wraith2**) that deliberately take on the wall colour.
* **224–239** (floor ramp): floors, `Ground-0..7`, floor decorations, some gem holes, `Icon 3b/3c`, `Diff Screen`.

So editing *palettes* recolours all of that. Editing the *pairing rules* does not.
* **0–223**: fixed colours (`Main Base Palette` family) shared by every monster, item, portrait and UI piece. Monster frames use a subset (`work/aesop/dh_palette.json → monster_indices`). Imported sprites are quantized to that subset with a redmean metric.
* **224–238 floor ramp, 240–254 wall ramp**: each `wall/floor palette NN` (00–14) is a **15-step brightness ramp** (index 0 brightest → 14 near black) plus one accent colour. Its 11 shade tables step down the ramp for distance darkening. The SOP kernel picks palettes **by dungeon level** (`set_palette(1, table978[wallpal[party_lvl]])`), not by wallset. So wall/floor art stores **brightness levels**, and hue comes from the level. Imported walls are posterized with `normalize.to_ramp_target` against the **mean luminance profile of the palettes the rules actually allow for that target**, never colour-quantized. A plain 0→14 ramp is wrong for Stone and for floors whose palettes are two-ramp. demo 1 had exactly that bug, and demo2 fixes it. Palettes 15–20 have a different two-ramp shape. Avoid them as a model, or treat their indices 0–5 and 5–14 separately.
* DreamForge `COLORS` is a 256-colour 6-bit palette plus light tables. Its textures are full-colour, so expect a loss of hue identity (by design, as above). EOB1/2 walls are already 16-colour 4bpp, which is a near-lossless fit.

### Geometry ✔
All DH dungeon art is built from one **18-panel view-position unit** (shared with EOB3):

| pos | size | pos | size | pos | size |
|---|---|---|---|---|---|
| 0 | 24×120 near side | 6 | 24×120 near side (2) | 12 | 16×59 |
| 1 | 24×95 | 7 | 24×95 | 13 | 48×37 far front |
| 2 | 16×59 | 8 | **128×96 near front** | 14 | 48×37 (unused, empty) |
| 3 | 8×35 | 9 | 8×35 | 15 | 128×96 (unused, empty) |
| 4 | 24×35 | 10 | 24×35 | 16 | 80×59 mid front |
| 5 | 16×43 | 11 | 16×43 | 17 | 80×59 (unused, empty) |

A wallset (236) = 13 wall objects × 18 + two 176×120 specials at slots **36 and 217**. Objects start at 0, 18, 37, 55, 73, 91, 109, 127, 145, 163, 181, 199 and 218. Stairs = 2×18, doors = 3×18, keyholes and wall/special decorations = 18, floor/ground decorations = 2×18 + 2.

**Exact roles ✔**, from `AESOP.EXE`'s `draw_walls` tables (port in Thirdeye `runtime/dh.cpp`). An 18-panel object is **2 wall variants × 9 faces**. The variant is MAZE's per-tile `random(0,1)` byte.

| face | variant 0 | variant 1 |
|---|---|---|
| side, depth 0 (beside party) | 0 | 6 |
| side, depth 1 | 1 | 7 |
| side, depth 2 inner / outer | 2 / 5 | 12 / 11 |
| side, depth 3 inner / outer | 3 / 4 | 9 / 10 |
| front, depth 1 / 2 / 3 | 8 / 16 / 13 | mirrored 8 / 16 / 13 (so 15, 17, 14 are never drawn) |

Left/right faces are the same panel drawn mirrored.

**What uses which object ✔** (from `dungeon`/`doors`/`current *` script code):
* Wallset object 0 (slots 0–17) = plain wall.
* Wallset object 1 (slots 18–35) = **door frame**, drawn by `doors.render` at `position + 18`. Slot 36 = the frame seen from inside the doorway.
* Stairset = [**down 0–17**][**up 18–35**]: `current stairs down/up` report frame base 0 / 18.
* Doorset = `maxstate` blocks of 18, with `maxstate = report(3002) − 1 = 3` (a constant byte in `current door`). Stage `s = maxstate − state`, and `s > 0` draws block `s−1`. Block 0 = nearly open, block 2 = closed, fully open draws nothing.
* EOB3 doors = [frame][stage 1][stage 2][stage 3] (+ a 5th "bashed" block on Ruins wooden door). That maps **1:1** onto DH: frame → wallset object 1, stages → doorset blocks 0–2. The stage-count byte is not touched. ✔ demo3. This is the Westwood EOB view (8-px block columns, 176×120 view). Instead of hard-coding the projection, `normalize.warp_to_mask` uses **each original panel's opaque mask as the target shape**. Per column, the texture column u is interpolated perspective-correctly, using column height as 1/z. This works for EOB, EOB3 and DreamForge sources alike.

### Sprites ✔
DH monster = one shape table with 6 frames of 80×88. Order observed on Goblin: front, back, side, side, attack, attack. EOB1/2 monster `.CPS` sheets also carry 6 poses (verified on KOBOLD), so they map 1:1. DreamForge sprites are rotational and animated: choose 6 frames per monster. That needs the RES3 format reversed first.

### Worth it?
* **High value, low cost**: EOB1/EOB2 walls and floors (10 sets × ≤6 wall types), EOB1/2 monsters, EOB3 PCM sounds, Menzo wall textures.
* **Medium**: EOB3 walls and monsters (port the "1.10" decoder first), portraits, items.
* **Not worth it**: UI frames, Westwood music/SFX (OPL programs), all cutscenes (`.GFF`, `.DFA`), level data (`.MAZ/.INF`, Menzo `LEVELS.DAT`). DH generates its own levels.

## 3. Extraction plan per engine

### AESOP (DH + EOB3)
```
python3 -I pipeline.py extract          # does all three engines
```
* `work/aesop/{hack,open,eye}/manifest.json`: every entry with index, name, kind, size, attrib.
* `work/aesop/hack/*.png`: atlases of every DH shape table with frame numbers (wallsets: 9 columns).
* `raw/*.bin`, `raw/*.wav`: XMIDI, PCM (WAV preview at an *assumed* 11,025 Hz), palettes, EOB3 "1.10" shapes.
* daesop equivalents (build Thirdeye with `-DBUILD_DAESOP=ON`): `daesop /i HACK.RES out.txt`, `/x` and `/xh` to extract, `/r` and `/rh` to replace, `/create_tbl HACK.RES HACK.TBL`, `/test_old_bitmaps`. Use daesop to cross-check every build (§5).

### DreamForge (Menzoberranzan)
* Disk: `RES0-8`. CD-only: `7z x GAME.ISO RES9 RES10 -o work/iso/` (read-only extraction). Add them to the `range()` in `extract_dreamforge`.
* Output `work/dreamforge/RESn/NNNN_tXX.{png,xmi,wav,bin}`. Textures are pre-rendered with `COLORS`.
* Still to reverse: RES3/RES4 type 06 sprite records (`.bin`, already LZSS-unpacked), and the RES0–2/7/8 type 01/02 records (likely level/object data).

### Westwood (EOB1/EOB2)
* Use **EOB1 DE** (loose files) for art; ENG's `EOBDATA*.PAK` unpack with `westwood.unpak`. Art is language-neutral, except text baked into CPS screens.
* Output `work/westwood/eob{1,2}/`: every CPS as PNG (palette = same-name `.PAL` or `EOBPAL.COL` / `DUNG.PAL`). **Monster sheet colours depend on the level palette**, so re-export with the right palette per monster. `*_backdrop.png` is 176×120 floor/ceiling. `*_wtN_front.png` is the 128×96 near wall per wall type. Typically wt0/1 are plain walls; others are doors, stairs and decorated walls.
* Reference decoders: ScummVM `engines/kyra` (EOB), OpenRA (LCW).

## 4. Integration strategy

### Rule: replace in place, never add slots
DH's generator is `MAZE.EXE` (layout, zones, item and feature counts; writes `LEVELS.DAT`, `FEA%02d.DAT`, `ITEMS.DAT`) plus SOP code in `HACK.RES`. The SOP code picks palettes and wallsets, and monster classes are SOP objects bound to their art by name. **Adding** wallsets or monsters means editing SOP tables and code (daesop disassembly + Thirdeye's `arc` compiler). That is logic work. **Re-skinning** existing slots needs no logic change. The art just has to keep the frame count and the per-frame w×h (`verify` enforces this).

### Randomizer hook (no logic changes)
`pipeline.py roll POOL SEED NAME` is a **build-time randomizer**. For every DH slot (7 wallsets, 8 floors, the monster tables you list), it draws a skin from the merged pool (`pool/pool.json`) and rebuilds `HACK.RES` + `HACK.TBL` into `build/NAME/`. DH's own runtime randomness still decides *which* slot appears where, and each roll changes *what the slots look like*. A new seed gives a new mashup, and the recipe is saved as `pool/rolled_NAME_SEED.json` for reproducibility. Going further means patching SOP tables (e.g. `wallpal`/`floorpal`, monster spawn lists). Treat that as phase 2 and do it with daesop.

### Path A — EOB3 → DH (same family, not same format)
1. ✔ "1.10" decoder ported (`aesop.decode_vfx110`). `extract` writes EOB3 atlases with 18-column rows.
2. Walls, stairs, doors: `panels` job copies 18-panel objects 1:1 and remaps PAL_WALLS indices onto the target's real ramp profile (✔ demo2). Pair with a `palette_rules` job when the target's pairing palettes have the wrong ramp shape. Monsters: export frames, pick 6, then `sprites` job.
3. Sounds: `raw` job (u8 PCM to u8 PCM). Music: `raw` job into `OPEN.RES` XMIDI slots (`"res": "OPEN.RES"`). Pick the Roland or AdLib variant to match the slot name.

### Path B — DreamForge → DH
1. Walls: RES4 64×192 texture → `wallset` job (to_ramp posterize → mask warp). Curate textures, because many are doors, alcoves, bookshelves or tapestries.
2. Floors: needs a floor-plane projection into 176×120 (TODO: perspective warp by row, mirroring `warp_to_mask`).
3. Monsters: reverse RES3 first. Then slice 6 frames → `sprites` job.
4. Sound: resample RES6 PCM to DH's rate (confirm the rate; see §7). Music: `raw` job.

### Path C — Westwood → DH (best fit)
1. Walls: `*_wtN_front.png` → `wallset` job (✔ demo: EOB2 DUNG → Stone Wallset).
2. Floors: `*_backdrop.png` → `floor` job (✔ demo: EOB1 BLUE → Floor-0).
3. Monsters: CPS → `normalize.slice_sheet` → order [front, back, side, side, atk, atk] → `sprites` job (✔ demo: EOB1 KOBOLD → Goblin).

## 5. Pipeline

```
(repository root)
  config.json          game paths (relative to the project root)
  pipeline.py          inventory | snapshot | extract | build | verify | roll
  tools/aesop.py       RES/TBL read+append-replace, names, palettes, old-shape decode/encode
  tools/westwood.py    LCW, CPS, PAL, VCN, VMP, PAK
  tools/dreamforge.py  RES container, LZSS, COLORS, textures
  tools/normalize.py   to_ramp, quantize_fixed, fit_sprite, warp_to_mask, slice_sheet
  pool/                recipe_demo.json, pool.json, sliced sprites, rolled recipes
  work/                extraction output (disposable)
  build/NAME/          patched full copy of DH (playable)
  backup/DH-<sha>/     pristine snapshot + SHA256SUMS
```
```bash
python3 -I pipeline.py inventory
python3 -I pipeline.py snapshot
python3 -I pipeline.py extract
python3 -I pipeline.py build pool/recipe_demo.json demo     # verify runs automatically
python3 -I pipeline.py roll  pool/pool.json 1234 roll1234
```
Recipe job types: `wallset {target, texture, frames}`, `floor {target, image}`, `sprites {target, images[]}`, `raw {target, file, res?}`, `panels {target, target_first, source, source_first, count, source_palette, ramp_of?, keep_empty?}` (EOB3 → DH), `palette_rules {wall_palettes: {"Stone Wallset": [..]}}` (runs first, validated). Recipe-level `"compact": false` turns off RES compaction (on by default; useful for bisecting).
Recipes: `recipe_demo.json` (first demo; its Stone reskin has the two-ramp bug), `recipe_demo2.json` (correct), `recipe_stress.json` (size ceiling), `pool.json` + `roll`.
How a replacement is written: the new entry is appended to the RES and its directory slot repointed. The old bytes are counted in `lost_space`, exactly as AESOP's own resource manager does. Then the `.TBL` is regenerated from the new pointer table.

**Verified so far (structural):** demo and roll builds parse, the TBL matches all slots, changed shape tables decode with the original frame count and sizes, and the originals are untouched (cmp against the snapshot).
**Not verified yet:** running the build in DOSBox (no DOSBox on this machine).

## 6. Testing & rollback

**In-game smoke test** (DOSBox / DOSBox-Staging):
```
dosbox -c "mount c "build/demo"" -c "c:" -c "HACK.BAT"
```
(The GOG copy-protection prompt accepts any input.) Also try Thirdeye's `thirdeye` binary for quick DH loads. Its DH renderer is still in progress, so DOSBox is authoritative.

| Category | Check |
|---|---|
| All | Game boots past `aesop open opening` and `aesop hack phase-one`; no "Unable to read from .TBL"; `daesop /i build/X/HACK.RES` parses; `daesop /create_tbl` output == our TBL (byte compare) |
| Walls | Walk a full level at every depth: side panels align with front panels, no gaps at 8-px column seams, distance shading darkens smoothly, door frames (unreplaced variants) still look right next to new walls |
| Floors | Horizon line matches the walls; no ceiling/floor seam |
| Monsters | All 6 frames at all distances (runtime scaling); facing order correct when circling; attack frames fire; transparency correct (no index-0 halos) |
| Palette | Each dungeon level (different ramps): walls readable, not crushed; monsters not shifting colour between levels |
| Sounds/music | Plays at the right pitch (rate); AdLib and MT-32 drivers both |
| Memory | Long session plus a save/restore round-trip. AESOP/16 runs in 640 KB real mode, so watch `payload growth` in `verify` |

Per-source matrix: run each category once with an EOB1, an EOB2, an EOB3 and a Menzo asset before mixing.

**Rollback:** builds never touch `Dungeon Hack/`. `backup/DH-<sha>/` is a full copy with `SHA256SUMS`, so `sha256sum -c` restores confidence. Every build stores its recipe and `MASHUP_BUILD.json` (recipe hash), and rolled recipes are kept, so any build can be regenerated exactly. To version the pool, commit `pool/` + `config.json` + `tools/` to git (not `work/`/`build/`, which are regenerable, and not game data).

## 7. Risks & gotchas

1. **TBL drift**: any RES change without regenerating `.TBL` breaks DH (the EXE reads it). `build` always rewrites it; `verify` checks it.
2. **Frame count/size lock**: SOP code and the renderer assume the original shape count and dimensions per resource. `verify` flags any change.
3. **Real-mode memory**: dithered textures RLE-compress worse. The demo grew HACK.RES payloads by +8 KB and the roll by +19 KB. Use `"dither": false` per job if memory trouble appears. Large growth also makes the RES file bigger because of appended entries (lost space). Compacting is a future step (daesop rebuild or a rewrite pass).
4. **Hue loss on walls is by design**: walls/floors take colour from the level's ramp palette. To keep a source's colour, you would have to replace `wall/floor palette NN` resources, which recolours *every* wallset on those levels.
5. **Index 0 = transparent / 240–255 reserved**: never emit 0 inside opaque sprite areas (quantizer excludes it). Monster art must stay in the fixed range.
6. **AdLib timbres**: DH's `STDPATCH.AD` is 222 B, while EOB3's is 5,162 B. Imported EOB3 or Menzo XMIDI may play with missing instruments on AdLib. Test MT-32/GM first, or swap in EOB3's `STDPATCH.AD` (reversible file swap).
7. **PCM rate: 8 kHz (likely, not proven)**: DH/EOB3/Menzo store headerless u8 PCM. DH's SOP calls `sound_effect(index)` with no rate, so the rate is fixed in `AESOP.EXE`, which stores 8000 in a global (`C7 06 66 8D 40 1F` = `mov [8D66h],1F40h` at file offset 74517). Thirdeye also plays EOB3 at 8 kHz. Previews now use 8,000 Hz (`config.json`). Confirm by ear in DOSBox.
7a. **Memory model**: `AESOP.EXE` loads resources per entry into a heap with XMS spill (`HACK_XMS`, "[%d to xms %d bytes]", "Out of DOS memory"). So file size is not the ceiling; per-resource size and per-level working set are. ✔ The stress build (every wallset panel, floor and monster reskinned, dithered) grew content by +58 KB, and **no resource exceeds the largest original** (104,922 B vs Ice Wallset 106,504 B). Compaction keeps `HACK.RES` at 7.10 MB vs 7.08 MB original. Whether the per-level working set fits is still an in-game question: run `stress` in DOSBox.
7b. **Weak boot oracle**: a build with 95 zeroed `.TBL` entries still reaches the title menu, so "it boots" proves little. Only `smoke.py shots` (screenshots in the dungeon) counts as verification.
8. **DreamForge**: LZSS is verified; sprite records (RES3/RES4 type 06) are not decoded. Texture orientation is column-major and palette `COLORS[4:772]`. Both render convincingly but are inferred, so re-check a few textures against in-game screenshots. LoftRES-style "try several palettes" advice applies: some records may use other palette tables in `COLORS`.
9. **EOB1/2 palettes**: monster sheets render with whichever level palette you choose. Wrong palette = wrong source colours before quantization.
10. **Unsupported Westwood compression**: `SKELWAR.CPS` uses method 3 (Format40/XOR delta?). Skipped.
11. **Language builds**: DH FRE/GER `HACK.RES` sizes differ (strings). Build from ENG only, or run the recipe per language.
12. **Legal**: personal-use modding of games you own. Don't distribute patched RES files; share recipes and tools instead.

## 8. Smoke testing (`smoke.py`)
* `boot NAME…`: headless DOSBox-Staging (bundled in `third_party/`, v0.83.0), runs `aesop hack phase-one`. A weak oracle (see 7b). ✔ base, demo, demo2 and stress all pass.
* `fixture NAME`: after you create one character and enter the dungeon in a build, saves its `savegame/` as the shared starting state.
* `shots STEPS NAME…`: Xvfb + xdotool + ImageMagick `import`. Runs `maze` + `aesop hack phase-two` from the fixture, uses `AUTOTYPE` for the copy-protection prompt, follows a step script (keys, clicks, screenshot points), then diffs each build against the base install. **Not run yet: Xvfb is not installed** (`sudo pacman -S xorg-server-xvfb`).

## 9. External references
* **Thirdeye / daesop** (GPLv3): used. Built daesop standalone with `g++ *.cpp`. Its `/create_tbl` output is byte-identical to ours on every build. Its docs gave the palette bases, and its `bitmap.cpp` gave the "1.10" decoder.
* **ScummVM Kyra (EOB1/2)**: the clean reference for EOB wall *position* tables. That is the remaining piece for copying EOB1/2's hand-drawn side walls instead of warping front walls.
* **Game Extractor** (DreamForge `.res` plugin): container reference only. Our LZSS reader goes further.
* EOB2 original source on archive.org: not used. Our formats are verified against your files, and that archive is very likely leaked proprietary code.

## 9a. Round-3 findings and gates
* **`Eye_of_the_Beholder_II_Engine_Westwood_Studios_1991_Source_Code/`** contains no Westwood code. It holds John Miles' AESOP/32 runtime (`arun/src`), the compiler and manuals (`aesop32/`), DAESOP 0.85, and forum archives. Useful: `RTRES.H/C` (resource cache), `ARC`/`PALCOMP`/`RSCOMP` (original resource compiler), `ADDITIONAL_DH_RUNTIME_FUNCTIONS.TXT`.
* **Memory model:** LRU cache over `DA_FIXED / DA_PRECIOUS (0x20) / DA_DISCARDABLE (0x10)` entries. The entry `attrib` we preserve *is* these flags. Pressure means discardable art is evicted and reloaded (hitches). A hard failure only happens when one allocation can't fit. Neither the runtime nor DOSBox exposes heap use. **Planned stand-in:** a memory-margin test. Run base and stress from the same dungeon fixture while lowering DOSBox `memsize` / XMS, and compare the first failure or hitch point.
* **Slot cap:** AESOP/32 has `MAX_OBJ_TYPES 2450`. DH's `.TBL` has 3,081 slots (2,963 used), so the probable headroom for *added* resources is about 118.
* **Ramp regression check** (`verify` → `check_ramps`). Fails if a wallset's allowed palettes mix ramp shapes, if reskinned art was built for a different shape than the rules now give it, or if rules changed a wallset's shape while its original art remains. ✔ The negative control `pool/negative_rules_only.json` fails as intended. Builds made before the check are flagged until rebuilt.
* **Gate:** demo3 (stairs + doors) is a *candidate*. Structural, TBL and ramp checks pass and the composited preview is correct, but per review, nothing past demo3 starts until `smoke.py shots` (Xvfb) shows clean diffs on demo2, demo3 and stress, including a door in a corridor with side walls visible (occlusion).

## 10. Next targets (in value order)
1. **Gate:** in-game verification of demo2, demo3 and stress (`smoke.py shots` once Xvfb is installed, plus a one-time character fixture), then the memory-margin test.
2. ✔ Stairs/doors mapping resolved from code (demo3 candidate). Remaining: slot 36 (frame seen from inside the doorway) still shows DH's stone art. EOB3 has no direct equivalent, so either warp EOB3's frame panels or accept the mismatch.
3. EOB3 monsters ("1.10" decode is done; choose 6 frames per monster).
4. EOB1/2 hand-drawn side walls via ScummVM's VMP position tables.
5. Menzo RES3 sprite records. Defer: needs re-projection even after decoding.
6. Phase 2: *adding* slots (SOP table and code edits via daesop disassembly).
