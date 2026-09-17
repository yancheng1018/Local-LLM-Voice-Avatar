# 研究大纲：清理待处理遗留

> 生成：2026-09-18（/plan-research，强模型）
> 用途：供 /research-doc（弱模型）按本大纲执行研究并产出 research_清理待处理遗留.md
> 用户意图：分析待处理遗留，根据分析结果决定解决顺序

## 1. 研究问题定义

对 current-work.md「待处理遗留」的 10 条遗留逐条核实现状、分类定性、梳理依赖耦合与量级，产出一个分批的解决顺序建议（供用户裁决），而非直接执行清理。

## 2. 需要回答的子问题

1. **现状核实**：每条遗留的当前真实状态是什么？是否已被后续工作吸收、部分完成或过时（如 type12 裁决已吸收进 research2 阶段、r2 系列两份测试已转正）？
2. **性质分类**：每条属于哪一类——① 触发条件未满足的挂起项（如 l2d.ts 拆分、test_release_passes_downhit）② 待用户裁决项（repo-format 处置、stage 测试去留）③ 待立项项（launcher 集成、重建回滚）④ 按需/远期项（emotionMap、阶段 C）？各条声明的触发条件现在是否已满足？
3. **依赖与耦合**：条目间有哪些先后/耦合关系？（已知：repo-format 的 15 个 tests 文件与 test-sweep 裁决耦合；hotzone-arch 多子项依赖站点取证；l2d.ts 拆分是多个 live2d 功能项的潜在前置；spec-writing 候选影响后续所有规格书）
4. **量级估计**：每条的工作量与风险量级（涉及面/是否需要独立规格/是否触碰硬性契约）？
5. **顺序建议**：综合 1–4，推荐怎样的分批解决顺序？哪些可并行、哪些必须串行、哪些继续挂起，判定依据是什么？

## 3. 每个子问题的资料/代码位置

| 子问题 | 位置 | 只读内容 |
|--------|------|----------|
| 1 现状核实 | docs/context/current-work.md（§待处理遗留，权威清单） | 全节 10 条原文 |
| 1 现状核实 | docs/context/archive.md | 各条对应的收尾/验收记录，核实是否已吸收 |
| 1/2 状态与分类 | docs/context/research_leftover-triage.md | 上一轮遗留分诊的框架与先例（stage1/stage2 结论） |
| 1/2 live2d 相关条目 | docs/context/minimal-frontend-live2d.md | R2-a/b/c/d 契约、l2d.ts 拆分例外入档原文 |
| 2 hotzone-arch | docs/context/spec-l2d-touch-engine.md | 该条锚点文档，确认待裁决子项清单原文 |
| 1/3 阶段 C 依据 | docs/context/research_live2d动作链条修正.md §7/§8 | 延后项原始依据 |
| 2 spec-writing | docs/context/spec-writing.md | 检查项候选是否已有归属/部分落地 |
| 1/3 test-sweep | frontend-minimal/tests/（目录盘点） | 核实 10 个带 stage/debug 痕迹文件是否仍在、r2 系列是否已改名转正 |
| 4 repo-format 现状 | 命令：`ruff format --check .`（只读检查） | 核实未格式化文件数是否仍为 25 |

补充定位手段：对条目中的符号/文件名（如 test_release_passes_downhit、scan_live2d_models.py）先用 rg 定位再读相关片段，不整读大文件。

## 4. 输出文档结构（research_清理待处理遗留.md）

1. 研究问题与范围
2. 遗留清单盘点（逐条表：条目 / 来源锚点 / 现状核实结果 / 性质分类）
3. 触发条件核查（挂起项的触发条件是否已满足）
4. 依赖与耦合分析（必须串行的链、可并行的组、单向耦合对）
5. 量级与风险评估（每条：工作量档位 / 是否需独立规格 / 风险点）
6. 解决顺序建议（分批方案：近期可执行 / 待裁决后执行 / 独立立项 / 继续挂起，含判定依据）
7. 遗留候选与边界说明（本次研究自身产生的新候选，仅记录不处理）

## 5. 已知约束和边界

- 本研究**只分析排序，不执行任何清理**：不删改 current-work.md、不动代码、不跑 format、不做 git 操作；顺序方案是建议，裁决权在用户。
- 清单以 current-work.md §待处理遗留为唯一权威来源，共 10 条；archive.md 仅用于核实，不一致时以 current-work.md 为准并在报告中标注差异。
- 触发条件明确未满足的项（l2d.ts 拆分 = 下次加新功能前；downhit 断言 = 首次误报时）默认维持挂起，只核实不改判。
- 「待用户裁决」类（repo-format 处置、stage 测试去留）研究只给建议与选项，不替用户裁决。
- hotzone-arch 一条含 ①–④ 多组子项且部分依赖站点取证（需下载 chunk 反查），本研究不取证，只按子项拆开排序。
- 弱模型执行时不修改任何文件（含本大纲）；研究文档中新建硬性契约只能列「契约候选」。
