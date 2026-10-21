# V2 数据合同

正式入口为 `scripts/run_v2.py`。历史 run_stage1–5 仅留作回归，不进入 V2 安装包。

- 产品边界：独立 Skill 生成的 Markdown，内含同一份结构化事实。ASIN/站点/变体须匹配；未上架且未分配ASIN的资料模式可用SKU/站点/变体匹配，绝不把竞品ASIN充作目标商品。核心类型或必要页面证据缺失时停止筛词。
- 源行：文件 SHA256、文件名、Sheet、原行号、原词、规范词、字段原值、缺失状态（column_missing/blank/observed/invalid）、目标 ASIN 集、相关 ASIN 集、日期和来源口径。规范化只做 Unicode NFKC、空白整理、小写；不扩词，不合并语义近义词。
- 竞品身份：Sheet 明示单 ASIN 可识别；多 ASIN 表读取 Asin 清单与行相关 ASIN 的交集；无清单的探索表保留逐行相关ASIN，但只称观测、不称同期验证。原表相关产品数可能大于目标清单，独立保留，不冒充目标覆盖。
- 批次：无清单仅探索。正式清单必须逐个文件匹配哈希、站点、起止日期、工具、口径及目标 ASIN；不同窗口或来源口径分开，禁止跨批次统计。文件名日期不冒充核实日期。
- 数值：搜索量等词市场指标同口径同窗口取中位数，保留全部原值；不同口径不合并。探索展示单个代表源行的数值，并标记日期未核、指标可能不一致，不将混合来源中位数当同期结果。竞品数是 ASIN 去重，文件数从不代替。购买率为比例、PPC 币种依来源与站点校验，第三方估计非本商品广告 CVR/CPC。
- 逐词判断：覆盖候选全部 ID，每个含 decision(include/hold/exclude)、priority(P1/P2/P3或null)、level(一级/二级/长尾)、tags、match、reason、fact_ids、fit(supported/unknown/conflict)、test_hypothesis、evidence_note、order。入表 conflict 禁止，P3 必须具体假设；未知能力须披露；未知配件可能买错应 hold。模型判断不可引入新词。
- `judgments.json` 的完整外层是 `{"request_sha256":"<实际 request.json 的 SHA256>","judgments":[{"id":"<候选原ID>","decision":"include","priority":"P1","level":"一级","tags":["核心需求"],"match":"Exact / Phrase","reason":"实际需求与商品事实的关系","fact_ids":["type"],"fit":"supported","test_hypothesis":"","evidence_note":"","order":1}]}`。`match` 是字符串，只能为 `Exact`、`Phrase`、`Broad`、`Exact / Phrase`、`Phrase / Exact`；它独立于优先级。未入表词 `priority:null`，仍须判断并保留理由。上述仅示结构，不能把示例词或结论当商业答案。
- 质量审查：每个入表 P1/P2 全量核对；所有核心概念词及常见变体复查；额外复查非 P1/P2 搜索量前20和已核覆盖前20。43词参考逐词解释差异。复核表覆盖实际ID、结论与理由；不虚构质量准确率。
- `review.json` 的外层是 `{"decisions_sha256":"<实际 decisions.json 的 SHA256>","core_ids":["<经全量查找的核心概念候选ID>"],"core_review_note":"查漏范围、修正与理由","items":[{"id":"<review-request及core_ids覆盖的ID>","result":"pass","reason":"本词为何维持或修正当前结论"}],"over_150_review":"仅当超过150词时填写实际复查与保留依据"}`。有未解决问题时不写 pass，应修正 judgments、重新 apply 并复核；脚本只校验覆盖和结构，不能代替人的语义审查。
- Excel：六种稳定判断信息加当次可用数值、必要证据说明。一词一行，不合并主题单元格；无 HTML。150 仅交付前提醒，超过时须留下复查说明。

旧五维分数、ABCD、45/60/75门槛、主题治理、60%主题占比、150截断均不进入 V2 调用链。

