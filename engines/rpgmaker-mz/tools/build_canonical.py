# -*- coding: utf-8 -*-
"""Build canonical translation map: identical source -> most common translation."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import *

def parse_out(path):
    blocks = {}; cur = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.startswith('@@'):
            cur = line[2:].strip(); blocks[cur] = []
        elif cur is not None and line.strip() != '':
            blocks[cur].append(line)
    return blocks

def main():
    trans = {}
    for fn in sorted(os.listdir(TRANS)):
        if fn.endswith('.txt'):
            trans.update(parse_out(os.path.join(TRANS, fn)))
    boxes = [json.loads(l) for l in open(os.path.join(WORK, 'boxes.jsonl'), encoding='utf-8')]
    misc = [json.loads(l) for l in open(os.path.join(WORK, 'misc.jsonl'), encoding='utf-8')]
    groups = collections.defaultdict(list)
    for b in boxes + misc:
        t = trans.get(b['id'])
        if t:
            groups[b['src']].append(normalize_lines(t))
    canon = {}
    conflicts = 0
    for src, outs in groups.items():
        if len(outs) < 3 or len(src) < 4:
            continue
        cnt = collections.Counter(tuple(o) for o in outs)
        if len(cnt) > 1:
            conflicts += 1
        best, n = cnt.most_common(1)[0]
        if n * 2 > len(outs):     # majority at least half
            canon[src] = list(best)
    print(f'sources with 3+ occurrences: {sum(1 for s, o in groups.items() if len(o) >= 3 and len(s) >= 4)}')
    print(f'inconsistent: {conflicts}, canonical entries: {len(canon)}')
    with open(os.path.join(WORK, 'canonical.json'), 'w', encoding='utf-8') as f:
        json.dump(canon, f, ensure_ascii=False, indent=0)
    print('wrote work/canonical.json')

if __name__ == '__main__':
    main()
