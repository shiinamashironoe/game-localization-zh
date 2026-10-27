# -*- coding: utf-8 -*-
"""Patch the game font so Chinese text renders correctly.

Modes:
  replace     : use a supplied Chinese font as GameFont (recommended)
  drop-empty  : keep the original font, but remove cmap entries that point to
                empty glyphs, so the browser falls back to a system font for
                just those characters (keeps the original look for the rest)

Usage:
  python font_patch.py --game "E:/Game" --mode replace --font zh.otf          # dry-run
  python font_patch.py --game "E:/Game" --mode replace --font zh.otf --apply
  python font_patch.py --game "E:/Game" --mode drop-empty --apply

Always backs up gamefont.css and the original font first. Works for RPG Maker
MV/MZ; for Ren'Py / VX Ace it prints manual instructions.
"""
import argparse, io, os, re, shutil, sys, time

def find_mv(game):
    for root in (os.path.join(game, "www"), game):
        css = os.path.join(root, "fonts", "gamefont.css")
        if os.path.exists(css):
            return root, css
    return None, None

def parse_css(css):
    txt = io.open(css, encoding="utf-8-sig", errors="ignore").read()
    urls = re.findall(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', txt)
    return txt, urls

def gb2312():
    s = set()
    for b1 in range(0xA1, 0xF8):
        for b2 in range(0xA1, 0xFF):
            try:
                s.add(bytes([b1, b2]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return s

def coverage(font_path):
    from fontTools.ttLib import TTFont
    f = TTFont(font_path, fontNumber=0, lazy=True)
    cmap = f.getBestCmap() or {}
    chars = gb2312()
    miss = [c for c in chars if ord(c) not in cmap]
    return len(chars), len(miss), "".join(miss[:30])

def drop_empty(src, dst):
    from fontTools.ttLib import TTFont
    f = TTFont(src)
    if "glyf" not in f:
        sys.exit("drop-empty needs a TrueType (glyf) font; this one is CFF/OTF")
    glyf = f["glyf"]
    removed = 0
    for table in f["cmap"].tables:
        for cp, g in list(table.cmap.items()):
            try:
                if glyf[g].numberOfContours == 0:
                    del table.cmap[cp]
                    removed += 1
            except Exception:
                pass
    f.save(dst)
    return removed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--mode", choices=["replace", "drop-empty"], required=True)
    ap.add_argument("--font")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    root, css = find_mv(a.game)
    if not css:
        print("Not an RPG Maker MV/MZ layout.")
        print("Ren'Py : put the ttf under game/fonts/ and set  define gui.text_font = \"fonts/xxx.ttf\"")
        print("VX Ace : drop the font into Fonts/ and set Font.default_name in the scripts")
        return

    txt, urls = parse_css(css)
    if not urls:
        sys.exit("no url() in gamefont.css")
    old = os.path.join(root, "fonts", urls[0])
    if not os.path.exists(old):
        sys.exit("font file referenced by css not found: %s" % old)

    print("css      :", css)
    print("font     :", old)
    print("mode     :", a.mode)

    if a.mode == "replace":
        if not a.font or not os.path.exists(a.font):
            sys.exit("--font <file> is required for replace mode")
        ext = os.path.splitext(a.font)[1].lower()
        new_name = "GameFont-zh" + ext
        new_path = os.path.join(root, "fonts", new_name)
        total, miss, sample = coverage(a.font)
        print("new font GB2312 coverage: %d/%d missing=%d %s" %
              (total - miss, total, miss, sample))
        if miss > total * 0.02:
            print("WARNING: new font still misses >2%% of GB2312; consider another font")
        print("plan: copy ->", new_path)
        print("plan: css url ->", new_name)
        if a.apply:
            ts = time.strftime("%Y%m%d-%H%M%S")
            shutil.copyfile(css, css + ".bak-" + ts)
            shutil.copyfile(old, old + ".bak-" + ts)
            shutil.copyfile(a.font, new_path)
            new_css = re.sub(r'url\(\s*["\']?[^"\')]+["\']?\s*\)',
                             'url("%s")' % new_name, txt)
            io.open(css, "w", encoding="utf-8").write(new_css)
            print("done. backups: *.bak-%s" % ts)

    else:
        base = os.path.basename(old)
        stem, ext = os.path.splitext(base)
        if ext.lower() not in (".ttf", ".ttc"):
            sys.exit("drop-empty only supports .ttf (TrueType outlines)")
        new_name = stem + "-dropempty.ttf"
        new_path = os.path.join(root, "fonts", new_name)
        print("plan: remove empty-glyph cmap entries ->", new_path)
        if a.apply:
            ts = time.strftime("%Y%m%d-%H%M%S")
            shutil.copyfile(css, css + ".bak-" + ts)
            shutil.copyfile(old, old + ".bak-" + ts)
            n = drop_empty(old, new_path)
            new_css = re.sub(r'url\(\s*["\']?[^"\')]+["\']?\s*\)',
                             'url("%s")' % new_name, txt)
            io.open(css, "w", encoding="utf-8").write(new_css)
            print("removed empty cmap entries:", n)
            print("done. backups: *.bak-%s" % ts)
            print("note: those chars now fall back to a system font (style may differ)")

if __name__ == "__main__":
    main()
