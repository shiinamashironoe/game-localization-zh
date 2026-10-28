#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""開工前查「這款遊戲有沒有現成漢化」——四源查詢 + 候選表。

用法：
    python find_existing_l10n.py --game "<遊戲目錄>"
    python find_existing_l10n.py --title "千恋＊万花" --appid 1144400
    python find_existing_l10n.py --rj RJ01208749 --out existing_l10n.md

來源（全部免 API key）：
    DLsite  作品頁  → 官方中文
    Steam   appdetails / storesearch → 官方中文
    VNDB    kana API（POST）→ 已有哪些語言版本（含民間補丁登記）
    GitHub  search API → 公開倉庫型補丁
另外產生「手工搜尋連結」（2DFan / 貼吧 / Bangumi / Google），**不自動抓灰產站**。

原則：
  * 只查、只報告，不下載任何東西。
  * 網路失敗一律降級成「未查」，不讓整個流程掛掉。
  * 輸出同時寫入檔案（預設 existing_l10n.md）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "game-localization-zh/1.3 (pre-flight l10n check)"
TIMEOUT = 20

ZHS = ("zh-Hans", "zh-hans", "zh_CN", "schinese", "簡體", "简体", "簡体")
ZHT = ("zh-Hant", "zh-hant", "zh_TW", "tchinese", "繁體", "繁体", "繁体中文")

HITS = []          # [(source, kind, langs, confidence, risk, url, note)]


# ---------- 基礎 ----------
def http_get(url: str, timeout: int = TIMEOUT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def http_post_json(url: str, payload: dict, timeout: int = TIMEOUT) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def say(msg: str) -> None:
    print(msg, flush=True)


def add(source, kind, langs, conf, risk, url, note=""):
    HITS.append(dict(source=source, kind=kind, langs=langs,
                     conf=conf, risk=risk, url=url, note=note))


# ---------- 本地識別 ----------
def clean_title(raw: str) -> str:
    """去掉版本號、DLC、位數等雜訊，留下作品名。"""
    t = raw
    t = re.sub(r"\[[^\]]*\]", " ", t)                       # [社團]
    t = re.sub(r"(RJ|VJ|RE)\d{6,8}", " ", t, flags=re.I)
    t = re.sub(r"\bv?\d+\.\d+([.\w]*)?", " ", t, flags=re.I)  # v1.041 / 1.10
    t = re.sub(r"\bver\.?\s*\d+", " ", t, flags=re.I)
    t = re.sub(r"\b(DLC|64bit|32bit|x64|patch|update)\b", " ", t, flags=re.I)
    t = re.sub(r"[\(\)（）\[\]【】_\-–—+|:：]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .-_")
    return t


def guess_title(path: str) -> str | None:
    """目錄名 → exe 檔名 → readme/version 檔，優先取含 CJK 的。"""
    def has_cjk(s: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", s))

    cands = []
    base = os.path.basename(os.path.abspath(path))
    cands.append(clean_title(base))
    if os.path.isdir(path):
        try:
            exes = [f for f in os.listdir(path) if f.lower().endswith(".exe")]
            exes.sort(key=lambda f: os.path.getsize(os.path.join(path, f)), reverse=True)
            for e in exes[:2]:
                cands.append(clean_title(os.path.splitext(e)[0]))
        except OSError:
            pass
        for name in ("version.txt", "readme.txt", "README.txt", "説明.txt"):
            p = os.path.join(path, name)
            if os.path.isfile(p):
                try:
                    head = open(p, encoding="utf-8", errors="replace").readline().strip()
                    if 2 < len(head) < 60:
                        cands.append(clean_title(head))
                except OSError:
                    pass
    cands = [c for c in cands if c and len(c) >= 2]
    for c in cands:
        if has_cjk(c):
            return c
    return cands[0] if cands else None


def detect_from_path(path: str) -> dict:
    info = {"rj": None, "appid": None, "title": None, "steam_acf": None}
    base = os.path.basename(os.path.abspath(path))
    m = re.search(r"(RJ\d{6,8})", base, re.I)
    if m:
        info["rj"] = m.group(1).upper()
    info["title"] = guess_title(path)
    for name in ("steam_appid.txt", "steam_api.ini"):
        p = os.path.join(path, name)
        if os.path.isfile(p):
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
                m = re.search(r"\b(\d{4,7})\b", txt)
                if m:
                    info["appid"] = m.group(1)
            except OSError:
                pass
    for name in os.listdir(path) if os.path.isdir(path) else []:
        if name.startswith("appmanifest_") and name.endswith(".acf"):
            p = os.path.join(path, name)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
                m = re.search(r'"appid"\s+"(\d+)"', txt)
                if m:
                    info["appid"] = m.group(1)
                m = re.search(r'"name"\s+"([^"]+)"', txt)
                if m and not info["title"]:
                    info["title"] = m.group(1)
            except OSError:
                pass
    return info


# ---------- DLsite ----------
def check_dlsite(rj: str):
    if not rj:
        return
    url = "https://www.dlsite.com/maniax/work/=/product_id/%s.html" % rj
    try:
        html = http_get(url)
    except Exception as e:                                   # noqa: BLE001
        add("DLsite", "查詢失敗", "-", "低", "-", url, str(e)[:60])
        return
    if "この作品は削除" in html or "not found" in html.lower():
        add("DLsite", "頁面不存在", "-", "低", "-", url)
        return
    text = re.sub(r"<[^>]+>", " ", html)
    langs = []
    if re.search(r"中国語|簡体字|简体字", text):
        langs.append("簡體")
    if re.search(r"繁体字|繁體字", text):
        langs.append("繁體")
    if langs:
        add("DLsite", "官方中文", "/".join(sorted(set(langs))), "高", "A", url,
            "商店頁標示有中文，優先考慮直接購買")
    else:
        add("DLsite", "僅日文（頁面未見中文）", "ja", "中", "-", url)
    time.sleep(1)


# ---------- Steam ----------
def check_steam(appid: str | None, title: str | None):
    if not appid and title:
        try:
            q = urllib.parse.quote(title)
            data = json.loads(http_get(
                "https://store.steampowered.com/api/storesearch/?term=%s&l=schinese&cc=cn" % q))
            items = data.get("items") or []
            best = None
            for it in items:
                nm = it.get("name", "") or ""
                if re.search(r"体验版|体験版|试玩|試玩|Demo|demo", nm):
                    continue
                if best is None:
                    best = it
                if nm.strip() == (title or "").strip():
                    best = it
                    break
            if best:
                appid = str(best["id"])
                title = best.get("name") or title
        except Exception:                                    # noqa: BLE001
            pass
    if not appid:
        return
    try:
        data = json.loads(http_get(
            "https://store.steampowered.com/api/appdetails?appids=%s&l=schinese" % appid))
        info = (data.get(str(appid)) or {}).get("data") or {}
    except Exception as e:                                   # noqa: BLE001
        add("Steam", "查詢失敗", "-", "低", "-", "appid=%s" % appid, str(e)[:60])
        return
    if not info:
        return
    langs = re.sub(r"<[^>]+>", "", info.get("supported_languages", "") or "")
    found = []
    if "简体中文" in langs or "簡體中文" in langs:
        found.append("簡體")
    if "繁体中文" in langs or "繁體中文" in langs:
        found.append("繁體")
    url = "https://store.steampowered.com/app/%s/" % appid
    if found:
        add("Steam", "官方中文", "/".join(found), "高", "A", url, info.get("name", ""))
    else:
        add("Steam", "官方無中文", "ja/en", "高", "-", url, info.get("name", ""))


# ---------- VNDB ----------
def check_vndb(title: str | None):
    if not title:
        return
    try:
        out = http_post_json("https://api.vndb.org/kana/vn", {
            "filters": ["search", "=", title],
            "fields": "id,title,alttitle,languages",
            "results": 3,
        })
    except Exception as e:                                   # noqa: BLE001
        add("VNDB", "查詢失敗", "-", "低", "-", "-", str(e)[:60])
        return
    for v in out.get("results", []):
        langs = v.get("languages") or []
        zh = [l for l in langs if l in ZHS or l in ZHT]
        url = "https://vndb.org/%s" % v["id"]
        if zh:
            add("VNDB", "已有中文版本（含民間補丁登記）",
                "/".join("簡" if l in ZHS else "繁" for l in zh), "中", "B", url,
                v.get("title", ""))
        else:
            add("VNDB", "未見中文版本", "ja", "中", "-", url, v.get("title", ""))
        break
    else:
        add("VNDB", "查無條目", "-", "低", "-", "-",
            "VNDB 未收錄，這裡查不到不代表沒有人做過")
    time.sleep(1)


# ---------- GitHub ----------
def check_github(title: str | None):
    if not title:
        return
    seen = set()
    for q in ('"%s" 汉化' % title, '"%s" 漢化' % title, '"%s" 中文 patch' % title):
        url = ("https://api.github.com/search/repositories?q=%s&sort=stars&per_page=3"
               % urllib.parse.quote(q))
        try:
            data = json.loads(http_get(url))
        except Exception:                                    # noqa: BLE001
            time.sleep(2)
            continue
        for it in (data.get("items") or [])[:3]:
            name = it["full_name"]
            if name in seen:
                continue
            seen.add(name)
            stars = it.get("stargazers_count", 0)
            add("GitHub", "公開補丁倉庫（需人工確認內容）",
                "?", "中" if stars >= 30 else "低",
                "B" if stars >= 30 else "C",
                it.get("html_url", ""), "%s  ★%s" % (name, stars))
        time.sleep(2)
    if not seen:
        add("GitHub", "未見公開補丁倉庫", "-", "低", "-", "-",
            "GitHub 沒有命中，不代表沒有（多數補丁只在論壇/網盤）")


# ---------- 手工搜尋連結 ----------
def manual_links(title: str | None, rj: str | None):
    key = title or rj or ""
    if not key:
        return []
    q = urllib.parse.quote(key)
    return [
        ("2DFan（漢化補丁索引，需自行判斷）", "https://2dfan.com/search?q=%s" % q),
        ("Bangumi（條目/討論）", "https://bgm.tv/subject_search/%s" % q),
        ("百度貼吧", "https://tieba.baidu.com/f/search/res?qw=%s" % q),
        ("Google（加引號精確比對）", "https://www.google.com/search?q=%s" % urllib.parse.quote(
            '"%s" 汉化 OR 漢化 OR 中文补丁' % key)),
    ]


# ---------- 報告 ----------
def render(info: dict, out_path: str | None) -> str:
    lines = []
    lines.append("# 現成漢化查詢結果\n")
    lines.append("- 作品：`%s`" % (info.get("title") or "未識別"))
    lines.append("- DLsite：`%s`　Steam appid：`%s`" % (info.get("rj") or "-", info.get("appid") or "-"))
    lines.append("- 查詢時間：%s" % time.strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    if HITS:
        lines.append("| 來源 | 判定 | 語言 | 置信度 | 風險級 | 連結／備註 |")
        lines.append("|---|---|---|---|---|---|")
        for h in HITS:
            link = h["url"] if h["url"].startswith("http") else h["url"]
            note = ("%s ｜ %s" % (link, h["note"]) if h["note"] else link)
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                h["source"], h["kind"], h["langs"], h["conf"], h["risk"], note))
    lines.append("")
    official = [h for h in HITS if h["kind"] == "官方中文"]
    patches = [h for h in HITS if h["kind"].startswith("已有中文") or h["kind"].startswith("公開補丁")]
    lines.append("## 結論\n")
    if official:
        lines.append("- **有官方中文**：建議直接購買官方版本（最安全、也支持作者）。")
    if patches:
        lines.append("- **有民間／公開補丁**：先看風險級；C 級只給連結不代裝，D 級一律拒裝。")
    if not official and not patches:
        lines.append("- **未查到現成中文**：按正常流程自己做漢化。")
    lines.append("- 免責：本表只做「有沒有」的提示，不下載、不保證第三方補丁安全或合法；"
                 "補丁的著作權狀態依當地法律與原作者授權為準。")
    links = manual_links(info.get("title"), info.get("rj"))
    if links:
        lines.append("\n## 手工搜尋（灰產站不自動抓，請自行判斷）\n")
        for name, url in links:
            lines.append("- %s：%s" % (name, url))
    text = "\n".join(lines) + "\n"
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", help="遊戲目錄（自動識別 RJ 號 / appid / 標題）")
    ap.add_argument("--title")
    ap.add_argument("--rj")
    ap.add_argument("--appid")
    ap.add_argument("--out", default="existing_l10n.md")
    ap.add_argument("--no-network", action="store_true", help="只輸出模板與手工連結")
    a = ap.parse_args()

    info = detect_from_path(a.game) if a.game else {"rj": None, "appid": None, "title": None}
    if a.title:
        info["title"] = a.title
    if a.rj:
        info["rj"] = a.rj.upper()
    if a.appid:
        info["appid"] = a.appid

    say("作品：%s ｜ RJ:%s ｜ appid:%s" % (info["title"], info["rj"], info["appid"]))
    reliable = bool(info["title"] and re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", info["title"]))
    if not a.no_network:
        check_dlsite(info["rj"])
        check_steam(info["appid"], info["title"])
        if reliable:
            check_vndb(info["title"])
            check_github(info["title"])
        else:
            add("VNDB", "未查（標題不可靠）", "-", "低", "-", "-",
                "請用 --title 指定作品原名")
            add("GitHub", "未查（標題不可靠）", "-", "低", "-", "-",
                "請用 --title 指定作品原名")

    text = render(info, a.out)
    say("")
    say(text)
    say("[written] %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
