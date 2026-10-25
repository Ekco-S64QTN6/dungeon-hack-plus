"""Save-slot backup, restore, and inspection helper for Dungeon Hack.

Manages saves across builds and protects against Iron Man permadeath.

Usage:
  python3 -I mashup/tools/savegame.py list
  python3 -I mashup/tools/savegame.py inspect [DIR]
  python3 -I mashup/tools/savegame.py backup BUILD_NAME [--label LABEL]
  python3 -I mashup/tools/savegame.py restore BACKUP_NAME BUILD_NAME
"""
import datetime
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MASHUP = os.path.dirname(HERE)
SAVES_DIR = os.path.join(MASHUP, 'backup', 'saves')


def read_pc_name(sg_dir):
    p = os.path.join(sg_dir, 'PC.DAT')
    if os.path.exists(p):
        raw = open(p, 'rb').read()
        null_idx = raw.find(b'\0')
        if null_idx != -1:
            return raw[:null_idx].decode('latin1', errors='replace')
    return 'Unknown'


def read_seed(sg_dir):
    p = os.path.join(sg_dir, 'SEED.TXT')
    if os.path.exists(p):
        for line in open(p, errors='replace'):
            if 'Seed=' in line:
                return line.strip()
    lp = os.path.join(sg_dir, 'LEVELS.DAT')
    if os.path.exists(lp):
        raw = open(lp, 'rb').read()
        if len(raw) >= 4:
            s = struct.unpack('<I', raw[:4])[0]
            return f'Seed={s:08X}'
    return 'Unknown'


def inspect_save(sg_dir):
    """Return dict of savegame details."""
    if not os.path.isdir(sg_dir):
        return None
    files = sorted(os.listdir(sg_dir))
    pc = read_pc_name(sg_dir)
    seed = read_seed(sg_dir)
    fea_count = len([f for f in files if f.startswith('FEA') and f.endswith('.DAT')])
    total_sz = sum(os.path.getsize(os.path.join(sg_dir, f)) for f in files if os.path.isfile(os.path.join(sg_dir, f)))
    return {
        'path': sg_dir,
        'character': pc,
        'seed_info': seed,
        'levels': fea_count,
        'file_count': len(files),
        'total_bytes': total_sz,
    }


def cmd_list():
    os.makedirs(SAVES_DIR, exist_ok=True)
    backups = sorted(os.listdir(SAVES_DIR))
    if not backups:
        print('No save backups found in', SAVES_DIR)
        return

    print(f'Save backups in {SAVES_DIR}:\n')
    print('| Name | Character | Seed | Levels | Size |')
    print('|---|---|---|---|---|')
    for b in backups:
        bp = os.path.join(SAVES_DIR, b)
        info = inspect_save(bp)
        if info:
            print(f'| {b} | {info["character"]} | {info["seed_info"]} | {info["levels"]} | {info["total_bytes"]//1024} KB |')


def cmd_backup(build_name, label=None):
    src = os.path.join(MASHUP, 'build', build_name, 'savegame')
    if not os.path.isdir(src):
        # Check fixture or base
        src = os.path.join(MASHUP, 'fixtures', build_name)
    if not os.path.isdir(src):
        sys.exit(f'Save directory not found: {src}')

    info = inspect_save(src)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    char_safe = ''.join(c if c.isalnum() else '_' for c in info['character']).strip('_')
    tag = f'_{label}' if label else ''
    dst_name = f'{ts}_{build_name}_{char_safe}{tag}'
    dst = os.path.join(SAVES_DIR, dst_name)

    shutil.copytree(src, dst)
    print(f'Backed up save from {src} -> {dst}')
    print(f'  Character: {info["character"]}')
    print(f'  Seed:      {info["seed_info"]}')
    print(f'  Files:     {info["file_count"]} ({info["total_bytes"]} bytes)')


def cmd_restore(backup_name, target_build):
    src = os.path.join(SAVES_DIR, backup_name)
    if not os.path.isdir(src):
        sys.exit(f'Backup not found: {src}')

    dst = os.path.join(MASHUP, 'build', target_build, 'savegame')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    info = inspect_save(dst)
    print(f'Restored {backup_name} -> {dst}')
    print(f'  Character: {info["character"]}')
    print(f'  Seed:      {info["seed_info"]}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == 'list':
        cmd_list()
    elif args[0] == 'inspect':
        sg = args[1] if len(args) > 1 else os.path.join(MASHUP, 'fixtures', 'savegame')
        inf = inspect_save(sg)
        print(json.dumps(inf, indent=2))
    elif args[0] == 'backup':
        bname = args[1] if len(args) > 1 else 'savegame'
        lbl = args[3] if len(args) > 3 and args[2] == '--label' else None
        cmd_backup(bname, lbl)
    elif args[0] == 'restore':
        if len(args) < 3:
            sys.exit('Usage: savegame.py restore BACKUP_NAME TARGET_BUILD')
        cmd_restore(args[1], args[2])
    else:
        sys.exit(__doc__)
