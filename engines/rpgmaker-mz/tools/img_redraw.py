# -*- coding: utf-8 -*-
"""Redraw Chinese labels on RPG MZ images, driven by _localization/img_cfg.json.

Each item:
  {
    "file": "pictures/NamePlate.png_",
    "mode": "hgrad" | "rowwise" | "mask" | "bar",
    "box":  [x0, y0, x1, y1],          # area to clear / where text goes
    "text": "大叔",
    "size": 40,
    "color":  [255,255,255,255],
    "shadow": [30,30,30,200],
    "samples": [99, 233, 368],          # hgrad only: x columns to sample
    "sx": 65,                           # rowwise only: clean column inside the widget
    "text_box": [x0,y0,x1,y1]           # optional: draw area if different from box
  }

modes:
  hgrad   - widget has a horizontal gradient (name plates, title buttons): rebuild the band by
            interpolating between sample columns, keeping the original alpha shape.
  rowwise - widget is horizontally uniform (pills, bars): fill each row with the colour of a
            text-free column (sx).
  mask    - text sits on artwork: erase only glyph pixels (bright/dark) by row-fill from the
            nearest clean pixel, then draw.
  bar     - translucent bar fading horizontally: constant RGB + per-column alpha.

usage:  RM_GAME=<game root> python img_redraw.py [--preview]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, BASE, CFG
from img_lib import load, save
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(BASE, 'work')
BACKUP = os.path.join(BASE, 'backup', 'img_orig')
FONT = os.path.join(GAME, 'fonts', CFG.get('font_filename', 'NotoSansSC-game.otf'))
CFG_PATH = os.path.join(BASE, 'img_cfg.json')


def fill_hgrad(im, box, cols):
    x0, y0, x1, y1 = box
    src = im.copy(); px = im.load()
    samples = [(cx, src.getpixel((cx, (y0 + y1) // 2))) for cx in cols]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if x <= samples[0][0]:
                col = samples[0][1]
            elif x >= samples[-1][0]:
                col = samples[-1][1]
            else:
                col = samples[-1][1]
                for i in range(len(samples) - 1):
                    ax, ac = samples[i]; bx, bc = samples[i + 1]
                    if ax <= x <= bx:
                        t = (x - ax) / max(1, bx - ax)
                        col = tuple(int(ac[k] + (bc[k] - ac[k]) * t) for k in range(4))
                        break
            a = src.getpixel((x, y))[3]
            px[x, y] = (col[0], col[1], col[2], a)


def fill_rowwise(im, box, sx):
    x0, y0, x1, y1 = box
    src = im.copy(); px = im.load()
    for y in range(y0, y1):
        col = src.getpixel((sx, y))
        for x in range(x0, x1):
            px[x, y] = col


def fill_bar(im, box):
    x0, y0, x1, y1 = box
    px = im.load()
    from collections import Counter
    cnt = Counter()
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            p = px[x, y]
            if p[3] > 60 and not (p[0] > 200 and p[1] > 200 and p[2] > 200):
                cnt[(p[0] // 4 * 4, p[1] // 4 * 4, p[2] // 4 * 4)] += 1
    if not cnt:
        return
    rgb = cnt.most_common(1)[0][0]
    alpha = []
    for x in range(im.width):
        vals = sorted(a for a in (px[x, y][3] for y in range(y0, y1)) if a < 200)
        alpha.append(vals[len(vals) // 2] if vals else 0)
    for x in range(im.width):
        if alpha[x] < 3:
            l = alpha[x - 1] if x else 0
            r = alpha[x + 1] if x + 1 < im.width else 0
            alpha[x] = max(l, r)
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = (rgb[0], rgb[1], rgb[2], alpha[x])


def erase_mask(im, box, bright=200, dark=110, dilate=1):
    x0, y0, x1, y1 = box
    src = im.copy(); px = im.load()

    def is_text(p):
        if p[3] < 40:
            return False
        l = (p[0] * 299 + p[1] * 587 + p[2] * 114) / 1000
        return l > bright or l < dark

    m = [[is_text(src.getpixel((x, y))) for x in range(x0, x1)] for y in range(y0, y1)]
    h, w = len(m), len(m[0])
    for _ in range(dilate):
        d = [r[:] for r in m]
        for yy in range(h):
            for xx in range(w):
                if m[yy][xx]:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = yy + dy, xx + dx
                            if 0 <= ny < h and 0 <= nx < w:
                                d[ny][nx] = True
        m = d
    for yy, y in enumerate(range(y0, y1)):
        x = x0
        while x < x1:
            if not m[yy][x - x0]:
                x += 1; continue
            xs = x
            while x < x1 and m[yy][x - x0]:
                x += 1
            xe = x
            left = right = None
            lx = xs - 1
            while lx >= 0:
                p = src.getpixel((lx, y))
                if p[3] > 40 and not is_text(p):
                    left = (xs - lx, p); break
                lx -= 1
            rx = xe
            while rx < im.width:
                p = src.getpixel((rx, y))
                if p[3] > 40 and not is_text(p):
                    right = (rx - xe + 1, p); break
                rx += 1
            cands = [c for c in (left, right) if c]
            col = min(cands, key=lambda t: t[0])[1] if cands else (0, 0, 0, 0)
            for xx in range(xs, xe):
                px[xx, y] = col


def draw_text(im, box, text, size, color, shadow, off=(0, 2), bold=1):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, size)
    while size > 8 and d.textlength(text, font=f) > (x1 - x0) - 6:
        size -= 1
        f = ImageFont.truetype(FONT, size)
    tw = d.textlength(text, font=f)
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - size) / 2
    for ox in range(bold):
        for oy in range(bold):
            d.text((tx + off[0] + ox, ty + off[1] + oy), text, font=f, fill=tuple(shadow))
    d.text((tx, ty), text, font=f, fill=tuple(color))


def main(preview=False):
    if not os.path.exists(CFG_PATH):
        sys.exit(f'missing {CFG_PATH}')
    cfg = json.load(open(CFG_PATH, encoding='utf-8'))
    imgs = []
    for it in cfg['items']:
        im = load(it['file'])
        mode = it.get('mode', 'mask')
        box = it['box']
        if mode == 'hgrad':
            fill_hgrad(im, box, it['samples'])
        elif mode == 'rowwise':
            fill_rowwise(im, box, it['sx'])
        elif mode == 'bar':
            fill_bar(im, box)
        else:
            erase_mask(im, box, it.get('bright', 200), it.get('dark', 110), it.get('dilate', 1))
        draw_text(im, it.get('text_box', box), it['text'], it.get('size', 28),
                  it.get('color', [255, 255, 255, 255]), it.get('shadow', [30, 30, 30, 200]),
                  tuple(it.get('shadow_off', [0, 2])))
        imgs.append((it['file'], im))
        if not preview:
            save(it['file'], im, backup=BACKUP)

    # montage for review
    if imgs:
        cell = 420
        cols = 2
        rows = (len(imgs) + cols - 1) // cols
        canvas = Image.new('RGB', (cols * cell, rows * (cell + 14)), (255, 0, 255))
        d = ImageDraw.Draw(canvas)
        for i, (rel, im) in enumerate(imgs):
            bg = Image.new('RGBA', im.size, (250, 250, 250, 255)); bg.alpha_composite(im)
            t = bg.convert('RGB'); t.thumbnail((cell - 8, cell - 8))
            x = (i % cols) * cell; y = (i // cols) * (cell + 14)
            canvas.paste(t, (x + 4, y + 14))
            d.text((x + 4, y + 2), os.path.basename(rel)[:-5], fill=(0, 0, 0))
        p = os.path.join(OUT, 'img_montage.jpg')
        canvas.save(p, quality=90)
        print('montage ->', p)
    print('preview only' if preview else f'saved {len(imgs)} images')


if __name__ == '__main__':
    main('--preview' in sys.argv)
