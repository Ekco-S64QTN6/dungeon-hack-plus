"""Regenerate every pool asset the recipes use, from the user's own games.

  python3 -I tools/pool_assets.py          (or: python3 -I dhplus.py assets)

The repository ships code and recipes only; pool/ images and sounds are derived from the
games, so a fresh clone runs this once after filling base_games/:
  pool/floors/<SET>_backdrop.png     EOB1/EOB2 floor/ceiling backdrops (VMP backdrop entries)
  pool/walls/<SET>_wt<N>_front.png   EOB1/EOB2 near front walls (used by the early presets)
  pool/floors/eob3_<set>.png         EOB3 backdrops (19th frame of each wall object)
  pool/monsters/<name>/0..5.png      EOB1/EOB2 (tools/monsters.py) and EOB3 (tools/eob3_monsters.py)
  pool/sounds/raw|wav                EOB3 PCM (tools/sounds.py)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import paths      # noqa: E402
import westwood   # noqa: E402

POOL = os.path.join(ROOT, 'pool')


def westwood_sets():
    """Backdrops and near front walls of every EOB1/EOB2 wallset, as `pipeline.py extract` renders them."""
    from pipeline import save_indexed, CFG
    for game in ('eob1', 'eob2'):
        base = paths.get_game_dir(game)
        if not os.path.isdir(base):
            print('skip', game, '(not installed)'); continue
        files = os.listdir(base)
        default = westwood.read_pal(os.path.join(base, CFG['games'][game]['default_pal']))
        for fn in sorted(files):
            stem, ext = os.path.splitext(fn)
            if ext.upper() != '.VCN' or stem + '.VMP' not in files:
                continue
            blocks, remap = westwood.vcn_blocks(os.path.join(base, fn))
            ent = westwood.vmp(os.path.join(base, stem + '.VMP'))
            pal = westwood.read_pal(os.path.join(base, stem + '.PAL')) if stem + '.PAL' in files else default
            w, h, px = westwood.render_blocks(ent[:330], blocks, 22)          # 176x120 backdrop
            os.makedirs(os.path.join(POOL, 'floors'), exist_ok=True)
            save_indexed(os.path.join(POOL, 'floors', stem + '_backdrop.png'), w, h, bytes(remap[v] for v in px), pal)
            os.makedirs(os.path.join(POOL, 'walls'), exist_ok=True)
            for t in range((len(ent) - 330) // 431):
                wt = ent[330 + 431 * t:330 + 431 * (t + 1)]
                w, h, px = westwood.render_blocks(wt[239:], blocks, 16)       # near front wall 128x96
                save_indexed(os.path.join(POOL, 'walls', '%s_wt%d_front.png' % (stem, t)), w, h,
                             bytes(remap[16 + v] for v in px), pal)
        print(game, 'wallsets -> pool/floors, pool/walls')


def eob3_floors():
    import aesop
    from PIL import Image
    import eob_classic
    e3 = aesop.ResFile(paths.get_game_file('eob3', 'EYE.RES'))
    for wall, pal, _ in eob_classic.EOB3_SETS:
        img, _ = eob_classic.eob3_colours(e3, wall, pal)
        Image.fromarray(img).save(os.path.join(POOL, 'floors', 'eob3_%s.png' % wall.split()[0].lower()))
    print('eob3 floors -> pool/floors')


def main():
    westwood_sets()
    eob3_floors()
    import monsters, eob3_monsters, sounds
    monsters.extract_all()
    eob3_monsters.extract_all()
    sounds.extract_all()
    print('pool assets regenerated')


if __name__ == '__main__':
    main()
