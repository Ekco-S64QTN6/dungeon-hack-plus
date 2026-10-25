# base_games: your game files go here

This repository contains code and recipes only, no game data. Dungeon Hack+ builds everything from
your own copies of the games, which you place in the folders below. They are only ever read: builds
go to `build/`, and anything unpacked goes to `work/`.

The GOG releases and Steam's *Forgotten Realms: The Archives* collections both work (Steam's Dungeon
Hack files are byte-identical to GOG's). Copy the folder that contains the files named below.

| Folder | Game | Needed? | Key file | Used for |
|---|---|---|---|---|
| `dungeon_hack/` | Dungeon Hack (English) | **required** | `HACK.RES`, `OPEN.RES`, `AESOP.EXE`, `MAZE.EXE` | the game itself |
| `eob1/` | Eye of the Beholder | optional | `EOBPAL.COL`, or `EOBDATA*.PAK` | walls, floors, stairs, doors, decorations, monsters, portraits |
| `eob2/` | Eye of the Beholder II | optional | `DUNG.PAL` | walls, floors, stairs, doors, decorations, monsters, portraits |
| `eob3/` | Eye of the Beholder III | optional | `EYE.RES` | walls, floors, stairs, doors, portraits, sounds, intro/ending and in-game music |
| `menzo/` | Menzoberranzan | optional | `RES0`-`RES8` | walls, floors, in-game music |
| `dungeon_hack_fre/`, `dungeon_hack_ger/` | French / German Dungeon Hack | optional | `HACK.RES` | `dhplus.py --lang fre\|ger` |

Notes:
* **EOB1:** the English release packs its data in `EOBDATA*.PAK`; the German one has loose files.
  Either works: the PAKs are unpacked once into `work/eob1_unpacked/` (the graphics are identical).
* **Save games:** GOG keeps Dungeon Hack's savegame template (`SAVEGAME\SAVEGAME.DIR` and friends)
  outside the game folder; without it Save and Continue crash. Builds find it automatically in a
  `SAVEGAME` folder inside `dungeon_hack/`, in Steam's install, or in GOG/Heroic's support folder
  (or set `dh_save_template` in `config.json`).
* Paths can be changed in `config.json`, or per run with `DHPLUS_<GAME>_DIR`
  (e.g. `DHPLUS_EOB1_DIR=/path/to/EYE`).

Check what was found, then generate the art and sound pool:

```bash
python3 -I dhplus.py detect
python3 -I dhplus.py assets
```

Known hashes (`detect` compares them):

| File | SHA-256 |
|---|---|
| `HACK.RES` (English) | `207eaf4081eee453c718fc8f761a707ab5c36bf974255185e2bc90ebe84cac66` |
| `OPEN.RES` (English) | `7bc61e506cbf3aa144acc1b6dd6992ba0e2267d1f7b29294e9eaac83dcf61486` |
| `EYE.RES` (GOG) | `a11d5a2150ce65225af99655dab029788128af242eaa18ef5eb876a15e2cf767` |

Everything in this folder except this README is git-ignored, so game files are never committed.
