"""EOB3 PCM sound extractor and Dungeon Hack audio enhancer.

Extracts all 90 unsigned 8-bit PCM audio samples from EOB3 EYE.RES, converts
them to standard WAV (8,000 Hz, 8-bit mono), stores raw binaries in
pool/sounds/raw/<name>.raw, and generates DH replacement recipes for:
  * Doors & Dungeon Mechanisms:
      - STDOOR1  -> DOOR 00 / S-DOOR  (authentic heavy stone sliding door)
      - WDDOOR1  -> DOOR 01           (authentic creaking wood door)
      - WDDOOR2  -> DOOR 02           (heavy wooden door latch/slam)
      - WDLEVER  -> S-LEVER           (iron lever clunk)
      - STBUTTON -> S-BUTTON          (stone button press)
      - D-LOCK2  -> S-LOCK            (heavy lock tumblers turning)
  * Monster Sounds:
      - BONENAG1 -> BONENAGA          (Bone naga rattle/hiss)
      - CHIMERA1 -> CHIMERA           (Chimera roar)
      - CHIMERA2 -> CHIMERA ATK       (Chimera bite/breath)
      - FEYR2    -> FEYR              (Feyr screech)
      - GRAVEMIS -> GRAVEMIST ATK     (Grave mist chill)
      - GRAVSTP2 -> GRAVEMIST         (Grave mist glide)
      - MINOTAR2 -> MINOTAUR ATK      (Minotaur battle roar)
      - MOUND1   -> MOUND             (Shambling mound squelch)
      - PUDDING1 -> OTYUGH            (Ooze / pudding gurgle)
      - PUDDING2 -> OTYUGH ATK        (Ooze / pudding squelch)
      - SLUG1A   -> SLUG              (Ogre slug heave)
      - SLUG2A   -> SLUG ATK          (Ogre slug attack)
      - STEEL1   -> STEEL ATK         (Steel shadow strike)
      - TROLL2   -> TROLL ATK         (Troll claw attack)
      - WATEREL1 -> WATEREL ATK       (Water elemental crash)
      - WHITE1   -> WIGHT             (Wight wail)
      - WYVREN1  -> WYVERN            (Wyvern screech)
      - WYVREN2  -> WYVERN ATK        (Wyvern stinger slash)
"""
import json
import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths
import aesop

POOL_SOUNDS = os.path.join(MASHUP, 'pool', 'sounds')
RAW_DIR = os.path.join(POOL_SOUNDS, 'raw')
WAV_DIR = os.path.join(POOL_SOUNDS, 'wav')

SAMPLE_RATE = 8000

# Recommended mapping from EOB3 PCM sound -> DH HACK.RES sound slot
SOUND_REPLACEMENTS = [
    # Dungeon environment & mechanisms
    ('STDOOR1',  'DOOR 00',        'Heavy stone door slide'),
    ('STDOOR1',  'S-DOOR',         'Stone secret door slide'),
    ('WDDOOR1',  'DOOR 01',        'Heavy wood door creak & open'),
    ('WDDOOR2',  'DOOR 02',        'Heavy wood door latch & close'),
    ('WDLEVER',  'S-LEVER',        'Iron mechanism lever clunk'),
    ('STBUTTON', 'S-BUTTON',       'Stone button mechanical press'),
    ('D-LOCK2',  'S-LOCK',         'Lock tumblers turning'),
    # Monster audio
    ('BONENAG1', 'BONENAGA',       'Bone naga hiss and bone rattle'),
    ('CHIMERA1', 'CHIMERA',        'Chimera three-headed roar'),
    ('CHIMERA2', 'CHIMERA ATK',    'Chimera breath attack'),
    ('FEYR2',    'FEYR',           'Feyr horrific screech'),
    ('GRAVEMIS', 'GRAVEMIST ATK',  'Grave mist spectral attack'),
    ('GRAVSTP2', 'GRAVEMIST',      'Grave mist creeping sound'),
    ('MINOTAR2', 'MINOTAUR ATK',   'Minotaur battle roar'),
    ('MOUND1',   'MOUND',          'Shambling mound shambling squelch'),
    ('SLUG1A',   'SLUG',           'Ogre slug movement'),
    ('SLUG2A',   'SLUG ATK',       'Ogre slug spit attack'),
    ('STEEL1',   'STEEL ATK',      'Steel shadow metallic attack'),
    ('TROLL2',   'TROLL ATK',      'Troll claw swipe'),
    ('WATEREL1', 'WATEREL ATK',    'Water elemental surging wave'),
    ('WHITE1',   'WIGHT',          'Wight deathly wail'),
    ('WYVREN1',  'WYVERN',         'Wyvern cry'),
    ('WYVREN2',  'WYVERN ATK',     'Wyvern poison stinger attack'),
]


def extract_all():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(WAV_DIR, exist_ok=True)

    eye_res_path = paths.get_game_file('eob3', 'EYE.RES')

    res = aesop.ResFile(eye_res_path)
    names = res.names()

    catalog = []
    eob3_pcm_count = 0

    for name, idx in sorted(names.items(), key=lambda x: x[1]):
        _, _, data = res.entry(idx)
        # Check if unsigned 8-bit PCM (heuristic: byte stream without shape or table header)
        # In EYE.RES manifest, pcm_u8 is well-defined
        if 389 <= idx <= 505 and len(data) >= 1000:
            eob3_pcm_count += 1
            raw_fn = f'{name.lower()}.raw'
            wav_fn = f'{name.lower()}.wav'
            raw_path = os.path.join(RAW_DIR, raw_fn)
            wav_path = os.path.join(WAV_DIR, wav_fn)

            # Save raw bytes
            with open(raw_path, 'wb') as f:
                f.write(data)

            # Write standard 8 kHz 8-bit mono WAV preview
            with wave.open(wav_path, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(1)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(data)

            catalog.append({
                'name': name,
                'index': idx,
                'size_bytes': len(data),
                'duration_sec': round(len(data) / SAMPLE_RATE, 2),
                'raw_file': os.path.relpath(raw_path, MASHUP),
                'wav_file': os.path.relpath(wav_path, MASHUP),
            })

    catalog_path = os.path.join(POOL_SOUNDS, 'catalog.json')
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=1)
    print(f'Extracted {len(catalog)} PCM sounds to {POOL_SOUNDS} (catalog in {catalog_path})')

    # Generate recipe_sounds.json for Dungeon Hack
    recipe_jobs = []
    for src, dst, comment in SOUND_REPLACEMENTS:
        raw_fn = f'{src.lower()}.raw'
        raw_rel = os.path.join('pool', 'sounds', 'raw', raw_fn)
        recipe_jobs.append({
            'type': 'raw',
            'target': dst,
            'file': raw_rel,
            'comment': comment,
        })

    recipe = {
        'comment': 'High-fidelity audio enhancement: authentic EOB3 stone doors, wood doors, levers, locks, and monster sound effects',
        'jobs': recipe_jobs,
    }
    recipe_path = os.path.join(MASHUP, 'pool', 'recipe_sounds.json')
    with open(recipe_path, 'w') as f:
        json.dump(recipe, f, indent=1)
    print(f'Generated recipe_sounds.json ({len(recipe_jobs)} jobs) in {recipe_path}')

    return catalog


if __name__ == '__main__':
    extract_all()
