# Base Games Drop-In Directory

Welcome to **Dungeon Hack+**!

To ensure full copyright compliance and legal distribution, this repository contains **only open-source patcher code, reverse-engineered format decoders, and procedural recipes**. It contains **zero proprietary game code, assets, audio, or graphics**.

To build and play enhanced Dungeon Hack mashup builds, you must provide your own legally acquired game installations (such as those from GOG.com's *Forgotten Realms: The Archives* collections, or original retail floppy/CD-ROM releases).

---

## Supported Base Games & Directory Layout

Drop your game files or folders into the corresponding subdirectories below:

### 1. `base_games/dungeon_hack/` (REQUIRED)
The core target game.
- **Source**: GOG *Forgotten Realms: The Archives - Collection Three* (or retail MS-DOS floppy release).
- **Key Files**:
  - `HACK.RES` (Primary game archive, ~24.9 MB)
  - `OPEN.RES` (Intro cinematic archive, ~608 KB)
  - `AESOP.EXE` (16-bit real-mode AESOP engine executable)
  - `MAZE.EXE` (Dungeon generator)
  - `CONFIG.DAT`, `SETTINGS.DAT`, `HACK.BAT`, etc.
- **Pristine SHA-256 Hashes**:
  - `HACK.RES`: `207eaf4081eee453c718fc8f761a707ab5c36bf974255185e2bc90ebe84cac66`
  - `OPEN.RES`: `7bc61e506cbf3aa144acc1b6dd6992ba0e2267d1f7b29294e9eaac83dcf61486`

### 2. `base_games/eob3/` (OPTIONAL - Highly Recommended)
*Eye of the Beholder III: Assault on Myth Drannor* (1993, AESOP/32 engine).
- **Provides**: All 4 full wallsets (Marble, Mausoleum, Ruins, Forest), animated dungeon doors, wall decorations, niche items, keys, and 31 high-resolution monster sprites.
- **Key Files**:
  - `EYE.RES` (32-bit AESOP container)
- **Pristine SHA-256 Hash**:
  - `EYE.RES`: `dfdb3fcb089c2c62c3e414c81062b08a0d783a37ba772ee6b5f4c4cbe9e0fc02`

### 3. `base_games/eob1/` (OPTIONAL)
*Eye of the Beholder* (1991, Westwood Studios engine).
- **Provides**: Classic Kobold, Skeleton, Zombie, Kuo-Toa, Kenku, Displacer Beast, Mind Flayer, Hellhound sprites, character portraits, and item icons.
- **Key Files**:
  - `EOBPAL.COL`, `*.CPS`, `*.PAK`

### 4. `base_games/eob2/` (OPTIONAL)
*Eye of the Beholder II: The Legend of Darkmoon* (1991, Westwood Studios engine).
- **Provides**: Darkmoon dungeon palettes, additional monster variations, and high-detail character portraits.
- **Key Files**:
  - `DUNG.PAL`, `*.CPS`, `*.PAK`

### 5. `base_games/menzo/` (OPTIONAL)
*Menzoberranzan* (1994, DreamForge Intertainment).
- **Provides**: Underdark caverns, high-depth wall tilesets, and sound effects.
- **Key Files**:
  - `RES0` through `RES8`, `GAME.ISO`

---

## Verifying Your Installation

Once you have placed your game files into these folders, run the verification tool from the project root:

```bash
python3 -I dhplus.py detect
```

The tool will scan your `base_games/` directory, verify SHA-256 hashes against known pristine retail and GOG distributions, and report the readiness of each asset source.

---

## Git Safety

The repository's `.gitignore` is configured to exclude all files inside `base_games/` (except `.gitkeep` placeholders). Your commercial game files will **never** be committed or pushed to your repository.
