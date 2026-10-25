# Dungeon Hack+

A patcher for the 1993 roguelike **Dungeon Hack** that rebuilds its graphics, monsters, sound and
music from its sister games: *Eye of the Beholder* I, II and III and *Menzoberranzan*.
Start a new game and every dungeon level can be built from a different game's art: EOB1's
Waterdeep sewers, EOB2's Darkmoon halls, EOB3's Myth Drannor ruins, or Dungeon Hack's own
walls, with doors, decorations and monsters drawn from all of them.

This repository contains **code and recipes only**. You supply your own copies of the games, and
everything is built from them into a separate `build/` folder; your installs are never modified.

---

## How the mix works

Dungeon Hack picks a level's look at new-game start from fixed slots: 7 wallsets (each with
its own stairs, door frame and decorations), 8 floors, 21 colour palettes, 16 doors, 20
generic wall decorations and its monster list. Dungeon Hack+ patches the engine to pick from
**8 wallsets**, and fills the slots from all the games:

- **Wallsets**: hand-drawn EOB1/EOB2 walls are copied 1:1 from each view position
  (ScummVM's Kyra tables), EOB3 walls panel by panel. Each imported set gets its own floor
  (the set's own floor/ceiling backdrop) and palettes matched to its colours.
- **Menzoberranzan walls**: texture strips warped onto every DH view panel, with floors and
  ceilings projected from Menzo's flats using DH's own view geometry.
- **Doors**: EOB1/EOB2 doors are cut from their door sheets and animated as DH's three door
  stages; EOB3 doors are converted directly.
- **Decorations**: EOB1/EOB2 wall decorations are placed per view position exactly as EOB
  draws them; EOB3 decorations are converted directly.
- **Monsters**: EOB1/EOB2 monsters, using the exact frame layouts from the games' own level
  scripts. (30 of EOB3's 31 monsters already *are* Dungeon Hack's monsters; the Shadow Hound
  is the one new one.)
- **In-game music**: the original plays music only in the intro (it unloaded the music driver
  during play to save memory). Dungeon Hack+ patches the engine to load it, play a track per
  wallset and loop it: Dungeon Hack's own, Menzoberranzan's and EOB3's tracks, each vetted in
  game. MT-32/General MIDI setups get the full pool; AdLib setups get DH's own tracks.
- **Sound**: EOB3 sound effects at DH's 8 kHz rate, and EOB3 music for the intro and ending.
- **Fixes**: a resource-cache leak in item handling, Ice stairs that were invisible from three
  squares away, and save/continue crashing on installs that lack GOG's savegame template.

`dhplus.py roll` re-rolls which sets go into the slots, so new games keep looking different.

Everything is checked twice: `verify` checks every resource and the pairing rules (a bad rule
would hang new-game creation, so rule sets are validated before writing), and an in-game
screenshot gate drives DOSBox headlessly through walls, stairs, doors and decorations.

---

## Quick start

Requirements: Linux (macOS/WSL should work), Python 3.10+ with `numpy` and `Pillow`, and
[DOSBox-Staging](https://www.dosbox-staging.org/) (system install, or place it in
`third_party/dosbox-staging/`).

1. **Copy your games into `base_games/`** (see [`base_games/README.md`](base_games/README.md)):

   ```
   base_games/
   ├── dungeon_hack/   required: HACK.RES, OPEN.RES, AESOP.EXE ...
   ├── eob1/           Eye of the Beholder
   ├── eob2/           Eye of the Beholder II
   ├── eob3/           Eye of the Beholder III (EYE.RES)
   └── menzo/          Menzoberranzan
   ```

   Sources: GOG, or Steam's *Forgotten Realms: The Archives* collections. Optional extra
   languages go in `dungeon_hack_fre/` and `dungeon_hack_ger/`.

2. **Check them and generate the art and sound pool** (once):

   ```bash
   python3 -I dhplus.py detect
   python3 -I dhplus.py assets
   ```

3. **Build and play the mix:**

   ```bash
   python3 -I dhplus.py build mix
   python3 -I dhplus.py launch mix --skip-intro

   # later: a new random mix (your saves in build/mix are kept)
   python3 -I dhplus.py launch mix --reroll --skip-intro
   ```

`MIX.TXT` in the build folder lists which game each slot came from.

---

## Commands

| Command | Description |
|---|---|
| `detect` | Find and verify the base games. |
| `assets` | Regenerate `pool/` art and sounds from your games. |
| `list` | List presets and difficulty settings. |
| `build <preset> [name]` | Build a preset into `build/<name>/`. Rebuilding keeps that build's saves. |
| `roll [seed] [name]` | Roll a new mix (random seed by default) and build it. |
| `launch <build> [--skip-intro] [--reroll]` | Start a build in DOSBox-Staging. |
| `difficulty <preset> <build>` | Set the dungeon generator settings of a build. |
| `rollback <name>` | Delete a build. |
| `test` | Build and verify every preset. |
| `--lang fre\|ger` | Build from the French or German Dungeon Hack. |

## Presets

| Preset | What it is |
|---|---|
| `mix` | **The main build**: DH, EOB1, EOB2 and EOB3 in one game, plus fixes, sound and music. |
| `eob1_waterdeep` | All EOB1: five Waterdeep wallsets with their floors, doors, decorations, monsters. |
| `eob2_darkmoon_classic` | All EOB2: Darkmoon, Silver, Crimson, Mezz and forest sets, doors, decorations, monsters. |
| `eob3_mythdrannor` | All EOB3: Mausoleum, Ruins and Forest with their floors, doors and stairs. |
| `fixes` | Only the bug fixes, on otherwise original Dungeon Hack. |
| others | Earlier experiments and single-feature test presets (`dhplus.py list`). |

The single-game presets are useful for seeing one game's art on its own; `mix` is the
intended way to play.

---

## Documentation

- [`ROADMAP.md`](ROADMAP.md): what is done, verified, and still open.
- [`CLAUDE.md`](CLAUDE.md): working notes: formats, engine facts, gotchas, test tooling.
- [`DUNGEON_HACK_DEEP_DIVE.md`](DUNGEON_HACK_DEEP_DIVE.md): reverse-engineering background.

## Credits

- Event Horizon Software / DreamForge Intertainment (Dungeon Hack, EOB3, Menzoberranzan),
  Westwood (EOB1, EOB2), SSI, TSR.
- The authors of `daesop` and Thirdeye (AESOP formats), the ScummVM team (Kyra engine tables
  for EOB1/EOB2), and the DOSBox-Staging team.

## License

MIT for the code in this repository (see `LICENSE`). Dungeon Hack, Eye of the Beholder,
Menzoberranzan, Forgotten Realms and Advanced Dungeons & Dragons are trademarks of their
owners; no game data is included.
