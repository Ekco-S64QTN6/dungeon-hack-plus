# Dungeon Hack Bug Triage & Engine Quirks Catalogue

**Date**: 2026-10-24  
**Scope**: Community reports (GOG, Vogons, Thirdeye issue tracker, AESOP runtime disassembly)  
**Status**: Completed (ROADMAP Phase 4, lines 78, 80, 81)

---

## 1. Executive Summary

This report catalogues and triages known bugs, engine quirks, and failure modes in *Dungeon Hack* (1993, Event Horizon / SSI). Each issue is classified by severity and remediation strategy:
* **Class A**: Fixable as a same-size byte patch in `HACK.RES` or `AESOP.EXE`.
* **Class B**: Requires tool / pipeline enforcement or DOSBox configuration.
* **Class C**: Requires AESOP/16 bytecode compiler (`arc`) to reassemble SOP classes.
* **Class D**: Unfixable without complete EXE rewrite (handled by Thirdeye reimplementation).

> **Evidence audit (Claude, 2026-10-24)** — status of each claim after checking bytes/sources:
> * Bug 1 (unlock shape): **CONFIRMED in bytecode.** `items` handlers "lock shape" and "unlock shape" are identical; both call `C:lock_resource` (runtime 620). `unlock_resource` (624) exists in the runtime table but is not imported by `items.IMPT`. Fix = add the import + retarget the RCRS operand (same-size code). In-game memory impact not yet demonstrated.
> * Bug 2 (printer hang): **UNVERIFIED hypothesis.** `printer_on_line` (runtime 188) is real and imported by `dungeon`; "polls without timeout" is not shown (INT 17h AH=02 normally returns at once). Test in DOSBox before patching.
> * Bug 3 (MAZE hang): **MISATTRIBUTED.** Thirdeye's note names the three non-terminating loops as *monster scatter, room scatter, door punch*, not key/trap density. The `difficulty.py` caps target the wrong trigger; no hanging seed is documented yet.
> * Bugs 4–6: behaviour descriptions, not engine bugs; 5 is our own pipeline hazard (guarded by `check_ramps`).

---

## 2. Issue Catalogue & Triage

### Bug 1: The "Unlock Shape" Resource Leak (Class A / C)
* **Component**: `HACK.RES` resource `items` (and `items.IMPT`)
* **Symptom**: During long play sessions, inspecting, manipulating, and dropping numerous inventory items causes progressive heap degradation, culminating in `"Out of DOS memory"` crashes.
* **Root Cause**: In the `items` SOP class, the message handler for `"unlock shape"` accidentally invokes runtime C-function `lock_resource` instead of `unlock_resource`. Instead of freeing discardable item shapes from the LRU cache, it increments the lock count, pinning shapes indefinitely in conventional memory.
* **Triage**:
  * *Option 1*: Same-size byte patch in `items.IMPT` if `unlock_resource` is present in the runtime table (runtime slot 148).
  * *Option 2*: Documented in `ADDITIONAL_DH_RUNTIME_FUNCTIONS.TXT`; resolved in Thirdeye native runtime.

---

### Bug 2: Printer Map Hang / LPT1 Lockup (Class A / B)
* **Component**: `HACK.RES` resource `dungeon`, runtime call `printer_on_line`
* **Symptom**: Clicking the printer icon on the Automap screen causes the game to completely hang, requiring a hard DOSBox kill.
* **Root Cause**: `printer_on_line` polls the BIOS printer status port (INT 17h, AH=02h) for LPT1. When no physical printer or DOSBox virtual printer is configured, the BIOS poll loops without timeout.
* **Triage**:
  * *Config Fix*: Configure `dosbox-dh.conf` with `parallel1 = dummy` or `printer`.
  * *SOP Patch*: Patch the automap print button handler in `dungeon` to return 0 (offline) immediately.

---

### Bug 3: MAZE.EXE Generator Hang on Dense Key/Trap Constraints (Class B)
* **Component**: `MAZE.EXE` (16-bit generator)
* **Symptom**: Dungeons fail to generate, hanging indefinitely on `..\maze %1 %2` with 100% CPU usage.
* **Root Cause**: Identified by Thirdeye research. When dungeon size is small (`depth=0`, 10 levels) and `FREQ_KEYS` and `FREQ_TRAPS` are set to maximum (`7`) alongside high illusionary walls, the carver's placement validation enters an infinite `while(!placed)` loop because the topological branch constraints cannot fit all mandatory key/lock pairs into available dead ends.
* **Triage**:
  * *Avoidance*: `mashup/tools/difficulty.py` enforces safe maximums (capping keys/traps to 5 when depth < 3).
  * *Seed Blacklist*: Document known failing seeds; `difficulty.py` validates settings combinations before invoking `MAZE.EXE`.

---

### Bug 4: Iron Man Permadeath Save Deletion (Class B)
* **Component**: `HACK.RES` resource `PC`, runtime call `delete_saves`
* **Symptom**: Selecting "Iron Man" mode deletes the entire `SAVEGAME/` folder contents upon character death. Any power glitch, crash, or accidental death wipes hours of progress.
* **Triage**:
  * *Resolved*: [mashup/tools/savegame.py](../tools/savegame.py) provides automatic timestamped snapshotting (`savegame.py backup`) to allow painless recovery from Iron Man wipeouts.

---

### Bug 5: Two-Ramp Wallset Brightness Crushing (Class B)
* **Component**: `HACK.RES` resource `kernel` (`table1070`, `table1112`)
* **Symptom**: Reskinned wallsets appear completely pitch black or starkly blown out on certain levels.
* **Root Cause**: `Stone Wallset` natively uses two-ramp brightness palettes (palettes 15–20), whereas all other 6 wallsets use 1-ramp palettes (palettes 00–14). If rules pair a single-ramp wall texture with a two-ramp level palette, luminance indices 240–255 map into the wrong curve.
* **Triage**:
  * *Resolved*: `mashup/tools/kernel_rules.py` and `pipeline.py` implement `check_ramps` with negative control regression tests (`pool/negative_rules_only.json`). All multi-ramp ports (EOB3 Mausoleum, Ruins, Forest) automatically inject validated `palette_rules` jobs into the recipe.

---

### Bug 6: Copy-Protection Prompt Nuisance (Class A / Informational)
* **Component**: `HACK.RES` resource `validity checker` (`idx 2926`)
* **Symptom**: Character creation displays a retro manual check prompt (`On page X, enter word Y`).
* **Root Cause & Behavior**: In GOG / Archives releases, `kernel` sets `B:auto_on = 1`. Any input (or pressing Enter) instantly passes.
* **Triage**: Preserved as-is per user request; non-blocking and harmless. Full breakdown documented in [mashup/smoke_runs/copy_protection_report.md](../smoke_runs/copy_protection_report.md).
