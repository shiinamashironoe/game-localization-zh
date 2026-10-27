#!/usr/bin/env python3
"""
check_l10n.py - 遊戲漢化譯文自動驗證工具（僅用 Python 標準庫）

檢查項目：
  1. 條目數 / ID 是否一致（缺失、多出、錯位）
  2. 控制碼、佔位符、變數是否與原文完全一致（數量與內容）
  3. 譯文是否為空 / 是否與原文相同（疑似漏譯）
  4. 是否殘留日文假名（疑似漏譯）
  5. 換行符數量是否一致
  6. （可選）譯文能否以指定編碼回寫（缺字檢查）
  7. （可選）每行長度是否超過上限

支援格式：
  - JSON：{"id": "文本"}、["文本", ...]、或 [{"id":..,"source":..,"target":..}, ...]
  - CSV / TSV：以欄位名指定原文與譯文欄
  - TXT：逐行對應

用法範例：
  python check_l10n.py source.json translated.json
  python check_l10n.py sheet.csv --src-col source --dst-col target
  python check_l10n.py src.txt dst.txt --encoding gbk --max-line-len 28
  python check_l10n.py src.json dst.json --placeholder "\\\\V\\[\\d+\\]"

結束碼：0 = 全部通過，1 = 有錯誤，2 = 參數或讀檔失敗
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 常見遊戲控制碼 / 佔位符（可用 --placeholder 追加）
DEFAULT_PATTERNS = [
    r"\\[A-Za-z]+\[[^\]]*\]",          # RPG Maker: \C[1] \V[3] \N[1]
    r"\\[A-Za-z{}|.!<>^$]",             # RPG Maker 單字元: \G \. \! \| \{ \}
    r"<[^<>\n]{1,64}>",                 # 標籤: <color=red> </b> <br>
    r"\{[^{}\n]{0,64}\}",               # {0} {name} {player_score}
    r"%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sdifxXoceEgGu%]",  # printf: %s %d %1$s %%
    r"\$[A-Za-z_][A-Za-z0-9_]*",        # $var
    r"\[[A-Za-z_][A-Za-z0-9_]*(?:[ =:][^\]\n]*)?\]",     # [name] [wait time=10] (KAG/Ren'Py)
    r"@[A-Za-z_][A-Za-z0-9_]*",         # @cmd
]

KANA_RE = re.compile(r"[\u3041-\u3096\u30A1-\u30FA\u31F0-\u31FF\uFF66-\uFF9D]")
# 允許保留的假名符號（長音、中點等不視為殘留）
KANA_ALLOW = set("ー・ヽヾゝゞ")


def die(msg: str) -> None:
    print(f"[錯誤] {msg}", file=sys.stderr)
    sys.exit(2)


def read_text(path: Path, encoding: str | None) -> str:
    raw = path.read_bytes()
    if encoding:
        return raw.decode(encoding)
    for enc in ("utf-8-sig", "utf-16", "shift_jis", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    die(f"無法判斷 {path} 的編碼，請用 --input-encoding 指定")
    return ""


def load_entries(path: Path, args, role: str) -> dict[str, str]:
    """回傳 {id: 文本}。role 為 'src' 或 'dst'（單檔表格模式下用來選欄）。"""
    text = read_text(path, args.input_encoding)
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
        if isinstance(data, list):
            out: dict[str, str] = {}
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    key = str(item.get(args.id_col, i))
                    col = args.src_col if role == "src" else args.dst_col
                    val = item.get(col)
                    out[key] = "" if val is None else str(val)
                else:
                    out[str(i)] = "" if item is None else str(item)
            return out
        die(f"{path}: 不支援的 JSON 結構")

    if suffix in (".csv", ".tsv"):
        delim = "\t" if suffix == ".tsv" else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        col = args.src_col if role == "src" else args.dst_col
        if reader.fieldnames is None or col not in reader.fieldnames:
            die(f"{path}: 找不到欄位「{col}」，現有欄位：{reader.fieldnames}")
        out = {}
        for i, row in enumerate(reader):
            key = row.get(args.id_col) or str(i)
            out[str(key)] = row.get(col) or ""
        return out

    # 其他一律視為逐行對應的純文字
    return {str(i + 1): line for i, line in enumerate(text.splitlines())}


def build_placeholder_re(extra: list[str], only_custom: bool) -> re.Pattern:
    patterns = list(extra) if only_custom else DEFAULT_PATTERNS + list(extra)
    return re.compile("|".join(f"(?:{p})" for p in patterns))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="遊戲漢化譯文自動驗證（控制碼、漏譯、條目數、編碼、行長）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("source", help="原文檔（或同時含原文/譯文欄的 CSV/TSV/JSON）")
    ap.add_argument("translated", nargs="?", help="譯文檔；省略時從 source 的譯文欄讀取")
    ap.add_argument("--src-col", default="source", help="原文欄名（預設 source）")
    ap.add_argument("--dst-col", default="target", help="譯文欄名（預設 target）")
    ap.add_argument("--id-col", default="id", help="ID 欄名（預設 id，沒有則用列號）")
    ap.add_argument("--input-encoding", help="讀檔編碼（預設自動判斷）")
    ap.add_argument("--encoding", help="回寫目標編碼，例如 gbk / shift_jis / big5，用於缺字檢查")
    ap.add_argument("--max-line-len", type=int, help="譯文每行最大字數（全形算 1）")
    ap.add_argument("--placeholder", action="append", default=[], help="追加自訂控制碼正規表示式，可重複")
    ap.add_argument("--only-custom", action="store_true", help="只用 --placeholder，不用內建規則")
    ap.add_argument("--allow-kana", action="store_true", help="不檢查殘留假名")
    ap.add_argument("--allow-same", action="store_true", help="允許譯文與原文相同（例如純數字、專有名詞）")
    ap.add_argument("--limit", type=int, default=200, help="最多顯示幾條問題（預設 200）")
    args = ap.parse_args()

    src_path = Path(args.source)
    if not src_path.exists():
        die(f"找不到檔案：{src_path}")
    src = load_entries(src_path, args, "src")
    if args.translated:
        dst_path = Path(args.translated)
        if not dst_path.exists():
            die(f"找不到檔案：{dst_path}")
        dst = load_entries(dst_path, args, "dst")
    else:
        dst = load_entries(src_path, args, "dst")

    ph_re = build_placeholder_re(args.placeholder, args.only_custom)
    errors: list[str] = []
    warnings: list[str] = []

    missing = [k for k in src if k not in dst]
    extra = [k for k in dst if k not in src]
    if len(src) != len(dst):
        errors.append(f"條目數不一致：原文 {len(src)} 條，譯文 {len(dst)} 條")
    for k in missing:
        errors.append(f"[{k}] 譯文缺少此條目")
    for k in extra:
        errors.append(f"[{k}] 譯文多出原文沒有的條目")

    for key, s in src.items():
        if key not in dst:
            continue
        d = dst[key]
        if not s.strip():
            continue
        if not d.strip():
            errors.append(f"[{key}] 譯文為空")
            continue
        if d == s and not args.allow_same and (KANA_RE.search(s) or re.search(r"[A-Za-z]{3,}", s)):
            warnings.append(f"[{key}] 譯文與原文相同，疑似漏譯：{s[:40]}")

        sp = Counter(ph_re.findall(s))
        dp = Counter(ph_re.findall(d))
        if sp != dp:
            lost = list((sp - dp).elements())
            added = list((dp - sp).elements())
            detail = []
            if lost:
                detail.append(f"遺失 {lost}")
            if added:
                detail.append(f"多出/被改 {added}")
            errors.append(f"[{key}] 控制碼不一致：{'；'.join(detail)}")

        if not args.allow_kana:
            stripped = ph_re.sub("", d)
            kana = [c for c in KANA_RE.findall(stripped) if c not in KANA_ALLOW]
            if kana:
                warnings.append(f"[{key}] 殘留假名「{''.join(kana)[:10]}」：{d[:40]}")

        for nl in ("\\n", "\n", "\\r\\n"):
            if s.count(nl) != d.count(nl):
                warnings.append(f"[{key}] 換行數不一致（{nl!r}：原文 {s.count(nl)}，譯文 {d.count(nl)}）")
                break

        if args.encoding:
            bad = []
            for c in d:
                try:
                    c.encode(args.encoding)
                except UnicodeEncodeError:
                    bad.append(c)
            if bad:
                errors.append(f"[{key}] 無法以 {args.encoding} 編碼的字元：{''.join(dict.fromkeys(bad))}")

        if args.max_line_len:
            plain = ph_re.sub("", d)
            for line in re.split(r"\\n|\n", plain):
                if len(line) > args.max_line_len:
                    warnings.append(f"[{key}] 行長 {len(line)} 超過上限 {args.max_line_len}：{line[:40]}")
                    break

    def show(title: str, items: list[str]) -> None:
        if not items:
            return
        print(f"\n== {title}（{len(items)}）==")
        for line in items[: args.limit]:
            print("  " + line)
        if len(items) > args.limit:
            print(f"  ……其餘 {len(items) - args.limit} 條未顯示")

    print(f"檢查條目：原文 {len(src)} 條 / 譯文 {len(dst)} 條")
    show("錯誤", errors)
    show("警告", warnings)
    if not errors and not warnings:
        print("\n全部通過。")
    elif not errors:
        print("\n沒有錯誤，請人工確認上述警告。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
