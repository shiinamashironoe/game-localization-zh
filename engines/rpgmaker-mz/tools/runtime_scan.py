# -*- coding: utf-8 -*-
"""Scan plugin JS + plugins.js for Japanese strings that are DISPLAYED at runtime.

Two classes of false positives must be ignored:
  * plugin header (@plugindesc / @param text / @help) - editor metadata
  * plugin @command param labels - editor metadata

What matters is string literals inside executable code (arrays of names, format strings,
drawText arguments, hardcoded UI labels).

usage:  RM_GAME=<game root> python runtime_scan.py [--all]
        --all  also list strings found in plugins.js params (those are usually real UI labels)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, KANA

PLUG = os.path.join(GAME, 'js', 'plugins')
PJS = os.path.join(GAME, 'js', 'plugins.js')
STR = re.compile(r"""'([^'\\\n]{1,80})'|"([^"\\\n]{1,80})\"""")


def strip_header(src):
    """Drop the leading /*: ... */ block (plugin metadata)."""
    i = src.find('/*:')
    if i < 0:
        return src
    j = src.find('*/', i)
    return src[j + 2:] if j > 0 else src


def main(show_all=False):
    print('== executable string literals with kana ==')
    for fn in sorted(os.listdir(PLUG)):
        if not fn.endswith('.js'):
            continue
        src = open(os.path.join(PLUG, fn), encoding='utf-8', errors='replace').read()
        body = strip_header(src)
        body = re.sub(r'^\s*//.*$', '', body, flags=re.M)
        hits = []
        for m in STR.finditer(body):
            s = m.group(1) if m.group(1) is not None else m.group(2)
            if KANA.search(s):
                line = body[:m.start()].count('\n') + 1
                hits.append((line, s))
        if hits:
            print(f'\n-- {fn} ({len(hits)})')
            seen = set()
            for line, s in hits:
                if s in seen:
                    continue
                seen.add(s)
                print(f'   L{line}: {s}')

    if show_all:
        print('\n== plugins.js parameters with kana ==')
        s = open(PJS, encoding='utf-8').read()
        d = json.loads(s[s.index('['):s.rindex(']') + 1])
        for p in d:
            for k, v in (p.get('parameters') or {}).items():
                if isinstance(v, str) and KANA.search(v):
                    print(f"  {p.get('name')}.{k} = {v[:120]}")


if __name__ == '__main__':
    main('--all' in sys.argv)
