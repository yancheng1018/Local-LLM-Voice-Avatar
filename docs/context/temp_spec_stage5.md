# 规格书 · stage5：拖拽像素制 + circle 翻转开关 + 空参数区注册 + idle 单次化 + 实测协议

> 供弱模型执行。stage4 实现后人工验收失败：①光辉 TouchDrag4/5 方向幅度仍不准；②光辉打开页面
> 只显示 TouchDrag4/5、无法切换动作；③吾妻 TouchIdle1 不见、TouchDrag8 面板停留太短、
> TouchDrag6/7 幅度方向不准。主模型本轮挖到了引擎**定义体**（不再是调用点推断），四个根因全部
> 实锤（§0）。测试集：guanghui_9 + wuqi_3 + xinnong_6。
> **本规格最大新增：§5 实测协议为强制项**——静态 pytest 断言已连续两轮「全绿但实际不可用」，
> 本轮起以真实浏览器行为为准。
> 红线：不改 AGENTS.md、backend、官方 `frontend/`；不改 `l2d_touch.ts` 既有导出签名；命令一律 PowerShell。

## 0. 根因（deob 定义体/数据实锤，弱模型可复核 Temp/su_modelRuntime_deob.js）

1. **slide 拖拽增量单位 = CSS 像素，不是模型局部单位**。定义体（字符串表索引法定位）：
   - `live2DUnityDragDelta(interaction, currentX, currentY, axis)`：
     `axis==='x' ? currentX − interaction.x : interaction.y − currentY`
     —— x 右正、**y 上正**（按压点−当前），单位 = 指针事件的 clientX/Y（像素）。
   - `live2DLinearDragValue(rule, base, delta, axis)`：
     `base + delta / (axis==='x' ? offsetX : offsetY)`（offset 非 0 才算，0/缺失则返回 undefined）。
   - 数据印证：offset 全按像素标定——wuqi_3 TouchDrag2/3 offsetY=-150（150px=丝袜开关全程）、
     TouchDrag6=-10（300px=明暗全程 [0,30]）、TouchDrag7=-2（360px=时间 ±180 全程，start=180）、
     光辉 TouchDrag4/5=-15/-20（快滑）。我们现用模型局部单位：光辉灵敏度差 ~30 倍（拖满全程要
     几十个屏高）、吾妻差 ~5 倍且 Y 方向与引擎相反（引擎 y 上正，我们经 pixi 局部空间是 y 下正）。
2. **circle 点戳 = 翻转开关，不是「到位自动回落」**。触发路径 deob：circle 规则触发时
   `|当前值 − target| < 0.05 → 目标 = startValue，否则目标 = target`，然后平滑趋近并**停留**
   （revert=-1 不回落）。下次点击才翻回。吾妻 TouchDrag8（type2+circle，range [0,30]）= 显示 UI
   面板：现实现到位即自动回落 → 面板闪现即逝（症状③b）。
3. **空参数规则也要注册**。吾妻 TouchIdle1：`parameter='empty'` 但有 drawable、有
   `action: touch_drag12`、有 ATA——引擎按 drawable 注册、不看 parameter。我们的注册
   （v1 起的 `!param → skip`）把这类规则全丢了 → TouchIdle1「不见了」（症状③a）。
4. **idle 在循环 → 区集坍缩漂移**（症状②）。motion3.json `Meta.Loop=true`，pixi-live2d-display
   会循环播放 idle；站点引擎播一次即冻结终帧。idle 循环 → Touch* 区随动画漂移，冻结姿态永远不
   出现：打开页面那一瞬间大多区在画布外（O），只剩 TouchDrag4/5 可见可点，且点击目标乱跑
   （「无法切换到别的动作」）。
5. **转盘改屏幕像素空间**：引擎 circle 公式的 center 与 currentX/Y 同为像素坐标（y 下、
   `atan2(curX−cx, cy−curY)` 字面）。stage4 用模型局部坐标算角度，y 轴语义与引擎差一次翻转；
   改为屏幕像素空间逐字对齐（区中心的屏幕坐标可用现成 modelRectToScreen 链路取中心）。

## 1. 文件清单

| 操作 | 路径 | 内容 |
|------|------|------|
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | slide 增量像素化；转盘像素空间；空参数规则注册；idle 单次化；叠加层参数读数 |
| 修改 | `frontend-minimal/src/renderer/l2d_params.ts` | poke 到位后停留（删自动回落）；holdAcc 语义改像素（调用方换算） |
| 修改 | `frontend-minimal/src/renderer/l2d_touch_debug.ts` | 标签追加实时参数值 `touch_dragN=V`（每帧刷新，验收仪表盘） |
| 新建 | `frontend-minimal/tests/test_l2d_hotzone_stage5.py` | pytest 断言（§6） |
| 修订 | `frontend-minimal/tests/test_l2d_hotzone_stage4.py` | 与 §2/§3 冲突断言改写并报告 |
| 不改 | `main.ts`、`l2d_touch.ts`、三模型 touch.json | 保持（xinnong_6 数据 stage4 已换新，回归断言保留） |

## 2. 实现项

### 2.1 slide 像素化（修症状①）

- `accumulateDrag` 改传**像素增量**：`dxPx = e.clientX − prevX`（右正）、
  `dyPx = prevY − e.clientY`（**上正**，引擎 `interaction.y − currentY` 同构）；`prevX/Y` 每帧更新。
- `holdAcc` 语义 = 像素累积；`stepSlide` 公式骨架不变（轴选择 `|accX/ox| ≥ |accY/oy|`，offset 0
  按 1 兜底），但**删除 DRAG_VALUE_SCALE**（像素即引擎单位，恒 1），`value = startValue +
  chosen/offset` → `clampChain` → smooth 写参数。`stepDrag`（type1/6/7）同改像素幅值。
- 释放/持久化语义不变。

### 2.2 转盘像素空间（stage4 机制保留，坐标系对齐引擎）

- `dialValueFor` 改用：区包围盒**中心 = modelRectToScreen 后矩形的几何中心**（l2d_touch_debug
  已有同款换算，可抽公共函数），指针 = `e.clientX/clientY`；公式逐字保持
  `atan2(curX − cx, cy − curY) × 180/π → +360−start → mod 360 → /360 × rangeMax`。
- hold 中每帧重算（区随姿态动，中心跟随）；释放/持久化语义不变。

### 2.3 circle 点戳翻转开关（修症状③b）

- `stepCircle` 非持有（tap）路径：到位（|v−pokeTarget|<ε）后 **phase='idle' 停留，不自动回落**；
  下一次 `poke()` 时按「当前值已在 circleTarget → 目标翻回 startValue，否则 → circleTarget」翻转。
- hold（转盘）路径与释放 revert 语义不变（§0.1/2.2）。
- 自检：吾妻 TouchDrag8 单击 → 面板出现并**保持**；再单击 → 消失；第三次 → 再出现。

### 2.4 空参数区注册（修症状③a）

- `loadTouchRules` 注册门槛改为：`getDrawableIndex(drawAbleName) >= 0` 即注册空间热区，
  **不再要求 parameter 非空**（`'empty'` 同样注册）；无 parameter 的规则不进 ParamDriver，
  仅走 TouchChain 动作路径（`actionNamesOf` 取 action）。
- 默认区「未被规则占用」判断、诊断日志（注册 N/M + 原因枚举去「参数空」、增「无动作且无参数」
  计数）同步调整。
- 注意：空参数规则多数带 ATA.idle 门槛（吾妻 TouchIdle1 要求 idleIndex==1），不可交互时叠加层
  照常标 G——这是引擎语义，不算缺失。

### 2.5 idle 单次化（修症状②，核心）

- 目标：idle 组**播一次**（不循环），播完模型冻结在终帧；playAction 后的 `playIdleOnce` 同样单次。
- 机制（按序尝试，报告说明用了哪种）：
  1. 模型加载后改写设置与已加载定义：`motionManager.definitions.idle[*].Meta.Loop = false`
     （若 0.5.0-beta 从此处读 Loop）；
  2. 若无效：拦截已加载的 motion 对象（motionManager 内部持有）置 `Meta.Loop=false` / 等效字段；
  3. 若仍无效：motion 结束事件后立即 `stopMotion()` 并把该次终帧参数写回（保持姿态）。
- 自检（并入 §5 协议）：加载后静置 15s，两次截图姿态一致；`[Touch]`/控制台无循环重播痕迹。

### 2.6 验收仪表盘（支撑 §5 实测协议）

- 叠加层标签追加该区参数实时值：`TouchDrag5 [ok] touch_drag5=12.3`（每帧刷新，ParamDriver 暴露
  `getValue(parameter|id)` 只读接口）。无 parameter 的区显示 `action=xxx`。

## 3. 明确不做

type12/type7-listenerData/relationParameter 超出 lookup103/tips/dragRate/ignoreDrag 维持不实现；
不做逐像素 alpha；不为 ATA 门槛做自动解锁（链推进自然解锁）。

## 4. 明确不动

`stepSlide` 的轴选择与 clamp 链、TouchChain、默认区、playAction 名字匹配、playIdleOnce 触发时机、
xinnong_6 数据（stage4 已换新）。

## 5. 实测协议（**强制**，本轮验收以本表为准；弱模型用真实浏览器自动化执行并填表，人工照表复测）

准备：`npm --prefix frontend-minimal run build` + 本地起服务加载模型；开触摸叠加层（仪表盘模式）。

| # | 模型 | 操作 | 期望（含算式） | 判定 |
|---|------|------|----------------|------|
| T1 | 光辉 | 加载后静置 15s，截两帧 | 两帧姿态一致（idle 不循环） | 帧差=0 |
| T2 | 光辉 | TouchDrag5 按住**向下**拖 40px | 读数 ≈ 40/20 = **2.0**（dy 上负→/-20→正，range[0,30]） | 误差 ±15% |
| T3 | 光辉 | TouchDrag4 按住**向上**拖 30px | 读数 ≈ 30/15 = **2.0**（dy 上正→/-15→负，range[-10,30] 从 0 向负） | 误差 ±15% |
| T4 | 光辉 | TouchDrag1/2/15 绕区中心顺时针画一圈 | 读数 0→1 连续走完，方向随角度 | 单调 |
| T5 | 光辉 | TouchDrag3 画一圈 | 0→10 连续 | 单调 |
| T6 | 光辉 | 依次单击头/身/特殊区 | touch_head/touch_body/touch_special 动作播放 | 各 1 次 |
| T7 | 吾妻 | TouchDrag2 **向下**拖 150px | 读数 → **1**（150/150）；**向上**拖 → 0（dragDirect=1） | 精确到钳制 |
| T8 | 吾妻 | TouchDrag7 向上拖 90px | 读数 ≈ 180 − 90/2 = **135**（时间回拨） | 误差 ±15% |
| T9 | 吾妻 | TouchDrag6 向下拖 100px | 读数 ≈ 100/10 = **10**（[0,30]） | 误差 ±15% |
| T10 | 吾妻 | TouchDrag8 单击 → 等 5s → 再单击 | 面板出现**保持≥5s**；第二次点击消失；第三次再现 | 翻转 |
| T11 | 吾妻 | TouchIdle1 单击 | touch_drag12 动作播放（需先经 body 链把 idleIndex 推到 1；若被 G 拦截，记录链前置步骤后复测） | 播放或标注门槛原因 |
| T12 | 信浓 | 加载 + 注册汇总日志 | `[Touch] xinnong_6 注册 N/M` 与新数据一致（shipSkinId 307085）；body 链可推进 | 无脚本报错 |
| T13 | 全部 | 每模型叠加层截图 | 全部已注册区可见（含 O/G 提示）；无控制台异常 | 无 error |

弱模型产出：上表逐行填「实测值/PASS-FAIL/截图或读数证据」，写入研究文档 stage1d 章节；
FAIL 行必须附控制台日志。**本表全 PASS 之前不得声称完成。**

## 6. 测试用例（新建 `test_l2d_hotzone_stage5.py`；stage4 冲突断言改写并报告）

| # | 用例名 | 断言点 |
|---|--------|--------|
| 1 | test_slide_pixel_delta | l2d.ts：增量来自 clientX/Y（`e.clientX`/`prevY` 字样），无 `toModelPosition` 参与 slide 增量；DRAG_VALUE_SCALE 不存在 |
| 2 | test_slide_y_up | l2d.ts：y 增量为 `prevY - ` 形态（上正） |
| 3 | test_dial_screen_space | l2d.ts：转盘中心经屏幕换算（modelRectToScreen 或等价）+ `clientX` |
| 4 | test_circle_toggle_stay | l2d_params.ts：tap 到位分支无自动回落（无「pokeTarget = startValue」的到位后赋值；翻转仅在 poke 入口） |
| 5 | test_empty_param_registered | l2d.ts：注册门槛不含「parameter 为空跳过」（`!param` 或 `param === 'empty'` 不在空间注册路径） |
| 6 | test_idle_no_loop | l2d.ts：`Meta.Loop` 置 false 或等效单次机制存在 |
| 7 | test_overlay_readout | l2d_touch_debug.ts：标签含参数值读数（getValue 或等价） |
| 8 | test_regression_core | TouchChain 签名；`l2d-param:`/`l2d-touch:`；playAction；OE_TYPES；ATA 门槛；poke 翻转入口；xinnong 数据 shipSkinId==307085 |
| 9 | test_build_and_bundle | 构建通过 + 字面量仍在 |

## 7. 步骤分类

**工具可完成**：rg 定位；构建；pytest；§5 协议的浏览器自动化与截图。
**需要判断**：idle 单次化三种机制的实际取舍（报告注明）；转盘 smooth 手感；T11 的链前置操作步骤；
像素增量在窗口缩放下的观感（如需要，仅允许加具名全局系数并报告标定值）。

## 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_l2d_hotzone_stage5.py frontend-minimal/tests/test_l2d_hotzone_stage4.py frontend-minimal/tests/test_l2d_touch_chain.py frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
