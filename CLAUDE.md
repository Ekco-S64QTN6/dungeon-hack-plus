# CLAUDE.md — Dungeon Hack+ (handoff notes)

Read `PLAN.md` first (format specs, compatibility matrix, palette and pairing rules, the 18-panel role map, the door/stairs model), then `ROADMAP.md` (the checklist; `[~]` items carry audit caveats). This file covers what those don't: environment, tool locations, how to drive the tests, gate status, and gotchas.

## Project layout (moved 2026-10-24 from `~/github/DnDProject/mashup`; the old folder is deleted)
* Repo root is this folder; GitHub remote `origin`. Commit/push only when the user asks.
* `base_games/{dungeon_hack, dungeon_hack_fre, dungeon_hack_ger, eob1 (DE, loose files), eob1_eng (PAK), eob2 (EN), eob3, menzo (+ GAME.ISO)}` are **real copies** (formerly symlinks into the old folder, materialized and verified byte-identical). Git-ignored.
* `reference/aesop_release/`: John Miles' AESOP/32 runtime (`arun/src`), compiler and manuals (`aesop32/`), DAESOP 0.85, forum archives. Git-ignored. The user is fine using anything in it.
* `backup/DH-207eaf4081/`: pristine DH snapshot with SHA256SUMS.
* `config.json` + `tools/paths.py` resolve game paths (no fallbacks to the old folder).
* Code: `pipeline.py` (build/verify/extract/roll), `dhplus.py` (user CLI: detect/list/build/launch/difficulty/roll/test/rollback), `launch.py`, `smoke.py`, `smoke/`, `tools/`.

## Ground rules from the user
* Verification first. Phase-1 gate: in-game screenshot evidence before trusting a pipeline. Gemini (another agent) checked off much of Phases 2–6 without the gate, so **re-verify its check marks before building on them**. The ROADMAP now carries audit notes.
* Never write into `base_games/`. Builds go to `build/NAME/`.
* Don't remove copy protection unless asked. It is only documented in `smoke_runs/byte_patch_catalogue.md`; no recipe applies it.
* Answer reviews with evidence from bytes, code or screenshots; say plainly when something is unverified or was wrong earlier.
* Run Python with `python3 -I`. The session scratchpad does not persist, so keep anything worth keeping in the repo.

## Tools (`third_party/`)
* `dosbox-staging/dosbox` v0.83.0 (Linux release). Headless boot: `SDL_VIDEODRIVER=offscreen`. Screenshots need Xvfb (installed).
* `daesop/daesop` (+ `bytecode.def`), built from Thirdeye (github.com/psi29a/thirdeye @4ec4e6a, GPLv3): `-j RES "<name>" out` disassembles a code resource; `-k RES 3 out` dumps the runtime function table; `-create_tbl`.
* `disasm/`: saved disassemblies (`kernel`, `dungeon`, `doors`, `current door/stairs/arch`, `lowlevel`) and `thirdeye_dh.cpp` (draw_walls geometry tables).

## Facts not in PLAN.md
* Code-resource tables are addressed by payload byte offset (daesop `table978` = kernel offset 978).
* Kernel long tables: `718` 19 doors (0 = rejected), `794` Floor-0..7, `826` Ground-0..7, `858` 16 levers, `922` 7 stairsets, `950` 7 wallsets, `978` 21 palettes. Per-level choices live in kernel statics `wallnum/floornum/wallpal/floorpal/doornum/levernum[25]`, `wdeco[100]`.
* "randomize graphics" runs at new-game start in phase-two and is **time-seeded**. Comparable screenshots need the test-only `force_graphics` job. Wall decorations (`wdeco`) are *not* forced and still vary run to run.
* Report attributes: 4 = art resource, 3101 = frame base (stairs down 0 / up 18), 3002 = door stages + 1 (= 4, so 3 stages), 5/7 = automap glyph/char.
* FEA records (8 B): 0 = party start, 1 = door (byte 3: 0x05 N/S, 0x0a E/W), 2 = door frame button, 3 = illusionary wall, 4 = stairs up, 5 = stairs down, 12 = level creature, 16 = level decoration. `LEVELS.DAT` = u32 seed + 10 × 32×32 (0/1 wall variant, 0xFF open).
* **Bug 1 confirmed:** `items` "unlock shape" calls `C:lock_resource` (runtime 620) exactly like "lock shape"; `unlock_resource` (624) is never imported.
* **DH Marble wallset = EOB3 Marble walls** (pixel-identical in game). Foil shares EOB3 Marble silhouettes; Stone and Ice share most EOB3 Forest silhouettes. DH Marble stairs reuse EOB3 silhouettes but are repainted.
* EOB3 palette regions: fixed 0x00–0xAF, PAL_WALLS 0xB0–0xBF. `Fixed palette` (#335), `Marble/Forest/Mausoleum/Ruins palette`.

## Smoke testing (works end to end)
* Fixtures: `fixtures/savegame` (character "Rhenovia Swiftthorn", dungeon seed `000E6986`, post-MAZE state, no save slot) and `fixtures/savegame_nomon` (the same, level creatures removed). `aesop hack phase-two` lands in the dungeon in ~4 s, with no copy-protection prompt on this path.
* Level-1 landmarks: start (23,2) facing N; stairs up (23,3) right behind; door (25,6) N/S; stairs down (11,3) only reachable through doors.
* **DH drops key presses**, even held ones. `smoke/walker.py` is closed-loop: compass template-match (`smoke/compass_[NESW].png`, crop rows 328–366 × cols 450–492) after every key, repeat turns until confirmed, verify steps by a >5% view change. Keys: `KP_8` forward, `KP_7`/`KP_9` turn.
* Screenshot geometry: 640×480 = x×2, y×2.4. View crop (276,31)–(628,320). The scaler bleeds about 2 px across the view edge. The parchment automap (game 52–110 × 140–190) depends on the walk path, so the gate masks it.
* `smoke/gate.py [--base B] [PLAN] BUILD…` runs the walk on base twice (noise estimate) and on each build, then writes `smoke_runs/gate[_LABEL]/gate_report.{md,png}`. `smoke/variants.py PRESET` builds forced variants per wallset the preset reskins (palette chosen from the *built* rules) and prints the pairs.
* `smoke.py boot` is a weak oracle (95 zeroed `.TBL` entries still reach the title).

## Gate status (end of session)
* **Phase-1 gate closed.** In-game gate passed for demo2, demo3, stress, eob3_complete × {marble, wood, rock, stone}, eob1_sewers, eob2_darkmoon and mixed (`smoke_runs/gate*/gate_report.{md,png}`): walks match base, 0 px outside-view change, visuals reviewed.
* ✔ Door stages (`smoke/door_open.json`): click the door face at depth 1 (game 226,73); needs `mouse_capture=seamless` (set in `smoke.py`); zero-delay burst.
* ✔ Stairs down (`smoke/stairs_down.json`, `fixtures/savegame_nomon_stairsdown`): FEA type-0 record = party start; edit it to place the party anywhere.
* ✔ Monster sprites in game (`smoke/monsters.json`, fixture with monsters, stress build): the approaching monster renders as the EOB1 kobold, scale and anchoring correct.
* ✔ PCM rate 8,000 Hz measured from a DOSBox audio capture (`smoke/audio_rate.json` + Ctrl+F6 hotkey; `smoke_runs/audio_rate_capture.md`). Use duration, not sample correlation.
* `walker.py` actions: `goto` (+`through_doors`), `face`, `forward`, `click`, `hotkey`, `burst`, `wait`, `shot`.
* Warp `wallset` jobs now default to frames `0-35` (wall object 0 + door frame object 1); presets and the randomizer were updated.
* ✔ Classic themes `eob2_darkmoon_classic` / `eob1_waterdeep`: all 10 wallsets gated, monsters checked in game.
* ✔ Fixes (`pool/recipe_fixes.json`): Bug 1 links and runs (item juggle test); Ice Stairs depth-3 fix confirmed in game.
* Open findings: `eob2_darkmoon` (Gemini's) is mostly EOB3 art, so prefer `eob2_darkmoon_classic`; DH Marble wallset = EOB3 Marble walls (Marble→Marble is a no-op); memory-margin test covers start-up only; EOB1/2 doors not ported yet.
* `dhplus.py test` covers 17 presets (incl. the classic themes and `fixes`); all pass.
* Not yet gated individually: eob3_marble/mausoleum/ruins/forest/temple (subsets of eob3_complete), eob3_decorations (needs a walk past a wall deco), sounds/music (non-visual).

## New this session (Claude, after the move)
* `westwood.VMP_POS` / `DH_PANEL` / `dh_panel()`: EOB view positions (ScummVM `_vmpOffsetsDefault`) mapped 1:1 to DH faces, with crop offsets from both engines' y positions. Wall types are consistent across sets: wt0/wt1 plain variants, wt2 door frame, wt3 stairs up, wt4 stairs down, wt5 decorated (BRICK/XANATHA have no stairs; FOREST has only wt0/wt1).
* `vmp_walls` job (hand-drawn EOB1/2 walls, frames, stairs; `frame_set`/`stairs_set` borrow from a sibling set; one brightness stretch per set keeps EOB depth shading).
* `tools/eob_classic.py` → `recipe_eob2_darkmoon_classic.json` (+21 EOB2 monsters mapped to DH slots by identity) and `recipe_eob1_waterdeep.json`. Each wallset is paired with its own floor and 3 hue-matched palettes via `palette_rules` keys `wall_palettes`, `wall_floors`, `floor_palettes`, `allow_pairs` (all validated by `kernel_rules.problems`).
* `tools/monsters.py` now extracts the EOB2 roster (21 of 22; WASP sheet layout differs; `eob2_guard1` back/side frames are bad, so it is excluded from themes). The slicer drops sprites < 20% of the largest box. `pool/monsters/*` frames are already in DH order.
* `tools/rtd.py`: AESOP dictionary codec (hash = byte sum mod H; chains; end-of-dict u16 0), byte-exact on all 702 IMPT/EXPT + name tables.
* Fix jobs: `fix_unlock_shape` (Bug 1; daesop confirms, in-game check pending) and `fix_ice_stairs` (original Ice Stairs has the depth-3 stairs-down art in panel 12 and an empty panel 13; swap; `verify` accepts declared reorders via `layout_fixes` in MASHUP_BUILD.json). In-game test staged: `smoke/ice_stairs.json` + `fixtures/savegame_ice` (start (15,1), stairs down moved to (12,1)) + builds `smokebase_ice` / `smoke_fix_ice`.
* `smoke.py` sets `mouse_capture=seamless` and `capture_dir=<run>/capture` (Ctrl+F6 audio capture via the walker's `hotkey` action).
* Doors: `eob_door` job + `tools/eob_doors.py` (`door_spec(kind)`; kinds iron/grate/slab/web/mouth/eye (EOB1) and e2_* (EOB2)). DH doors only use front panels 8/16/13 per stage; doorway box comes from the target's closed stage. `colors: 'fixed'` (default) vs `'ramp'`. `SEE_THROUGH` lists level-colour indices that are background (iron/grate floor 0xF0+, web 236-238).
* EOB1 palette rule: `westwood.eob1_palette(dir, level_pal)` = EOBPAL.COL below 0xE0 + the level band. Never use a level .PAL alone for EOB1 sprites. EOB2 level palettes agree on the fixed range.
* Monsters: `tools/monsters.py` cuts EOB's exact frame rectangles (`EOB_LAYOUTS`) with layouts from `tools/eob_monster_layouts.json` (parsed from EOB2 INF `0xEC, layout, slot, name` and EOB1 ELO `layout, name`). Frames are pre-composed 80x88 (DH order); `job_sprites` uses 80x88 images as-is.
* Decorations: `vmp_deco` job; `pipeline.WALL_DECOS` maps each wallset to its decoration resources (from the `decoration` object's `table14` at offset 14; indices 28+ are generic). `force_graphics` accepts `wall_deco` (test only) to point every decoration at one resource. Fixture `savegame_deco` starts at (14,11) facing the decorated south face of (14,10). FEA type 16 byte 3 = decorated faces bitmask (N1 E2 S4 W8).
* Languages: `dhplus.py --lang fre|ger` / `DHPLUS_DH_DIR=base_games/dungeon_hack_fre`. Kernel tables are located by content (`kernel_rules.locate`); never hard-code kernel offsets again.
* DH's bestiary is EOB3's: 30/31 EOB3 monsters match DH monsters by silhouette (only Shadow Hound is new). DH Marble wallset = EOB3 Marble walls. Real "new" EOB3 content = Mausoleum/Ruins/Forest walls, doors, stairs, backdrops.
* `panels` jobs targeting `Door-*` default to fixed colours (doors show on all wallsets); others use the target's ramp profile.
* EOB decorations: `.DEC` (EOB2) / `.DAT` (EOB1) = u16 n, n × 52 B (shape[10], next, flags, x[10], y[10]), u16 nrects, rects (x/8,y,w/8,h) into the sheet .CPS. `next == 0` ends a chain (dec 0 is usually a floor pit — chaining into it was a bug). EOB2 sheets: BROWN1-3 (pal DUNG), AZURE1-2, MEZZ1-2, SILVER1-2, CRIMSON/2, FOREST; one `.DEC` serves several sheets, so most indices only make sense with one of them (check contact sheets). Plan `smoke/deco_views.json` + `force_graphics.wall_deco` gates any decoration slot.
* The **mix** (`tools/mix.py`) is what the user plays; single-game presets are stepping stones. Design rule: fill DH's fixed slots from all games, re-roll per new game. Anything new (Menzo walls, more doors...) should land in the mix pool.
* Pool assets are not in git: `dhplus.py assets` regenerates them. Recipes/code only in the repo; `third_party/`, `work/`, `smoke/*.png`, `pool/**` (except json) are ignored.
* Wallset slots hold more than walls: objects 2-12 (arches, windows, pillars...), stairs and 4 decos stay DH art unless replaced, so changing a slot's ramp shape needs `reramp` (auto-inserted).
* **8th wallset** (`extra_wallset` job, `kernel_rules.add_wallset`): code tables are addressed by absolute u16 operands (`LTDA "L:table950"` = byte 950 of the kernel) and PRG_HDR has no length, so 8-entry copies of table950/table922 are appended to the kernel and the two loads in "setup level graphics" repointed; `rnd(0, 7-1)` → 8 in "randomize graphics" (pattern `kernel_rules.RND_WALL`). Masks are 8-bit (bit 7 free). Door rules compare wallnum to 0/2/3 only; wdeco for wallnum 7 = indices 28-31 = generic Wall Deco 29-32. Only other per-wallset table: "current pillar" table14 (7 longs; appended 8-entry copy, LTDA repointed). All 334 code resources disassembled into `work/disasm/` (`daesop -j`): only kernel + current pillar use wallnum / "wallset index". New resources go in free directory slots (2963+, 109 free) with names added via `rtd`; `verify` checks them against the resource they were copied from (`MASHUP_BUILD.json` "added"). Test pin: `force_graphics` `"wallnum": 7`.
* Pillars are FEA type 25 (dungeon "create thing" → current pillar); fixture level 1 has one at (5,10). Walker routes around them.
* Menzo walls (`tools/menzo_walls.py`): RES4 type-05 64x192 strips, four make a 4:3 DH face; floors are 64x64 flats projected with DH's fitted view geometry (faces at z = n + 0.59, horizon y 39.2).
* **In-game music** (`game_music` job, `tools/game_music.py`): the original has none on purpose (SOUND32.C: `unload_music` "to conserve heap resources during game"). The runtime calls exist: `load_music()` (driver from SOUND.CFG + fixed sequence buffer + state + timbre cache), `play_sequence(LA, AD, PC)` (resource per device; reads it into the buffer: tracks must be ≤ 8,112 B, DH's own largest), `sequence_playing()`. Kernel imports added at 312/316/320 (`add_runtime_import`), stubs hooked into "enter game" (load), "setup level graphics" (play the level's track) and "timer tick" (replay when finished); per-wallset LA/AD track tables appended. `play_sequence` **aborts the game** if a track needs a timbre the library lacks: AdLib versions must be DH's own (STDPATCH.AD = 222 B, DH's 6 timbres); MT-32/GM candidates are vetted in game by `smoke/music_tracks.py` → `tools/music_tracks.json`. Verify music with `smoke/music_check.py` (FluidSynth + Ctrl+F6 audio capture; original dungeon = 0.0 sounding).
* **Bytecode writing:** `AIS n` (RT.ASM do_AIS) shifts the top value and ADDS it into the stack entry below, popping: an array lookup is `SHTC 0; PUSH; <index>; AIS 2; LTDA table` (the pushed 0 is the base). Forgetting the base corrupts whatever was pushed before. Calls: `RCRS f; PUSH; arg1; PUSH; ...; last arg; CALL n` (`RCRS f; CALL 0` for none). Branch operands are absolute u16 offsets; appended stubs work.
* EOB2 music is Westwood AdLib `.ADL` (INTRO, FINALE1/2, per-area sets), not XMIDI; EOB1 ships none as files. Needs an ADL→MIDI converter before it can join the music pool.
* EOB monster sprites: transparency is colour INDEX 0 only (EOB1 indices 12/254 are opaque black).
* **16 wallsets / 16 floors**: `widen_masks` (16-bit masks via LTWA stubs, located later by `DHW`+id markers), `add_wallsets`, `add_floors`, `extended_rules` (what the jobs leave, for roll validation). Wallset names: `kernel_rules.WALLSETS` = DH's 7 + `Eighth` + `W08`..`W15` ("<name> Wallset/Stairs"); floors `Floor-8..15` / `Ground-8..15`. Opcodes: AIS 0x27, LTBA 0x28, LTWA 0x29, LTDA 0x2a; `x PUSH y SHL` = x << y. The decoration object has three per-decoration tables (table14 art, table206 text, table398 flags) indexed after SEND "wall deco index". Extra door slots (`Extra Door NN`) must be treated like `Door-*` (fixed colours) everywhere.
* Wallset objects (painted in game): 2 panel 0 = slot 36 doorway post; 11 = arch face; 4 = window grille inside object 1 (door frame).

## Gotchas
* **Save/Continue need GOG's savegame template.** GOG ships `SAVEGAME\SAVEGAME.DIR` (12 × `<empty>\r\n`), `VISIBLE.DAT`, `SETSAVE.DAT`, `HISCORE.DEF/.DAT`, `NEWSCORE.EXE` outside the game folder (support "save" folder, overlaid as `cloud_saves`). Without `SAVEGAME.DIR`, Save Game and Continue abort with "Couldn't open savegame directory for reading", HACK.BAT exits and DOSBox closes (looks like a crash). `paths.seed_savegame()` adds them to every build (pipeline build + launch.py); `paths.get_dh_save_template()` finds them, language-matched: config `dh_save_template` (str or {eng,fre,ger}), `<dh>/SAVEGAME` (Steam Archives layout; base_games FRE/GER have it), `<dh>/cloud_saves/SAVEGAME`, Steam `Collection Three/games/Dungeon Hack-<LANG>/GAME/HACK/SAVEGAME` (libraryfolders.vdf + /mnt/*/SteamLibrary), Heroic `gog-support/*/*/save/SAVEGAME` (ENG only). FRE/GER templates are localized (`<vide>`, different SAVEGAME.DIR/SETSAVE.DAT); ENG Steam = GOG byte-for-byte. Steam game files are byte-identical to base_games (all three languages). Rebuilds keep an existing `build/<name>/savegame/`. Slots are `SAVE_NN.BIN` + `ITEMS_NN.BIN`. Our smoke fixtures never had the template, which is why no test caught it.
* Don't infer sub-bitmap layouts from dimensions alone; confirm against `draw_walls` tables or script code.
* Preview with a palette the kernel rules actually pair with the target (two-ramp Stone hid a bug once).
* A plain screenshot diff is meaningless without `force_graphics` (time-seeded randomization).
* `pipeline.py build` compacts by default (`"compact": false` to bisect). `HACK.TBL` stays at 12,324 B and is byte-identical to `daesop -create_tbl`.
