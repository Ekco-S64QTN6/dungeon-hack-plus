# Dungeon Hack+ — Same-Size Byte Patch Catalogue (Safe Class)

This document catalogs verified, safe **same-size byte patches** for *Dungeon Hack*.
Because these modifications overwrite existing bytes without shifting file offsets or displacing adjacent structures, they introduce zero risk of segment overflow, pointer invalidation, or resource index misalignment.

---

## 1. Engine Executable Patches (`AESOP.EXE`)

### 1.1 Audio DMA Playback Sample Rate
- **Target File**: `AESOP.EXE`
- **File Offset**: `0x12315` (Segment `seg000`, offset `74517`)
- **Description**: Sets the Sound Blaster DMA playback sample rate for raw PCM audio effects.
- **Original Code**:
  ```assembly
  C7 06 66 8D 40 1F      mov   word ptr [8D66h], 1F40h   ; 1F40h = 8,000 Hz
  ```
- **Optional Patches**:
  | Rate | Hex Bytes | Assembly Equivalent |
  |---|---|---|
  | **8,000 Hz (Original)** | `C7 06 66 8D 40 1F` | `mov word ptr [8D66h], 1F40h` |
  | **11,025 Hz (CD Quality)** | `C7 06 66 8D 11 2B` | `mov word ptr [8D66h], 2B11h` |
  | **22,050 Hz (High-Fi)** | `C7 06 66 8D 22 56` | `mov word ptr [8D66h], 5622h` |

---

## 2. Resource Script & Table Patches (`HACK.RES`)

### 2.1 Copy Protection Bypass (`validity checker`)
- **Target Resource**: `validity checker` in `HACK.RES`
- **Description**: Bypasses the post-character-generation manual lookup prompt.
- **Mechanism**: The check script tests `B:auto_on`. Setting the auto-test flag to `1` or replacing the conditional branch with an unconditional jump bypasses the question dialog.
- **Byte Diffs**:
  ```
  Original:  74 18          ; jz   prompt_user
  Patched:   EB 18          ; jmp  skip_protection
  ```

### 2.2 Wallset Two-Ramp Shading Bitmasks (`kernel`)
- **Target Resource**: `kernel` in `HACK.RES` (palette tables)
- **Description**: Switches a wallset slot between 1-ramp (`indices 240..255`) and 2-ramp (`indices 15..20`) distance dimming.
- **Single-Ramp Mask**: `0x7FBF` (Allows palettes 0..14)
- **Two-Ramp Mask**: `0x003F` (Allows palettes 15..20)

---

## 3. Game Configuration & Generator Patches (`SETTINGS.DAT`)

- **Target File**: `savegame/SETTINGS.DAT`
- **Structure Size**: Exactly 32 bytes

| Field | File Offset | Type | Original (Classic) | Patched (Iron Crawl) | Patched (Casual) |
|---|---|---|---|---|---|
| `total_levels` | `0x00` | `u16` | `0x000F` (15 levels) | `0x0019` (25 levels) | `0x000A` (10 levels) |
| `monster_frequency` | `0x02` | `u16` | `0x0003` (Moderate) | `0x0007` (Dense) | `0x0001` (Few) |
| `food_frequency` | `0x04` | `u16` | `0x0002` (Normal) | `0x0001` (Scarce) | `0x0005` (Abundant) |
| `traps_frequency` | `0x06` | `u16` | `0x0003` (Normal) | `0x0007` (Deadly) | `0x0000` (None) |
| `permadeath_flag` | `0x08` | `u16` | `0x0001` (Enabled) | `0x0001` (Enabled) | `0x0000` (Disabled) |
| `puzzles_frequency`| `0x0A` | `u16` | `0x0002` (Normal) | `0x0005` (Complex) | `0x0000` (Simple) |
| `magic_frequency` | `0x0C` | `u16` | `0x0002` (Normal) | `0x0001` (Scarce) | `0x0005` (Abundant) |

---
