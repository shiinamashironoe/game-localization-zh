# -*- coding: utf-8 -*-
"""Font compatibility check for game localization.

Detects which font a game renders with, then checks whether that font can draw
the Chinese characters we plan to use. Reports two different failure modes:

  missing : codepoint absent from the font  -> browser falls back (visible, but
            in a different typeface, so the line looks mixed-weight)
  empty   : codepoint present but the glyph has no outline (0 contours)
            -> browser does NOT fall back, it draws a full-width blank gap
            (this is the "字突然不见" bug)

Usage:
  python font_compat.py --game "E:/Game"
  python font_compat.py --game "E:/Game" --report font_report.md
  python font_compat.py --game "E:/Game" --charset gb2312 --render
"""
import argparse, io, json, os, re, subprocess, sys, tempfile

GB2312 = None

def gb2312_chars():
    global GB2312
    if GB2312 is None:
        s = set()
        for b1 in range(0xA1, 0xF8):
            for b2 in range(0xA1, 0xFF):
                try:
                    s.add(bytes([b1, b2]).decode("gb2312"))
                except UnicodeDecodeError:
                    pass
        GB2312 = s
    return GB2312

def find_engine(game):
    if os.path.exists(os.path.join(game, "www", "js", "rpg_core.js")):
        return "mv", os.path.join(game, "www")
    if os.path.exists(os.path.join(game, "js", "rmmz_core.js")):
        return "mz", game
    if os.path.exists(os.path.join(game, "game")) and any(
            f.endswith(".rpy") for f in os.listdir(os.path.join(game, "game"))):
        return "renpy", game
    if os.path.isdir(os.path.join(game, "Fonts")):
        return "vxace", game
    return "unknown", game

def parse_gamefont_css(root):
    css = os.path.join(root, "fonts", "gamefont.css")
    if not os.path.exists(css):
        return None, []
    txt = io.open(css, encoding="utf-8-sig", errors="ignore").read()
    urls = re.findall(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', txt)
    files = []
    for u in urls:
        p = os.path.join(root, "fonts", u)
        files.append(p if os.path.exists(p) else None)
    return css, [f for f in files if f]

def parse_renpy_font(root):
    for fn in ("gui.rpy", "options.rpy", "screens.rpy"):
        p = os.path.join(root, "game", fn)
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding="utf-8-sig", errors="ignore"):
            m = re.match(r"\s*define\s+gui\.(?:text_font|name_text_font|interface_text_font)\s*=\s*[\"']([^\"']+)[\"']", line)
            if m:
                f = m.group(1)
                f = f.replace("fonts/", "")
                cand = os.path.join(root, "game", f)
                if os.path.exists(cand):
                    return cand
    return None

def collect_chars(root, extra):
    chars = set(gb2312_chars())
    for base in (os.path.join(root, "www", "data"), os.path.join(root, "data")):
        if not os.path.isdir(base):
            continue
        for fn in os.listdir(base):
            if not fn.endswith(".json"):
                continue
            try:
                txt = io.open(os.path.join(base, fn), encoding="utf-8-sig", errors="ignore").read()
            except Exception:
                continue
            chars.update(txt)
    for p in extra:
        if os.path.exists(p):
            chars.update(io.open(p, encoding="utf-8-sig", errors="ignore").read())
    chars.update(chr(c) for c in range(0x3040, 0x3100))     # kana (untranslated bits)
    chars.update(chr(c) for c in range(0x20, 0x7F))
    chars.update(chr(c) for c in range(0x3000, 0x3040))
    return {c for c in chars if c.strip() or c in (" ", "\u3000")}

def check_font(path, chars):
    from fontTools.ttLib import TTFont
    f = TTFont(path, fontNumber=0, lazy=True)
    cmap = f.getBestCmap() or {}
    has_glyf = "glyf" in f
    glyf = f["glyf"] if has_glyf else None
    missing, empty, ok = [], [], 0
    for ch in chars:
        cp = ord(ch)
        g = cmap.get(cp)
        if g is None:
            missing.append(ch)
            continue
        if has_glyf:
            try:
                if glyf[g].numberOfContours == 0:
                    empty.append(ch)
                    continue
            except Exception:
                pass
        ok += 1
    return {"path": path, "glyf": has_glyf, "missing": missing, "empty": empty, "ok": ok,
            "cmap_size": len(cmap), "name": font_name(f)}

def font_name(f):
    try:
        for rec in f["name"].names:
            if rec.nameID == 4:
                return rec.toUnicode()
    except Exception:
        pass
    return "?"

def find_chrome():
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(p):
            return p
    return None

def render_check(font_path, chars, limit=300):
    """Render chars with headless Chromium and report which produce zero ink."""
    chrome = find_chrome()
    if not chrome:
        return None
    chars = chars[:limit]
    html = """<!DOCTYPE html><meta charset="utf-8">
<style>@font-face{font-family:TF;src:url("file:///%s");}</style>
<pre id="r">pending</pre><script>
const chars = %s;
const c = document.createElement('canvas'); c.width = 96; c.height = 96;
const x = c.getContext('2d', {willReadFrequently:true});
const blank = [];
for (const ch of chars) {
  x.clearRect(0,0,96,96); x.fillStyle='#000'; x.font='64px TF'; x.textBaseline='top';
  x.fillText(ch, 4, 4);
  const d = x.getImageData(0,0,96,96).data; let ink = 0;
  for (let i=3;i<d.length;i+=4) if (d[i] > 8) ink++;
  if (ink === 0) blank.push(ch);
}
document.getElementById('r').textContent = JSON.stringify(blank);
</script>""" % (font_path.replace("\\", "/").lstrip("/"), json.dumps(chars, ensure_ascii=False))
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, "t.html")
        io.open(hp, "w", encoding="utf-8").write(html)
        try:
            out = subprocess.run([chrome, "--headless=new", "--disable-gpu",
                                  "--allow-file-access-from-files", "--virtual-time-budget=8000",
                                  "--dump-dom", "file:///" + hp.replace("\\", "/")],
                                 capture_output=True, text=True, timeout=90).stdout
        except Exception as e:
            return {"error": str(e)}
    m = re.search(r'<pre id="r">(.*?)</pre>', out, re.S)
    if not m:
        return {"error": "no output"}
    try:
        return {"blank": json.loads(m.group(1))}
    except Exception:
        return {"error": m.group(1)[:100]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--report")
    ap.add_argument("--charset", default="auto")
    ap.add_argument("--chars", default=None, help="extra text file to include")
    ap.add_argument("--render", action="store_true", help="confirm blanks with headless Chromium")
    a = ap.parse_args()

    engine, root = find_engine(a.game)
    print("engine:", engine, "root:", root)

    fonts = []
    css = None
    if engine in ("mv", "mz"):
        css, fonts = parse_gamefont_css(root)
        print("css:", css)
    elif engine == "renpy":
        f = parse_renpy_font(a.game)
        fonts = [f] if f else []
    elif engine == "vxace":
        d = os.path.join(a.game, "Fonts")
        fonts = [os.path.join(d, x) for x in os.listdir(d) if x.lower().endswith((".ttf", ".otf", ".ttc"))]
    else:
        for d in (os.path.join(root, "fonts"), os.path.join(a.game, "fonts")):
            if os.path.isdir(d):
                fonts += [os.path.join(d, x) for x in os.listdir(d) if x.lower().endswith((".ttf", ".otf"))]

    if not fonts:
        sys.exit("no font file detected; inspect the engine manually")

    chars = collect_chars(a.game, [a.chars] if a.chars else [])
    print("target charset:", len(chars))

    lines = ["# 字体兼容性体检 Font compatibility", "",
             "| 项目 | 值 |", "|---|---|",
             "| 引擎 | %s |" % engine,
             "| 字体链 | %s |" % (css or "-"),
             "| 目标字符数 | %d |" % len(chars), ""]
    for fp in fonts:
        r = check_font(fp, chars)
        print("\nfont:", os.path.basename(fp), "|", r["name"], "| cmap", r["cmap_size"],
              "| glyf", r["glyf"])
        print("  ok %d | missing %d | empty %d" % (r["ok"], len(r["missing"]), len(r["empty"])))
        if r["missing"]:
            print("  missing sample:", "".join(r["missing"][:40]))
        if r["empty"]:
            print("  EMPTY sample  :", "".join(r["empty"][:40]))
        if a.render and r["empty"]:
            rc = render_check(fp, r["empty"])
            if rc and "blank" in rc:
                print("  render-confirmed blanks:", "".join(rc["blank"][:40]))
                r["render_blank"] = rc["blank"]
            else:
                print("  render check skipped/failed:", rc)
        lines += ["## %s (%s)" % (os.path.basename(fp), r["name"]), "",
                  "- cmap: %d, glyf: %s" % (r["cmap_size"], r["glyf"]),
                  "- 正常: %d" % r["ok"],
                  "- 缺码位（会回退系统字体，字重会不一致）: %d %s" % (len(r["missing"]), "".join(r["missing"][:60])),
                  "- 空字形（空白、占一格，必须修）: %d %s" % (len(r["empty"]), "".join(r["empty"][:60])),
                  ""]
        if r["empty"]:
            lines.append("> 结论：**必须换字体或补字**，否则这些字在游戏里是空白。")
            lines.append("")

    if a.report:
        io.open(a.report, "w", encoding="utf-8").write("\n".join(lines))
        print("\nreport ->", a.report)

if __name__ == "__main__":
    main()
