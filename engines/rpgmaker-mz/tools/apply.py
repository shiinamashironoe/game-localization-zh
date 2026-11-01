# -*- coding: utf-8 -*-
"""Apply translated batches back into data/*.json.

Always reads the pristine originals from <GAME>/_localization/backup/data_orig and
writes to <GAME>/data, so it is safe to re-run after every new batch.

usage:  RM_GAME=<game root> python apply.py [--apply]
"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import *

SRC = os.path.join(BASE, 'backup', 'data_orig')
if not os.path.isdir(SRC):
    sys.exit(f'missing pristine backup: {SRC}\n(run  python snapshot.py --apply  first)')


def parse_out(path):
    blocks = {}; cur = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.startswith('@@'):
            cur = line[2:].strip(); blocks[cur] = []
        elif cur is not None and line.strip() != '':
            blocks[cur].append(line)
    return blocks


def load_all_translations():
    out = {}; dup = collections.Counter()
    for fn in sorted(os.listdir(TRANS)):
        if not fn.endswith('.txt'):
            continue
        for k, v in parse_out(os.path.join(TRANS, fn)).items():
            if k in out:
                dup[k] += 1
            out[k] = v
    return out, dup


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8')]


CANON_PATH = os.path.join(WORK, 'canonical.json')
CANON = json.load(open(CANON_PATH, encoding='utf-8')) if os.path.exists(CANON_PATH) else {}


def main(apply=False):
    trans, dup = load_all_translations()
    boxes = load_jsonl(os.path.join(WORK, 'boxes.jsonl'))
    misc = load_jsonl(os.path.join(WORK, 'misc.jsonl'))
    missing_box = [b['id'] for b in boxes if b['id'] not in trans]
    missing_misc = [m['id'] for m in misc if m['id'] not in trans]
    print(f'translations: {len(trans)} (dup {len(dup)})')
    print(f'boxes {len(boxes)} missing {len(missing_box)}')
    print(f'misc  {len(misc)} missing {len(missing_misc)}  (sys_names etc. may be skipped on purpose)')
    if missing_box[:3]:
        print('  e.g.', missing_box[:3])
    if not apply:
        return

    by_file = collections.defaultdict(list)
    for b in boxes:
        by_file[b['file']].append(b)
    files = sorted({b['file'] for b in boxes} | {m['file'] for m in misc})
    for fn in files:
        path = os.path.join(DATA, fn)
        doc = read_json(os.path.join(SRC, fn))
        nbox = nset = 0
        lists = {ctx: lst for ctx, lst in event_lists(doc, fn)}

        # misc first: indices refer to the pristine file, and boxes change list lengths
        for m in misc:
            if m['file'] != fn:
                continue
            out = trans.get(m['id'])
            if not out:
                continue
            val = '\n'.join(normalize_lines(out))
            p = m['path']
            if p and p[0] == '@ctx':
                lst = lists.get(p[1])
                if lst is None:
                    continue
                cur = lst[p[2]]
                for k in p[3:-1]:
                    cur = cur[k]
                cur[p[-1]] = val
            else:
                set_path(doc, p, val)
            nset += 1

        # boxes: replace 401 runs (descending index keeps earlier indices valid)
        for b in sorted(by_file.get(fn, []), key=lambda b: (b['ctx'], -b['start'])):
            lst = lists.get(b['ctx'])
            if lst is None:
                continue
            out = trans.get(b['id'])
            if not out:
                continue
            out = CANON.get(b['src'], out)
            out = normalize_lines(out)
            start, run = b['start'], b['n']
            if not all(isinstance(lst[start + k], dict) and lst[start + k].get('code') == 401
                       for k in range(run)):
                print('SKIP box mismatch', b['id']); continue
            last = lst[start + run - 1]
            newcmds = []
            for ln in out:
                c = dict(last)
                c['code'] = 401
                c['indent'] = last.get('indent', 0)
                c['parameters'] = [ln]
                newcmds.append(c)
            lst[start:start + run] = newcmds
            nbox += 1

        if fn == 'System.json':
            if CFG.get('title_cn'):
                doc['gameTitle'] = CFG['title_cn']
            if CFG.get('font_filename'):
                doc['advanced']['mainFontFilename'] = CFG['font_filename']
            if CFG.get('currency_unit'):
                doc['currencyUnit'] = CFG['currency_unit']
        write_json(path, doc)
        print(f'{fn}: boxes={nbox} misc={nset}')


if __name__ == '__main__':
    main('--apply' in sys.argv)
