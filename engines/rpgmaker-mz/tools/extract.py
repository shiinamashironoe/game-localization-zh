# -*- coding: utf-8 -*-
"""Extract all display-text slots into boxes.jsonl / misc.jsonl."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import *

MISC_DB = {'Items.json': ('name', 'description'), 'Weapons.json': ('name', 'description'),
           'Armors.json': ('name', 'description'), 'Skills.json': ('name', 'description'),
           'Actors.json': ('name', 'nickname', 'profile'), 'Classes.json': ('name',),
           'States.json': ('name',), 'Enemies.json': ('name',)}

boxes = []
misc = []

def add_misc(idx, kind, fname, path, value):
    if not value or not value.strip():
        return
    misc.append({'id': idx, 'kind': kind, 'file': fname, 'path': list(path), 'src': value})

files = sorted(f for f in os.listdir(DATA) if f.endswith('.json'))
for fn in files:
    doc = read_json(os.path.join(DATA, fn))

    if fn == 'MapInfos.json':
        for k, m in enumerate(doc):
            if isinstance(m, dict) and isinstance(m.get('name'), str) and m['name'].strip():
                add_misc(f'MapInfos.json|{k}|name', 'mapinfo', fn, (k, 'name'), m['name'])

    elif fn == 'CommonEvents.json' or fn.startswith('Map'):
        for ctx, lst in event_lists(doc, fn):
            i = 0
            n = len(lst)
            while i < n:
                c = lst[i]
                if not isinstance(c, dict):
                    i += 1; continue
                code = c.get('code'); ps = c.get('parameters') or []
                if code == 401:
                    j = i
                    lines = []
                    while j < n and isinstance(lst[j], dict) and lst[j].get('code') == 401:
                        lines.append((lst[j].get('parameters') or [''])[0] if lst[j].get('parameters') else '')
                        j += 1
                    txt = '\n'.join(lines)
                    if txt.strip():
                        boxes.append({'id': f'{fn}|{ctx}|{i}', 'file': fn, 'ctx': ctx,
                                      'start': i, 'n': j - i, 'src': txt})
                    i = j
                    continue
                if code == 102 and ps and isinstance(ps[0], list):
                    for k, s in enumerate(ps[0]):
                        add_misc(f'{fn}|{ctx}|{i}|102|{k}', 'choice', fn, ('@ctx', ctx, i, 'parameters', 0, k), s)
                elif code == 405 and ps:
                    add_misc(f'{fn}|{ctx}|{i}|405', 'scroll', fn, ('@ctx', ctx, i, 'parameters', 0), ps[0])
                elif code in (320, 321, 322) and len(ps) > 1:
                    add_misc(f'{fn}|{ctx}|{i}|{code}', 'actor', fn, ('@ctx', ctx, i, 'parameters', 1), ps[1])
                elif code in (356, 357) and ps and ps[0] == 'DTextPicture':
                    for ai, a in enumerate(ps):
                        if isinstance(a, dict) and isinstance(a.get('text'), str):
                            add_misc(f'{fn}|{ctx}|{i}|{code}|text', 'dtext', fn,
                                     ('@ctx', ctx, i, 'parameters', ai, 'text'), a['text'])
                i += 1

    elif fn in MISC_DB:
        for oi, o in enumerate(doc):
            if not isinstance(o, dict):
                continue
            for k in MISC_DB[fn]:
                v = o.get(k)
                if isinstance(v, str):
                    add_misc(f'{fn}|{oi}|{k}', f'db_{k}', fn, (oi, k), v)

    elif fn == 'System.json':
        for key in ('elements', 'skillTypes', 'weaponTypes', 'armorTypes', 'equipTypes'):
            for k, v in enumerate(doc.get(key) or []):
                if isinstance(v, str) and v:
                    add_misc(f'System.json|{key}|{k}', 'sys_list', fn, (key, k), v)
        terms = doc.get('terms') or {}
        for cat in ('basic', 'commands', 'params'):
            for k, v in enumerate(terms.get(cat) or []):
                if isinstance(v, str) and v:
                    add_misc(f'System.json|terms.{cat}|{k}', 'sys_terms', fn, ('terms', cat, k), v)
        for k, v in (terms.get('messages') or {}).items():
            if isinstance(v, str) and v:
                add_misc(f'System.json|terms.messages|{k}', 'sys_msgs', fn, ('terms', 'messages', k), v)
        for key in ('variables', 'switches'):
            for k, v in enumerate(doc.get(key) or []):
                if isinstance(v, str) and v:
                    add_misc(f'System.json|{key}|{k}', 'sys_names', fn, (key, k), v)

    elif fn == 'MapInfos.json':
        for k, m in enumerate(doc):
            if isinstance(m, dict) and isinstance(m.get('name'), str) and m['name'].strip():
                add_misc(f'MapInfos.json|{k}|name', 'mapinfo', fn, (k, 'name'), m['name'])

# write
with open(os.path.join(WORK, 'boxes.jsonl'), 'w', encoding='utf-8') as f:
    for b in boxes:
        f.write(json.dumps(b, ensure_ascii=False) + '\n')
with open(os.path.join(WORK, 'misc.jsonl'), 'w', encoding='utf-8') as f:
    for m in misc:
        f.write(json.dumps(m, ensure_ascii=False) + '\n')

print('boxes', len(boxes), 'lines', sum(b['n'] for b in boxes), 'chars', sum(len(b['src']) for b in boxes))
import collections
c = collections.Counter(m['kind'] for m in misc)
print('misc', len(misc), dict(c))
print('misc chars', sum(len(m['src']) for m in misc))
