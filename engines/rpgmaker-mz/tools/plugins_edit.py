# -*- coding: utf-8 -*-
"""Targeted string replacements inside js/plugins.js (UI labels baked into plugin params).

Driven by cfg.json:
    "plugin_string_pairs": [["A/Bボタン入れ替え", "A/B键互换", 1], ...]
        [japanese, chinese, expected_count]   count -1 = don't check

Plugin params hold labels shown at runtime (option names, job panel, custom menu, etc.).
Plugin *descriptions* also contain Japanese but are editor-only - they are left alone.

usage:  RM_GAME=<game root> python plugins_edit.py [--apply]
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, CFG, KANA

P = os.path.join(GAME, 'js', 'plugins.js')

def main(apply=False):
    src = open(P, encoding='utf-8').read()
    pairs = CFG.get('plugin_string_pairs', [])
    if not pairs:
        print('cfg.json has no plugin_string_pairs'); return
    out = src
    bad = 0
    done = 0
    for jp, zh, exp in pairs:
        n = out.count(jp)
        already = out.count(zh)
        if n == 0 and already:
            done += 1
            print(f'  0  {jp[:32]!r} -> already applied ({already}x)')
            continue
        flag = '' if exp < 0 or n == exp else '  <-- count mismatch'
        if flag:
            bad += 1
        print(f'{n:3d}  {jp[:32]!r} -> {zh}{flag}')
        out = out.replace(jp, zh)
    left = len(KANA.findall(out))
    print(f'applied={done} pending-ok={len(pairs)-done-bad} mismatch={bad}')
    print(f'kana left in plugins.js: {left} (mostly @desc / comment lines - check manually if large)')
    if bad:
        print('fix the mismatched pairs before --apply')
        return
    if apply:
        json.loads(out[out.index('['):out.rindex(']') + 1])   # keep it parseable
        open(P, 'w', encoding='utf-8', newline='\n').write(out)
        print('WROTE', P)

if __name__ == '__main__':
    main('--apply' in sys.argv)
