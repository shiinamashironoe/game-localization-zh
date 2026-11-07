#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""glossary_to_dict.py — 把 R18 種子術語表轉成批次翻譯工具吃的格式。

支援欄位：原文,簡中,繁中,分層,類別,備註（見 reference/nsfw/glossary-nsfw.csv）

用法：
    # 預設：完整 CSV 轉成 SakuraLLM / GalTransl 的「原文->譯文」
    python scripts/glossary_to_dict.py reference/nsfw/glossary-nsfw.csv

    # 只要標準與粗兩層，輸出繁體
    python scripts/glossary_to_dict.py glossary.csv --tier 標準,粗 --variant traditional

    # 只要部位類，輸出 two-column CSV（AiNiee / LinguaGacha）
    python scripts/glossary_to_dict.py glossary.csv --category 部位 --format csv --out dict.csv

退出碼：0 成功；2 輸入有問題（缺欄位、重複原文譯法衝突、空表）。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from typing import NoReturn

TIER_ALIASES = {
    "軟": "軟", "软": "軟", "soft": "軟", "l": "軟",
    "標準": "標準", "标准": "標準", "standard": "標準", "s": "標準",
    "粗": "粗", "vulgar": "粗", "v": "粗", "hard": "粗",
}
REQUIRED = ("原文", "簡中", "繁中")
FORMATS = ("arrow", "csv", "jsonl")


def die(msg: str) -> NoReturn:
    print(f"[glossary_to_dict] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def norm_tiers(spec: str) -> set[str] | None:
    if not spec or spec.strip().lower() in ("all", "*"):
        return None
    out = set()
    for raw in spec.replace("，", ",").split(","):
        key = raw.strip()
        if not key:
            continue
        if key.lower() in ("all", "*"):
            return None
        tier = TIER_ALIASES.get(key) or TIER_ALIASES.get(key.lower())
        if not tier:
            die(f"未知分層 `{key}`，可用：軟／標準／粗（或 all）")
        out.add(tier)
    return out or None


def load_rows(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            missing = [c for c in REQUIRED if c not in fields]
            if missing:
                die(f"{path} 缺少欄位：{'、'.join(missing)}；現有欄位：{fields}")
            rows = [dict(r) for r in reader]
    except FileNotFoundError:
        die(f"找不到檔案：{path}")
    except UnicodeDecodeError as exc:
        die(f"{path} 不是 UTF-8：{exc}")

    cleaned = []
    for lineno, row in enumerate(rows, start=2):
        src = (row.get("原文") or "").strip()
        if not src:
            continue
        if "->" in src or "\n" in src:
            die(f"第 {lineno} 行原文含 `->` 或換行，會破壞字典格式：{src!r}")
        cleaned.append((lineno, row))
    if not cleaned:
        die("表裡沒有任何有效詞條")
    return cleaned


def build(cleaned, tier_filter, category, variant, tag_tier):
    chosen: dict[str, dict] = {}
    conflicts: list[str] = []

    for lineno, row in cleaned:
        tier = TIER_ALIASES.get((row.get("分層") or "").strip()) or TIER_ALIASES.get(
            (row.get("分層") or "").strip().lower()
        )
        if tier_filter and tier not in tier_filter:
            continue
        cat = (row.get("類別") or "").strip()
        if category and category not in cat:
            continue

        src = row["原文"].strip()
        dst = (row.get("繁中") if variant == "traditional" else row.get("簡中")) or ""
        dst = dst.strip()
        if not dst or dst == "＝":
            dst = (row.get("簡中") or "").strip() if variant == "traditional" else ""
        if not dst:
            print(f"[glossary_to_dict] 跳過無譯文：第 {lineno} 行 {src!r}", file=sys.stderr)
            continue
        if tag_tier and tier:
            dst = f"{dst}（{tier}）"

        if src in chosen:
            if chosen[src]["dst"] != dst:
                conflicts.append(
                    f"{src!r}：第 {chosen[src]['line']} 行作 {chosen[src]['dst']!r}，"
                    f"第 {lineno} 行作 {dst!r}"
                )
            continue
        chosen[src] = {"src": src, "dst": dst, "tier": tier or "", "category": cat, "line": lineno}

    if conflicts:
        die("同一原文有兩種譯法，先統一再轉：\n  " + "\n  ".join(conflicts))
    if not chosen:
        die("篩選後沒有任何詞條（檢查 --tier / --category）")
    return list(chosen.values())


def emit(rows: list[dict], fmt: str) -> str:
    if fmt == "arrow":
        return "\n".join(f"{r['src']}->{r['dst']}" for r in rows) + "\n"
    if fmt == "jsonl":
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return _csv_text(rows)


def _csv_text(rows: list[dict]) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["原文", "譯文"])
    for r in rows:
        writer.writerow([r["src"], r["dst"]])
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="把 R18 種子術語表轉成批次翻譯工具的字典格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("csv", help="術語表 CSV（glossary-nsfw.csv 或專案自己的表）")
    ap.add_argument(
        "--format", "-f", choices=FORMATS, default="arrow",
        help="輸出格式：arrow（預設，原文->譯文）、csv（兩欄）、jsonl",
    )
    ap.add_argument("--tier", "-t", default="all", help="分層篩選：標準,粗 或 all（預設）")
    ap.add_argument("--category", "-c", default="", help="類別子字串篩選，如 部位 / 行為 / 稱呼")
    ap.add_argument(
        "--variant", "-v", choices=("simplified", "traditional"), default="simplified",
        help="輸出簡中或繁中譯文（預設簡中）",
    )
    ap.add_argument("--tag-tier", action="store_true", help="在譯文後加（分層），給人看的表用")
    ap.add_argument("--out", "-o", help="輸出檔（預設印到 stdout）")
    args = ap.parse_args()

    rows = build(
        load_rows(args.csv), norm_tiers(args.tier), args.category, args.variant, args.tag_tier
    )
    text = emit(rows, args.format)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print(f"[glossary_to_dict] {len(rows)} 條 → {args.out}", file=sys.stderr)
    else:
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except BrokenPipeError:  # 被 `| head` 之類截斷，不是錯誤
            try:
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
            except OSError:
                pass
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
