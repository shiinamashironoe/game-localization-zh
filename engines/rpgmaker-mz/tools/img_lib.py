# -*- coding: utf-8 -*-
"""Image redraw helpers for RPG MZ encrypted PNG assets."""
import json, os, sys, io, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, CFG
from PIL import Image, ImageDraw, ImageFont

IMGDIR = os.path.join(GAME, 'img')
KB = bytes.fromhex(json.load(open(os.path.join(GAME, 'data', 'System.json'), encoding='utf-8'))['encryptionKey'])
FONT_PATH = os.path.join(GAME, 'fonts', CFG.get('font_filename', 'NotoSansSC-game.otf'))

def load(rel):
    p = os.path.join(IMGDIR, rel.replace('/', os.sep))
    raw = open(p, 'rb').read()
    b = bytearray(raw[16:])
    for i in range(16):
        b[i] ^= KB[i]
    return Image.open(io.BytesIO(bytes(b))).convert('RGBA')

def save(rel, im, backup=None):
    p0 = os.path.join(IMGDIR, rel.replace('/', os.sep))
    if backup and os.path.exists(p0):
        os.makedirs(backup, exist_ok=True)
        dst = os.path.join(backup, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            shutil.copy2(p0, dst)
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    data = buf.getvalue()
    head = bytes([0x52, 0x50, 0x47, 0x4D, 0x56, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 0])
    b = bytearray(data)
    for i in range(16):
        b[i] ^= KB[i]
    p = os.path.join(IMGDIR, rel.replace('/', os.sep))
    open(p, 'wb').write(head + bytes(b))

def erase_rowfill(im, bbox):
    """Replace bbox content with horizontal nearest-opaque-pixel fill."""
    x0, y0, x1, y1 = bbox
    px = im.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            # nearest non-masked pixel left / right
            lx = x - 1
            while lx >= 0 and x0 <= lx < x1:
                lx -= 1
            rx = x + 1
            while rx < im.width and x0 <= rx < x1:
                rx += 1
            cands = []
            if lx >= 0: cands.append((x - lx, px[lx, y]))
            if rx < im.width: cands.append((rx - x, px[rx, y]))
            if not cands:
                continue
            cands.sort(key=lambda t: t[0])
            px[x, y] = cands[0][1]

def draw_center(im, bbox, text, size, fill=(255, 255, 255, 255), stroke=(30, 40, 60, 255),
                stroke_w=2, bold=1, font_path=FONT_PATH, dy=0):
    x0, y0, x1, y1 = bbox
    font = ImageFont.truetype(font_path, size)
    d = ImageDraw.Draw(im)
    # shrink to fit
    while size > 8:
        tw = d.textlength(text, font=font)
        th = size
        if tw <= (x1 - x0) - 2 and th <= (y1 - y0) - 2:
            break
        size -= 1
        font = ImageFont.truetype(font_path, size)
    tw = d.textlength(text, font=font)
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - size) / 2 + dy
    for ox in range(bold):
        for oy in range(bold):
            d.text((tx + ox, ty + oy), text, font=font, fill=fill,
                   stroke_width=stroke_w, stroke_fill=stroke)
    return im
