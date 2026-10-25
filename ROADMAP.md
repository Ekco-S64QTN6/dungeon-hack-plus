# ROADMAP — "Dungeon Hack+"

Goal: a stable, playable Dungeon Hack whose random dungeons draw on art, monsters, sound and music from EOB1, EOB2, EOB3 and Menzoberranzan, plus fixes and quality-of-life improvements. It ships as a **patcher that the user applies to their own copy**: recipes and tools only, never patched game files.

Legend: `[x]` done · `[~]` partly done / candidate · `[ ]` to do. **(G)** = gate: nothing after it starts until it passes.
Effort: S ≈ hours, M ≈ a day or two, L ≈ several days, XL ≈ open-ended RE.
Specs live in `PLAN.md`; session notes and gotchas in `CLAUDE.md`.

---

## Phase 0 — Foundations (done)
- [x] Inventory all games; identify engines and containers (AESOP/16, AESOP/32, Westwood, DreamForge)
- [x] AESOP RES read / append-replace / compact; `.TBL` regeneration (byte-identical to `daesop -create_tbl`)
- [x] DH old-shape decoder and encoder (all 632 round-trip); EOB3 "1.10" decoder (all 312)
- [x] Westwood LCW/CPS/PAL/VCN/VMP/PAK; DreamForge RES + LZSS + textures
- [x] Palette model: fixed 0–223, floor ramp 224–239, wall ramp 240–255; level pairing rules decoded (`kernel_rules.py`)
- [x] 18-panel view unit and exact roles; wallset = 13 objects × 18 + 2; stairs/door models from script code
- [x] Recipe pipeline (`wallset`, `floor`, `sprites`, `raw`, `panels`, `palette_rules`, test-only `force_graphics`), `roll` randomizer, `verify` + ramp regression check with negative control
- [x] DOSBox-Staging + Xvfb smoke harness, deterministic forced-graphics screenshots, fixture save

## Phase 1 — Close the verification gate (G)
- [x] S  Fix the walk: closed-loop `smoke/walker.py` (compass template-match after every key, repeat dropped turns, verify steps by view change); start facing N was right, the real problem was DH dropping key presses
- [x] S  Capture a door in a corridor at depths 2 and 1, plus stairs up and stairs down: door d2/d1 + stairs up ✔ for base/demo2/demo3/stress and all four `eob3_complete` wallsets; stairs down ✔ base/demo3 via `fixtures/savegame_nomon_stairsdown` (FEA type-0 start moved to (12,3); confirms type 0 = party start)
- [x] S  Open a door and capture all 3 stages: ✔ base + demo3 (`smoke/door_open.json`): closed → stage 2 → stage 1 → open in order, frame and side walls stable. Clicks only work with DOSBox `mouse_capture=seamless` (the default first click is swallowed for capture)
- [x] S  One-command gate: `smoke/gate.py [--base B] [PLAN] BUILD…` (walk-position match + outside-view diff net of base-vs-base noise, 2 px scaler margin, automap masked) → `smoke_runs/gate*/gate_report.{md,png}`; per-preset forced variants via `smoke/variants.py PRESET`
- [~] M  Memory-margin test (`smoke/mem_margin.py`, Gemini): base and stress both cliff at ~444 KB free conventional memory, XMS on or off. **Caveat (audit):** it only boots level 1 and takes one step, so it mostly measures start-up; it does not prove a worst-case level (many monster types, doors, decos) fits. Extend with a long walk / several levels
- [x] S  Ear check: **measured** from a DOSBox audio capture of a door opening: the 1.55 s event only fits `DOOR 01` at 8,000 Hz (1.59 s); at 11,025 Hz no door sample is longer than 1.15 s (`smoke_runs/audio_rate_capture.md`)
- [x] S  Automated in-game checks in place of the quick look: walls, door (3 stages), stairs up/down, floor, monster reskin (stress: the approaching monster renders as the EOB1 kobold, correct scale and anchoring)
- [ ] S  Bug 1 leak measurement: needs a test-only probe reading `heapfree()` (runtime) into something visible; the fix itself is confirmed in bytecode and runs
- [ ] S  Human playtest (≈15 min) of `mixed` or `eob3_complete`: feel, pacing, anything the screenshots can't judge
- [x] **(G)** demo2, demo3, stress, eob3_complete (×4 wallsets), eob1_sewers, eob2_darkmoon and mixed pass the in-game gate (`smoke_runs/gate*/`). The panel pipeline is trusted; the warp pipeline now also reskins door frames (wall object 1). Remaining human playtest is non-blocking

## Phase 2 — Complete the asset ports (reskins only, no game-logic changes)
**Walls, stairs, doors (EOB3, ≈1:1)**
- [x] M  Map every EOB3 wall object: Marble/Forest/Mausoleum/Ruins walls → 4 of DH's 7 wallsets, each with matching `palette_rules` (`tools/eob3_mapping.py` + `recipe_eob3_complete.json`). **In-game gate ✔ (all four).** Finding: DH's own Marble wallset *is* EOB3 Marble walls (pixel-identical in game), so Marble→Marble is a no-op; to add EOB3 Marble, target a different wallset
- [x] M  EOB3 stairs (all sets) → the matching DH stairsets; EOB3 doors (Marble, Mausoleum ×2, Ruins ×2, Temple ×2) → DH Door-xx slots (frame → wallset object 1, 3 stages; drop the Ruins "bashed" block; `tools/eob3_mapping.py`)
- [x] S  Slot 36 (the door-frame jamb post seen when standing in a doorway facing along the wall): EOB1/2 sets warp a quarter-width slice of their own near front wall onto it (`vmp_walls`), EOB3 sets their exported front panel, Menzo sets their wall face. Identified in game by painting it (`smoke/doorway.json`), then checked
- [x] M  Wall decorations, keyholes, levers, gem holes, special decos: map EOB3 decoration resources (all 18-panel) onto DH `Wall Deco nn` / `Keyhole nn` / lever resources (`tools/eob3_mapping.py` maps 18 decos, 12 keyholes, 8 levers; `recipe_eob3_decorations.json` built & verified with -118 KB payload savings)
- [x] M  Wallset objects identified in game by painting each a solid fixed colour (`paint_objects` test job, `smoke/arch_window.json` + fixture `savegame_archwin`): object 2 panel 0 = slot 36 (doorway post), 11 = arch face, 4 = window grille (drawn inside object 1, the door frame). EOB/Menzo sets now texture the arch with their own wall; window grilles stay DH art (bars stay bars), re-ramped
- [ ] S  Objects 3, 5-10, 12 (small details, rubble): not identified yet; re-ramped DH art

**Walls and floors (EOB1/2, Westwood)**
- [x] M  EOB1/2 *hand-drawn* walls: VMP view-position table from ScummVM kyra (`_vmpOffsetsDefault`, 9 positions = 431 blocks) mapped 1:1 onto DH's 9 faces with exact crop offsets (`westwood.VMP_POS/DH_PANEL/dh_panel`); `vmp_walls` job fills wall object 0 (variants from wt0/wt1), door frame (wt2) and stairs (wt3 up / wt4 down; `frame_set`/`stairs_set` borrow from a sibling set). In-game gate ✔ (EOB2 DUNG on Rock)
- [x] M  EOB1/2 **doors** → DH Door-xx (`eob_door` job, `tools/eob_doors.py`): EOB animates doors procedurally, so the 3 DH stages are synthesized (rise / split jaws / dissolve) from EOB's near/mid/far shapes (EOB1 cut table from ScummVM create_kyradat; EOB2 boxes scanned from LEVEL*.INF) and fitted into DH's own doorway boxes. 6 EOB1 + 9 EOB2 kinds; fixed-palette colours by default (doors appear on every wallset incl. two-ramp Stone). In game ✔: iron rises, jaws part, web dissolves; both classic themes now use EOB doors on all 16 DH door slots
- [x] S  EOB1/2 stairs ✔ (`vmp_walls`); decorated walls ✔ (`vmp_deco`: wt5 minus wt0 overlay → the wallset's own decoration slots; kernel `wdeco = wallnum*4 + 0..3` resolved by the `decoration` object's `table14`: Marble 00-03, Stone 04-07, Wood 08-11, Ice 12-15, Mine 16-19, Rock 20-23, Foil 24-26). In game ✔ (EOB1 rune-pillar wall head-on, `smoke/deco_front.json`)
- [x] M  EOB decorations from `.DEC/.DAT` → generic slots `Wall Deco 29–48` (`eob_wall_deco` job, `tools/eob_decos.py`: EOB's own placement tables from ScummVM, i.e. `_dscWallMapping`, `kEoB1/2DscShapeIndexDOS`, `kEoB1/2DscXDOS`, mapped to DH faces; fixed colours). Darkmoon: 20 EOB2 pieces (webs, hanging skeleton, banners, emblems, windows, ankh…); Waterdeep: 6 EOB1 pieces (webs, gargoyle, spider emblems, plaque), the rest keep DH tapestries. Functional-looking pieces (levers, keyholes, buttons, mouths, niches) and floor furniture are left out. In-game ✔ (`smoke/deco_views.json`: fronts + side panels at depth 1–3). EOB1 BRICK has no deco sheet in the install; `.DEC` ↔ sheet pairs come from the EOB2 `LEVEL*.INF` scripts
- [x] M  Floors and ceilings: EOB backdrops are 176×120 ✔; Menzo flats projected with DH's view geometry ✔. `Ground-0..7` (pits/holes, floor-ramp art) are re-ramped when a floor's palettes change shape (`reramp` Floor-N, auto-inserted; `check_ramps` now fails otherwise; it caught the bug on floors 0/1/6 of the mix)
- [ ] M  Ground sets drawn from the source games (EOB pit art) instead of re-ramped DH pits; MAZE produced no pit records in tests, so a pit fixture is needed first
- [ ] M  Menzo RES6 sound effects: 386 headerless 8-bit PCM records, rate unknown and no names; needs a listening pass (or Menzo script RE) to map them to DH sound slots

**Monsters**
- [x] M  Monster extraction rebuilt on EOB's own frame rectangles (3 layouts, ScummVM `kEoB1/2EncodeMonsterDefsDOS`) with each sheet's layout read from the level scripts (`tools/eob_monster_layouts.json`, 46 sheets, unambiguous); one common scale per monster, bottom-centre in 80×88. Fixes fragmented frames (zombie, skeleton, kobold) and two-figure cuts (clerics, guards, medusa). Roster: 17 EOB1 + 26 EOB2 monsters (75 in pool). EOB1 colours now use the global `EOBPAL.COL` below 0xE0 (level .PALs hold saturated junk there; 4 of Gemini's EOB1 monsters were 8-55% off). Westwood CPS method 3 (RLE) supported
- [x] M  EOB1/2 monsters: per-monster sheet → 6 frames [front, back, side, side, atk, atk]. Fix the palette per monster (`tools/monsters.py` extracts 9 classic monsters with authentic palettes; contact sheet in `pool/monsters/monsters_sheet.png`; integrated into `pool.json`)
- [~] M  EOB3 monsters: extracted (Gemini), **but 30 of 31 are already Dungeon Hack's own monsters** (identical silhouettes; some recoloured, e.g. Troll). Only the Shadow Hound is new. Presets that put EOB3 monsters into other slots just move DH art around
- [x] S  Keep Weird and Wraith2 special (they use wall-ramp colours on purpose): `sprites` refuses them unless `"force": true` (only the stress test preset sets it); no mix roll touches them (checked 199 seeds)
- [x] S  Monster sounds: EOB3 PCM (`STDOOR1`-style, raw u8) → DH monster sound slots (`raw` job); trim/resample if the rate differs (`tools/sounds.py` extracts 116 PCM sounds at 8,000 Hz, generates WAV previews, writes `pool/sounds/catalog.json` and verified `recipe_sounds.json`)

**Items, portraits, UI art**
- [x] M  Item icons and floor items (EOB1/2 ITEMICN/ITEMS1/ITEML1, EOB3 icons) → DH `Icon xx` and item shapes (confirmed DH icon size 17×17; `tools/icons.py` extracts 309 icons, centered/padded to 17×17 with DH base palette; `pool/icons/icons_sheet.png`)
- [x] S  Portraits: EOB1/2 CHARGENA, EOB3 CHARPICS / `Portrait n` → DH 31×32 portrait slots (`tools/portraits.py` extracts 184 portraits from EOB1, EOB2, EOB3; quantized to DH base palette; `pool/portraits/portraits_sheet.png`)
- [ ] —  UI frames and screens: not planned (SOP hard-codes layout); optional full-screen art swaps only

**Audio**
- [x] S  Music: EOB3 and Menzo XMIDI → DH `OPEN.RES` intro/ending slots (Native `xmidi` job in `pipeline.py` supports both EOB3 XMIDI and Menzo RES5 tracks [104 tracks available]; `recipe_music.json` replaces intro/ending themes for Roland, AdLib, and PC Speaker; verified!)
- [x] M  **In-game music** (`game_music` job): DH has no dungeon music by design (memory). Kernel patched to load the music driver on entering the game, play a track per wallset at level setup and loop it from the timer; verified in game (FluidSynth capture: original 0.0, music build 1.0 sounding). Track pool: DH + Menzo + EOB3 tracks vetted in game (`smoke/music_tracks.py`); AdLib setups get DH's own tracks only. Menzo files hold a silent stub sequence first; tracks are repackaged to the song only. Memory: start-up cliff unchanged (444 KB pass / 439 KB fail, same as the original)
- [ ] L  EOB2 `.ADL` (Westwood AdLib) → MIDI converter so EOB2's intro/finale/area music can join the in-game pool (EOB1 has no music files)

**Menzoberranzan (DreamForge)**
- [~] Wall textures exported (64×192); curate a stone/brick subset → `wallset` jobs
- [ ] XL Reverse RES3/RES4 type-06 sprite records (drow etc.). Even then, monsters need re-projection; defer
- [x] S  Extract CD-only `RES9`/`RES10` from `GAME.ISO`; check for portraits/UI art (Extracted and documented: `RES9` contains 469 animation/portrait records; `RES10` contains 274 voice tracks [55 MB])

**Classic EOB themes**
- [x] M  `eob3_mythdrannor` (in `tools/eob_classic.py`): EOB3 Mausoleum/Ruins/Forest walls + doors/stairs (from `recipe_eob3_complete`), the four EOB3 176×120 backdrops as floors, own-floor + hue-matched rules (two-ramp EOB3 sets matched to DH palettes 15–20), Shadow Hound. Door panels now use fixed colours. In-game gate ✔ (4 wallsets)
- [x] M  `tools/eob_classic.py` → `recipe_eob2_darkmoon_classic.json` (DUNG/SILVER/CRIMSON/MEZZ/FOREST) and `recipe_eob1_waterdeep.json` (BLUE/BRICK/DROW/GREEN/XANATHA): hand-drawn walls+frames+stairs, each set's own floor, and kernel rules pairing each wallset with its own floor and its 3 hue-matched palettes (`kernel_rules.match_palettes`, `set_wall_floors`, `set_floor_palettes`, `allow_pairs`). In-game gate ✔ for all 10 wallsets (`smoke_runs/gate_eob*_classic__*`, `gate_eob1_waterdeep__*`); monsters ✔ in game (Darkmoon: EOB2 priestess, Waterdeep: kuo-toa). Darkmoon uses 21 EOB2 monsters. Doors are still DH's (EOB1/2 doors live in CPS, not VMP)
- [x] S  Fix: original `Ice Stairs` stores its depth-3 stairs-down art in panel 12 and leaves panel 13 empty, so Ice stairs-down are **invisible from 3 squares away**. Confirmed in game (`smoke/ice_stairs.json`, fixture with stairs moved to a long corridor); `fix_ice_stairs` swaps them and the stairs appear; depths 2/1 unchanged

**Pool and randomizer**
- [x] S  Test harness hardening: DOSBox windows found by process id (never another run's), Xvfb refuses a display already in use, SIGTERM (`timeout`) runs cleanup so no orphaned DOSBox keeps a build folder mounted; `SMOKE_DISPLAY` lets runs go in parallel on separate displays
- [x] L  **`mix` = the main build** (`tools/mix.py`, `dhplus.py roll/launch --reroll`): the 7 wallset slots (5 external + 2 DH by default), 8 floors, 16 doors, 20 generic decorations and monster slots filled from DH + EOB1 + EOB2 + EOB3 by seed; each external set gets its own floor + hue-matched palettes; kept DH sets keep original rules on the leftover floors; rules validated with `problems()`. 25 random seeds build + verify clean; seed 1's 5 EOB slots pass the in-game gate. `MIX.TXT` lists the roll
- [x] M  `reramp` job, auto-inserted by `pipeline build` for every wallset whose palette rules change: DH art left in a slot (wallset objects 2-12 = arches/windows/pillars, stairs, decorations) is converted to the slot's new single/two-ramp shape. `check_ramps` now fails when a slot's shape changed and its stairs weren't built for the new shape (caught latent bugs in eob3_mythdrannor, eob3_ruins, demo2)
- [x] S  EOB2 doors use the palette of the levels they appear on (`eob_doors.EOB2_DOOR_PAL`; glyph door runes were white under DUNG.PAL)
- [x] S  Every playable recipe carries the fixes (`eob_classic.FIX_JOBS`); Ice Stairs' 48x38 depth-3 panel accepts 48x37 art (EOB stairs now fill it)
- [x] S  `dhplus.py assets` / `tools/pool_assets.py` regenerates all pool art+sound from the user's games; verified from an empty pool: 755/755 files identical
- [x] M  Menzoberranzan walls into the mix (`tools/menzo_walls.py`): 6 sets (blue drow stone, purple city stone, red stone, gold stone, mossy cave, wood planks) from RES4 64x192 strips (4 per 4:3 face, decorated strip pair for variant 1) warped onto every DH panel; floors/ceilings = 64x64 flats projected with DH's fitted view geometry. In-game gate ✔ for all 6 (`pool/smoke/menzo_test.json`)
- [x] L  **8 wallsets per game** (`extra_wallset` job + `kernel_rules.add_wallset`): new Eighth Wallset/Stairs resources, kernel tables appended + loads repointed, rnd(0..7), pairing bits, "current pillar" table extended (would otherwise read code bytes as a resource on wallset 7). Every code resource disassembled to find wallnum users (only kernel + current pillar). In-game ✔ with the kernel pinned to wallset 7: walls, floor, stairs, doors (`smoke_eighth`), pillar at 1/2/3 squares + side (`smoke/pillar_views.json`, fixture `savegame_pillar`). The mix always fills the 8th slot
- [x] L  **16 wallsets and 16 floors per game**: `kernel_rules.widen_masks` turns the three 8-bit pairing masks into 16-bit word tables (each LTBA lookup in "randomize graphics" → BRA to a stub `PUSH; SHTC 1; SHL; LTWA table; BRA back` + `DHW` marker), `add_wallsets`/`add_floors` extend the wallset/stairs/floor/ground tables and rnd() bounds; `extra_wallset` (count) also extends "current pillar" and the decoration object's three per-decoration tables (wallset w uses indices 4w..4w+3; 48+ reuse generic decorations); `extra_floors` adds Floor-N/Ground-N. Every user of wallnum/floornum audited across all 334 code resources. In-game ✔ on wallset 12 (`smoke_w12`: walls, floor 12, stairs, doors, pillar, decoration index 48+). The mix fills all 9 new slots plus 4 of DH's 7 with external sets (13 of 19 sources per game), each on its own floor
- [x] M  **35 doors per game** (`extra_doors` job + `kernel_rules.add_doors`): 16 new door resources, door table appended and its 3 loads repointed, rnd(0..34). Only the kernel and the doors script use doornum (doors: 3/7/14/17 see-through). The mix gives every EOB door (22) a slot, see-through ones in 3/7/14/17. In-game ✔ with doornum pinned to 20 (EOB2 glyph door: views + opening)
- [x] M  Curate `pool/pool.json` per category with source tags and per-asset `palette_rules` presets (All 57 DH monster targets mapped; 40 monster skins tagged with source & theme; self-contained `pool/walls` and `pool/floors`)
- [x] S  `roll` covers panels/doors/stairs/decos/sounds, not just wallset/floor/monsters; keep ramp/rule consistency per roll (`tools/randomizer.py` builds comprehensive 98-job mashup with automated two-ramp rule patching)
- [~] S  Theme presets: "EOB1 sewers", "EOB2 Darkmoon", "EOB3 Myth Drannor", "Mixed" (all build, verify and pass the in-game gate). **Audit:** `eob2_darkmoon` is mislabeled: its walls, doors, stairs and all but one monster are EOB3 (Mausoleum, Feyr, Death Knight…). A real Darkmoon preset needs EOB2 walls (needs the EOB1/2 hand-drawn wall item) + EOB2 monsters

## Phase 3 — *Adding* content (game-logic edits; needs the Phase 1 gate)
- [x] M  Confirm the resource-slot ceiling (`.TBL` 3,081 slots, ~118 free; AESOP/32 `MAX_OBJ_TYPES 2450`) with a test that appends dummy resources (`tools/verify_ceiling.py`: populated all 3,072 slots across `HACK.RES`'s 24 blocks and booted cleanly into dungeon; report in `smoke_runs/slot_ceiling_report.md`)
- [x] L  More wallsets than 7 / more floors than 8: done (16 / 16), see above
- [ ] L  More floors/palettes: `rnd(0..7)` / `rnd(0..20)` constants and mask widths (table1112 is 32-bit, so palettes ≤ 32)
- [ ] XL New monster *types*: new SOP classes (stats, AI, spawn lists `mon_types[75]`). Needs a bytecode assembler for AESOP/16 (check Thirdeye `arc` / `aesop32/DEV` compiler; AESOP/16 vs /32 bytecode compatibility unknown)
- [ ] XL New items / spells from EOB data (`ITEM.DAT`, EOB3 item classes): same assembler dependency
- [x] S  Same-size byte patches catalogue (safe class): constants, tables, masks. Document each with before/after bytes (Documented in `smoke_runs/byte_patch_catalogue.md`: AESOP sample rate, copy protection auto-bypass, wallset pairing masks, SETTINGS.DAT binary flags)

## Phase 4 — Fixes
- [x] M  Collect known DH bugs and triage (`smoke_runs/bug_triage_report.md`; see its evidence audit: Bug 1 confirmed in bytecode, Bug 2 unverified, Bug 3 misattributed)
- [x] S  Bug 2 (automap Print hang) tested in game: "automap output" beeps and returns when `printer_on_line()` is false, and DOSBox-Staging has no parallel port at all (`parallel1` is not a setting), so Print → beep → Exit returns to the dungeon. Not reproducible with our launcher; only a DOSBox with a configured printer port (e.g. GOG's 0.74) could reach the print path. No fix needed
- [x] S  Fix Bug 1: `fix_unlock_shape` adds `C:unlock_resource` to `items.IMPT` (slot 90) and retargets the RCRS operand (daesop confirms). In game: links and runs; 40 pick-up/put-down cycles plus a step are pixel-identical to base (`smoke/item_juggle.json`). `tools/rtd.py` reads/writes AESOP dictionaries byte-exactly (702/702). The leak *reduction* itself is not measured (needs a very long session)
- [x] S  Verify the GOG build's copy-protection behaviour (prompt seen in phase-one/two paths?) and document it. Don't remove it unless the user asks (`validity checker` bytecode verified; `B:auto_on == 1` bypass confirmed; report in `smoke_runs/copy_protection_report.md`)
- [x] S  Infinite-retry hazards: floor/palette loops are validated by `kernel_rules.problems()`. Door loop (`doornum = rnd(0..18)` until `table718[doornum] != 0` and: door 8 not with wallnum 0/3, door 9 only with wallnum 2 or >3, wallnum 2 needs door ∈ {5,6,7,11,18}) is satisfiable for every wallset as long as `table718` and those constants are untouched — no job edits them (door 5 works everywhere). Decoration loops re-roll until two distinct picks from 4 (wallset) / 20 (generic) — always satisfiable. Any future job that edits `table718` or adds wallsets must re-check this
- [x] S  MAZE.EXE hang hunt (`smoke/maze_seeds.py FIRST COUNT --settings HEX`): original MAZE.EXE, 1,000 seeds × 5 setting profiles (fixture, everything maxed incl. 25 levels/zones/water/puzzles, deep + max monsters, classic, pacifist): **0 hangs, 0 errors**, every run ≤ 1.2 s at max cycles. The retry loops Thirdeye flags exist but don't trigger in practice; re-run the tool after any MAZE-related change
- [x] S  Save/Continue crash (user report): base install lacked GOG's savegame template; builds are now seeded and rebuilds keep saves. Verified in game: save to slot → Continue → restore
- [x] S  `smoke/save_restore.py BUILD`: camp → Save Game → slot 1 → quit → menu → Continue → restore, with file + screen checks. PASS on `mix`; `--no-template` negative control FAILS as it should (reproduces the GOG crash)
- [x] S  FRE/GER builds: `dhplus.py --lang fre|ger …` (or `DHPLUS_DH_DIR`). Same 2,953 resources/indices; strings, ~15 UI images and the kernel differ (kernel 18 B shorter). `kernel_rules.locate()` now finds the graphics tables by content (identical offsets in all three, fallback for forced test kernels). Classic themes + fixes verify in FRE/GER; French Waterdeep passes the in-game gate

## Phase 5 — Modernization / Quality of Life
**Zero-risk (DOSBox config only)**
- [x] S  Curated `dosbox-staging` conf: integer/sharp scaling or CRT shader option, aspect correction, `cpu_cycles` tuned, mouse capture, MT-32 / General MIDI via FluidSynth soundfont (DH ships MT32MPU.ADV), SB16 digital sound (`dosbox-dh.conf`)
- [x] S  One-click launcher script: apply chosen recipe → build → launch, with optional skip of the intro (`OPEN.RES` phase) (`launch.py`)
- [x] S  Save-slot backup/restore helper (copy `savegame/` with timestamps; "iron man" deletes saves, so warn) (`tools/savegame.py`)

**Low-risk data patches**
- [x] S  Difficulty/settings presets via `SETTINGS.DAT` (MAZE FREQ_* fields are documented in Thirdeye), e.g. "more treasure", "fewer traps", "classic" (`tools/difficulty.py` provides 5 curated presets and CLI custom generator)
- [x] S  Deterministic "seed of the week" sharing (SEED.TXT format), plus a seed browser that renders level maps from `LEVELS.DAT`/`FEA*.DAT` (`tools/map_renderer.py`)
- [x] M  Automap export to PNG per level (spoiler/strategy aid) (`tools/map_renderer.py`: renders all 10 levels and composite `work/maps/dungeon_atlas.png`)

**Engine-level QoL (larger)**
- [ ] L  Use Thirdeye as an alternative native runtime once its DH renderer is complete: modern OS, no DOSBox, possible higher-res view and smoother movement. Keep DOSBox as the authority for "original behaviour"
- [ ] XL Bytecode-level QoL (keyboard shortcuts for spells/inventory, auto-eat, more save slots): needs the assembler (Phase 3 dependency)

## Phase 6 — Packaging and release
- [x] M  `dhplus` patcher: detect the user's GOG/retail install (hash check against known `HACK.RES` SHA256), back it up, build from a chosen preset, write to a separate folder, verify (`dhplus.py` CLI supporting detect, list, build, launch, difficulty, and roll)
- [x] S  Rollback command (`dhplus.py rollback <build>` safely removes synthesized builds and verifies base game integrity)
- [x] S  Release contents: tools, recipes, presets, docs. **No game files and no patched RES files.** Credit Thirdeye/daesop, John Miles, ScummVM (`DUNGEON_HACK_DEEP_DIVE.md`, `README.md`, `base_games/README.md`, `.gitignore`, `LICENSE`)
- [x] S  User docs: install, presets, known issues, how to roll new mashups (`README.md` and `base_games/README.md`)
- [x] S  Regression suite in CI-like form: `dhplus.py test` automates building and verifying all 14 presets; verified ALL TESTS PASSED ✔

## Suggested order
Phase 1 (gate) → EOB3 walls/stairs/doors (biggest visual payoff, ≈1:1) → EOB1/2 monsters + portraits → audio → EOB1/2 hand-drawn walls → pool/presets → Phase 5 zero-risk QoL + launcher → packaging → (optional) Phase 3 content additions and the assembler question → Menzo sprites last.
