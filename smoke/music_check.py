"""Does a build play music in the dungeon? Records DOSBox's raw MIDI output and counts notes.

  python3 -I smoke/music_check.py BUILD [BUILD ...]     ('base' = original install)

Boots the fixture save into the dungeon (aesop hack phase-two, SOUND.CFG = MT-32/MPU-401 as
shipped), waits for the level to load, records MIDI for 20 s with DOSBox-Staging's
"record MIDI" hotkey (Ctrl+Alt+F8), and counts note-on events in the captured .mid.
The original game plays no music in the dungeon, so 'base' is the negative control (0 notes).
"""
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import smoke   # noqa: E402


# MIDI must go to a real synth or DOSBox disables MIDI output (and with it the capture)
MIDI = ('mididevice=fluidsynth', 'soundfont=' + next((f for f in ('/usr/share/soundfonts/FluidR3_GM.sf2',
        '/usr/share/sounds/sf2/FluidR3_GM.sf2') if os.path.exists(f)), 'default.sf2'))


def note_ons(mid):
    """Count note-on events (status 0x9n, velocity > 0) in a Standard MIDI File, with running status."""
    d = open(mid, 'rb').read()
    count, i = 0, 0
    while True:
        i = d.find(b'MTrk', i)
        if i < 0:
            return count
        n = int.from_bytes(d[i + 4:i + 8], 'big'); p, end, status = i + 8, i + 8 + n, 0
        while p < end:
            while d[p] & 0x80:            # delta time (variable length)
                p += 1
            p += 1
            if d[p] & 0x80:
                status = d[p]; p += 1
            if status == 0xFF:
                ln = d[p + 1]; p += 2 + ln; status = 0; continue
            if status in (0xF0, 0xF7):
                ln = d[p]; p += 1 + ln; status = 0; continue
            hi = status & 0xF0
            if hi == 0x90 and d[p + 1] > 0:
                count += 1
            p += 1 if hi in (0xC0, 0xD0) else 2
        i = end


def run(name, env):
    smoke.FIXTURE = os.path.join(ROOT, 'fixtures', 'savegame_nomon')
    d = smoke.stage(name)
    cap = os.path.join(d, 'capture')
    p, _ = smoke.dosbox(d, ['aesop hack phase-two'], env, 0, settings=MIDI)
    wid = smoke.window_id(env, p.pid)
    key = lambda: subprocess.run(['xdotool', 'key', '--window', wid, 'ctrl+F6'], env=env, timeout=10)   # audio capture
    try:
        time.sleep(30)                    # boot + level load (+ music start)
        key(); time.sleep(20); key(); time.sleep(3)
    finally:
        p.kill(); p.wait()
    wavs = sorted(glob.glob(os.path.join(cap, '*.wav')))
    return (sounding(wavs[-1]) if wavs else None), wavs


def sounding(wav):
    """Fraction of 100 ms windows louder than -50 dBFS (music plays continuously; the
    original dungeon is silent between footsteps and monster noises)."""
    import wave
    import numpy as np
    w = wave.open(wav)
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, w.getnchannels()).mean(axis=1)
    win = w.getframerate() // 10
    rms = np.sqrt(np.mean(a[:len(a) // win * win].reshape(-1, win) ** 2, axis=1)) / 32768
    return round(float((rms > 10 ** (-50 / 20)).mean()), 2)


def main():
    x = smoke.start_xvfb()
    env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy'); env.pop('WAYLAND_DISPLAY', None)
    try:
        time.sleep(1)
        for name in sys.argv[1:]:
            notes, mids = run(name, env)
            print('%-14s audio capture: %s, sounding fraction of 20 s: %s' % (name, os.path.basename(mids[-1]) if mids else 'none', notes))
    finally:
        x.kill()


if __name__ == '__main__':
    main()
