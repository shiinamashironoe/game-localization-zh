# 外部詞典、模型與工具

> 本庫的詞表是人腦整理的固定版本；查不到的詞再來這裡翻。連結為 2026-11 查證可用，失效時搜名稱。

## 1. 日語色情詞典

| 資源 | 內容 | 怎麼用 |
|---|---|---|
| [下ネタ辞典（simoneta）](https://simoneta.saenskinbot.com/) | 日語性俗語、身體部位、行為、黃段子的線上辭典，詞條有解釋與語感 | 查單詞的語感與使用場景，不是日中對照 |
| [simoneta-yomitan](https://github.com/W1ght/simoneta-yomitan) | 上者的 Yomitan 詞典包，可在瀏覽器直接查詞、可自動更新 | 配合 Yomitan 擴充，把原文丟進瀏覽器查 |
| [性風俗用語大辞典](https://lewd.sakura.ne.jp/top.html) | 約 1,395 條風俗／性行為用語的日文解說 | 查風俗店題材、AV 用語、角色扮演稱呼 |
| [lewd-yomitan](https://github.com/W1ght/lewd-yomitan) | 上者的 Yomitan 版 | 同上 |
| [Japanese Sex Terms](https://japanesesexterms.com/) | 英日對照的情色詞彙表，由母語譯者整理，涵蓋部位、感覺、動作、場景 | 卡住時用英文義項反推中文，比日→中直翻可靠 |
| [Wiktionary：日語性詞彙附錄](https://en.wiktionary.org/wiki/Appendix:Glossary_of_Japanese_sex_terms) | 英日對照，條目穩定、可引用 | 查生僻詞與外來語 |
| [日維：性風俗用語一覧](https://ja.wikipedia.org/wiki/%E6%80%A7%E9%A2%A8%E4%BF%97%E7%94%A8%E8%AA%9E%E4%B8%80%E8%A6%AC) | 分類清單，適合掃盲與找同義詞 | 建術語表時補漏 |
| DLsite《エロティカ和英・和英辞典》 | 商業 PDF 和英／英和詞典 | 付費；只在長期做 R18 時值得買，**不得散布** |

## 2. 模型

| 資源 | 說明 |
|---|---|
| [SakuraLLM](https://github.com/SakuraLLM/SakuraLLM) | 針對日文輕小說／Galgame 日中翻譯微調的開源模型系列；支援術語表（GPT 字典），對控制符與人稱一致性較好 |
| SakuraLLM 的 HF 組織 | 各尺寸 GGUF／量化版本；選 Qwen2.5 底的較新一代 |
| 一般大模型（DeepSeek、Claude、GPT） | 品質足夠，但**預設會審查與淡化**；必須用 `prompt-pack.md` 的 System Prompt 壓住 |

- 模型卡授權多為非商用（CC BY-NC-SA 類），商用前逐一確認。
- 模型不是萬靈丹：術語表與抽檢才是品質來源。

## 3. 批次工具

| 工具 | 說明 |
|---|---|
| [GalTransl](https://github.com/GalTransl/GalTransl) | Galgame 漢化流水線：抽取、批次翻譯、校對、回寫；支援 GPT 字典與多模型 |
| [AiNiee](https://github.com/NEKOparapa/AiNiee) | 多模態翻譯工具，支援遊戲／書籍／字幕，能吃術語表 |
| [LinguaGacha](https://github.com/neavo/LinguaGacha) | AiNiee 同作者的新一代文本翻譯器，TypeScript，支援多格式 |
| [KeywordGacha](https://github.com/neavo/KeywordGacha)（同作者，安裝前先確認） | 從文本抽關鍵詞／術語，適合開工時建表 |

- 這類工具都吃「原文→譯文」對照；`glossary-nsfw.csv` 可用
  `python scripts/glossary_to_dict.py <csv> --format arrow` 轉成 `原文->譯文`。
- 工具只負責搬運與呼叫模型，**分層與一致性仍要人定**。

## 4. 資料集（進階，非必要）

Hugging Face 上有社群製作的日語 NSFW roleplay／對話資料集（多為合成資料），可用於微調或風格參考。
搜尋關鍵字：`japanese nsfw roleplay`、`synthetic japanese dialogue`。
注意：來源與授權混亂，**不要直接餵進商業專案**，只當語感參考。

## 5. 授權與界線

1. 商業詞典（DLsite 那類）只可自用，不得轉貼、打包、再散布。
2. Yomitan 詞典包的授權看各 repo；原站詞條內容版權屬原作者。
3. 本目錄的詞表是**譯法整理**（語言對照），不是原文詞條的複製。
4. 工具與模型授權各異，商用前逐一確認；本 skill 不代為判斷。
