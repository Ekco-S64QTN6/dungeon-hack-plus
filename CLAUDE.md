# CLAUDE.md: Dungeon Hack+ handoff notes

Dungeon Hack+ patches the 1993 roguelike Dungeon Hack (AESOP/16 engine) so that each level can be built
from the art, monsters, music and sound of its sister games: Eye of the Beholder 1/2 (Westwood),
EOB3 (AESOP/32) and Menzoberranzan (DreamForge), plus fixes and engine extensions. **The product
is the `mix` preset** (`tools/mix.py`): one build whose graphics slots are filled from all games.
Single-game presets are stepping stones and tests.

Read order: this file, then `ROADMAP.md` (checklist with audit notes), then `PLAN.md` (the original
design: formats, compatibility matrix, palette/pairing model; partly historical, see its header).

## Ground rules from the user
* **Verification first.** Nothing counts as done without in-game evidence (screenshots, audio capture,
  save files). Gemini (another agent) checked off roadmap items without that; re-verify before building on them.
* **Commit and push verified work** to the public repo github.com/Ekco-S64QTN6/dungeon-hack-plus
  (branch main) at natural checkpoints. Run `python3 -I dhplus.py test` first and check
  `git status --short` for game data (see "Repository" below). Never change repo settings the user
  didn't ask for (it was once made private unasked; the user was very unhappy).
* Never write into `base_games/` (the user's game copies). Builds go to `build/<name>/`.
* Don't remove copy protection unless asked (only documented in `smoke_runs/byte_patch_catalogue.md`).
* Answer with evidence from bytes, code or screenshots; say plainly when something is unverified or was wrong.
* Run Python with `python3 -I`. The session scratchpad does not persist; keep anything useful in the repo.

## Project layout
* `base_games/`: `dungeon_hack`, `dungeon_hack_fre`, `dungeon_hack_ger`, `eob1` (DE, loose files),
  `eob1_eng` (PAK), `eob2` (EN), `eob3`, `menzo` (+ `GAME.ISO`). Real copies, git-ignored. Steam's
  Archives collection is byte-identical for DH ENG/FRE/GER.
  `paths.get_game_dir` honours `DHPLUS_<GAME>_DIR`; a packed EOB1 (`EOBDATA*.PAK`, the English
  release) is unpacked to `work/eob1_unpacked/` (graphics identical to DE; English names some sheets
  `<NAME>1.CPS`). A pool regenerated from `eob1_eng` is byte-identical to the one in use (icons aside).
* `pipeline.py`: build / verify / extract and every job type. `dhplus.py`: user CLI (detect, assets,
  list, build, roll, launch [--reroll], difficulty, rollback, test, `--lang fre|ger`). `launch.py`:
  DOSBox-Staging launcher (`dosbox-dh.conf`). `smoke.py` + `smoke/`: in-game test harness.
* `tools/`: format codecs and builders (see "Code map"). `pool/`: recipes (`*.json`, tracked) and
  game-derived assets (git-ignored; `dhplus.py assets` regenerates them from the user's games).
* `reference/aesop_release/`: AESOP/32 runtime source (`arun/src`, `arun/asm/RT.ASM` = interpreter),
  compiler, manuals, DAESOP 0.85 (git-ignored; usable freely). `backup/DH-207eaf4081/`: pristine DH.
* `work/`: local scratch (Menzo extraction, `work/disasm/` = all 334 HACK.RES code resources and
  `work/disasm_open/` = OPEN.RES, disassembled with `daesop -j`). Git-ignored.
* `fixtures/`: test save states (git-ignored game data). `user_*` are the user's own saves from debugging.

## Repository (public)
Code, recipes and docs only. Ignored: `base_games/`, `build/`, `pool/**` except json, `third_party/`,
`work/`, `fixtures/`, `reference/`, `smoke/*.png`, `smoke_runs/*` except `.md`, game file extensions.

## Code map
* `tools/aesop.py`: RES container (`ResFile`: replace, compact, TBL), old shape codec, VFX "1.10", palettes.
  `tools/rtd.py`: AESOP dictionaries (IMPT/EXPT, name table entry 0), byte-exact.
* `tools/kernel_rules.py`: kernel graphics tables. `locate` (by content and by the LTDA operands that
  read them), `read`/`write`/`problems` (unsatisfiable rules hang new-game creation), `match_palettes`,
  `force` (tests), and the engine extensions `add_wallsets`, `add_floors`, `add_doors`, `widen_masks`,
  `extended_rules`. `tools/game_music.py`: in-game music kernel patch.
* `tools/westwood.py` (LCW/RLE3/CPS/PAK/VCN/VMP, view positions), `tools/eob_doors.py`, `tools/eob_decos.py`,
  `tools/monsters.py` (EOB1/2 sprites), `tools/eob3_monsters.py`, `tools/menzo_walls.py`, `tools/dreamforge.py`
  (Menzo RES), `tools/normalize.py` (ramp posterization, warp), `tools/paths.py` (game paths, savegame template).
* Recipe builders: `tools/mix.py` (the mix), `tools/eob_classic.py` (EOB1/EOB2/EOB3 themes),
  `tools/pool_assets.py` (`dhplus.py assets`). Older Gemini tools (`randomizer.py`, `eob3_mapping.py`,
  `icons.py`, `portraits.py`, `sounds.py`, ...) produced some pool data; `pipeline.py roll` is the old
  pool randomizer, superseded by `dhplus.py roll` (= the mix).

## How a build works (`pipeline.py build RECIPE NAME`)
* Copies the DH install to `build/NAME/`, keeps an existing `savegame/` (rebuilds never delete saves),
  seeds GOG's savegame template (see Gotchas), runs the jobs, compacts, rewrites `.TBL`, verifies.
* Job order: engine extensions (`extra_doors`, `extra_wallset`, `extra_floors`), then `palette_rules`,
  then auto-inserted `reramp` jobs (every wallset/floor whose rules change), then recipe order;
  `force_graphics` (tests only) last.
* `MASHUP_BUILD.json`: recipe, `ramp_shapes` (what each piece was posterized for), `layout_fixes`,
  `added` (new resources: name → the resource it was copied from, or null for new data).
* `verify`: TBL consistency, frame layouts (added resources against their source), and `check_ramps`:
  fails if a wallset's palettes mix single/two-ramp shapes, if a reskinned wallset doesn't match its
  palettes, or if a slot's or floor's shape changed without its stairs / ground set re-ramped.

## The mix (`tools/mix.py`, `dhplus.py roll [SEED]`, `launch mix --reroll`)
* Engine: 16 wallsets, 16 floors, 35 doors (originals: 7, 8, 19). The 9 new wallset slots plus 4 of
  DH's 7 take external sets (13 of 19: EOB1 ×5, EOB2 ×5, EOB3 Mausoleum/Ruins/Forest, Menzo ×6),
  each on its own floor with hue-matched palettes; the other 3 slots keep DH's art.
* Per external set: walls + door frame (+ slot 36 post, arch), stairs (own art, or `stairs_from` a
  matching DH style), window/shelf/pillars (`furniture_from` the DH style in `mix.FURNITURE_DONOR`),
  decorations (own, else cosmetic EOB ones in DH's slots), floor backdrop.
* Doors: every EOB door (22) gets a slot; see-through ones in DH's see-through numbers 3/7/14/17.
* Generic decorations 29-48, monsters (~half of the slots with an EOB counterpart), portraits (~half,
  same sex group), in-game music per wallset (58 vetted tracks), EOB3 sounds and intro music.
* `MIX.TXT` in the build lists the roll. Any new asset type should land in the mix.

## Engine facts
* Code-resource tables are addressed by absolute u16 operands into the resource (`LTDA "L:table950"`
  = byte 950 of the kernel). PRG_HDR (static size, imports, exports, parent) has no length, so tables
  and code can be appended and loads repointed. ENG/FRE/GER kernels keep the tables at the same offsets.
* Kernel tables: 718 doors (19, entry 1 = 0 never picked), 794 Floor-N, 826 Ground-N, 858 levers (16),
  922 stairsets, 950 wallsets, 978 palettes (21), masks 1062 floor→wallsets, 1070 wall palette→wallsets,
  1091 floor palette→floors, 1112 wall palette→floor palettes (32-bit). Per-level picks: statics
  `wallnum/floornum/wallpal/floorpal/doornum/levernum[25]`, `wdeco[100]`.
* "randomize graphics" runs at new-game start (time-seeded): wallnum = rnd, floor until mask, floor
  palette until mask, wall palette until masks; door until table718 != 0 plus rules on doornum 5-9/11/18
  vs wallnum 0/2/3; decorations wdeco = wallnum·4 + rnd(0..3) and 28 + rnd(0..19). The retry loops never
  give up, so `kernel_rules.problems()` must pass for every rule set.
* Who uses what (audited across all code resources): wallnum → kernel + "current pillar" (per-wallset
  text for the second pillar state); floornum → kernel only; doornum → kernel + doors ("blocks view": 3/7/14/17 see-through);
  decoration index → the decoration object's table14 (art), table206 (text), table398 (flags).
* FEA records (8 B): 0 party start (edit to place the party), 1 door (byte 3: 0x05 N/S, 0x0a E/W),
  2 door-frame button, 3 illusionary wall, 4/5 stairs up/down, 6/7 buttons, 8 lever, 9-11 locks,
  12 creature, 14/15 object/spell shooter, 16 decoration (byte 3 = faces N1 E2 S4 W8), 17 solid wall,
  18 spikes, 19 floor pit (`13 x y 0f dx dy dlevel 03`), 20 ceiling pit, 21 teleporter, 22 spinner,
  23 arch, 24 window, 25 pillar, 26 shelf, 27 healer, 28 floor deco, 29/30 special window/pillar.
  `LEVELS.DAT` = u32 seed + n × 32×32 (0xFF open).
* Wallset resource = 236 frames; a feature draws base + view position (0-17, 18 = standing in it), base
  from its script (report 3101 or a constant; `pipeline.py` comment above `ARCH_FRAMES`): 0-17 walls
  (variant 0/1 side panels), 18-35 door frame, 36 doorway jamb post, 37-72 door-frame button off/on,
  73-90 window panel (over the door frame), 91-108 shelf, 109-144 hidden button off/on, 145-162 pillar,
  163-198 wall button off/on, 199-216 arch, 217 arch post (standing in it), 218-235 pillar state 2
  (rubble/table/crate/fountain; `current pillar` rolls the state; its table14 is description text).
  Canvases are identical in all 7 DH sets (except 80). Stairs = [down 0-17][up 18-35].
  Doors = 3 stages × 18 panels, only front panels 8/16/13 used; stage = maxstate − state.
* Report attributes: 4 art resource, 3101 frame base, 3002 door stages + 1, 5/7 automap glyph/char.
* Original DH has no dungeon music on purpose (SOUND32.C `unload_music` "to conserve heap resources").
* Bug 1 (fixed by `fix_unlock_shape`): `items` "unlock shape" called `C:lock_resource`.
  Ice Stairs stores its depth-3 stairs-down art in panel 12 (fixed by `fix_ice_stairs`; its panel 13 is
  48×38 where others are 48×37: importers pad/crop one row).

## Engine extensions (all verified in game)
* `extra_wallset` (count): new `<name> Wallset/Stairs` resources (names from `kernel_rules.WALLSETS`:
  DH's 7, `Eighth`, `W08`..`W15`), tables extended, rnd bound raised, pairing bits copied from the
  source set, pillar table and (past 12) the decoration tables extended. Past 8 wallsets/floors the
  masks are widened (`widen_masks`: each LTBA lookup → BRA to `PUSH; SHTC 1; SHL; LTWA word_table;
  BRA back`, followed by an unexecuted `DHW`+id+offset marker that `read()` uses).
* `extra_floors` (Floor-8.., Ground-8..), `extra_doors` (`Extra Door NN`, door table + 3 loads + rnd).
* `game_music`: imports `C:load_music/play_sequence/sequence_playing` (offsets 312/316/320 via
  `add_runtime_import`), stubs in "enter game", "setup level graphics", "timer tick"; per-wallset
  track tables. Tracks ≤ 8,112 B (fixed sequence buffer); Menzo files are repackaged to their song
  sequence (sequence 0 is a silent stub). `play_sequence` aborts the game on a missing timbre:
  AdLib versions are always DH's own; MT-32/GM tracks are vetted (`tools/music_tracks.json`).
* Test pins in `force_graphics`: `"wallnum": n`, `"doornum": n` (pin the real rnd path), `wall_deco`.
* **Resource slots:** 3,072 directory slots; the mix uses 3,032 (40 free). New resources take free
  slots (`_add_copies`); plan any further extension against that limit.
* **Writing bytecode** (opcodes: AIS 0x27, LTBA 0x28, LTWA 0x29, LTDA 0x2a, BRF 0x01, BRA 0x02,
  RCRS 0x20, CALL 0x21, PUSH 0x04, SHTC 0x1d, INTC 0x1e, NOT 0x06, SHL 0x13):
  `AIS n` shifts the top value and ADDS it into the entry below (popping), so a lookup is
  `SHTC 0; PUSH; <index>; AIS 2; LTDA table`; forgetting the base corrupts what was pushed before
  (this hung the first music patch). Calls: `RCRS f; PUSH; arg; PUSH; ...; last arg; CALL n`.
  `x PUSH y SHL` = x << y. Branch operands are absolute; a hook overwrites a 3-byte instruction with
  BRA to an appended stub that re-executes it and branches back.

## Asset facts
* Palettes: 0-223 fixed; floor ramp 224-239; wall ramp 240-255 (15 steps + accent). Palettes 15-20
  are two-ramp. Art is posterized against the real palettes the rules pair with it
  (`normalize.to_ramp_target`); doors, decorations and sprites use fixed colours (they show anywhere).
* EOB1 colours: `westwood.eob1_palette(dir, level_pal)` (EOBPAL.COL below 0xE0 + the level band).
  EOB doors/decorations take the palette of the levels they belong to (`EOB1_DOOR_PAL`, `EOB2_DOOR_PAL`).
* EOB walls: `vmp_walls` copies hand-drawn views 1:1 (ScummVM `_vmpOffsetsDefault` → DH faces).
  Wall types: wt0/wt1 plain, wt2 frame, wt3/wt4 stairs up/down, wt5 decorated.
* EOB decorations: `.DEC`/`.DAT` = u16 n, n × 52 B (shape[10], next, flags, x[10], y[10]), u16 nrects,
  rects into the sheet .CPS; `next == 0` ends a chain; placed with ScummVM's tables (`eob_decos.py`).
* EOB monsters: exact frame rectangles (`tools/eob_monster_layouts.json`); transparency = index 0 only.
  30 of 31 EOB3 monsters and most EOB3 portraits are DH's own art; DH Marble walls = EOB3 Marble.
* Menzo: walls = RES4 64×192 strips (4 per DH face), floors = 64×64 flats projected with DH's view
  geometry (faces at z = n + 0.59, horizon y 39.2); RES5 = XMIDI; RES6 = 386 unnamed PCM (not used).
* EOB2 music is Westwood `.ADL` (AdLib programs; only INTRO/FINALE1/FINALE2 are music); EOB1 ships none.
* Portraits: DH's chooser gives men 0-31, women 29-44 (29-31 shared helmeted/hooded).
* Portraits/icons are quantized to the colours DH's own monster sprites use (`normalize.dh_sprite_indices`).

## Testing
* DOSBox-Staging 0.83 (`third_party/dosbox-staging`), Xvfb, xdotool. Each harness starts its own Xvfb
  (`smoke.start_xvfb`, refuses a busy display), finds its DOSBox window by pid, and kills its
  processes on exit or SIGTERM. `SMOKE_DISPLAY=:78` runs a second harness in parallel.
* `smoke/walker.py PLAN BUILD...`: closed loop (DH drops key presses): compass template match after
  every turn, steps verified by view change; routes around doors/pillars/pits. Actions: goto
  (+through_doors), face, forward, click, hotkey, burst, wait, shot. 640×480 shots; view crop
  (276,31)-(628,320).
* `smoke/gate.py [--base B] [PLAN] BUILD...` (screenshots + diff report), `smoke/variants.py PRESET
  ["W12 Wallset" ...]` (forced per-wallset variants, base = same engine with DH art). The mechanical
  diff is weak when only part of the graphics is pinned: review `gate_report.png`.
* Plans: gate_walk (start, stairs, door at 2 and 1), door_open, stairs_down, ice_stairs, monsters,
  deco_views, pillar_views, doorway (slot 36), arch_window, pit_views, item_juggle, audio_rate.
* Fixtures: `savegame` (Rhenovia, seed 000E6986), `savegame_nomon` (no creatures; start (23,2) N,
  stairs up behind, door (25,6)); variants with the start moved or a record added: `_stairsdown`,
  `_ice`, `_deco` (14,11), `_pillar` (5,11), `_archwin` (27,11), `_pit` (pit at (23,1)).
* `smoke/save_restore.py BUILD [--no-template]`, `smoke/music_check.py BUILD...` (FluidSynth +
  Ctrl+F6 audio capture; sounding fraction), `smoke/music_tracks.py SPEC|@FILE` (track vetting),
  `smoke/maze_seeds.py` (MAZE hang hunt: 1,000 seeds, none hang), `smoke/mem_margin.py` (start-up cliff).
* `dhplus.py test`: builds and verifies all 19 presets.

## Gotchas
* **Save/Continue need GOG's savegame template** (`SAVEGAME.DIR` etc., shipped outside the game folder).
  Without it the game aborts ("Couldn't open savegame directory for reading") and DOSBox closes.
  `paths.seed_savegame()` adds it to every build; `paths.get_dh_save_template()` finds it
  (language-matched: Steam keeps it in the game folder, GOG/Heroic in a support folder).
* A screenshot diff is meaningless without `force_graphics` (time-seeded picks).
* Preview with a palette the rules actually pair with the art (two-ramp Stone hid a bug once).
* Don't infer layouts from dimensions; confirm by script code or by painting in game.
* `pkill -f <pattern>` matches the shell running it; kill by pid.
* Never splice code by slicing between two function names without checking their order (it once
  duplicated a block of `pipeline.py`).
* `pipeline.py build` compacts by default (`"compact": false` to bisect).
