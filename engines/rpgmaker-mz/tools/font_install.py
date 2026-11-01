# -*- coding: utf-8 -*-
"""Install a Chinese main font and point System.json at it.

cfg.json: "font_filename": "NotoSansSC-game.otf"
Font file is copied from --font <path> (default: skill assets NotoSansSC-game.otf).

usage:  RM_GAME=<game root> python font_install.py --install [--font <otf>]
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, DATA, TRANS, CFG, read_json, write_json, normalize_lines
from fontTools.ttLib import TTFont

SKILL_FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'assets', 'NotoSansSC-game.otf')

def install(src):
    name = CFG.get('font_filename')
    if not name:
        sys.exit('cfg.json needs "font_filename"')
    shutil.copyfile(src, os.path.join(GAME, 'fonts', name))
    p = os.path.join(DATA, 'System.json')
    doc = read_json(p)
    old = doc['advanced'].get('mainFontFilename')
    doc['advanced']['mainFontFilename'] = name
    write_json(p, doc)
    print(f'mainFontFilename: {old} -> {name}')

def coverage():
    name = CFG.get('font_filename')
    if not name:
        return
    t = TTFont(os.path.join(GAME, 'fonts', name), lazy=True)
    cmap = set()
    for tb in t['cmap'].tables:
        cmap |= set(tb.cmap)
    chars = set()
    for fn in os.listdir(TRANS):
        if fn.endswith('.txt'):
            for line in open(os.path.join(TRANS, fn), encoding='utf-8'):
                if not line.startswith('@@'):
                    chars |= set(''.join(normalize_lines([line.rstrip('\n')])))
    miss = sorted(c for c in chars if ord(c) not in cmap and not c.isspace())
    print(f'unique chars in translations: {len(chars)}, missing in font: {len(miss)}')
    if miss:
        print('missing (browser falls back, no tofu expected):', ''.join(miss[:80]))

if __name__ == '__main__':
    args = sys.argv[1:]
    if '--install' in args:
        src = SKILL_FONT
        if '--font' in args:
            src = args[args.index('--font') + 1]
        install(src)
    coverage()
