# 规格书 · stage3 v2（修正版）：拖拽参数管线补全 + 热区可见性诊断

> 供弱模型执行。stage3 v1 已实现且人工验收失败。主模型复核代码与数据后的结论（§0）：
> 症状①（拖拽互动无反应）根因已锁定并有 deob 证据；症状②（部分模型背景互动热区缺失）数据层
> 已排除，剩余疑点用「诊断先行 + 叠加层状态可视化」收口。**先执行 §2 阶段A 诊断，再改代码。**
> 测试集：guanghui_9 + **wuqi_3**（吾妻·心向何方的指导课，本地 touch.json 已核验与站点一致）。
> 红线：不改 AGENTS.md、backend、官方 `frontend/`；不改 `l2d_touch.ts` 既有导出签名；命令一律 PowerShell。

## 0. 失败根因（主模型复核，弱模型可按指引复核）

1. **拖拽参数管线缺口（症状①，证实）**：现实现 `accumulateDrag`（l2d.ts:184-198）只对
   `actionTrigger.type ∈ {1,6,7}` 的规则累积拖拽；`toParamRule`（l2d.ts:404-436）只注册
   circle 型（432）、type1/6/7 型（433）、mode2 型（434）。而真实数据里：
   - guanghui_9（62 条）：type 分布 `{2:58, None:2, 12:1, 7:1}` —— **没有一条 type1/6**；
     可拖拽区 = TouchDrag4/5（**slide 型**：无 actionTrigger、offsetY=-15/-20）+
     TouchDrag1/2/3/15（**circle 型**：type2+circle，target=1/1/10/1）。
   - wuqi_3（34 条）：type 分布 `{2:29, None:4, 12:1}`；slide 型 = TouchDrag2/3（offsetY=-150）、
     TouchDrag6（-10）、TouchDrag7（-2）。
   → 两模型的拖拽区**全部**落在未实现的两类里，type∈{1,6,7} 一条都不存在 → 拖拽死路。
2. **引擎真实拖拽语义（deob，修正此前理解）**：
   - `offsetX/offsetY` 对 slide 型规则是**拖拽轴灵敏度**（非位置偏移）：引擎
     `live2DLinearDragValue` 按轴算值、`|dx/offsetX| >= |dy/offsetY|` 选主轴（offset 为 0 按 1
     兜底），线性值 → clamp 链 → smooth 写参数（`setOfficialLive2DParameterTarget`）。
   - circle 型是**按住拖拽的画圈手势**（引擎有 `live2DCircleDragParameterValue`）：按住期间参数向
     `circleTarget` 逼近，`|v-target|<0.05` 后回落 `startValue`，可继续逼近（循环）；单击=一次
     逼近+回落。v1~v3 的「仅 tap poke」不完整。
   - type1/4：拖拽中按 num/time 触发 action（本次数据无此类，保留通用分支即可）。
3. **症状②现状（部分排除）**：wuqi_3 本地 touch.json 与站点 `/data/ships/CN/39904.json` 完全一致
   （34 条、offset 分布相同，WebFetch 已核验）；wuqi_3/guanghui_9 的 moc3 均含
   TouchBody/TouchHead/TouchSpecial 绘画件（默认区存在）；链/门槛/idle 均已实现。
   剩余假设：**姿态相关的区可见性**（冻结姿态不同 → 区在画布外/透明度 0，stage1b §9.6 已证站点
   自身 0~7 区波动）、叠加层只画「可用」区导致被剔除的区「看不见」、个别模型默认区绘画件缺失。
   → 不臆测，按 §2 阶段A 诊断后对症。

## 1. 文件清单

| 操作 | 路径 | 内容 |
|------|------|------|
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | toParamRule 增 slide 注册；accumulateDrag 改通用 hold 管线；诊断日志 |
| 修改 | `frontend-minimal/src/renderer/l2d_params.ts` | hold 驱动：slide 轴选择 + circle 画圈循环 |
| 修改 | `frontend-minimal/src/renderer/l2d_touch_debug.ts` | 叠加层显示全部已注册区 + 状态标记 |
| 修改 | `frontend-minimal/tests/test_l2d_hotzone_stage3.py` | 断言更新（§5） |
| 不改 | `frontend-minimal/src/main.ts`、`l2d_touch.ts` | 现实现正确，保持 |

## 2. 阶段A：双模型诊断（必做，先诊断后修改；结论追加 research_live2d_stage1.md「stage1c」）

1. **本地诊断日志**：给 loadTouchRules 加逐规则剔除原因计数并在 console 输出一行汇总：
   `[Touch] guanghui_9 注册 28/62：drawable缺失1、画布外23、（其余成功）`（字段名可自定，语义对齐）。
2. **本地姿态快照**：guanghui_9 与 wuqi_3 加载完成（idle 播完冻结后）各记录一次：哪些 Touch*
   区在画布内、透明度、渲染序（用现有诊断日志或控制台手查）。
3. **站点对照（爬取已授权）**：浏览器开 `https://l2d.su/cn/skins/399042/`（wuqi_3）与
   `/cn/skins/237031/`（guanghui_9），开「显示→触摸区域」叠加层，记录：区数、区名、位置、
   各区点击/拖动是否响应；与本地快照对照，差异写入 stage1c。
4. **判定**：若站点同样显示区缺失/不响应（姿态或门槛所致），本地「缺失」即为站点同款行为，
   在报告中注明并保持现状；若站点有而本地无，按差异修（§3.4）。

## 3. 实现规格

### 3.1 拖拽参数管线（核心，修症状①）

1. **注册扩展**（`toParamRule`）：新增分支——无 `actionTrigger` 且（offsetX≠0 或 offsetY≠0）的
   slide 型 → `ParamRule { ..., slide: { ox: offsetX||0, oy: offsetY||0 } }`；保留 circle/mode2/
   type1/6/7 分支。
2. **hold 管线**（`ParamDriver` 新增）：`beginHold(id)` / `holdDelta(id, dx, dy)`（模型局部每帧
   位移）/ `endHold(id)`。l2d.ts 的 `accumulateDrag` 改为：downHit 规则是 ParamRule（slide 或
   circle 或 type1/6/7）即 `holdDelta`；pointerdown 时 `beginHold`，pointerup 时 `endHold`+`save()`。
3. **slide 驱动**（update 每帧，对 hold 中的 slide 规则）：
   `xv = accX / (ox || 1)`，`yv = accY / (oy || 1)`，取 `|xv| >= |yv| ? xv : yv`（引擎同款轴选择）；
   累积值经 `clampChain`（dragDirect/rangeAbs/range）→ smooth 趋近写参数。带 relationValue 的
   （如旧 31 集的 type6）先 `lookup103` 再写。观感不对调 `DRAG_VALUE_SCALE`（具名常量，目测校准）。
4. **circle 驱动**（hold 中）：目标 = `circleTarget`；`|v-target| < 0.05` → 目标 = `startValue`
   （可再次逼近，画圈循环）；`smooth` 趋近。**tap 语义保留**（快速单击 = 一次逼近+回落，走现有
   poke），拖拽按住则进入循环逼近——两种输入都有效。
5. **type1/4 通用分支**：拖拽结束（pointerup）时若 downHit 为 type1/4 规则 → 触发一次其 action
   （num/time 简化为 1 次）；无 action 则无操作。
6. 释放后 revert=-1 规则的值保留 + 持久化（现有语义不动）。

### 3.2 交互门槛（保持 stage3 v1 已实现，一处澄清）

- slide 型规则（无 actionTrigger）不做 ATA.idle 门槛、不做 OE_TYPES 检查（现在实现已如此，保持）；
  circle 放行分支保持。此节无代码改动，仅确认。

### 3.3 诊断与可视化（修症状②的「看不见」）

1. **叠加层状态化**（l2d_touch_debug.ts）：全部已注册区都画——可用区实色填充；被剔除区画描边 +
   原因标记（`O`=画布外、`T`=透明度≤0.01、`G`=门槛拦截、`H`=不可见），hover/文本可选。用户从此
   能直接看出「哪些区存在但被什么剔除」。
2. **诊断日志**（§2.1）保留为常驻一行汇总，不刷屏。
3. **默认区日志**：TouchSpecial/TouchHead/TouchBody drawable 缺失的模型输出一行说明（部分模型
   没有默认区 = 站点同款，不是缺陷）。
4. **姿态**：保持「加载播一次 idle → 冻结」（站点同款）；区集合随姿态波动不为缺陷，以阶段A 对照
   记录为准。**不新增**循环/追针机制。

### 3.4 明确不做

- type12（num 监听）、type7 listenerData（Limit_box14）、relationParameter 超出 lookup103 的部分、
  tips/dragRate/ignoreDrag——维持不实现；诊断中出现按「未实现」标注即可。

## 4. 测试用例（修订 `test_l2d_hotzone_stage3.py`；与 §3 冲突的旧断言一并改写并报告）

| # | 用例名 | 输入 | 预期 | 断言点 |
|---|--------|------|------|--------|
| 1 | test_slide_rule_registered | l2d.ts | 命中 | toParamRule 含「无 actionTrigger 且 offset≠0」分支（`slide` 字样或等价） |
| 2 | test_hold_pipeline | l2d.ts + l2d_params.ts | 命中 | `beginHold`/`holdDelta`/`endHold`（或等价命名）；accumulateDrag 不再限 type1/6/7 |
| 3 | test_slide_axis_choice | l2d_params.ts | 命中 | `offsetX`/`offsetY` 参与除法与 `|xv|>=|yv|`（或等价）轴选择 |
| 4 | test_circle_drag_loop | l2d_params.ts | 命中 | hold 中 target 在 circleTarget/startValue 间翻转（比较分支），非仅 poke |
| 5 | test_type14_branch | l2d.ts | 命中 | type1/4 拖拽结束触发 action 的分支 |
| 6 | test_overlay_status | l2d_touch_debug.ts | 命中 | 状态标记逻辑（原因字母或等价）+ 全区绘制（不再只画可用区） |
| 7 | test_diag_log | l2d.ts | 命中 | `[Touch]` 汇总日志含剔除原因计数 |
| 8 | test_regression_core | 三源文件 | 命中 | TouchChain 签名；`l2d-param:`/`l2d-touch:`；playAction；playIdleOnce；OE_TYPES；ATA.idle 门槛 |
| 9 | test_build_and_bundle | `npm --prefix frontend-minimal run build` | exit 0 | 构建通过 + 字面量仍在 |

## 5. 步骤分类

**工具可完成**：§2 数据/日志核验命令；rg 定位；`npm --prefix frontend-minimal run build`；pytest。
**需要判断**（报告说明取舍）：slide 轴选择与 `DRAG_VALUE_SCALE` 的目测校准；circle 画圈的手感
（smooth/revertSmooth）；叠加层原因标记的呈现方式；阶段A 若发现站点有本地没有的区，差异归因
（姿态 vs 数据 vs 门槛）与对应处理。

## 6. 验收口径（人工对照）

1. **拖拽有反应**（症状①）：guanghui_9 拖动 TouchDrag4/5 区 → touch_drag4/5 参数变化（叠加层/
   日志可见）；按住 TouchDrag1/2/3/15 画圈 → 参数逼近 target 后回落、可循环；快速单击点戳保留。
   wuqi_3 拖动 TouchDrag2/3/6/7 → 参数变化。
2. **热区可见可解释**（症状②）：两模型叠加层显示全部已注册区及状态标记；「缺失」的区能从标记
   看出原因；阶段A 的本地-站点对照表结论明确（同款/差异+归因）。
3. 默认区动作（head/body/special）与 body 连点链行为不回归；无 touch.json 模型不回归。
4. `tests/` 全部 pytest 文件全绿 + `npm run build` 通过。

## 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_l2d_hotzone_stage3.py frontend-minimal/tests/test_l2d_touch_chain.py frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
