# PCM playback rate: measured from DOSBox audio capture

**Result: Dungeon Hack plays its raw u8 PCM at 8,000 Hz.**

Method (`smoke/audio_rate.json`): walk to the door at (25,6), start DOSBox-Staging audio capture (Ctrl+F6, `capture_dir` set by `smoke.py`), click the door open, stop the capture. The 48 kHz capture contains a single loud event (envelope > 5% of peak):

| measured event | duration |
|---|---|
| door opening | **1.55 s** |

Audible span of HACK.RES door samples (envelope > 5% of peak) at each candidate rate:

| sample | samples | @ 8,000 Hz | @ 11,025 Hz |
|---|---|---|---|
| DOOR 00 / S-DOOR | 7,728 | 0.88 s | 0.64 s |
| DOOR 01 | 15,662 | **1.59 s** | 1.15 s |
| DOOR 02 | 11,365 | 1.41 s | 1.02 s |

At 11,025 Hz no door sample can last 1.55 s; at 8,000 Hz `DOOR 01` matches within 0.04 s. This agrees with the static evidence (`AESOP.EXE` stores 0x1F40 = 8000).
Note: a sample-level cross-correlation was tried first and is **not** usable (Pearson r ≈ 0.01 at both rates after DOSBox resampling/filtering); duration is the robust measure.
