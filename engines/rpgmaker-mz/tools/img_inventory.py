# -*- coding: utf-8 -*-
"""Inventory + contact sheets for every image in img/ (decrypted on the fly).

Step 1 (always):  build an inventory and a contact sheet of the *non-CG* files.
                 CG prefixes are guessed from the biggest filename groups and skipped.
Step 2:          look at the sheets, decide which files carry baked text.

usage:  RM_GAME=<game root> python img_inventory.py [--sheet pictures/,...] [--all]
        --all    include every folder (no CG skipping)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, BASE, WORK
from img_lib import load
from PIL import Image, ImageDraw

IMGDIR = os.path.join(GAME, 'img')
SKIP_PREFIX = ('H_', 'stand_', 'RoomCG_', 'effects', 'back_', 'Heart_', 'Number', 'hand', 'penis')


def inventory():
    rows = []
    for root, _, files in os.walk(IMGDIR):
        for f in files:
            if not f.endswith('.png_'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, IMGDIR).replace('\\', '/')
            try:
                im = load(rel)
                rows.append((rel, im.width, im.height))
            except Exception as e:
                rows.append((rel, -1, -1))
    rows.sort()
    with open(os.path.join(WORK, 'img_inventory.tsv'), 'w', encoding='utf-8') as f:
        for r in rows:
            f.write('\t'.join(map(str, r)) + '\n')
    print(f'{len(rows)} images -> work/img_inventory.tsv')
    return rows


def sheet(rels, name, cell=300, cols=5):
    rows = (len(rels) + cols - 1) // cols
    canvas = Image.new('RGB', (cols * cell, rows * (cell + 16)), (255, 0, 255))
    d = ImageDraw.Draw(canvas)
    for i, rel in enumerate(rels):
        im = load(rel)
        bg = Image.new('RGBA', im.size, (250, 250, 250, 255)); bg.alpha_composite(im)
        t = bg.convert('RGB'); t.thumbnail((cell - 8, cell - 8))
        x = (i % cols) * cell; y = (i // cols) * (cell + 16)
        canvas.paste(t, (x + 4, y + 16))
        d.text((x + 4, y + 2), os.path.basename(rel)[:-5][:38], fill=(0, 0, 0))
    p = os.path.join(WORK, name)
    canvas.save(p, quality=85)
    print(f'sheet {name}: {len(rels)} images')


def main(show_all=False):
    rows = inventory()
    if show_all:
        cand = [r[0] for r in rows]
    else:
        cand = [r[0] for r in rows
                if not os.path.basename(r[0]).startswith(SKIP_PREFIX)]
    print(f'non-CG candidates: {len(cand)}')
    for i in range(0, len(cand), 40):
        sheet(cand[i:i + 40], f'img_sheet_{i//40+1}.jpg')


if __name__ == '__main__':
    main('--all' in sys.argv)
