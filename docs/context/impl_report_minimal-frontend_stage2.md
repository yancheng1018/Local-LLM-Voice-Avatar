# 实现报告 · minimal-frontend stage2

> 2026-09-14。规格书：`temp_spec_minimal-frontend_stage1.md`（stage1）+ `temp_spec_minimal-frontend_stage2.md`（stage2，本文件）。
> 本报告只写结论与判断。行数变化以 stage1 交付时为基线；stage1~2 期间前端目录尚未纳入 git，故为文件快照对比而非 diff。

## 1. 状态

**完成。** stage1 + stage2 全部改动落地，pytest 12 passed、全量 77 passed、tsc 与 build 均退出码 0。
未做 §6 人工验收（需浏览器与服务运行时），此项仍待用户执行。
`l2d_debug_panel.ts` 恰为 200 行，卡在约束线上，无余量。

## 2. 实际改动的文件清单

| 文件 | 行数变化 | 说明 |
|------|---------|------|
| `src/renderer/l2d_debug_panel.ts` | 新建 → 200 | stage1 建为 266，经拆分/压缩；stage2 只改 `ids()` 与 `buildList` 四处 |
| `src/renderer/l2d_debug_panel_types.ts` | 新建 → 33 | stage1 拆分产物：`DebugCoreModel`/`DebugPanelModel`/`Row` |
| `tests/test_debug_panel.py` | 74 → 112 | stage2 重写为 11 个精确正则用例（原 9 个宽松子串断言） |
| `tests/test_debug_panel_runtime.py` | 新建 → 37 | stage2 L2 编排：tsc 编译 → node --test |
| `tests/debug_panel_runtime.test.mjs` | 新建 → 167 | stage2 运行时用例 + mini-DOM + 假核心模型（附录 A 照抄） |
| `tests/__tsout__/` | 新建（产物） | 编译中间产物，不在 vite 引用图内；可删 |
| `index.html` / `src/ui.ts` / `src/main.ts` | +1 处 / +3 处 / +3 处 | stage1 接线，stage2 未动 |
| `src/renderer/types.ts` / `l2d.ts` / `style.css` | +2 行 / +12 行 / +15 行 | stage1 接线与样式，stage2 未动 |

## 3. 与规格书的一致性

**按规格完成**：stage2 §2 的路径修正（`parameters.ids`/`parts.ids`）、四项文件动作、§4 的 11 个用例、§5 命令原样执行。
**按规格完成**：stage1 的六处插入、四区 DOM、行工厂、RAF 刷新、行为快照语义，以及 §3.1 两个导出接口。
**偏离 1**：类型拆到独立文件（stage1 未要求）——单文件 266 行超 200 上限，3 次压缩后仍 227 行。
**偏离 1 续**：stage2 §0 已明确追认此偏离，故现视为规格内；`export type ... from` 再导出保证了公共导出名不变。
**偏离 2**：`#debug-panel-btn` 追加进既有按钮选择器列表（规格书未提）——否则按钮不继承胶囊样式，是功能必需。
**偏离 3**：源码保持 `model?.[field]?.ids` 单行（放弃 100 字符行宽折行）——折行会让 §4 用例 6 的正则失效。
**未偏离**：stage2 §0 列出的接线链逐处未动，`l2d_debug_panel_types.ts` 也未改动。

## 4. 遇到的问题

**根因（stage1 遗留）**：`ids()` 读 `core.model.parameterIds`，该路径不存在，故参数/部件区永远空。
`parameterIds`/`partIds` 是框架 CubismModel 的 private 字段，公开结构是 `model.parameters.ids`/`model.parts.ids`。
stage1 §2 的 API 面未经运行时验证，且 stage1 测试全是子串断言——「字符串存在」≠「路径正确」，故 9 绿仍坏。

**卡点（stage1 行数）**：266 行，3 次压缩（合并双 builder → 瘦身 → DOM 工厂）后仅到 227 行，随即停止上报。
结论是超标部分非排版冗余（约 45 行是规格强制的两个导出接口），故建议拆分而非放宽，用户采纳。

**失败尝试**：DOM 工厂 `elem(tag, text?, className?)` 净增 2 行，已删除改回直接 `createElement`。
**失败尝试**：`makeRow` 由返回元素改为返回 void，导致 `appendChild(this.makeRow(...))` 类型报错，已修调用处。
**失败尝试**：`model?.[field]?.ids` 折行触发 `test_id_path_fixed` 失败（正则跨不过换行），按 §5 约束改源码而非测试。

**反向验证**：把 `ids()` 改回错误路径后 L2 层立刻红（`actual: undefined, expected: true`），确认新测试能真抓此根因。

## 5. 改进建议

**API 面必须运行时验证**：规格书写「已核实」的路径实为静态推断。建议凡涉及第三方库内部结构的断言，附一条可在控制台执行的自检命令。
**测试分层应前置**：stage1 只做子串断言是本次返工主因。建议今后凡「功能可跑」的实现，一律配 L2 运行时层（真代码 + 假模型 + mini-DOM）。
**行数上限宜在规格书预算**：stage1 给的单文件方案实测超限 33%，建议规格书先估行数再定文件划分。
**规格书代码片段需注明是否强约束格式**：§2 的单行写法被用例正则依赖，但未说明；建议标注「勿折行」或改用跨空白正则。
**新增依赖规避路径**：规格书称 L2 层「零新依赖」，实际依赖 tsc 直接编译单文件绕过 vite，此模式可复用于其他前端模块。

## 6. 待确认疑点

**疑点 A（需立即决策）**：§6 自检命令 `__vtuber.renderer.model.internalModel.coreModel.model.parameters.ids.length` 未经实测。
`l2d.ts` 中 `model`/`coreModel` 的访问层级我只验证过 stage1 的 `coreModel.model`，未验证能否穿过 `renderer.model`。
若报错或返回 `undefined`，是命令写法问题还是功能问题需区分；面板是否出滑条应以 §6 第 3 项为准。

**疑点 B（可延后）**：`l2d_debug_panel.ts` 恰 200 行零余量，后续任何新增都会破线。
建议下阶段动手前先决定：接受再次拆分，还是将上限调为 220（参照 `l2d_params.ts` 已有先例）。

**疑点 C（可延后）**：`tests/__tsout__/` 编译产物是否入库未定——已随目录被 git 视为未跟踪，建议加 `.gitignore`。
**疑点 D（可延后）**：`frontend-minimal/` 整体仍未纳入 git 版本控制，stage1~2 均无提交历史可比。
