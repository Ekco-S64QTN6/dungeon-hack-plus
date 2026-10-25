"""Which tracks can the in-game music use? Plays each candidate in the dungeon and checks it.

  python3 -I smoke/music_tracks.py SPEC|@FILE ...      (SPEC = dh:<name> | menzo:<rec> | eob3:<name>; @FILE = one per line)

play_sequence() aborts the game ("timbre not found") if a track asks for an instrument the
driver's timbre library lacks, so a track is usable only if the game is still running and
sound comes out. Each candidate gets a build of original DH + game_music with that track as the
MT-32/GM version on every wallset (DH's own AdLib track as the AdLib version). Results are
merged into tools/music_tracks.json, which tools/mix.py reads.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import smoke         # noqa: E402
import music_check   # noqa: E402

OUT = os.path.join(ROOT, 'tools', 'music_tracks.json')
AD_SAFE = 'dh:Music Scene Two Adlib/Pc'


def test(spec, env):
    name = 'zz_track'
    recipe = {'comment': 'track test', 'jobs': [{'type': 'game_music', 'default': {'la': spec, 'ad': AD_SAFE}, 'tracks': {}}]}
    rp = os.path.join(smoke.RUNS, 'zz_track.json'); json.dump(recipe, open(rp, 'w'))
    b = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'pipeline.py'), 'build', rp, name], capture_output=True, text=True)
    if 'VERIFY OK' not in b.stdout:
        return 'build failed: ' + (b.stdout + b.stderr).strip().splitlines()[-1][:120]
    sounding, wavs = music_check.run(name, env)
    return sounding


def main():
    results = json.load(open(OUT)) if os.path.exists(OUT) else {}
    x = smoke.start_xvfb()
    env = dict(os.environ, DISPLAY=smoke.DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy'); env.pop('WAYLAND_DISPLAY', None)
    try:
        time.sleep(1)
        specs = [l.strip() for a in sys.argv[1:] for l in (open(a[1:]) if a.startswith('@') else [a]) if l.strip()]
        for spec in specs:
            if spec in results:
                continue
            r = test(spec, env)
            results[spec] = r
            print('%-24s %s' % (spec, r), flush=True)
            json.dump(results, open(OUT, 'w'), indent=1, sort_keys=True)
    finally:
        x.kill()


if __name__ == '__main__':
    main()
