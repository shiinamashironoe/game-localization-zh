# -*- coding: utf-8 -*-
"""Split extracted slots into translation batches."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import *

W = WORK
BD = os.path.join(W, 'batches')
os.makedirs(BD, exist_ok=True)

def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8')]

boxes = load(os.path.join(W, 'boxes.jsonl'))
misc = load(os.path.join(W, 'misc.jsonl'))

def dump(name, rows):
    with open(os.path.join(BD, name), 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return sum(len(r.get('src', '')) for r in rows)

def chunk(rows, maxchars):
    cur, n = [], 0
    for r in rows:
        L = len(r['src']) + 12
        if cur and n + L > maxchars:
            yield cur; cur, n = [], 0
        cur.append(r); n += L
    if cur: yield cur

i = 0
for part in chunk(boxes, 20000):
    i += 1
    c = dump(f'box_{i:02d}.jsonl', part)
    print(f'box_{i:02d}.jsonl  boxes={len(part):4d} chars={c}')
print('box batches', i)

# misc: choices separately (keep each 102 set together)
sets = {}
order = []
for m in misc:
    if m['kind'] != 'choice':
        continue
    key = m['id'].rsplit('|', 1)[0]
    if key not in sets:
        sets[key] = []; order.append(key)
    sets[key].append(m)
rows = []
for k in order:
    rows.append({'id': k, 'src': sets[k]})
j = 0
for part in chunk(rows, 20000):
    j += 1
    with open(os.path.join(BD, f'choice_{j:02d}.jsonl'), 'w', encoding='utf-8') as f:
        for r in part:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'choice_{j:02d}.jsonl sets={len(part)} chars={sum(len(x["src"][0]["src"])*len(x["src"]) for x in part)}')
print('choice batches', j)

others = [m for m in misc if m['kind'] not in ('choice', 'sys_names')]
k = 0
for part in chunk(others, 20000):
    k += 1
    dump(f'misc_{k:02d}.jsonl', part)
    print(f'misc_{k:02d}.jsonl n={len(part)} chars={sum(len(x["src"]) for x in part)}')
print('misc batches', k)
print('skipped sys_names', sum(1 for m in misc if m['kind'] == 'sys_names'))
