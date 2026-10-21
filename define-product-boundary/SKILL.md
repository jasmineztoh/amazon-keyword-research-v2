---
name: define-product-boundary
description: 界定亚马逊商品的功能、卖点、适配限制和包装内容。用户给 ASIN、站点、Listing、说明书或页面截图时，先生成可复用的产品边界，供关键词和广告工作使用。
---

# 功能卖点界定

独立运行，不筛关键词，不拓词，不生成 Excel。输出 `产品边界.md`。

1. 明确 ASIN、站点和变体。尚未分配 ASIN 的新品可用资料中的 SKU 标识，写 `asin=unassigned`、`sku` 和 `input_mode=materials`，不得借用竞品 ASIN 或伪称读过页面。用户资料可独立使用；只给 ASIN 时读取对应亚马逊前台。两者都有时互证，冲突以前台为准。页面失败后改用对应 ASIN 的前台截图或导出，不无限重试；均不可得时记录 `blocked`，说明缺少页面证据，停止下游正式筛词。训练资料不冒充本次在线读取。
2. 从原文提取商品类型、支持功能、场景、限制、包装配件。每项绑定来源及原文摘录。分析、关键词种子和投放提示不是事实。明确不支持记 `unsupported`；未证实记 `unknown`。包装未列配件不等于不附带。
3. 已有同 ASIN/站点/变体边界可复用；未分配 ASIN 的新品须同 SKU/站点/变体。身份不匹配、事实改变或新证据推翻旧事实时重建。变体未知只能与未知变体匹配，不跨变体默认复用。
4. Agent 自动编写下述 JSON，不让用户填技术字段，然后运行：

```text
python scripts/boundary.py build --input facts.json --output 产品边界.md
python scripts/boundary.py check --input 产品边界.md --asin ASIN --market US --variant unknown
```

JSON 合同：`version: 2`；`asin`（10位；未上架填 `unassigned` 并提供 `sku`）、`market`（US/DE/UK/CA/FR/IT/ES/JP/AU）、`variant`（未知写 unknown）、`input_mode`（materials/asin/both）、`sources`、`facts`、`conflicts`。未上架模式仅接受资料来源，每份来源也写相同 `sku`。

每个 source：`id, kind, locator, asin, market, variant, captured_at, content`。kind 为 `live_page/page_export/screenshot/material`；content 是本次实际读到的文字，截图则写可辨识文字，禁止猜读。locator 是 URL 或文件路径；captured_at 是证据取得日期；原资料时间不详写 unknown。每个 fact：`id, category, claim, state, source_ids, quotes`；category 为 `type/feature/scenario/compatibility/limit/package`；state 为 `supported/unsupported/unknown`；quotes 是 `{source_id: 原文摘录}`。unknown 也需要说明检查过什么资料；完全缺证据时 sources 和 facts 可为空，输出待核实边界。conflicts 为 `{claim, source_ids, resolution, winner_source_id}` 列表，前台证据胜出；不能用原文不存在的推断写成已证实事实。

脚本核对身份、摘录和结构，不能替代事实理解。生成后亲自核对事实与来源，确保商品类型清楚；下游从同一 Markdown 读取机器数据，防止人看的边界与机器看的边界分离。

