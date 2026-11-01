# -*- coding: utf-8 -*-
"""Shared helpers for RPG Maker MZ localization.

Target game is taken from the RM_GAME environment variable (or --game).

Project-specific settings live in  <GAME>/_localization/cfg.json  :

{
  "title_cn": "观摩大叔",
  "font_filename": "NotoSansSC-game.otf",
  "currency_unit": "日元",
  "save_title_from": "見抜きおじさん",
  "actor_rename": [["おじさん", "大叔"]],
  "plugin_string_pairs": [["A/Bボタン入れ替え", "A/B键互换", 1]]
}
"""
import json, os, re, sys

GAME = os.environ.get('RM_GAME')
if not GAME:
    for i, a in enumerate(sys.argv):
        if a == '--game' and i + 1 < len(sys.argv):
            GAME = sys.argv[i + 1]
            break
if not GAME:
    sys.exit('set RM_GAME or pass --game <game root>')
GAME = os.path.abspath(GAME)
DATA = os.path.join(GAME, 'data')
BASE = os.path.join(GAME, '_localization')
WORK = os.path.join(BASE, 'work')
TRANS = os.path.join(BASE, 'translations')
for _d in (WORK, TRANS):
    os.makedirs(_d, exist_ok=True)

CFG_PATH = os.path.join(BASE, 'cfg.json')
CFG = json.load(open(CFG_PATH, encoding='utf-8')) if os.path.exists(CFG_PATH) else {}

KANA = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
CJK = re.compile(r'[\u4e00-\u9fff]')
# message control codes: \ac[270] \ms[3] \n[1] \v[62] \c[17] \> \. \| \! \{ \} \\ \$ ...
CODE = re.compile(r'\\[A-Za-z]+\[[^\]]*\]|\\[A-Za-z]|\\\\|\\[.|!|>|<|^|{|}]')

# cross-batch text normalisation (character-level fixes applied before canonical vote + apply).
# Add project-specific name harmonisation here.
NORMALIZE = [
    ('・', '·'),
    ('¥', '￥'),
    ('◯', '○'),
    ('欸', '诶'),
    ('\ufeff', ''),
]


def normalize_lines(lines):
    out = []
    for ln in lines:
        for a, b in NORMALIZE + [tuple(p) for p in CFG.get('normalize_pairs', [])]:
            ln = ln.replace(a, b)
        out.append(ln)
    return out


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, path)


def event_lists(doc, fname):
    """Yield (ctx, list) for every command list in a data document."""
    if isinstance(doc, list):
        for ev in doc:                       # CommonEvents.json
            if isinstance(ev, dict) and 'list' in ev:
                yield f"CE{ev.get('id')}", ev['list']
        return
    if isinstance(doc, dict) and 'events' in doc:      # MapXXX.json
        mid = doc.get('id') or fname.replace('Map', '').replace('.json', '')
        for ei, ev in enumerate(doc.get('events', [])):
            if not isinstance(ev, dict):
                continue
            for pi, pg in enumerate(ev.get('pages', [])):
                if 'list' in pg:
                    yield f"M{mid}_E{ei}_P{pi}", pg['list']


def get_path(obj, path):
    cur = obj
    for k in path:
        cur = cur[k]
    return cur


def set_path(obj, path, val):
    cur = obj
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = val
