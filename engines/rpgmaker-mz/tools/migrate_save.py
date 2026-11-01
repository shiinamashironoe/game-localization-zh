# -*- coding: utf-8 -*-
"""Migrate RPG MZ save files (actor names / save title) to Chinese.

Reads cfg.json:  save_title_from, title_cn, actor_rename [[jp, cn], ...]
Backups are written next to the save with a timestamp suffix.

usage:  RM_GAME=<game root> python migrate_save.py [--apply]
"""
import json, os, shutil, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, CFG

SAVE = os.path.join(GAME, 'save')

def decode(path):
    raw = open(path, 'rb').read()
    latin = raw.decode('utf-8').encode('latin-1')     # MZ writes a pako binary string as UTF-8
    return json.loads(zlib.decompress(latin).decode('utf-8'))

def encode(path, obj):
    data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    out = zlib.compress(data, 1).decode('latin-1').encode('utf-8')
    open(path, 'wb').write(out)

def main(apply=False):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    title_from = CFG.get('save_title_from')
    title_cn = CFG.get('title_cn')
    renames = {jp: cn for jp, cn in CFG.get('actor_rename', [])}
    for name in sorted(os.listdir(SAVE)) if os.path.isdir(SAVE) else []:
        if not name.endswith('.rmmzsave'):
            continue
        p = os.path.join(SAVE, name)
        obj = decode(p)
        tmp = p + '.rt'
        encode(tmp, obj)
        ok = decode(tmp) == obj
        os.remove(tmp)
        changed = []
        if name == 'global.rmmzsave' and isinstance(obj, list) and title_from and title_cn:
            for s in obj:
                if isinstance(s, dict) and s.get('title') == title_from:
                    s['title'] = title_cn; changed.append('global.title')
        else:
            for a in obj.get('actors', {}).get('_data', []):
                if isinstance(a, dict) and a.get('_name') in renames:
                    a['_name'] = renames[a['_name']]
                    changed.append(f"actor{a.get('_actorId')}._name")
        print(f'{name}: roundtrip={ok} changes={changed}')
        if apply and changed:
            bak = f'{p}.bak-zh-{stamp}'
            shutil.copyfile(p, bak)
            encode(p, obj)
            print('   wrote + backup', os.path.basename(bak))

if __name__ == '__main__':
    main('--apply' in sys.argv)
