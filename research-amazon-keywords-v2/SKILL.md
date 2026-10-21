---
name: research-amazon-keywords-v2
description: 从上传的亚马逊竞品反查表筛选投前广告关键词，核对产品边界，按P1/P2/P3交付有数值依据的Excel。支持异构表头、多ASIN和缺失指标，不主动拓词。
---

# 关键词调研 V2

先读 `references/contract-v2.md`，与 `define-product-boundary` 并列安装。Python需要openpyxl；Excel使用Node的@oai/artifact-tool。探测依赖一次，不假定PATH有Python。仅使用当前环境允许的方式解决依赖问题，不生成伪Excel。

## 执行流程

1. 读取同ASIN/站点/变体的《产品边界.md》；未分配ASIN的新品改用同SKU/站点/变体，没有则调用前置Skill。核心类型或必要页面证据未就绪时停止筛词。事实改变时重建。已有用户资料写material，不冒充本次在线读取。
2. `python scripts/run_v2.py prepare --input 原表目录 --boundary 产品边界.md --asin ASIN --market US --variant unknown --output 工作目录`
   - 未上架新品使用 `--asin unassigned --sku 资料中实际SKU`，且产品边界必须为资料模式；不能借用竞品ASIN。
   - `--mapping`可传原表头到合同字段的JSON，由agent核实含义后编写。不得把本品广告CVR映射为市场购买率。
   - `--batch`仅用于有可核实同期清单的输入；无日期保持exploratory。口径或日期冲突分批处理。
   - 检查diagnostics和sources的源行、ASIN粒度、缺值、真实0和未知列，不把文件数当竞品数。
3. 自主阅读request.json全部候选与产品事实，大批次分段读完、保留进度，不抽样代替全量判断。生成judgments.json，顶层为request_sha256与judgments；各项见合同。按事实适配、实际数值和需求决定优先级及顺序，每个理由明确该词的需求。
4. `python scripts/run_v2.py apply --work 工作目录 --judgments judgments.json`
5. 全量复核P1/P2的产品适配、需求宽窄、优先级及组内顺序；从全部候选查核心概念和常见变体漏收，再看review-request.json的额外机会样本。参考词表在独立初判后逐词解释一致/调整/不适用，不照抄答案。修正判断须重新apply和复核。
6. 编写review.json：decisions_sha256、core_ids（全部核心概念候选ID）、core_review_note、items（id/result/reason）。每个result必须经过实际复核才写pass。超过150先复查，确有必要保留则写over_150_review，不按排序截断。
7. `python scripts/run_v2.py export --work 工作目录 --review review.json`
8. `node scripts/export_v2.mjs 工作目录/excel.json 工作目录`
   若当前环境确实没有 `@oai/artifact-tool`，使用 `python scripts/export_v2_fallback.py 工作目录/excel.json 工作目录`，并核对保存后的工作簿。不得先跳过首选导出器来省事。
9. 查看实际成品，核对数值、行数、筛选和文本安全。默认交付关键词库.xlsx；必要异常放说明页，不生成HTML。保留sources/decisions/review/manifest审计记录，不向用户堆内部文件。

## 判断原则

- 最终词只来自上传的反查词。明确产品冲突不收；未知与明确不支持分开。关键配件未知且可能买错时暂缓。
- P1准确核心，缺指标仍可P1并披露竞品效果未知；估算PPC高不自动降级。P2宽需求、条件适配、次要场景；能力未知且缺指标可有限测试并披露。未知能力升P1须解释有利与不利证据，不能单看覆盖数。
- P3须具体小额测试假设；竞品品牌可P3但不自动入表，明确冲突不能用P3放行。未入表不等于否词。
- 层级由真实需求约束决定：完整商品概念为一级，新增一项约束为二级，多个约束为长尾，不按词数分级。多标签不复制行，匹配方式依测试目的独立判断。
- 边界案例：USB-A限制的mouse for macbook为P2；能转手持的杆式机car vacuum为P3；软管未证实包含的duschkopf mit schlauch暂缓。三例仅检查边界，不能代替整批质量验收。
- 不调用历史run_stage1–5、评分或主题治理。旧100分、45/60/75阈值、ABCD、60%占比、150截断均无效。
- 用户只解决既有规则无法解决的新增商业争议，用具体词例提问；接口、逐词初判、自验与差异解释由agent完成。

复用目录前核对商品与输入变化；输入、事实或判断改变必须重跑下游。探索批次不得声称同期验证。提交/打包只收通用程序，不含用户原表、商品资料或本地审计结果。

