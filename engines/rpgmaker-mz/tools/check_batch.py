# -*- coding: utf-8 -*-
"""Validate a translated batch: ids, control codes, kana residue, width."""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import KANA

CTRL = re.compile(r'\\[A-Za-z]+\[[^\]]*\]|\\[A-Za-z]|\\\\')
WIDTH_MAX = int(os.environ.get('WIDTH_MAX', '38'))

def parse_out(path):
    blocks = {}
    cur = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.startswith('@@'):
            cur = line[2:].strip()
            blocks[cur] = []
        elif cur is not None:
            if line.strip() == '':
                continue
            blocks[cur].append(line)
    return blocks

def chars_wide(s):
    n = 0
    for ch in s:
        n += 1 if ord(ch) > 0x2E80 else 0.5
    return n

def main(inp, outp):
    rows = [json.loads(l) for l in open(inp, encoding='utf-8')]
    out = parse_out(outp)
    problems = []
    missing = [r['id'] for r in rows if r['id'] not in out]
    extra = [k for k in out if k not in {r['id'] for r in rows}]
    if missing: problems.append(f'缺少 {len(missing)} 条，例如 {missing[:5]}')
    if extra: problems.append(f'多余 id {len(extra)} 条，例如 {extra[:5]}')
    kana_hits = []; code_hits = []; wide = []
    for r in rows:
        got = out.get(r['id'])
        if got is None: continue
        src_codes = collections.Counter(CTRL.findall(r['src']))
        dst_codes = collections.Counter(CTRL.findall('\n'.join(got)))
        if src_codes != dst_codes:
            code_hits.append((r['id'], dict(src_codes - dst_codes), dict(dst_codes - src_codes)))
        for ln in got:
            if KANA.search(CTRL.sub('', ln)): kana_hits.append((r['id'], ln))
            if chars_wide(ln) > WIDTH_MAX: wide.append((r['id'], round(chars_wide(ln), 1), ln[:50]))
    if kana_hits: problems.append(f'残留假名 {len(kana_hits)} 行，例如 {kana_hits[:3]}')
    if code_hits: problems.append(f'控制码不一致 {len(code_hits)} 条，例如 {code_hits[:3]}')
    print(f'entries={len(rows)} translated={len(rows)-len(missing)}')
    print(f'kana={len(kana_hits)} code_mismatch={len(code_hits)} too_wide={len(wide)}')
    if wide: print('  超宽示例:', wide[:5])
    if problems:
        for p in problems: print('PROBLEM:', p)
        return 1
    print('OK')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
