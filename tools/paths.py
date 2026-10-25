"""Central path resolution and base game discovery for Dungeon Hack+.

Handles:
- Project root discovery
- Drop-in base games directory (base_games/)
- Fallback detection for external GOG archives or previous workspace locations
- Verification of required game archives
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)

DEFAULT_CONFIG = {
    "root": ".",
    "base_games_dir": "base_games",
    "dh_install": "base_games/dungeon_hack",
    "games": {
        "dh":    {"engine": "aesop16",    "path": "base_games/dungeon_hack", "res": ["HACK.RES", "OPEN.RES"]},
        "eob3":  {"engine": "aesop32",    "path": "base_games/eob3",         "res": ["EYE.RES"]},
        "eob1":  {"engine": "westwood",   "path": "base_games/eob1",         "default_pal": "EOBPAL.COL"},
        "eob2":  {"engine": "westwood",   "path": "base_games/eob2",         "default_pal": "DUNG.PAL"},
        "menzo": {"engine": "dreamforge", "path": "base_games/menzo",        "iso": "GAME.ISO"}
    },
    "pcm_rate_guess": 8000
}


def load_config():
    cfg_file = os.path.join(PROJECT_ROOT, "config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG


FALLBACKS = {
    "dh": [
        "base_games/dungeon_hack",
        "base_games/Dungeon Hack",
        "Dungeon Hack",
        "Forgotten Realms The Archives - Collection Three/games/Dungeon Hack-ENG/GAME/HACK",
    ],
    "eob3": [
        "base_games/eob3",
        "base_games/Eye of the Beholder III/GAME/EOB3",
        "Forgotten Realms The Archives - Collection One/games/Eye of the Beholder III/GAME/EOB3",
    ],
    "eob1": [
        "base_games/eob1",
        "base_games/Eye of the Beholder DE/GAME/EYE",
        "Forgotten Realms The Archives - Collection One/games/Eye of the Beholder DE/GAME/EYE",
    ],
    "eob2": [
        "base_games/eob2",
        "base_games/Eye of the Beholder II - EN/GAME/DARKMOON",
        "Forgotten Realms The Archives - Collection One/games/Eye of the Beholder II - EN/GAME/DARKMOON",
    ],
    "menzo": [
        "base_games/menzo",
        "base_games/Menzoberranzan/GAME/MENZO",
        "Forgotten Realms The Archives - Collection Three/games/Menzoberranzan/GAME/MENZO",
    ]
}

KEY_FILES = {
    "dh": "HACK.RES",
    "eob3": "EYE.RES",
    "eob1": "EOBPAL.COL",
    "eob2": "DUNG.PAL",
    "menzo": "RES0",
}


def unpacked_eob1(folder):
    """EOB1's English release packs its data in EOBDATA*.PAK (the German one ships loose files;
    the graphics are byte-identical). Unpack once into work/eob1_unpacked/<folder hash>/ and use
    that; the game folder itself is never written."""
    import glob
    import hashlib
    paks = sorted(glob.glob(os.path.join(folder, "[Ee][Oo][Bb][Dd][Aa][Tt][Aa]*.[Pp][Aa][Kk]")))
    if not paks:
        return None
    tag = hashlib.sha1("|".join("%s:%d" % (os.path.basename(p), os.path.getsize(p)) for p in paks).encode()).hexdigest()[:10]
    out = os.path.join(PROJECT_ROOT, "work", "eob1_unpacked", tag)
    if not os.path.exists(os.path.join(out, KEY_FILES["eob1"])):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import westwood
        os.makedirs(out, exist_ok=True)
        for p in paks:
            for name, data in westwood.unpak(p).items():
                open(os.path.join(out, name.upper()), "wb").write(data)
    return out if os.path.exists(os.path.join(out, KEY_FILES["eob1"])) else None


def get_game_dir(game_key):
    """Resolve the directory containing game assets for `game_key`.
    DHPLUS_<KEY>_DIR (env) overrides it, e.g. DHPLUS_DH_DIR=base_games/dungeon_hack_fre."""
    req_file = KEY_FILES.get(game_key)
    ok = lambda d: os.path.exists(d) and (not req_file or os.path.exists(os.path.join(d, req_file)))
    env = os.environ.get("DHPLUS_%s_DIR" % game_key.upper())
    cands = [env] if env else []
    cfg = load_config()
    # 1. Configured path, 2. candidate fallbacks
    if not env and "games" in cfg and game_key in cfg["games"]:
        cands.append(cfg["games"][game_key].get("path", ""))
    if not env:
        cands += FALLBACKS.get(game_key, [])
    cands = [os.path.normpath(os.path.join(PROJECT_ROOT, c)) for c in cands]
    for cand in cands:
        if ok(cand):
            return cand
    if game_key == "eob1":
        for cand in cands:
            if os.path.isdir(cand) and unpacked_eob1(cand):
                return unpacked_eob1(cand)
    if env:
        return cands[0]

    # Return default base_games location if not found
    return os.path.normpath(os.path.join(PROJECT_ROOT, "base_games", game_key if game_key != "dh" else "dungeon_hack"))


def get_game_file(game_key, *subpaths):
    return os.path.join(get_game_dir(game_key), *subpaths)


def get_dh_dir():
    return get_game_dir("dh")


# --------------------------------------------------------------------------- savegame template
# DH's save screen, Continue and the Hall of Fame need files that GOG does not put in the game
# folder: they ship as a "save" support folder that the GOG launcher overlays on C: (cloud_saves).
# Without SAVEGAME\SAVEGAME.DIR, Save Game and Continue abort with
# "Couldn't open savegame directory for reading" and DOSBox closes.
SAVE_TEMPLATE_FILES = ('SAVEGAME.DIR', 'VISIBLE.DAT', 'SETSAVE.DAT', 'HISCORE.DEF', 'HISCORE.DAT', 'NEWSCORE.EXE')
EMPTY_SAVEGAME_DIR = b'<empty>\r\n' * 12          # GOG's SAVEGAME.DIR: 12 empty slot names


def _child_ci(parent, name):
    if not os.path.isdir(parent):
        return None
    for n in os.listdir(parent):
        if n.lower() == name.lower():
            return os.path.join(parent, n)
    return None


def _steam_common_dirs():
    import glob, re
    home = os.path.expanduser("~")
    roots = [os.path.join(home, ".local/share/Steam"), os.path.join(home, ".steam/steam"),
             os.path.join(home, ".var/app/com.valvesoftware.Steam/data/Steam")]
    libs = []
    for r in roots:
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            libs += re.findall(r'"path"\s+"([^"]+)"', open(vdf, errors="replace").read())
        libs.append(r)
    libs += glob.glob("/mnt/*/SteamLibrary") + glob.glob("/media/*/*/SteamLibrary")
    seen, out = set(), []
    for lib in libs:
        d = os.path.join(lib, "steamapps", "common")
        if os.path.isdir(d) and os.path.realpath(d) not in seen:
            seen.add(os.path.realpath(d)); out.append(d)
    return out


def get_dh_save_template(dh_dir=None):
    """Folder holding the initial SAVEGAME files for this DH install (language-matched), or None.
    Steam's Archives collection keeps them inside the game folder (HACK/SAVEGAME, localized per
    language); GOG keeps them in a support folder (cloud_saves / Heroic gog-support, English)."""
    import glob
    dh = dh_dir or get_dh_dir()
    low = os.path.basename(os.path.normpath(dh)).lower()
    lang = "FRE" if low.endswith("_fre") or "-fre" in low else "GER" if low.endswith("_ger") or "-ger" in low else "ENG"
    cfg = load_config()
    cands = []
    tpl_cfg = cfg.get("dh_save_template")
    if isinstance(tpl_cfg, dict):
        tpl_cfg = tpl_cfg.get(lang.lower())
    if tpl_cfg:
        cands.append(os.path.join(PROJECT_ROOT, tpl_cfg))
    cands.append(os.path.join(dh, "SAVEGAME"))                      # Steam layout, copied with the game
    for sub in ("cloud_saves", os.path.join("__support", "save"), os.path.join("..", "__support", "save")):
        cands.append(os.path.join(dh, sub, "SAVEGAME"))
    for common in _steam_common_dirs():
        cands.append(os.path.join(common, "Forgotten Realms The Archives - Collection Three", "games",
                                  "Dungeon Hack-%s" % lang, "GAME", "HACK", "SAVEGAME"))
    if lang == "ENG":                                                  # GOG sells the English version only
        home = os.path.expanduser("~")
        for heroic in (os.path.join(home, ".var/app/com.heroicgameslauncher.hgl/config/heroic"), os.path.join(home, ".config/heroic")):
            cands += sorted(glob.glob(os.path.join(heroic, "gogdlConfig/heroic_gogdl/gog-support/*/*/save/SAVEGAME")))
    for c in cands:
        d = c if os.path.isdir(c) else _child_ci(os.path.dirname(c), os.path.basename(c))
        if d and _child_ci(d, "SAVEGAME.DIR"):
            # a played-in folder is fine as long as we only copy the template files from it
            return d
    return None


def seed_savegame(game_dir):
    """Add the missing GOG savegame files to game_dir/savegame (never overwrites). -> list of notes."""
    import shutil
    sg = _child_ci(game_dir, "savegame") or os.path.join(game_dir, "savegame")
    os.makedirs(sg, exist_ok=True)
    tpl = get_dh_save_template()
    if tpl and os.path.realpath(tpl) == os.path.realpath(sg):
        tpl = get_dh_save_template(os.path.join(game_dir, "__none__"))  # don't seed a folder from itself
    notes = []
    for fn in SAVE_TEMPLATE_FILES:
        if _child_ci(sg, fn):
            continue
        src = _child_ci(tpl, fn) if tpl else None
        if src:
            shutil.copy2(src, os.path.join(sg, fn)); notes.append("added " + fn)
        elif fn == "SAVEGAME.DIR":
            open(os.path.join(sg, fn), "wb").write(EMPTY_SAVEGAME_DIR); notes.append("created empty SAVEGAME.DIR")
        else:
            notes.append("MISSING " + fn + " (GOG save template not found; set dh_save_template in config.json)")
    return notes
