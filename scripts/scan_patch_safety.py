#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""補丁/壓縮包靜態安全掃描（不需要任何第三方套件、不聯網）。

    python scan_patch_safety.py <檔案或目錄> [--json]

分級（A 最安全 → D 必須拒絕安裝）：
    A  官方渠道（用 --official 標記），或純資料/腳本且無紅旗
    B  只含遊戲資料/文本/圖片（無可執行檔），或已簽章的可執行檔
    C  含可執行檔/安裝器但未見紅旗 —— 只給連結，不代安裝
    D  命中紅旗（下載並執行、加殼、DLL 劫持名、腳本投放、路徑穿越…）—— 拒絕協助安裝

退出碼：0=A/B、2=C、3=D、1=參數錯誤。**掃描不能證明無毒**，只能攔掉明顯的壞東西。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import struct
import sys
import zipfile

DANGEROUS_EXT = {".exe", ".dll", ".scr", ".com", ".pif", ".msi", ".bat", ".cmd",
                 ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta",
                 ".lnk", ".reg", ".jar", ".apk"}
SCRIPT_EXT = {".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta"}
DLL_HIJACK = {"version.dll", "winmm.dll", "d3d9.dll", "dinput8.dll", "dsound.dll",
              "dxgi.dll", "opengl32.dll", "msimg32.dll", "userenv.dll", "wtsapi32.dll",
              "dbghelp.dll", "cryptbase.dll", "mpr.dll", "secur32.dll", "netapi32.dll"}
BAD_STRINGS = [
    (r"powershell(\.exe)?\s+.*-e(nc|ncodedcommand)", "PowerShell 編碼執行"),
    (r"-EncodedCommand", "PowerShell 編碼執行"),
    (r"certutil(\.exe)?\s+.*-urlcache", "certutil 下載"),
    (r"bitsadmin\s+/transfer", "bitsadmin 下載"),
    (r"mshta(\.exe)?\s", "mshta 執行"),
    (r"reg\s+add\s+.*\\run\b", "註冊表自啟"),
    (r"schtasks\s+/create", "排程自啟"),
    (r"vssadmin\s+delete", "刪除陰影副本"),
    (r"bcdedit\s+/set.*recoveryenabled\s+no", "關閉修復"),
    (r"Invoke-Expression|IEX\s*\(", "PowerShell 動態執行"),
    (r"FromBase64String", "Base64 解碼執行"),
    (r"VirtualAlloc(Ex)?\s*\(.*PAGE_EXECUTE", "記憶體配置可執行"),
    (r"CreateRemoteThread|WriteProcessMemory", "跨進程注入"),
    (r"\\\\[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\\", "UNC 內網路徑"),
]

findings: list[tuple[str, str, str]] = []   # (level, code, detail)


def add(level: str, code: str, detail: str) -> None:
    findings.append((level, code, detail))


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq if c)


def scan_text(name: str, blob: bytes) -> None:
    try:
        txt = blob.decode("utf-8", "ignore")
    except Exception:                                        # noqa: BLE001
        return
    low = txt.lower()
    for pat, why in BAD_STRINGS:
        if re.search(pat, txt, re.I):
            add("D", "SUSPICIOUS_STRING", "%s 內含「%s」（%s）" % (name, why, pat[:28]))
    if len(re.findall(r"[A-Za-z0-9+/=]{200,}", txt)) >= 2:
        add("D", "LONG_BASE64", "%s 內含多段超長 Base64 字串" % name)
    if low.count("http://") + low.count("https://") >= 5:
        add("C", "MANY_URLS", "%s 內含多個外部連結" % name)


def scan_pe(name: str, blob: bytes) -> None:
    if not blob.startswith(b"MZ"):
        return
    try:
        e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
        if blob[e_lfanew:e_lfanew + 4] != b"PE\0\0":
            add("D", "BAD_PE", "%s 有 MZ 頭但 PE 標記異常（常見於偽裝）" % name)
            return
        machine = struct.unpack_from("<H", blob, e_lfanew + 4)[0]
        nsec = struct.unpack_from("<H", blob, e_lfanew + 6)[0]
        opt_size = struct.unpack_from("<H", blob, e_lfanew + 20)[0]
        opt = e_lfanew + 24
        magic = struct.unpack_from("<H", blob, opt)[0]
        ddir = opt + (96 if magic == 0x10B else 112)
        sec_dir_rva, sec_dir_size = struct.unpack_from("<II", blob, ddir + 4 * 8)
        signed = sec_dir_size > 0
        add("INFO", "PE", "%s PE machine=0x%04x 節數=%d 簽章=%s" %
            (name, machine, nsec, "有" if signed else "無"))
        if not signed:
            add("C", "UNSIGNED_PE", "%s 未簽章的執行檔" % name)
        # 節區熵
        sec_off = opt + opt_size
        high = 0
        for i in range(min(nsec, 16)):
            try:
                s = blob[sec_off + i * 40: sec_off + (i + 1) * 40]
                raw_size = struct.unpack_from("<I", s, 16)[0]
                raw_ptr = struct.unpack_from("<I", s, 20)[0]
                body = blob[raw_ptr: raw_ptr + min(raw_size, 262144)]
                if len(body) > 512 and entropy(body) > 7.2:
                    high += 1
            except Exception:                                # noqa: BLE001
                pass
        if high >= 2:
            add("D", "PACKED", "%s 有 %d 個高熵節區（疑似加殼/加密）" % (name, high))
    except Exception as e:                                   # noqa: BLE001
        add("C", "PE_PARSE_FAIL", "%s PE 解析失敗：%s" % (name, str(e)[:40]))


def check_name(name: str) -> None:
    low = os.path.basename(name).lower()
    ext = os.path.splitext(low)[1]
    if ext in DANGEROUS_EXT:
        add("C", "HAS_EXECUTABLE", "含可執行檔：%s" % name)
    if low.count(".") >= 2 and ext in {".exe", ".scr", ".js", ".pdf"}:
        add("D", "DOUBLE_EXT", "雙重副檔名偽裝：%s" % name)
    if os.path.basename(low) in DLL_HIJACK:
        add("D", "DLL_HIJACK", "DLL 劫持常見名：%s" % name)
    if ".." in name or name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
        add("D", "PATH_TRAVERSAL", "可疑路徑（穿越/絕對路徑）：%s" % name)
    if os.path.basename(low).startswith(".") and ext not in (".gitignore",):
        add("C", "HIDDEN_FILE", "隱藏檔：%s" % name)


def scan_zip(path: str) -> None:
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:                                   # noqa: BLE001
        add("C", "ZIP_UNREADABLE", "無法解析壓縮檔（%s）——請解壓後掃目錄" % str(e)[:40])
        return
    names = z.namelist()
    add("INFO", "ZIP", "共 %d 個項目" % len(names))
    for n in names:
        check_name(n)
    for n in names:
        if n.endswith("/"):
            continue
        try:
            info = z.getinfo(n)
            if info.file_size > 8 * 1024 * 1024:
                continue
            blob = z.read(n)
        except Exception:                                    # noqa: BLE001
            continue
        scan_pe(n, blob)
        scan_text(n, blob)


def scan_dir(path: str) -> None:
    count = 0
    for root, _, files in os.walk(path):
        for f in files:
            count += 1
            p = os.path.join(root, f)
            rel = os.path.relpath(p, path)
            check_name(rel)
            try:
                if os.path.getsize(p) > 8 * 1024 * 1024:
                    continue
                blob = open(p, "rb").read()
            except OSError:
                continue
            scan_pe(rel, blob)
            scan_text(rel, blob)
    add("INFO", "DIR", "共 %d 個檔案" % count)


def magic_check(path: str) -> None:
    with open(path, "rb") as f:
        head = f.read(8)
    ext = os.path.splitext(path)[1].lower()
    kind = "unknown"
    if head.startswith(b"PK\x03\x04"):
        kind = "zip"
    elif head.startswith(b"7z\xbc\xaf"):
        kind = "7z"
    elif head.startswith(b"Rar!"):
        kind = "rar"
    elif head.startswith(b"MZ"):
        kind = "pe"
    if kind == "unknown":
        add("INFO", "TYPE", "未知格式（可能是自解壓或偽裝）")
        if ext in {".zip", ".7z", ".rar", ".exe"}:
            add("D", "MAGIC_MISMATCH", "副檔名 %s 與實際內容不符" % ext)
        return
    add("INFO", "TYPE", "實際格式：%s（副檔名 %s）" % (kind, ext or "-"))
    if ext in {".zip", ".7z", ".rar"} and kind != ext.lstrip("."):
        add("C", "EXT_MISMATCH", "副檔名與實際格式不符")
    if kind == "zip":
        scan_zip(path)
    elif kind == "pe":
        blob = open(path, "rb").read()
        scan_pe(os.path.basename(path), blob)
        scan_text(os.path.basename(path), blob)
    else:
        add("C", "NEED_MANUAL", "%s 無法內建解析，請解壓後對目錄再跑一次" % kind)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--official", action="store_true", help="來源是官方渠道（Steam/DLsite 官方）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    t = a.target
    if not os.path.exists(t):
        print("找不到目標：%s" % t)
        return 1
    if a.official:
        add("INFO", "OFFICIAL", "使用者標記為官方渠道")
    if os.path.isdir(t):
        scan_dir(t)
    else:
        magic_check(t)

    worst = "A"
    order = {"A": 0, "INFO": 0, "B": 1, "C": 2, "D": 3}
    for lv, _, _ in findings:
        if order.get(lv, 0) > order[worst]:
            worst = lv
    if a.official and worst != "D":
        worst = "A"

    verdict = {
        "A": "官方渠道或純資料，可直接使用",
        "B": "只含遊戲資料/文本，無可執行檔，風險低（仍建議備份原檔）",
        "C": "含可執行檔/安裝器或無法解析 —— 只給連結，不代為安裝；安裝前請自行 VirusTotal 檢查",
        "D": "命中紅旗 —— 拒絕協助安裝／執行，請改用官方或其他來源",
    }[worst]

    if a.json:
        print(json.dumps({"level": worst, "verdict": verdict,
                          "findings": [{"level": l, "code": c, "detail": d} for l, c, d in findings]},
                         ensure_ascii=False, indent=1))
    else:
        print("目標：%s" % t)
        print("判定：%s 級 —— %s" % (worst, verdict))
        print("-" * 60)
        for lv, code, detail in findings:
            print("[%s] %-18s %s" % (lv, code, detail))
        print("-" * 60)
        print("提醒：靜態掃描不能證明無毒，只能攔掉明顯的壞東西。")

    return {"A": 0, "B": 0, "C": 2, "D": 3}[worst]


if __name__ == "__main__":
    sys.exit(main())
