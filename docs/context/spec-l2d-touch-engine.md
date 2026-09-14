# 规格书 · frontend-minimal 触摸规则引擎（l2d.su 复刻，stage1~6 合并版）

> temp_spec_stage1~6 六份规格的精简合并。被后续 stage 推翻的语义**不在本文**，冲突处以本文为准。
> 依据：spec-l2dsu-engine.md（站点引擎逆向）+ research_live2d_stage1.md（stage1a~1e 实测记录）。
> 开发未完结，遗留项见 §11。红线：不改 AGENTS.md、backend、官方 `frontend/`；不动 `l2d_touch.ts` 导出签名。

## 1. 范围与数据源

- 目标：frontend-minimal 的 L2D 触摸互动按 touch.json 规则数据驱动，替代组名启发式。
- 数据：`live2d-models/<name>/touch.json`（源 `https://l2d.su/data/ships/CN/<shipGroupId>.json`
  的 `ship.skins[].model.live2dTouch`）；三测试模型已核验皮肤匹配
  （guanghui_9=237031×62 / wuqi_3=399042×34 / xinnong_6=307085×27）。
- 无 touch.json 或加载失败的模型退回启发式兜底（tapMotions/头身估计/touch_idleN 递进链），不得回归。
- 手势状态机（canvas 层）：单击 / 拖动（位移>40px 触发一次）/ 长按（≥800ms）。

## 2. 模块分工与测试

| 文件 | 职责 |
|------|------|
| `renderer/l2d_touch.ts` | `TouchChain`：ATA 白名单/链状态/冷却/localStorage（纯逻辑无 pixi） |
| `renderer/l2d_params.ts` | `ParamDriver`：slide/circle/mode2/type103 参数驱动 + 持久化（220 行封顶例外，见 minimal-frontend.md） |
| `renderer/l2d.ts` | 规则注册、命中判定、动作播放、idle、仪表盘数据源 |
| `renderer/l2d_touch_debug.ts` | 叠加层仪表盘（区状态/参数读数/idleIndex 读数） |
| `src/main.ts` | 手势分发：规则命中走 TouchChain/playAction，否则启发式 |

测试（pytest 静态断言 + `npm run build`，tsc strict）：`test_l2d_touch_chain.py`（TouchChain 契约）、
`test_l2d_hotzone_stage2~6.py`（各阶段语义+regression_core）、`test_touch_debug_overlay.py`（叠加层接线）。

## 3. 规则注册（l2d.ts loadTouchRules）

- `getDrawableIndex(drawAbleName) >= 0` 即注册空间热区；**parameter 为空/'empty' 也注册**
  （吾妻 TouchIdle1 类：不进 ParamDriver，只走动作路径）。
- 原始 rules 数组全量挂 `renderer.touchRules`（含未注册为区的规则，链查找用）。
- 默认区伪规则：TouchSpecial/TouchHead/TouchBody（对应绘画件未被规则占用时）。
- 剔除原因枚举：O=画布外、G=交互门槛拦截；**透明度不剔除**（偏离项 D1）。
- 诊断日志一行汇总：`[Touch] <模型> 注册 N/M：原因计数`；默认区绘画件缺失另有说明（站点同款非缺陷）。

## 4. 命中判定与择一（hitZoneAt）

- 逐 drawable **实时**读包围盒（`getDrawableBounds`，模型局部坐标）+ 可见性（`?? true` 兜底）；
  画布外/无限/零尺寸剔除。包围盒可用 = 有限且 w>0、h>0、画布内。
- 择一优先级（引擎 pickLive2DArea 同款）：class1（规则区 offsetX/offsetY≠0）> class2（区内动作
  名经 §6 名字索引可命中）> class3（其余）；同类内**实时渲染序降序**；再平局取包围盒面积小者。
- 渲染序读取链（stage1e 实测更正，0.5.0-beta 无单数方法、`core.drawables===undefined`）：
  `getDrawableRenderOrder?.(i) ?? getDrawableRenderOrders?.()[i] ?? core._model?.drawables?.renderOrders?.[i] ?? core?.drawables?.renderOrders?.[i] ?? 0`
- visibility 维持 `?? true`：native 单数方法缺失，`getDrawableDynamicFlagIsVisible(i)` 虽实测存在但
  位义未逐字核实，不启用（留后续决策）。

## 5. 动作链（TouchChain）

- `resolve(rule, kind, available)`：冷却命中未到期→null；有 ATA→applyActive；dispatch→null 则 null；
  `limitTime>0` 记冷却（秒→毫秒）。
- ATA 两形态：**形态A**（有 `idle_enable`/`idle_ignore`，含空数组）按当前 `idleIndex` 查表置
  enable/ignore（查表空→null）；**形态B**（`enable`/`ignore`/`idle:N`）直接设置，`idle` 数字写入
  idleIndex。
- **enable/ignore 空数组 = 无该名单放行**（站点 `officialLive2DActionAllowed` 的 `length>0` 才启用；
  stage1e 修正，光辉 `enable:[]` 曾被当空白名单导致只涨 idleIndex 不播动作）。
- 白名单**持续生效**直到下一条 ATA 覆盖（规则无 ATA 不清空）。
- `idleIndex` 门槛为**等值判定**（`==N` 非 `≥N`，TouchIdle5 实证）；链步进逐级解锁（TouchIdle17
  false→true 实证）。
- actionTrigger type 分发：1=拖动触发、2=触摸即发、6=链占位、7=拖动主控；1/6/7 只认 `kind='drag'`，
  2 只认非 drag；6/7 不直接播动作；`action` 数组随机取一；动作名 ∉ available → null。
- 持久化 `localStorage['l2d-touch:<模型名>']`：`{idleIndex, activeRuleId, cooldowns}`（跨刷新/换模型保留）。
- **链步进规则查找** `findChainRule(gname)`（main.ts body 链用，findRuleByParameter 的超集）：
  `parameter===gname` ∥ `drawAbleName===驼峰化(gname)`（`touch_idle17→TouchIdle17`）∥ action 含 gname。
- **body 连点链**（偏离项 D2，游戏语义）：TouchBody 命中走 touch_idleN 编号递进（闲置 10s 重置、
  走完一轮冷却 60s、冷却期播 touch_body/touch_*、缺号自动跳过），resolve 应用 ATA → idleIndex 推进。

## 6. 动作播放与 idle

- `playAction(action)`：模型加载后构建名字索引 `{group, index, name?, fileStem?}`（遍历
  FileReferences.Motions）；归一化 `s.trim().replace(/[-\s]+/g,'_')`；条目 group/name/fileStem 及其
  归一化与 action 精确或归一化相等即命中，**全部命中顺序连播**（FORCE）；无命中不播。
- `TouchChain.resolve` 的 `available` = 组名∪动作名∪文件名去重集合。
- **播放门控** `isPlayingTouchAction`：触摸动作播放期间，新互动只放行当前命中区自身规则链。
- **idle 单次化**：`Meta.Loop` 置 false + `setIsLoop(false)`（stage1d/1e 实测生效），播一次冻结终帧；
  不做循环/追针。`playIdleOnce()` 组名 = `idleIndex>0 ? 'idle'+idleIndex : 'idle'`，组内随机。

## 7. 拖拽/点戳参数（ParamDriver）

- ParamRule 注册分支：circle 型（type2+circle）/ slide 型（无 actionTrigger 且 offset≠0）/ mode2 型
  （指针位置反应 reactSum/canvasNorm）/ type1/6/7 型。
- **slide**：像素增量 `dxPx=e.clientX-prevX`（右正）、`dyPx=prevY-e.clientY`（**上正**，引擎
  `interaction.y-currentY` 同构）；轴选择 `|accX/(ox||1)| ≥ |accY/(oy||1)|` 取大者；
  `value=startValue+chosen/offset` → clampChain（dragDirect/rangeAbs/range/parameterRange）→ smooth。
  无 DRAG_VALUE_SCALE（像素即引擎单位）。offset 数据按像素标定（如 wuqi_3 TouchDrag2=-150=全程）。
- **circle 按住=转盘**：`deg=atan2(curX-cx, cy-curY)*180/π`；`angle=((deg+360-start)%360+360)%360`；
  `dialValue=rangeMax*angle/360`。cx/cy=区**屏幕**包围盒中心（modelRectToScreen），指针=clientX/Y；
  hold 中每帧重算+平滑趋近、**不回落**；顺时针=增；`offsetCircle.start` 当前数据均无→0。
- **circle 单击=翻转开关**：poke 目标=circleTarget；到位（|v-target|<0.05）后**停留不自动回落**；
  下次 poke 按当前值翻回 startValue（吾妻 TouchDrag8 面板开/关实证）。
- type1/4：拖拽结束触发一次其 action。释放 `revert===-1` 值保留；持久化 `l2d-param:<模型名>`。

## 8. 仪表盘（l2d_touch_debug.ts）

- 全部已注册区绘制：可用区实色填充；O/G 画描边+原因标记；T（透明）降级为提示、**仍填充可交互**；
  `blockedEnable` 标注（G 且动作被白名单拒）。
- 实时读数：区参数值 `touch_dragN=V` 或 `action=xxx`（ParamDriver.getValue 只读）；左上角
  `idleIndex=N` 随链步进刷新。

## 9. 偏离站点项（有意为之，勿"修回"）

- D1 命中判定不按透明度剔除（站点剔除；本地 Touch* 辅助件透明度随姿态抖动是净伤害，stage4）。
- D2 body 连点链 touch_idleN 递进（游戏语义；站点引擎无点击计数器，stage1b Q3 实证站点无递进）。
- D3 T 状态区仍可交互（D1 的叠加层呈现）。

## 10. 明确不做

type12（num 监听）、type7 listenerData（Limit_box）、relationParameter 超出 lookup103 部分、
tips/dragRate/ignoreDrag（全站 JS 0 命中死数据）、逐像素 alpha、ATA 门槛自动解锁、dynamicFlags
可见性启用。诊断中遇到按「未实现」标注。

## 11. 遗留问题与下一步

- **C4（BLOCKED·几何）**：光辉 TouchIdle17 门槛可解锁（interactive true）但绘画件屏幕投影
  y≈−4654 视口外，物理不可点。无代码解，除非改姿态/视口。
- **C6（BLOCKED·数据疑点）**：吾妻 TouchIdle1 的 action `touch_drag12` ∉ 自身 enable 白名单
  （enable 全文录于 research §12），按数据行事不绕过。
- 信浓链跳号（1→3→6）：model3.json 缺 touch_idle2/4/5/14 组，数据事实非缺陷。
- 待办：live2d.md 的 stage1 实测修正（§1/§5.1 矛盾点、数据接口"已失效"结论已被 stage1b 推翻、
  光辉 shipSkinId 疑点已核销）合并回 spec-l2dsu-engine.md / live2d.md。
- 代码债：l2d.ts 981 行远超「单模块 ≤200」上限，待功能收口后按注册/命中/播放/参数职责拆分。

## 12. 验收方式（改引擎必读）

- 静态 pytest 断言有局限（曾连续两轮全绿但实际不可用）→ **实测协议强制**：
  - stage5 §5 表 T1~T13（像素拖拽算式/转盘/翻转/默认区/idle 单次化）
  - stage6 §5 表 C1~C9（链推进/门槛解锁/渲染序择序）+ stage1e 补充（ATA.enable=[]）
  - 两表基准与逐行实测记录在 research_live2d_stage1.md §11/§12；改引擎必须重跑相关行并记录。
- 自动化要点：区位置随姿态漂移，**动作前即时重扫命中点**，不可跨步骤缓存坐标；内嵌浏览器
  `visibility=hidden` 时 rAF 停摆，先 `visibility.set(true)`。
- 回归：无 touch.json 模型（mao_pro 等）行为不变；三份既有 pytest 全绿 + `npm run build` 通过。
