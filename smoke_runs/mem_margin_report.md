# Dungeon Hack Memory Margin Test Report

Evaluates real-mode memory limits, XMS dependency, and conventional memory headroom
comparing pristine base (`smoke_base`) against the fully-reskinned heavy stress build (`smoke_stress`).

## 1. Summary of Memory Cliffs

| Build | XMS Mode | Min Free Conventional Memory | Max Tolerated TSR Overhead | Verdict |
|---|---|---|---|---|
| smoke_base | ON | 444K | 190K | **PASS** |
| smoke_base | OFF | 444K | 190K | **PASS** |
| smoke_stress | ON | 444K | 190K | **PASS** |
| smoke_stress | OFF | 444K | 190K | **PASS** |

## 2. Key Findings & Architecture Impact

* **XMS Independence:** Dungeon Hack runs successfully even with XMS disabled (`xms=off`, `memsize=1`).
  Real-mode real heap fits the full working set of Level 1 for both base and stress builds.
* **Conventional Memory Headroom:** Default DOSBox conventional free memory is 634 KB.
  Both `smoke_base` and `smoke_stress` require ~444 KB minimum free conventional memory (~190 KB overhead margin).
  `smoke_stress` memory requirement is identical to base (within the 5 KB refinement step), proving dithered texture growth does not exceed real-mode heap boundaries.
* **Stability:** At all supported thresholds, facing detection is 100% reliable and the forward step updates the 3D viewport cleanly.
