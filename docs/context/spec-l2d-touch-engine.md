# 规格书 · frontend-minimal 触摸规则引擎（l2d.su 复刻，stage1~6 + r2 系列合并版）

> temp_spec_stage1~6 六份 + r2 系列（v1~v4）规格的精简合并。被后续 stage 推翻的语义**不在本文**，
> 冲突处以本文为准。依据：spec-l2dsu-engine.md（站点引擎逆向）+ research_live2d_stage1.md
>（stage1a~1e 实测记录）+ research_live2d-hotzone-touch-r4.md（r2 系列定案取证，已保留归档）。
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

测试（pytest 静态断言 + 运行时数值对拍 + `npm run build`，tsc strict）：`test_l2d_touch_chain.py`
（TouchChain 契约）、`test_l2d_hotzone_stage2~7.py`（各阶段语义+regression_core）、
`test_l2d_touch_redlines.py`（r2 红线：状态序/链 action 优先/兜底静默/行数契约）、
`test_l2d_touch_param_semantics.py`（r2_v3/v4 参数语义：无 action 放行/slide 注册/轴排除/
dragDirect 门控/resetAll）、`test_l2d_clamp_chain_runtime.py`（clampChain 与站点三步链
运行时数值对拍）、`test_touch_debug_overlay.py`（叠加层接线）。

## 3. 规则注册（l2d.ts loadTouchRules）

- `getDrawableIndex(drawAbleName) >= 0` 即注册空间热区；**parameter 为空/'empty' 也注册**
  （吾妻 TouchIdle1 类：不进 ParamDriver，只走动作路径）。
- 原始 rules 数组全量挂 `renderer.touchRules`（含未注册为区的规则，链查找用）。
- 默认区伪规则：TouchSpecial/TouchHead/TouchBody（对应绘画件未被规则占用时）。
- 剔除原因枚举：O=画布外、G=交互门槛拦截、T=透明度 ≤ 阈值剔除（**r2 收回偏离项 D1**：
  透明 Touch* 虚拟标记不进命中池，站点同款；阈值与叠加层 T 判定同源）；仪表盘状态判定序
  **G 先于 T**（r2 C2：门槛锁死区不再误标「可点」）。
- **isRuleInteractive**（交互门槛）：typed 规则只要求 type∈Oe；**无 action 规则直接放行**
  （r2_v3：站点 live2DRulePointerEnabled 不要求 action，无 offset 的区可点但无效果）；
  有 action 须过 ATA 白名单 actionAllowed；ATA.idle 防重复判定见 §5。
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

- `resolve(rule, kind, available)`：冷却命中未到期→null；**dispatch 成功后才 applyActive/save**
  （r4 §10.4.4 时序，D 级推断+站点实测锚点：白名单判定用触发前的全局 enable——先应用会把
  规则自身 action 拒在自身 ATA.enable 外，核心区自锁；触发失败不推进链状态）；
  `limitTime>0` 记冷却（秒→毫秒）。
- ATA 两形态：**形态A**（有 `idle_enable`/`idle_ignore`，含空数组）按当前 `idleIndex` 查表置
  enable/ignore（查表空→null）；**形态B**（`enable`/`ignore`/`idle:N`）直接设置，`idle` 数字写入
  idleIndex。
- **enable/ignore 空数组 = 无该名单放行**（站点 `officialLive2DActionAllowed` 的 `length>0` 才启用；
  stage1e 修正，光辉 `enable:[]` 曾被当空白名单导致只涨 idleIndex 不播动作）。
- 白名单**持续生效**直到下一条 ATA 覆盖（规则无 ATA 不清空）。
- **ATA.idle = 防重复**（r4 §4.3 站点 `live2DActiveDataRepeatsCurrentIdle` 源码直证）：目标
  idle **== 当前链 idleIndex 时跳过**（防重复播同一 idle），非触发门槛——「不匹配即拒」方向
  相反，会锁死 453/874 条 typed 规则；链推进后原被跳过的区自然解锁（ATA.idle=0 的区开局
  显示 G 属预期）。
- actionTrigger type 分发：1=拖动触发、2=触摸即发、6=链占位、7=拖动主控；1/6/7 只认 `kind='drag'`，
  2 只认非 drag；6/7 不直接播动作；`action` 数组随机取一；动作名 ∉ available → null。
- 持久化 `localStorage['l2d-touch:<模型名>']`：`{idleIndex, activeRuleId, cooldowns}`（跨刷新/换模型保留）。
- **链步进规则查找** `findChainRule(gname)`（main.ts body 链用，findRuleByParameter 的超集）：
  **action 含 gname 优先**（r2 C3：真链成员如 TouchIdle20 播 touch_idle1；数组序兜底会让
  TouchIdle1 抢答致 tap1 即 0→11 跳号）；兜底 `parameter===gname` ∥ `drawAbleName===驼峰化(gname)`
  （`touch_idle17→TouchIdle17`）。
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
- **slide**：像素增量 `dxPx=e.clientX-prevX`（右正）、`dyPx=prevY-e.clientY`（**上正**，
  引擎 `interaction.y-currentY` 同构）；轴选择 = **offset≠0 的轴才参与**（0 轴排除为本地
  保留项 D4′，见 §9）；`value=holdBase+chosen/offset`（**holdBase=hold 起点当前值锚定**，
  r3 定案：拖拽从当前值续算，非 startValue 重锚）→ clampChain **三步链：dragDirect 方向
  门控 → rangeAbs 取绝对值 → range 钳幅**（r4 §3.1c 站点 fixLive2DParameterTargetValue
  次序源码直证，`test_l2d_clamp_chain_runtime.py` 运行时对拍钉死）→ smooth 趋近。
  无 DRAG_VALUE_SCALE（像素即引擎单位）。offset 数据按像素标定（如 wuqi_3 TouchDrag2=-150=全程）。
- **circle 按住=转盘**：`deg=atan2(curX-cx, cy-curY)*180/π`；`angle=((deg+360-start)%360+360)%360`；
  `dialValue=rangeMax*angle/360`。cx/cy=区**屏幕**包围盒中心（modelRectToScreen），指针=clientX/Y；
  hold 中每帧重算+平滑趋近、**不回落**；顺时针=增；`offsetCircle.start` 当前数据均无→0。
- **circle 单击=翻转开关**：poke 目标=circleTarget；到位（|v-target|<0.05）后**停留不自动回落**；
  下次 poke 按当前值翻回 startValue（吾妻 TouchDrag8 面板开/关实证）。
- type1/4：拖拽结束触发一次其 action。释放 `revert===-1` 值保留；持久化 `l2d-param:<模型名>`。
- **resetAll**（r3 R-1/R-2/R-5）：全部状态回 startValue、清 dirty/saved/hold/poke、删
  localStorage 持久化键（防「复位→刷新」残留回填）；接入「复位模型」序列
  （resetTouchChain → paramDriver.resetAll → playIdleOnce）。

## 8. 仪表盘（l2d_touch_debug.ts）

- 全部已注册区绘制：可用区实色填充；O/G 画描边+原因标记；T（透明）降级为提示、**仍填充可交互**；
  `blockedEnable` 标注（G 且动作被白名单拒）。
- 实时读数：区参数值 `touch_dragN=V` 或 `action=xxx`（ParamDriver.getValue 只读）；左上角
  `idleIndex=N` 随链步进刷新。

## 9. 偏离站点项（有意为之，勿"修回"）

- D2 body 连点链 touch_idleN 递进（游戏语义；站点引擎无点击计数器，stage1b Q3 实证站点无递进）。
- D4′ stepSlide 0 轴排除（站点源码实为 `||1` 兜底；用户实测站点纯垂直拖无误触发，r4 疑点 1
  未决，观感优先保留排除式，待站点数值取证后统一）。
- r2 已收回 D1/D3：透明度剔除与 T 区不可交互恢复为站点同款（原 stage4 超越项实测为净伤害）。

## 10. 明确不做

type12（num 监听）、type7 listenerData（Limit_box）、relationParameter 超出 lookup103 部分、
tips/dragRate/ignoreDrag（全站 JS 0 命中死数据）、逐像素 alpha、ATA 门槛自动解锁、dynamicFlags
可见性启用。诊断中遇到按「未实现」标注。

## 11. 遗留问题与下一步

- **C4（BLOCKED·几何）**：光辉 TouchIdle17 门槛可解锁（interactive true）但绘画件屏幕投影
  y≈−4654 视口外，物理不可点。无代码解，除非改姿态/视口。
- 信浓链跳号（1→3→6）：model3.json 缺 touch_idle2/4/5/14 组，数据事实非缺陷。
- **D5**（slide 闸门边界）：offsetX=Y=0 且带 offsetCircle 的样本未普查（r4 疑点 4）。
- **D6/D7**（r4 §5.2 优先级 4）：touch_drag7 棘轮三函数（stableLive2DDragValue /
  snapLive2DTouchParameter / live2DDragStartedAtTarget）与 triggerConditionMet 常量表未实现，
  需下载其余 chunk 反查常量；取证入口与已直证源码见 research_live2d-hotzone-touch-r4.md。
- §5 resolve 触发时序为 D 级推断（行为锚点=站点实测播放）；若站点取证推翻须修正顺序。
- 待办：live2d.md 的 stage1 实测修正（§1/§5.1 矛盾点、数据接口"已失效"结论已被 stage1b 推翻、
  光辉 shipSkinId 疑点已核销）合并回 spec-l2dsu-engine.md / live2d.md。
- 代码债：l2d.ts 1030 行远超「单模块 ≤200」上限，待功能收口后按注册/命中/播放/参数职责拆分。

## 12. 验收方式（改引擎必读）

- 静态 pytest 断言有局限（曾连续两轮全绿但实际不可用）→ **实测协议强制**（clampChain 已有
  运行时数值对拍补上一个洞，其余行为仍靠实测）：
  - stage5 §5 表 T1~T13（像素拖拽算式/转盘/翻转/默认区/idle 单次化）
  - stage6 §5 表 C1~C9（链推进/门槛解锁/渲染序择序）+ stage1e 补充（ATA.enable=[]）
  - 两表基准与逐行实测记录在 research_live2d_stage1.md §11/§12；改引擎必须重跑相关行并记录。
- 自动化要点：区位置随姿态漂移，**动作前即时重扫命中点**，不可跨步骤缓存坐标；内嵌浏览器
  `visibility=hidden` 时 rAF 停摆，先 `visibility.set(true)`。
- 回归：无 touch.json 模型（mao_pro 等）行为不变；三份既有 pytest 全绿 + `npm run build` 通过。
