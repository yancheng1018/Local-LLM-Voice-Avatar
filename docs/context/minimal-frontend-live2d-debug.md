# 极简前端 · Live2D 调试工具（调试栏 / 热区叠加层）

> 拆分自 minimal-frontend-live2d.md（2026-09-30，R30 裁决）。总入口与遗留 → minimal-frontend.md；兄弟分册：基础管线（工程/协议/历史/口型）→
> minimal-frontend-foundation.md、Live2D 主册（手势/触摸引擎/复位）→ minimal-frontend-live2d.md、Spine → minimal-frontend-spine.md、
> 模型切换 → minimal-frontend-model-switch.md

**stage1~2 仿 l2d.su 调试栏（2026-09-14，l2d_debug_panel.ts + l2d_debug_panel_types.ts）**：

- 顶栏「🧪 调试栏」开关，四区：显示（可见性/不透明度/眨眼/呼吸/物理开关）、动作（按组
  FORCE 播放）、参数（全参数滑条实时读写）、部件（部件不透明度滑条）。仅 Live2D；
  换模型 `onModelChanged()` 重建，Spine 无该方法面板自动消失
- ⚠️ **pixi-live2d-display 取核心模型的唯一公开途径是 `coreModel.getModel()` 方法**，
  核心结构为 `getModel().parameters.ids` / `getModel().parts.ids`。框架 CubismModel 的
  `_model` 是 private，**不存在 `.model` 公开访问器**——任何 `.model` 直读恒 undefined
  且经 `?.` 链静默短路（调试栏参数/部件区曾因此两轮空白：先错 `parameterIds`，再错
  `.model` 这一跳）。控制台一锤定音自检：
  `__vtuber.renderer.model.internalModel.coreModel.getModel().parameters.ids.length`
- **遗留清理候选**：l2d.ts 的 `coreModel?.model?.canvasinfo` 兜底永不执行（死代码，生产路径
  走 `internalModel.pixelsPerUnit`），建议改 `getModel()` 或删除，防再被当「先例」照抄
- 调试滑条被 ParamDriver/眨眼/呼吸/物理/口型每帧回写覆盖**属预期行为**（调试工具，
  不做协调逻辑）；RAF 刷新跳过用户拖动中的行。⚠️ `l2d_debug_panel.ts` 恰 200 行
  零余量（纯类型已拆到 `_types.ts`），加功能前先决策拆分或 220 行例外（参照 l2d_params.ts 先例）

**stage7 热区调试叠加层（2026-09-16，已验收）**：

- 叠加层 `l2d_touch_debug.ts`：区状态 ok/H/O/G/T 着色 + 参数读数 + idleIndex 读数（语义契约
  见 spec-l2d-touch-engine.md §8）；纯渲染逻辑已拆 `l2d_touch_debug_helpers.ts`（106 行）
- ⚠️ **行数上限例外：`l2d_touch_debug.ts` 实际守护 = 200 行**（`test_l2d_debug_line_budget`
  LIMIT=200；本条目旧「220 封顶」为过时口径）。research2 实施后实测 199 行，零余量，
  再加功能先拆分而非续压（参照 l2d_params.ts 先例）
- 调试栏滑条**指针捕获**（r4 §10.2-C）：pointerdown 即 `setPointerCapture`（try/catch 兜底），
  拖出滑条外释放 pointerup 也必达，防 `active` 滞留导致该行永不回写（面板"不刷新"）
