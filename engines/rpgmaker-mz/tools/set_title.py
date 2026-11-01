# -*- coding: utf-8 -*-
"""Set the Chinese game title in data/System.json, package.json and index.html.

index.html <title> wins over package.json in NW.js, so both must change.

usage:  RM_GAME=<game root> python set_title.py [--apply]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, DATA, CFG, read_json, write_json

TITLE = CFG.get('title_cn')

def main(apply=False):
    if not TITLE:
        sys.exit('cfg.json needs "title_cn"')
    sp = os.path.join(DATA, 'System.json')
    doc = read_json(sp)
    if doc.get('gameTitle') != TITLE:
        print(f'System.gameTitle: {doc.get("gameTitle")!r} -> {TITLE!r}')
        if apply:
            doc['gameTitle'] = TITLE
            write_json(sp, doc)

    pp = os.path.join(GAME, 'package.json')
    if os.path.exists(pp):
        doc = json.loads(open(pp, encoding='utf-8').read())
        old = doc.get('window', {}).get('title')
        if old != TITLE:
            print(f'package.window.title: {old!r} -> {TITLE!r}')
            if apply:
                doc['window']['title'] = TITLE
                open(pp, 'w', encoding='utf-8', newline='\n').write(
                    json.dumps(doc, ensure_ascii=False, indent=4) + '\n')

    ih = os.path.join(GAME, 'index.html')
    if os.path.exists(ih):
        s = open(ih, encoding='utf-8').read()
        import re
        new = re.sub(r'<title>.*?</title>', f'<title>{TITLE}</title>', s, count=1)
        if new != s:
            print('index.html <title> updated')
            if apply:
                open(ih, 'w', encoding='utf-8', newline='\n').write(new)

if __name__ == '__main__':
    main('--apply' in sys.argv)
