# 亚马逊关键词调研 V2

把竞品反查表整理成**有产品事实依据、可复核的投前广告关键词库**。先确认商品能做什么，再逐词判断搜索需求是否适合；交付按 P1 / P2 / P3 排列的 Excel，并保留每个决定的来源与理由。

本仓库包含两个并列的 Agent Skill：`define-product-boundary` 负责生成《产品边界.md》，`research-amazon-keywords-v2` 使用这份边界筛选上传的反查词。已在 Codex 工作流中验证。

## 适用场景

- 新品投放前，手里有 SellerSprite 等工具导出的竞品反查词表，需要确定先投哪些词。
- 商品功能、适配性或包装配件容易被搜索词误读，需要先核实事实。
- 多份表的列名、缺失值、ASIN 和统计窗口不统一，需要保留来源再做判断。

它是**投前选词**工具。不会凭空拓词，也不会把未入表词自动当成否词；第三方估算指标不等于本商品的广告实绩。

## 你会得到什么

| Skill | 输入 | 交付 |
| --- | --- | --- |
| [产品边界](define-product-boundary/SKILL.md) | 目标 ASIN 或未上架商品 SKU、站点、变体，以及可读取的 Listing、说明书、页面截图等 | 《产品边界.md》：商品类型、支持功能、限制、配件、原文证据和待核实事项 |
| [关键词调研](research-amazon-keywords-v2/SKILL.md) | 产品边界和上传的反查词 `.xlsx` / `.csv` / `.tsv` | `关键词库.xlsx`、逐词判断与复核记录、源行审计 |

```text
商品资料 / 目标 ASIN
        ↓
《产品边界.md》 ──→ 上传的竞品反查表
                            ↓
                  全部候选初判 → P1/P2 全量复核
                            ↓
               关键词库.xlsx + 本地审计记录
```

Excel 一词一行，可筛选。主表显示优先级、关键词、需求层级、匹配建议、入选理由，以及**本次原表确有提供**的月搜索量、ABA 排名、竞品数、估算购买率、估算 PPC 等数值。没有的字段留空；真实观测到的 `0` 才写 `0`。必要的数据口径说明放在 `说明` Sheet，不生成 HTML 报告。

## 安装

1. 从 [Releases 下载 v2.0.0 安装包](https://github.com/jasmineztoh/amazon-keyword-research-v2/releases/tag/v2.0.0)。
2. 解压后，把两个 Skill 文件夹**并列**放入 Codex Skills 目录，例如 `~/.codex/skills/`：

   ```text
   ~/.codex/skills/
   ├── define-product-boundary/
   └── research-amazon-keywords-v2/
   ```

3. 运行环境需要 Python 和 `openpyxl>=3.1,<4`。Excel 首选支持 `@oai/artifact-tool` 的 Node 工作环境；没有该工具时，安装包内有基于 `openpyxl` 的后备导出器。

两个文件夹缺一不可。旧 `.xls` 请先另存为 `.xlsx` 并检查列口径；正式输入支持 `.xlsx`、`.csv` 和 `.tsv`。

## 使用

将商品资料和反查表提供给 Agent，然后这样发起任务：

> 请先用 `define-product-boundary` 核对这件商品的功能、限制和包装内容，生成《产品边界.md》；再用 `research-amazon-keywords-v2` 处理我上传的竞品反查词表。站点是 US，目标 ASIN 是 `[实际 ASIN]`，变体是 `[实际变体或 unknown]`。请逐词判断、全量复核 P1/P2，解释重要的暂缓和排除原因，交付可筛选的 `关键词库.xlsx`。

如果新品尚未分配 ASIN，提供资料中的**真实 SKU**，让产品边界使用资料模式；不要借用竞品 ASIN。只有目标 ASIN、且亚马逊页面读不到，又没有该 ASIN 的截图或页面导出时，流程会说明缺少页面证据并停在产品边界环节，不会伪称已经完成在线核实。

Agent 会依次运行产品边界构建与校验、反查读取、全部候选判断、P1/P2 和核心词复核、Excel 导出。开发者需要的 JSON 字段及 `prepare → apply → export` 命令见[数据合同](research-amazon-keywords-v2/references/contract-v2.md)和两个 `SKILL.md`；普通使用无需手工填写 `judgments.json` 或 `review.json`。

### 结果如何判断

| 结果 | 含义 |
| --- | --- |
| P1 | 与已证实的核心商品需求高度匹配，优先考虑 |
| P2 | 需求更宽、条件适配或次要场景，需要控制投放范围 |
| P3 | 有明确的小额测试假设；不能用来放行已确认冲突的词 |
| 暂缓 / 排除 | 关键能力缺证据、与商品冲突，或当前没有充分的投前测试理由；**不自动等于否词** |

匹配方式与 P1/P2/P3 分开判断。即使搜索量缺失，准确的核心词仍可能是 P1；估算 PPC 高也不会自动降级。超过 150 词时只做交付前复查，不按数量机械截断。完整判断规则见[关键词 Skill](research-amazon-keywords-v2/SKILL.md)。

## 数据与证据边界

- 最终关键词只来自你上传的反查表；规范化不创造新词。
- 每条候选保留文件、Sheet、原行号和相关 ASIN 等来源线索。没有核实同批次清单与时间窗时，只标为**探索**，不把观测 ASIN 数称作同期竞品数。
- 产品明确不支持的功能不能靠高流量词绕过；“未证实”与“明确不支持”分别处理。
- 逐词初判、P1/P2 复核和差异解释由 Agent 完成。只有现有规则解决不了的新商业争议，才需要使用者拍板。
- 仓库和发布包不包含用户反查原表、商品资料、训练结果或本地审计文件。运行结果写入使用者指定的目录；请按所用 Agent 平台的数据政策处理输入。

## 项目结构

```text
define-product-boundary/
├── SKILL.md                 # 产品事实与页面证据流程
└── scripts/boundary.py      # 边界构建与身份校验

research-amazon-keywords-v2/
├── SKILL.md                 # 逐词判断与复核流程
├── references/contract-v2.md
└── scripts/
    ├── run_v2.py            # prepare / apply / export
    ├── export_v2.mjs         # 首选 Excel 导出
    ├── export_v2_fallback.py # 后备 Excel 导出
    └── v2/data.py            # 反查读取与证据归一
```

正式 V2 只按上述两个 `SKILL.md` 和 `run_v2.py` 执行。历史评分、主题治理、固定分数阈值和 HTML 输出均未纳入本仓库的发布源码与安装包。

## 验证与项目状态

`v2.0.0` 发布前，本地 103 项测试中 102 项通过、1 项跳过；三组训练资料及一组修复后的已见样本完成包内链路检查。封存样本**首次运行失败**，原因与修复均已记录；修复后通过的是已见样本回归，不能当作新的独立盲测成功。站点页面不可读且没有替代证据时，流程按规则停止。

发现问题时可提交 Issue，附上可复现步骤、预期和实际结果；不要上传未脱敏的商品资料或反查原表。代码变更请围绕正式 V2 入口，并说明对应的产品事实或数据合同影响。
