# Dungeon Hack Copy-Protection Mechanics & Verification Report

**Date**: 2026-10-24  
**Target Binary**: `Dungeon Hack/HACK.RES`  
**SOP Resource**: `2926: validity checker` (1,296 bytes)  
**Status**: Verified & Documented (ROADMAP line 79)

---

## 1. Overview & Architecture

Dungeon Hack's copy-protection is implemented entirely in AESOP/16 bytecode inside `HACK.RES`:
* **Controller**: `validity checker` (`idx 2926`, 1,296 bytes)
* **Imports**: `validity checker.IMPT` (`idx 2961`, 550 bytes)
  * `B:auto_on` (imported from `kernel` at slot 1972)
  * `B:buffer` (imported from `input` at slot 1961)
  * Runtime C APIs: `flush_input_events`, `beep`, `rnd`, `draw_bitmap`, `assign_subwindow`, `text_window`, `text_color`
* **Exports**: `validity checker.EXPT` (`idx 2962`, 94 bytes)
  * `OBJECT: validity checker` (methods 0, 1, 433, 615)
* **Text Strings**: Slots 1750–1756:
  * `1750`: `"On page "`
  * `1751`: `"Under the heading "`
  * `1752`: `"Please enter the "`
  * `1753`: `" word."`
  * `1754`: `"CORRECT!"`
  * `1755`: `"INCORRECT! TRY AGAIN ..."`
  * `1756`: `"INCORRECT! EXITING ..."`
* **Dictionary**: Slots 1757–1814 hold manual words, page numbers, and heading indices.

---

## 2. Execution Path

In `HACK.BAT`:
```bat
aesop hack phase-one
set F=1
if ERRORLEVEL 3 goto CONTINUE
if ERRORLEVEL 2 goto CHECKDEMO
if ERRORLEVEL 1 goto EXIT
cd savegame
..\maze %1 %2
cd ..
if ERRORLEVEL 1 goto EXIT
aesop hack phase-two
```
* `phase-one` (Character Creation & Setup):
  * When the user clicks "Start Game" or finishes creating a character, `phase-one` invokes `validity checker` right before exiting to `MAZE.EXE`.
  * The copy-protection prompt displays the page/heading/word prompt over the character screen.

---

## 3. GOG Release Behavior

Disassembly of `validity checker` at bytecode offset `0x04C0`:
```assembly
39 01 00     ; LAB "B:auto_on" (from kernel)
01 e9 04     ; BRT LBL_AUTO_PASS (branch if true)
```
* **Original Retail Floppy**: `auto_on == 0`. The user had to enter the exact manual word within 3 attempts or the game exited.
* **GOG / Archives Release**: GOG configured `kernel` with `auto_on == 1`.
  * The prompt is still drawn to preserve the retro aesthetic.
  * When input is entered (or even if the user simply presses **Enter** with an empty string), `validity checker` evaluates `B:auto_on`, immediately branches to `CORRECT!`, and proceeds cleanly into `MAZE.EXE` and `phase-two`.
  * **Result**: Zero risk of copy-protection lockout; accepts any arbitrary input.

---

## 4. Policy Recommendation

* Do **NOT** remove or strip the prompt:
  1. The user explicitly requested: *"Don't remove it unless the user asks"*.
  2. The prompt functions without friction (press Enter or any key).
  3. The headless smoke test harness (`smoke/route.py` and `AUTOTYPE`) easily satisfies the prompt deterministically.

---

## 5. Correction (2026-10-25, checked in game and in the kernel bytecode)

* The prompt is **not** only in `phase-one`. The kernel's `move` handler, on any level change, calls
  `flush_cache(200000)` and sends `validity check`, which runs the `validity checker` unless `B:passed` is
  already set. So in `phase-two` (continuing a save) the prompt appears on the **first level change of each
  session**, then never again in that session. Seen in game with F7 (`AESOP_DIAG`) on the fixture save.
* An **empty** Enter is ignored; any non-empty word followed by Enter passes (this release's `auto_on`).
  Test plans type `q` (with `AESOP_DIAG` set, `a`/`A` = armageddon, `x`/`X`, `o`, `t`/`T`, `i`/`I`, `E`
  are debug keys).
