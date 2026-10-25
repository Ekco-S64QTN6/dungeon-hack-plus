# Heap margin during play (2026-10-25)

Measured in game with the test-only `heap_probe` job (`tools/heap_probe.py`): every timer tick the game
writes `heapfree()`, `heapfree()` after `flush_cache(16 MB)` and `xmsfree()` to HEAP.LOG, which
`smoke/heap_log.py` polls during a walk. "Slack" = free heap once every unlocked resource is dropped, i.e.
what is left beyond the working set the game holds at that moment. DOSBox-Staging defaults (16 MB, XMS/EMS/UMB
on; same as `dosbox-dh.conf`), fixture `savegame` (Rhenovia), music on (MT-32 driver + SB digital).

## Levels (plan `heap_levels_deep`: F7 through all 10 levels with `AESOP_DIAG`, armageddon on arrival)

| Level | DH base: slack min | mix: slack min | DH base: free with cache min | mix: free with cache min |
|---|---|---|---|---|
| 0 | 323,696 | 300,912 | 68,400 | 239,104 |
| 1 | 325,440 | 302,656 | 137,504 | 30,576 |
| 2 | 325,056 | 298,176 | 147,392 | 39,056 |
| 3 | 320,976 | 298,192 | 255,024 | 22,448 |
| 4 | 321,712 | 298,928 | 133,952 | 115,728 |
| 5 | 320,512 | 297,728 | 149,952 | 33,552 |
| 6 | 321,952 | 299,168 | 147,472 | 15,968 |
| 7 | 320,832 | 298,048 | 148,064 | 232,864 |
| 8 | 320,272 | 297,488 | 273,408 | 120,128 |
| 9 | 286,016 | 263,232 | 136,224 | 20,704 |

* The mix keeps **≥ 263 KB** slack on every level; it runs a constant ~23 KB below DH (the in-game music
  driver, sequence buffer and timbre cache, plus the larger kernel tables), level for level.
* "Free with cache" is just how full the resource cache is (it evicts on demand); the mix fills it more.
* With monsters left alive (plan `heap_levels`, levels 0-4, where the level-1 party dies), slack minimum:
  DH 286,112, mix 263,328, mix forced to W13 / W15 (largest imported sets) 263,328 each.
* Both builds quit ~25 s into level 9, identically (not inspected; the party is poisoned and low by then, so most
  likely death), so level 9 is a short sample.

## Bug 1 (`items` "unlock shape" calls `lock_resource`)

Plans `item_juggle` (hand slot, 40×) and `item_juggle_pack` (backpack item, 20×), unfixed vs `fix_unlock_shape`:
both builds show the same pattern (the item's icon, 208 B with heap overhead, locked while in a slot and
released while held) and no growth over the run. The bytecode error is real, but no leak is measurable on
these paths; the fix stays (it is the evident intent and pixel-identical in game).
