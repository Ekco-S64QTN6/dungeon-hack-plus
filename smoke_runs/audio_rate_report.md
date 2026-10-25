# Audio Sample Rate Verification Report

## 1. Engine Binary Analysis

| Metric | Value |
|---|---|
| Driver Interface | Miles Sound System (MSS 2.0 / AIL) |
| Initialization Instruction | `mov word ptr [8D66h], 1F40h` (offset `0x12311`) |
| Configured Playback Rate | **8000 Hz** |
| 8,000 Hz constants in binary | 2 |
| 11,025 Hz constants in binary | **0** |

## 2. In-Engine Call Flow
* In `AESOP.EXE` at file offset `0x12315` (74517), the runtime assigns `0x1F40` (8,000) to memory location `[8D66h]`.
* It immediately branches into the Miles Sound System playback vector table (`cs:02ACh[bx]`) and invokes `AIL_start_sample`.
* The SOP bytecode function `sound_effect(index)` takes only a sound resource index; no sample rate parameter exists at the script level.
* **Conclusion:** All native and imported PCM digital audio in Dungeon Hack must be mastered at **8,000 Hz, 8-bit unsigned mono**.
