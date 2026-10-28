# game-localization-zh

**讓 AI Agent 做遊戲漢化時，上下文連貫、角色語氣一致，讀起來像原生中文，而不是機翻。**

一個免費、開源的 [Agent Skill](https://agentskills.io)，適用於 Claude Code、Gemini / Antigravity、Cursor、Codex 等支援 skills 的 AI Agent。
支援日文 / 英文 → 簡體 / 繁體中文。

[English summary](#english)

---

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

## 功能

- **專案記憶檔**：術語表、角色卡、風格決定、劇情摘要、進度。每批翻譯前必讀、翻完必更新，跨批次保持一致
- **以場景為單位翻譯**：先通讀、弄清誰對誰說話和情緒，再下筆
- **人稱、稱呼、敬語與關係演變**：角色從疏遠到親密，稱呼跟著劇情變
- **梗的處理**：直譯後在全形括號內加簡短解釋，例如 `直譯（解釋）`；同一個梗只解釋一次
- **用詞貼合遊戲語境**：古風、奇幻、校園、科幻各用各的說法
- **自動選簡繁**：遊戲自帶可用繁體資源用繁體，否則用簡體（省 token）
- **初翻、校對、潤色三道工序**
- **技術保護**：控制碼、變數、換行、編碼、缺字、UI 字數限制
- **自動驗證腳本**：`scripts/check_l10n.py`，純 Python 標準庫，免安裝套件
- **開局四查**：文字槽位、key 使用圖譜、圖片全盤點、存檔格式 —— 在翻譯前就把「日文死角」找出來
- **進度提醒協議**：只要檢查清單還有未通過項，AI 每個回覆都會在最後一行提醒，直到全部 ✅
- **一鍵／精修模式**：只要「全中文就好」的人回一句「啟動」即可，AI 自己跑完全程
- **失敗案例庫**：8 個實戰踩過的坑與對應硬規則，新專案直接迴避
- **只用免費工具**：需要下載任何工具前，先向使用者說明用途並取得同意

## 開局四查與進度提醒

看過太多「文字都翻好了，進遊戲還有一堆日文」的案例，根源幾乎都不是翻譯品質，而是**沒查乾淨就開工**。這個 skill 要求 AI 在動筆前先做四查：

| 查什麼 | 抓什麼 |
|---|---|
| 文字槽位 | 所有會顯示文字的位置（含純漢字日文、字串拼接、`jname` 之類的屬性） |
| key 圖譜 | 同一個值被「顯示」幾處、「比對」幾處、存檔有沒有存 —— 用數據決定能不能改 |
| 圖片 | 全量列尺寸與透明度，**優先看小圖**（按鈕條、時間圖、開關標籤最容易漏） |
| 存檔 | 格式與編碼；資料型遊戲常把角色資料快照存進存檔，改好文本讀檔會被蓋回原文 |

查完後 AI 會給一份【開工簡報】，使用者只回一句「啟動」，之後 AI 一路做完。**只要清單還有未通過項，每個回覆最後一行都會提醒**：

```
🔲 未完成檢查 (3/10)：⑤圖片盤點 ⑦實機巡檢
```

全部通過才會變成 `✅ 檢查全部通過`。

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
└── scripts/
    └── check_l10n.py     # 自動驗證
```

## 限制

- 規範能明顯改善品質，但不能取代模型本身的能力，也不能取代人工通讀與實機測試
- 本 skill 提供方法與流程，不內建各引擎的解包工具；需要時 Agent 會先徵求你的同意再下載
- 請只對你合法擁有的遊戲進行漢化，並遵守當地法律與原作者的授權條款

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

## 貢獻

歡迎 Issue 與 PR，特別是：

- 更多「機翻 vs 合格譯文」對照例子
- 各引擎的提取 / 回寫經驗
- 驗證腳本支援更多格式

## 授權

[MIT](LICENSE)

---

## English

**game-localization-zh** is a free, open-source Agent Skill that makes AI agents translate games (Japanese/English → Chinese) with consistent context and natural phrasing instead of literal machine-translation output.

It enforces a fan-translation-group workflow: persistent glossary / character sheets / style decisions / plot summary, scene-level translation, honorific and relationship-stage tracking, meme annotation `literal（explanation）`, setting-appropriate wording, translate → proofread → polish passes, control-code protection, and a stdlib-only validator script (`scripts/check_l10n.py`).

Install: `npx skills add shiinamashironoe/game-localization-zh`
