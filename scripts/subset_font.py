# -*- coding: utf-8 -*-
"""Subset a CJK font down to the characters a game actually needs.

Usage:
  python subset_font.py --font NotoSansSC-Regular.otf --out NotoSansSC-game.otf \
      --preset gb2312 --chars-from "E:/Game/www/data"

  # only characters found in the game files (+ kana/punctuation/ascii)
  python subset_font.py --font big.otf --out out.otf --preset none --chars-from game/data

  # print the charset size only
  python subset_font.py --font big.otf --preset gb2312 --dry-run
"""
import argparse, io, json, os, sys

ASCII = [chr(c) for c in range(0x20, 0x7F)]
KANA = [chr(c) for c in range(0x3040, 0x3100)]
PUNCT = ([chr(c) for c in range(0x3000, 0x3040)] +
         [chr(c) for c in range(0xFF01, 0xFF61)] +
         [chr(c) for c in range(0x2010, 0x2028)] + ["\u00b7", "\u203b"])

def gb2312():
    out = set()
    for b1 in range(0xA1, 0xF8):
        for b2 in range(0xA1, 0xFF):
            try:
                ch = bytes([b1, b2]).decode("gb2312")
            except UnicodeDecodeError:
                continue
            out.add(ch)
    return out

def chars_from_path(path):
    out = set()
    files = []
    if os.path.isdir(path):
        for dp, _, fs in os.walk(path):
            files += [os.path.join(dp, f) for f in fs if f.lower().endswith((".json", ".txt", ".csv", ".tsv"))]
    else:
        files = [path]
    for p in files:
        try:
            txt = io.open(p, encoding="utf-8-sig", errors="ignore").read()
        except Exception:
            continue
        out.update(txt)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--out")
    ap.add_argument("--preset", default="gb2312", choices=["gb2312", "none"])
    ap.add_argument("--chars-from", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    chars = set(ASCII) | set(KANA) | set(PUNCT)
    if a.preset == "gb2312":
        chars |= gb2312()
    for p in a.chars_from:
        chars |= chars_from_path(p)
    chars = {c for c in chars if c.strip() or c in (" ", "\u3000")}
    print("charset:", len(chars))

    if a.dry_run:
        return
    if not a.out:
        sys.exit("--out is required unless --dry-run")

    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.drop_tables += ["DSIG"]
    font = subset.load_font(a.font, opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes={ord(c) for c in chars})
    sub.subset(font)
    subset.save_font(font, a.out, opts)
    print("written:", a.out, os.path.getsize(a.out), "bytes")

if __name__ == "__main__":
    main()
