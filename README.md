# game-localization-zh

**讓 AI Agent 做遊戲漢化時，上下文連貫、角色語氣一致，讀起來像原生中文，而不是機翻。**

一個免費、開源的 [Agent Skill](https://agentskills.io)，適用於 Claude Code、Gemini / Antigravity、Cursor、Codex 等支援 skills 的 AI Agent。
支援日文 / 英文 → 簡體 / 繁體中文。｜v1.4.0｜[English](#english)

---

## 引擎支援狀態

**先看這個**——標題是通用漢化，但只有 RPG Maker 有專屬工程層，其餘走通用流程：

| 引擎 | 狀態 | 內容 |
|---|---|---|
| **RPG Maker MV / MZ** | ✅ **專屬層** | `engines/rpgmaker-mz/`：抽取／校驗／回寫／圖片解密重繪／字體／存檔／實機驅動，17 個腳本 |
| Ren'Py | 🟡 通用流程 | `.rpy` 純文字，直接套用主規範；無專屬腳本 |
| TyranoScript | 🟡 通用流程 | `.ks` 純文字＋標籤，直接套用主規範 |
| Wolf RPG / Kirikiri | 🟡 通用流程 | 需先自行解包，再套用主規範 |
| Unity / Unreal | 🟡 通用流程 | 需工具解包（AssetBundle／pak），無專屬層 |
| 其他／自製引擎 | 🟡 通用流程 | 四查＋驗證腳本照用 |

「通用流程」＝ 四查、術語表、譯文準則、check_l10n 驗證全部可用，只是**沒有現成的抽取／回寫腳本**，Agent 要現場寫。

## 為什麼需要它

直接叫 AI「幫我翻譯這個遊戲」，通常會得到：

- 逐句孤立翻譯，前後文接不上
- 同一個角色名、道具名前後譯法不同
- 角色說話都一個樣，敬語和稱呼亂跳
- 滿滿翻譯腔：「稍微在做思考的事情而已」
- 吞掉控制碼（`\C[1]`、`{name}`、`%s`），遊戲直接報錯

這個 skill 把民間漢化組與專業遊戲本地化的工作規範寫成 AI 必須遵守的流程。

| 原文 | 機翻 | 使用本 skill |
|---|---|---|
| …別に。ただ、ちょっと考え事してただけ | ……並不。只是，稍微在做思考的事情而已。 | ……沒什麼啦。只是在想點事情。 |

## 核心功能（五項）

- **專案記憶檔**：術語表、角色卡、風格決定、劇情摘要、進度。每批翻譯前必讀、翻完必更新，跨批次保持一致
- **先查有沒有現成漢化**：開工前查 DLsite／Steam／VNDB／GitHub，官方有中文就別白做
- **補丁安全掃描**：靜態紅旗檢查（可執行檔／DLL 劫持／加殼／編碼執行），D 級一律拒裝
- **自動驗證腳本**：`scripts/check_l10n.py`，純標準庫，檢查控制碼、殘留假名、漏譯、行長、編碼缺字
- **RPG Maker 專屬層**：`engines/rpgmaker-mz/`，從抽取到實機驗證的完整流水線

<details>
<summary>其餘功能（展開）</summary>

- **以場景為單位翻譯**：先通讀、弄清誰對誰說話和情緒，再下筆
- **人稱、稱呼、敬語與關係演變**：角色從疏遠到親密，稱呼跟著劇情變
- **梗的處理**：直譯後在全形括號內加簡短解釋，例如 `直譯（解釋）`；同一個梗只解釋一次
- **用詞貼合遊戲語境**：古風、奇幻、校園、科幻各用各的說法
- **自動選簡繁**：遊戲自帶可用繁體資源用繁體，否則用簡體（省 token）
- **初翻、校對、潤色三道工序**
- **技術保護**：控制碼、變數、換行、編碼、缺字、UI 字數限制
- **開局四查**：文字槽位、key 使用圖譜、圖片全盤點、存檔格式 —— 在翻譯前就把「日文死角」找出來
- **進度提醒協議**：只要檢查清單還有未通過項，AI 每個回覆都會在最後一行提醒，直到全部 ✅
- **一鍵／精修模式**：只要「全中文就好」的人回一句「啟動」即可，AI 自己跑完全程
- **成本預估與設置建議**（v1.4+）：四查完就給三檔預算、每萬字 token 量級、子代理併發數與 reasoning 檔位；選精修會提醒划不划算。**是估算，不是報價**
- **失敗案例庫**：11 個實戰踩過的坑與對應硬規則，新專案直接迴避
- **只用免費工具**：需要下載任何工具前，先向使用者說明用途並取得同意

</details>

## 安裝

### 方法一：skills CLI（推薦）

```bash
npx skills add shiinamashironoe/game-localization-zh
```

全域安裝（所有專案都能用）：

```bash
npx skills add shiinamashironoe/game-localization-zh -g
```

### 方法二：手動

把本倉庫複製到你的 Agent 的 skills 目錄，例如：

| Agent | 路徑 |
|---|---|
| Claude Code | `~/.claude/skills/game-localization-zh/` |
| Antigravity / Gemini | `~/.gemini/config/skills/game-localization-zh/` |
| 其他 | 參考該 Agent 的 skills 文件 |

```bash
git clone https://github.com/shiinamashironoe/game-localization-zh.git ~/.claude/skills/game-localization-zh
```

## 使用

對你的 Agent 說：

> 幫我給這款遊戲做中文漢化

Agent 會先回覆 `已載入game-localization-zh skill`，再開始流程。沒有看到這句話，表示 skill 沒被觸發，可以直接說「用 game-localization-zh skill」。

四查做完會給一份【開工簡報】＋成本預估，你回一句「啟動」就開始：

```text
【開工簡報】
作品：XXX（RPG Maker MZ）
模式：A 一鍵漢化
字體：簡體　←　依據：無繁中資源
現成漢化：官方無中文；民間補丁 0 個
文字：23 檔 / 11,755 條
圖片：25 張有文字，預計重繪 25
存檔：zlib+UTF8；會遷移 2 個檔，先備份
預估成本：標準 ≈ ¥5–8（30 萬字，deepseek-flash）⚠ 僅估算，非承諾
建議設置：子代理 8 併發／批次 1200 條／翻譯子代理 reasoning=medium
```

### 驗證腳本

```bash
# 原文檔 + 譯文檔（JSON、CSV、TSV、逐行 TXT）
python scripts/check_l10n.py source.json translated.json

# 單一表格，含原文欄與譯文欄
python scripts/check_l10n.py sheet.csv --src-col source --dst-col target

# 檢查回寫編碼缺字、每行字數
python scripts/check_l10n.py src.json dst.json --encoding gbk --max-line-len 28

# 自訂控制碼
python scripts/check_l10n.py src.json dst.json --placeholder "\\\\V\\[\\d+\\]"
```

會檢查：條目數與 ID、控制碼與佔位符、空白譯文、疑似漏譯、殘留假名、換行數、編碼缺字、行長。

## 先查有沒有現成漢化

翻譯前先花 30 秒查一下，可能整件事都不用做：

```bash
python scripts/find_existing_l10n.py --game "<遊戲目錄>"
```

查四個免 key 的來源（DLsite 官方中文、Steam 支援語言、VNDB 語言版本、GitHub 公開補丁），輸出候選表與結論。若要用第三方補丁，先掃：

```bash
python scripts/scan_patch_safety.py "<壓縮包或目錄>"
# A/B 可用、C 只給連結、D 拒絕安裝（退出碼 0 / 2 / 3）
```

原則：**只查、只報告，不下載、不代裝**；灰產站只給手工連結；官方中文永遠優先。

## 開局四查與進度提醒

看過太多「文字都翻好了，進遊戲還有一堆日文」的案例，根源幾乎都不是翻譯品質，而是**沒查乾淨就開工**。這個 skill 要求 AI 在動筆前先做四查：

| 查什麼 | 抓什麼 |
|---|---|
| 文字槽位 | 所有會顯示文字的位置（含純漢字日文、字串拼接、`jname` 之類的屬性） |
| key 圖譜 | 同一個值被「顯示」幾處、「比對」幾處、存檔有沒有存 —— 用數據決定能不能改 |
| 圖片 | 全量列尺寸與透明度，**優先看小圖**（按鈕條、時間圖、開關標籤最容易漏） |
| 存檔 | 格式與編碼；資料型遊戲常把角色資料快照存進存檔，改好文本讀檔會被蓋回原文 |

查完給【開工簡報】，使用者回「啟動」，之後一路做完。**只要清單還有未通過項，每個回覆最後一行都會提醒**：

```
🔲 未完成檢查 (3/10)：⑤圖片盤點 ⑦實機巡檢
```

全部通過才會變成 `✅ 檢查全部通過`。

## 引擎層：RPG Maker MV/MZ

`engines/rpgmaker-mz/` 是**選配層，不替代主規範**——翻譯規範、四查、簡報、進度協議一律照 `SKILL.md`，這裡只補引擎手法。

```bash
export RM_GAME="<遊戲根目錄>"
E=engines/rpgmaker-mz/tools

python $E/snapshot.py --apply     # 備份 data/js/index/save/fonts
python $E/extract.py              # 抽文本 → _localization/work/*.jsonl
python $E/runtime_scan.py --all   # 插件 JS 裡執行時才顯示的日文
python $E/img_inventory.py        # 圖片盤點 + 接觸表
python $E/apply.py --apply        # 從備份回寫（可重複執行）
python $E/verify_all.py           # 假名／日文助詞／控制碼／行寬
```

| 子命令 | 用途 |
|---|---|
| `extract.py` | 按白名單抽 401／102／405／320-322／DTextPicture／DB／System；跳過註解與變數名 |
| `apply.py` | 永遠從 `backup/data_orig/` 讀原始檔再寫，先 misc 後 box |
| `img_redraw.py` | 四種重繪模式（hgrad／rowwise／mask／bar），按 `img_cfg.json` 驅動 |
| `font_install.py` | 裝 Noto Sans SC 並檢查譯文缺字 |
| `migrate_save.py` | MZ 存檔遷移（zlib＋latin-1＋UTF-8 雙層編碼，先驗 1:1 往返） |
| `verify_all.py` / `check_assets.py` | 全量殘留檢查／JSON 與圖片完整性 |

詳細手法、11 條坑、圖片 token 預算見 [`engines/rpgmaker-mz/ENGINE.md`](engines/rpgmaker-mz/ENGINE.md)。

## 檔案結構

```
game-localization-zh/
├── SKILL.md              # 主規範（Agent 讀這個）
├── templates/            # 專案記憶檔範本，複製到遊戲旁的 _localization/
│   ├── glossary.md
│   ├── characters.md
│   ├── style.md
│   ├── summary.md
│   └── progress.md
├── scripts/
│   ├── check_l10n.py         # 自動驗證
│   ├── find_existing_l10n.py # 查現成漢化
│   ├── scan_patch_safety.py  # 補丁安全掃描
│   └── font_compat.py …      # 字體相容性
└── engines/                    # 引擎專用手法（選配，不替代 SKILL.md）
    └── rpgmaker-mz/
        ├── ENGINE.md           # RPG Maker MV/MZ 流水線與坑
        ├── tools/              # 17 個腳本（RM_GAME 環境變數驅動）
        └── templates/          # cfg.json 範本、批次翻譯指令模板
```

## 字體相容性（v1.1+）

漢化前先檢查遊戲字體畫不畫得出目標中文字，避免「文本全對、遊戲裡空白」：

```bash
python scripts/font_compat.py --game "<遊戲根目錄>" --report font_report.md
```

- **缺碼位**：瀏覽器回退系統字體 → 一行裡粗細混雜
- **空字形**（cmap 有、輪廓為 0）：瀏覽器不回退，直接空白一格

處理（自動備份 `gamefont.css` 與原字體）：

```bash
python scripts/font_patch.py --game "<遊戲根目錄>" --mode replace \
    --font "assets/fonts/NotoSansSC-game.otf" --apply
# 想保留原字體風格、只補洞：
python scripts/font_patch.py --game "<遊戲根目錄>" --mode drop-empty --apply
```

自帶字體 `assets/fonts/NotoSansSC-game.otf` 是 Noto Sans SC 子集（GB2312＋假名＋標點，SIL OFL 1.1，約 2MB）；可用 `scripts/subset_font.py` 依遊戲實際字符重新裁切。

## 限制

- 規範能明顯改善品質，但不能取代模型本身的能力，也不能取代人工通讀與實機測試
- 本 skill 提供方法與流程；除 RPG Maker MV/MZ 外，各引擎的解包工具要現場處理，需要時 Agent 會先徵求你的同意再下載
- 成本預估是**估算不是報價**，受模型單價、reasoning 檔位、重試次數影響
- 請只對你合法擁有的遊戲進行漢化，並遵守當地法律與原作者的授權條款

## 貢獻

歡迎 Issue 與 PR，特別是：

- 更多「機翻 vs 合格譯文」對照例子
- 各引擎的提取 / 回寫經驗（想加 `engines/<engine>/` 請附可跑的腳本）
- 驗證腳本支援更多格式

## 授權

[MIT](LICENSE)

---

## English

**game-localization-zh** is a free, open-source [Agent Skill](https://agentskills.io) that makes AI agents localize games (Japanese/English → Simplified or Traditional Chinese) with consistent context and natural phrasing instead of literal machine translation.

Works with Claude Code, Gemini / Antigravity, Cursor, Codex and any agent that supports skills.

### Engine support

| Engine | Status | Notes |
|---|---|---|
| **RPG Maker MV/MZ** | ✅ **dedicated layer** | `engines/rpgmaker-mz/`: extract / validate / apply / image decrypt-redraw / font / save / live-test, 17 scripts |
| Ren'Py, TyranoScript | 🟡 generic | plain-text scripts, use the main spec |
| Wolf RPG, KiriKiri | 🟡 generic | unpack first, then use the main spec |
| Unity, Unreal | 🟡 generic | unpack (AssetBundle/pak) first |
| Other / custom | 🟡 generic | the four checks and validators still apply |

"Generic" means the workflow (pre-flight checks, glossary, translation rules, validators) applies, but you have to write the extraction/apply layer yourself.

### Install

```bash
npx skills add shiinamashironoe/game-localization-zh      # or add -g for global
# manual: git clone https://github.com/shiinamashironoe/game-localization-zh.git ~/.claude/skills/game-localization-zh
```

### Usage

Say to your agent: *"localize this game into Chinese"*. It replies `已載入game-localization-zh skill`, runs the four pre-flight checks (text slots / key graph / image inventory / save format), prints a briefing with a cost estimate, and waits for one word: `啟動`.

### What it enforces

- **Persistent project memory**: glossary, character sheets, style decisions, plot summary, progress — read before every batch, updated after
- **Scene-level translation**: read the whole scene, work out who is talking to whom and how, then translate
- **Honorifics and relationship stages**: a character's address changes as the story advances
- **Meme handling**: literal translation plus a short parenthetical explanation, explained once
- **Control-code protection**: `\C[1]`, `{name}`, `%s`, newlines, encoding, missing glyphs, UI width limits
- **Pre-flight check for existing localizations**: queries DLsite / Steam / VNDB / GitHub before starting — skip the work if an official Chinese release exists
- **Patch safety scan**: static red-flag analysis of third-party patches (executables, DLL hijacking, packers, encoded payloads), class D is refused outright
- **Automated validator**: `scripts/check_l10n.py` (stdlib only) — entry count, control codes, untranslated lines, kana residue, line length, encoding coverage
- **Cost estimate before you commit**: three tiers (lean / standard / polished) with per-10k-character token figures, plus recommended sub-agent concurrency and reasoning effort. **An estimate, not a quote.**

### Limitations

Method, not magic — it cannot replace model capability or human review. Only localize games you legally own.

### License

[MIT](LICENSE)
