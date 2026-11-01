# -*- coding: utf-8 -*-
"""Integrity check: all data JSON parse, all images decrypt to valid PNG, plugins.js parses."""
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, DATA
from PIL import Image

def main():
    ok = True
    # data json
    bad = []
    for fn in sorted(os.listdir(DATA)):
        if not fn.endswith('.json'):
            continue
        try:
            json.load(open(os.path.join(DATA, fn), encoding='utf-8'))
        except Exception as e:
            bad.append((fn, str(e)[:80]))
    print(f'data json: {len([f for f in os.listdir(DATA) if f.endswith(".json")])} files, bad={len(bad)}')
    for b in bad: print('  ', b); ok = False

    # plugins.js
    s = open(os.path.join(GAME, 'js', 'plugins.js'), encoding='utf-8').read()
    try:
        json.loads(s[s.index('['):s.rindex(']') + 1])
        print('plugins.js: parses OK')
    except Exception as e:
        print('plugins.js: FAIL', e); ok = False

    # images
    KB = bytes.fromhex(json.load(open(os.path.join(DATA, 'System.json'), encoding='utf-8'))['encryptionKey'])
    imgdir = os.path.join(GAME, 'img')
    n = 0; bad_img = []
    for root, dirs, files in os.walk(imgdir):
        for f in files:
            if not f.endswith('.png_'):
                continue
            n += 1
            p = os.path.join(root, f)
            raw = open(p, 'rb').read()
            if raw[:16].hex() != '5250474d560000000003010000000000':
                bad_img.append((p, 'header')); continue
            b = bytearray(raw[16:])
            for i in range(16):
                b[i] ^= KB[i]
            try:
                Image.open(io.BytesIO(bytes(b))).verify()
            except Exception as e:
                bad_img.append((p, str(e)[:40]))
    print(f'images: {n}, bad={len(bad_img)}')
    for b in bad_img[:10]: print('  ', b)
    if bad_img: ok = False

    print('RESULT:', 'OK' if ok else 'FAIL')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
