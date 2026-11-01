# 引擎层：RPG Maker MV / MZ

> 本文是 `game-localization-zh` 的**引擎专用手法**，不是独立 skill。
> 主 skill 的规矩照旧：§0.0 模式、§0.1 四查、§0.0.1 开工简报、§0.2 进度协议、§3 译文准则、§4.1 自动验证。
> 这里只回答一件事：**MZ 的文本/图片/字体/存档怎么安全地挖出来再塞回去**，以及 MZ 特有的坑。
> 冲突时：翻译规范听主 skill，引擎事实听本文（例如「图片只加密前 16 byte」）。

## 怎么认出 MZ

目录里有 `data/*.json` + `js/rmmz_*.js` + `img/*.png_` + `Game.exe`（NW.js）。
判据：`data/System.json` 存在且 `js/rmmz_managers.js` 存在。

## 0. 开局（15 分钟，做完再动手）

```bash
export RM_GAME="<游戏根目录>"            # Windows: $env:RM_GAME="..."
E=<skill目录>/engines/rpgmaker-mz/tools
python $E/snapshot.py --apply            # 备份 data/js/index/package/save/fonts
python $E/extract.py                     # → <游戏>/_localization/work/boxes.jsonl + misc.jsonl
python $E/runtime_scan.py --all          # 运行时硬编码日文（插件 JS + plugins.js 参数）
python $E/img_inventory.py               # → work/img_inventory.tsv + 接触表
```

**然后立刻实机跑一遍**（`Game.exe` → 截图标题/对话/HUD/菜单）。这一步能提前抓到：
Chronus 日历的「1日目/08時/朝」、菜单里的姓名板图片、SNS 截图里的日文——漏了都要返工。

| 判断项 | 怎么看 |
|---|---|
| 引擎 | `data/System.json` + `js/rmmz_*.js` 存在 = MZ |
| 图片加密 | `img/*.png_` 前 16 byte = `5250474d56…`，`System.encryptionKey` 是 hex。**只加密前 16 byte**，其余是明文 PNG（不是整文件 XOR，这点最容易写错） |
| 字体 | `System.advanced.mainFontFilename`，常见是日文字体，缺简中字形 → 必换 |

## 1. 文本槽位（extract.py 已覆盖）

| code | 含义 | 是否显示 |
|---|---|---|
| 401 | 对话行 | ✅ 主体 |
| 102 | 选项 | ✅ |
| 405 | 滚动文字 | ✅ |
| 320/321/322 | 角色名/昵称/简介 | ✅ |
| 356/357 里带 `text` 的 dict | DTextPicture 文字（档案面板等） | ✅ |
| Items/Weapons/Skills/Actors… 的 name/description | 道具说明 | ✅ |
| System.terms / elements / types / MapInfos.name | 系统用语 | ✅ |
| 402 / 408 / 355 / 655 | 分支标签 / 注释 / 脚本 | ❌ 不显示，别翻 |
| System.variables / switches | 变量开关名 | ❌ 不显示，别翻（省一批 token） |

`\HINT[レベルアップ]`、`<プレゼント>`、`shop1`、praiseId 数字都是**查找 key**，保持原样。

## 2. 分批与翻译（成本大头）

```bash
python $E/split_batches.py               # 默认 2 万字符/批
python $E/build_canonical.py             # 重复原文取多数译法（一致性）
```

给子代理的指令：**读 `templates/PROMPT.md` + 项目 glossary/characters/style + 自己的批次**。

成本要点（跑过一轮实测）：
- **子代理用 medium effort，不要 max** —— 翻译质量靠术语表 + checker，不靠推理深度。
- 批次别切太碎：**每批 1000~1400 条**（约 2.5~3 万字符）。固定 prompt 开销 × 批次数 = 白烧。
- **所有子代理共用同一段前缀**（PROMPT + glossary 合并成一个文件再读）→ 命中 prompt cache。
- 一批一个子代理，同时不超过 10 个（DSH 上限）。

## 3. 回写

```bash
python $E/apply.py                # dry-run：报 missing
python $E/apply.py --apply        # 从 backup/data_orig 读、写 data/，可重复执行
```

`apply.py` 的硬约束：
- **先 misc 后 box**（box 会改变 list 长度，misc 的 index 是原始档的）
- 401 游程替换时复制最后一条命令的字段，只换 code/parameters
- System.json 最后覆写 title / font / currencyUnit（不然被 backup 冲掉）

## 4. 字体

```bash
python $E/font_install.py --install            # 装 skill 自带 Noto Sans SC
python $E/font_install.py                      # 只做覆盖率检查
```
缺字只在「浏览器连系统字体都找不到」时才是豆腐；一般只在字体不统一。报告里说清楚。

## 5. 图片（最容易翻车）

```bash
python $E/img_inventory.py            # 先看接触表，找出有字的
```
在 `_localization/img_cfg.json` 里逐张写规则，然后 `python $E/img_redraw.py --preview`。

四种模式，按背景结构选：

| mode | 适用 | 做法 |
|---|---|---|
| `hgrad` | 标题按钮、姓名板（横向渐变条） | 采样若干列插值重建，保留 alpha 形状 |
| `rowwise` | 粉色药丸标签、底部条（横向均匀） | 用「文字左侧干净列」的颜色逐行填 |
| `mask` | 文字压在插画上（TalkIcon） | 只擦亮/暗字形像素，行内就近取色 |
| `bar` | 半透明渐隐菜单条（pcmenu） | 固定 RGB + 逐列 alpha |

**别用整块填充**——会盖掉圆角、投影和高光。**试错要放子代理**：主 agent 只看 montage。

### 图片的 token 预算（实测）

单张不贵，贵的是「放在主上下文里被反复计费」。

| 尺寸 | tokens（28px patch 估算） |
|---|---|
| 1280×800 整屏截图 | ~1,300 |
| 1020×2136 montage | ~2,800 |
| 768×480 | ~470 |
| 300×300 缩略图 | ~115 |
| 40 张缩略图拼一张 | ~1,500（每张约 38） |

参照：1000 条对话 ≈ 25k tokens，所以 **看 20 张全屏图 ≈ 翻译 1000 条**。

实战数据（RJ01695949）：图片阶段看了 ~30 次 ≈ 40k tokens，因主上下文每轮重发，
实际占账单 10~15%（约 1.5~2.5 元）。

规则：
1. **主 agent 只在这两个时刻看图**：开局接触表一次、最终定稿一次。
2. **抠字试错全给子代理**——子代理上下文独立，试 10 轮也不进主账单。
3. **图压到 512px 以下**（`thumbnail((512,512))`），tokens 直接减 60%。
4. **先用文字判断有没有字**：扫像素颜色/行结构，确认有字才看图，别「先看一遍再判断」。
5. 拼 montage 时用 `cols=5, cell=300`，一张能放 20~40 张，成本约等于 1.5 张全屏图。


## 6. 存档

```bash
python $E/migrate_save.py --apply
```
格式：`JSON → zlib.deflate(level 1) → 按 latin-1 转成字符串 → 以 UTF-8 写盘`。
解码反过来：`read → utf-8 decode → latin-1 encode → zlib.decompress`。
脚本会先证明 1:1 往返再写。

## 7. 验证（缺一不可）

```bash
python $E/verify_all.py      # kana 0 / 日文助词 0 / 控制码失衡 0 / 超宽 0
python $E/check_assets.py    # data JSON 全部可解析 + plugins.js 可解析 + 图片全部可解码
```
然后实机：标题、开场、HUD、菜单、SNS/档案面板各截一张，确认字体和中文都到位。

**实机驱动用 CDP**（NW.js 加 `--remote-debugging-port=9222`）：
`Page.captureScreenshot` 截图、`Input.dispatchKeyEvent` 按键，不用抢鼠标。
注意：`SceneManager._scene` 为 null 时先 `Page.reload`（强制 kill 会留下 profile 锁）。

## 坑清单（都是真踩过的）

1. **强制 kill 后立刻重开会白屏** —— 等 8 秒让 NW.js 进程完全退出；或 `Page.reload`。
2. **窗口标题** 由 `index.html` 的 `<title>` 决定，不是 package.json；两处都要改。
3. **图片只加密前 16 byte**，整文件 XOR 会把图毁掉。
4. **`・`(U+30FB) 和 `ー`(U+30FC) 会被假名检查误判** —— 统一改成 `·` 和「——」。
5. **checker 要先剥控制码再扫假名**，否则 `\HINT[レベルアップ]` 永远报错。
6. **子代理写文件时 `\n` 会变字面反斜杠+n** —— 让它用 python 写，别用文本工具。
7. 路径含 `[`（如 `[Kimochi]`）→ Python 用 `os.listdir`/直接路径，别用 glob；PowerShell 一律 `-LiteralPath`。
8. **plugins.js 里改参数前先数出现次数**，多个 plugin 共用同一串（如「選択肢ヘルプ」在两处）。
9. **文件夹外的运行时文字**：Chronus 的时间段名硬编码在 `js/plugins/Chronus.js`（`{name: ' 朝', ...}`），不在任何 data 文件里。
10. **菜单姓名板 / 档案底板 / SNS 截图是图片里的字**，文本层面查不到——开局一定要过一遍接触表。
11. **别把 `_localization/` 写进发行包**，但留在游戏目录方便重跑。

## 工具清单

| 文件 | 作用 |
|---|---|
| `loc_core.py` | 路径、CFG、控制码正则、normalize、event_lists |
| `snapshot.py` | 备份原始档（data/js/index/package/save/fonts） |
| `extract.py` | 按白名单抽文本 → boxes.jsonl / misc.jsonl |
| `split_batches.py` | 切批（默认 2 万字符） |
| `check_batch.py` | 校验 id/控制码/假名/行宽 |
| `build_canonical.py` | 重复原文的多数译法 |
| `apply.py` | 从备份回写 data/ |
| `verify_all.py` | 全量残留检查 |
| `check_assets.py` | JSON/图片完整性 |
| `runtime_scan.py` | 插件 JS 里的运行时日文 |
| `img_inventory.py` | 图片盘点 + 接触表 |
| `img_redraw.py` | 按 img_cfg.json 重绘 |
| `img_lib.py` | 解密/加密/载入/保存 |
| `font_install.py` | 装字体 + 覆盖率 |
| `plugins_edit.py` | 按 cfg 替换 plugins.js 参数 |
| `set_title.py` | System/package/index 三处标题 |
| `migrate_save.py` | 存档迁移 |

## 预算参考

30 万字规模、medium effort、批次合并、图片外包：**5~7 元 / 2~3 小时**。
max effort + 逐张图试错：**15 元以上**。

## 项目配置

`<游戏>/_localization/cfg.json`，模板见 `templates/cfg.example.json`：
`title_cn` / `font_filename` / `currency_unit` / `save_title_from` / `actor_rename` /
`normalize_pairs` / `plugin_string_pairs`。
