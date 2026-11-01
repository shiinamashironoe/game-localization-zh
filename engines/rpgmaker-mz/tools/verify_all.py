# -*- coding: utf-8 -*-
"""Post-apply verification: kana residue, kanji-Japanese words, control codes, width."""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import *

KANJI_JP = ['体力', '気持', '時間', '様子', '当た', '発言', '残念', '収入', '十分', '無理', '心配', '大丈',
            '了解', '確認', '選択', '変更', '開始', '終了', '設定', '戻', '閉', '開', '使', '持', '作', '書',
            '読', '見', '聞', '話', '売', '買', '払', '飛', '走', '歩', '立', '座', '眠', '起', '洗', '着',
            '脱', '笑', '泣', '怒', '喜', '考', '思', '知', '分', '忘', '覚', '教', '習', '勉', '強', '弱']
BANNED = ['の', 'を', 'は', 'が', 'に', 'で', 'と', 'も', 'から', 'まで', 'です', 'ます', 'した', 'して',
          'する', 'ある', 'いる', 'こと', 'もの', 'ため', 'よう', 'そう', 'これ', 'それ', 'あれ']

unbalanced = []

def check_codes(s):
    # every \x[ must have ]
    for m in re.finditer(r'\\[A-Za-z]+\[', s):
        if s.find(']', m.end()) < 0:
            unbalanced.append(s[:60])

def main():
    rows = []
    files = sorted(f for f in os.listdir(DATA) if f.endswith('.json'))
    total = 0
    kana = []
    jpword = []
    for fn in files:
        doc = read_json(os.path.join(DATA, fn))
        if fn == 'MapInfos.json':
            for m in doc:
                if isinstance(m, dict) and isinstance(m.get('name'), str):
                    rows.append((fn, m['name'], 'mapinfo'))
        if fn == 'CommonEvents.json' or (fn.startswith('Map') and fn != 'MapInfos.json'):
            for ctx, lst in event_lists(doc, fn):
                for i, c in enumerate(lst):
                    if not isinstance(c, dict):
                        continue
                    code = c.get('code'); ps = c.get('parameters') or []
                    if code == 401 and ps:
                        rows.append((fn, ps[0], f'{ctx}:{i}'))
                    elif code == 102 and ps and isinstance(ps[0], list):
                        for s in ps[0]:
                            rows.append((fn, s, f'{ctx}:{i}:choice'))
                    elif code in (320, 321, 322) and len(ps) > 1:
                        rows.append((fn, ps[1], f'{ctx}:{i}'))
        elif fn in ('Items.json', 'Weapons.json', 'Armors.json', 'Skills.json', 'Actors.json', 'Classes.json'):
            for o in doc:
                if isinstance(o, dict):
                    for k in ('name', 'description', 'nickname', 'profile'):
                        if isinstance(o.get(k), str):
                            rows.append((fn, o[k], k))
        elif fn == 'System.json':
            t = doc.get('terms', {})
            for cat in ('basic', 'commands', 'params'):
                for s in t.get(cat) or []:
                    if isinstance(s, str):
                        rows.append((fn, s, cat))
            for k, s in (t.get('messages') or {}).items():
                if isinstance(s, str):
                    rows.append((fn, s, k))
            for key in ('elements', 'skillTypes', 'weaponTypes', 'armorTypes', 'equipTypes'):
                for s in doc.get(key) or []:
                    if isinstance(s, str):
                        rows.append((fn, s, key))

    total = len(rows)
    for fn, s, ctx in rows:
        if not isinstance(s, str) or not s.strip():
            continue
        check_codes(s)
        if KANA.search(CODE.sub('', s)):
            kana.append((fn, ctx, s[:60]))
        # kanji-only japanese heuristics: hiragana-only particles would already be kana;
        # check banned particles at end of line (japanese word order)
        for w in BANNED:
            if len(w) > 1 and w in s:
                jpword.append((fn, ctx, w, s[:50]))
                break

    print(f'total display strings: {total}')
    print(f'kana residue: {len(kana)}')
    for r in kana[:20]: print('  ', r)
    print(f'japanese particle hits: {len(jpword)}')
    for r in jpword[:20]: print('  ', r)
    print(f'unbalanced control code: {len(unbalanced)}')
    for r in unbalanced[:10]: print('  ', r)

    # width check
    over = []
    for fn, s, ctx in rows:
        if not isinstance(s, str):
            continue
        for ln in s.split('\n'):
            w = sum(1 if ord(ch) > 0x2E80 else 0.5 for ch in ln)
            if w > 45:
                over.append((fn, ctx, round(w, 1), ln[:40]))
    print(f'lines wider than 45: {len(over)}')
    for r in over[:10]: print('  ', r)
    return 0 if not kana and not unbalanced else 1

if __name__ == '__main__':
    sys.exit(main())
