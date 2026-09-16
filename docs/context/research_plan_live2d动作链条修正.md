# 研究大纲 · frontend-minimal Live2D 动作链条修正（/plan-research 产物）

> 2026-09-17。下一步：切换弱模型执行 /research-doc，按本大纲产出
> `research_live2d动作链条修正.md`。本文件为大纲，不含结论。

## 1. 研究问题定义

frontend-minimal 触摸规则引擎（TouchChain/ParamDriver/l2d.ts 规则注册与命中）在
guanghui_9 / shi_3 / xinnong_6 / feiteliedadi_3 四模型上与 l2d.su 行为存在偏差
（热区显隐、链状态死锁、参数串扰、自动复位/自动播放），需逐症状定位根因并分类
（实现缺陷 / 数据事实 / 有意偏离），产出修正方向候选。

## 2. 需要回答的子问题与查阅位置

### Q1 热区显隐机制：注册期静态剔除 vs 站点每帧刷新

现象锚点：guanghui_9「drag3 点击后 drag4/drag5 只隐约出现滑块、无热区不可互动」——
**已确认（2026-09-17）：「滑块」指模型画面本身**，即 drag4/drag5 对应绘画件在模型画面中
半显（参数驱动显示不完整），取证方向指向 ParamDriver 取值/范围而非调试 UI；
shi_3「初始缺 TouchIdle27」「TouchIdle1 后旧热区不消失、新热区组不出现」。
需回答：站点触发规则后「旧区隐藏/新区揭示」由哪段状态驱动（`updateLive2DOfficialRuleStates`
每帧刷新 + ATA 白名单 vs 我们 `isRuleInteractive` 单次判定）？guanghui_9 drag3 的
ATA/enable 结构在数据里到底怎么写？

查阅位置：
- `frontend-minimal/src/renderer/l2d.ts`：`isRuleInteractive`(L293)、`hitZoneAt`(L316)、
  `emitInteraction`(L387)、`touchZoneStates`(L446)、`loadTouchRules`(L496)
- `docs/context/spec-l2dsu-engine.md` §3（ATA 两形态）、§5（站点每帧刷新与命中算法）
- `docs/context/spec-l2d-touch-engine.md` §3（注册与剔除 O/G/T）、§5（ATA.idle 防重复）
- `live2d-models/{guanghui_9,shi_3}/touch.json`：drag3/drag4/drag5、TouchIdle1/27 的
  rules 原文（actionTrigger / actionTriggerActive / drawAbleName）
- 站点取证（必要时）：`live2DRulePointerEnabled` 消费逻辑（research_live2d-hotzone-touch-r4.md
  已有取证入口）

### Q2 链状态机死锁：idleIndex 推进与解锁路径

现象锚点：guanghui_9「touchhead 动作中点 drag3 → 动作结束后全屏无热区，死锁」。
需回答：touchhead 的 ATA 把 idleIndex 推到什么状态后，哪些区被 G 门控？我们是否存在
「idleIndex 进入无解锁路径的状态」（对照站点 `Ue(idle,idx,random)` / 形态A 按状态查表）？
播放门控 `isPlayingTouchAction` 期间 touchhead→drag3 的时序是否吞掉了某次 ATA 应用？

查阅位置：
- `frontend-minimal/src/renderer/l2d_touch.ts`（184 行全读：resolve/applyActive/findChainRule/reset）
- `frontend-minimal/src/renderer/l2d.ts`：`findChainRule`(L843)、`waitMotionFinish`(L761)、
  `playAction`(L742)
- `frontend-minimal/src/main.ts` L113~260：`onInteraction` 处理器全读
- `docs/context/spec-l2dsu-engine.md` §6（链状态机/打断/序列号守卫）
- localStorage `l2d-touch:guanghui_9` 实测值（死锁现场转储 idleIndex/activeRuleId/cooldowns）

### Q3 参数串扰与 idle 组选择：谁写了 touch_drag10 / 谁播了 idle10

现象锚点：shi_3「touchhead 后 touch_drag10 从 0.0 变 4.0」；xinnong_6「未操作自动进 idle10」
——**已确认（2026-09-17）：清空 localStorage/全新加载后仍复现**，排除持久化残留，
优先查 Idle 自动播放语义（站点确有仅自动播放的互动动画）与初始 idleIndex/组名选择逻辑。
需回答：touchhead 对应动作的 Idle 参数关键帧是否合法写 drag 组参数（站点也写？），
还是我们把 drag 组名当动作组播放所致？xinnong_6 的 idleIndex 持久化残留 vs
`idleGroupName()`(L787) 组名选择 vs Idle 动画含自动互动语义，三者谁是主因
（用户提示：站点部分互动动画确会在闲暇自动播放，仅限特定动作）？

查阅位置：
- `frontend-minimal/src/renderer/l2d_params.ts`（346 行全读：注册分支/写参数路径/resetAll）
- `frontend-minimal/src/renderer/l2d.ts`：`idleGroupName`(L787)、`playIdleOnce`(L793)、
  `toParamRule`(L606)、`attachParamDriver`(L903)
- `live2d-models/{shi_3,xinnong_6}/touch.json`：touchhead 规则、touch_drag10 规则、
  含 idle/Idle 字样的规则与 saveParameter/revert 字段
- localStorage `l2d-touch:xinnong_6` / `l2d-param:*` 实测
- 站点取证（必要时）：Idle 自动播放触发条件（xinnong_6 对照 l2d.su 闲暇行为）

### Q4 拖动链步进与自动复位：action_list 推进 / triggeredRuleIds 语义

现象锚点：feiteliedadi_3「drag3 点击后 drag4 短暂弹出即复位，drag3 随即不可互动」；
l2d.su 正确行为=「drag3 点击后屏幕只剩 drag2 和 drag4，不自动复位」；drag9 类似。
需回答：type6 链占位（`action_list.length<=1→triggeredRuleIds.add`）在我们实现里的对应物
是否把「本轮完成」误当成「立即复位/锁死」？「屏幕只剩 drag2/drag4」对应站点哪个
热区可见性状态？drag3 失去互动是冷却、白名单还是链完成锁？

查阅位置：
- `docs/context/spec-l2dsu-engine.md` §2（type1/6/7 分发）、§6（链步进/冷却/复位）
- `frontend-minimal/src/renderer/l2d.ts`：`emitInteraction`(L387)、`accumulateDrag`(L247)、
  `attachGestures`(L151)
- `live2d-models/feiteliedadi_3/touch.json`（注意目录名拼写 feiteliedadi，非 feteliedadi）：
  drag2/3/4/6/9 全部 rules + action_list 结构
- 站点取证（必要时）：drag3 点击后的 actionListIndices/idleIndex/activeRuleId 状态转储

### Q5 热区几何与互动锁：判定框计算 & 播放中是否锁全部热区

现象锚点：「隐约出现滑块」已确认为模型画面本身（见 Q1），归 ParamDriver 半显问题；
guanghui_9 现象 3 的「三种模式按 drag4 拖拽数值分档（Touchidle17/4/1+22）」=
relationParameter/type103 查表——**已确认（2026-09-17）属动作链条必还原部分**（用户裁定：
未还原即链条实现仍存在问题，见 §4 边界变更），需查明我们 type103/lookup103 实现到什么
程度、缺哪一档、数据侧 relation_value 结构如何表达三档分界。播放动作期间站点是否锁全部
热区（我们 `isPlayingTouchAction` 只放行当前区自身链，语义差异多大）？

查阅位置：
- `frontend-minimal/src/renderer/l2d.ts`：`hitZoneAt`(L316)、`drawableBounds`(L646)、
  `dialValueFor`(L214)
- `frontend-minimal/src/renderer/l2d_params.ts`：type103/lookup103 实现现状
- `docs/context/spec-l2d-touch-engine.md` §4（择一优先级）、§7（拖拽参数）、§9（偏离项）、
  §10（明确不做：listenerData type7/relationParameter 超 lookup103 部分）
- `frontend-minimal/src/renderer/l2d_touch_debug.ts` + `_helpers.ts`（叠加层作为取证工具）
- `live2d-models/guanghui_9/touch.json`：drag4 的 relationParameter 原文

## 3. 输出文档结构（research_live2d动作链条修正.md）

1. 结论速览（每个现象 → 根因分类：实现缺陷 / 数据事实 / 有意偏离 / 未决）
2. 四模型症状清单与复现条件（来自用户报告，逐条编号对齐）
3. 站点行为基准（l2d.su 对照取证，含状态转储；无法取证处标注）
4. 现实现四条路径梳理（注册/门控、命中择一、链状态机、参数驱动）
5. 逐症状归因分析（按模型分节，证据引用文件:行号）
6. 修正方向候选（仅建议与优先级，不写实现代码；新硬性契约列「契约候选」）
7. 未决疑点与需人工裁决项（含需站点人工协助清单）

## 4. 已知约束和边界

- 只读研究：不改任何源码、不改测试；产出仅为研究文档。
- 红线：不动 `l2d_touch.ts` 导出签名；不改 AGENTS.md、backend、官方 `frontend/`。
- 四模型全部有 touch.json（feiteliedadi_3 是目录拼写差异，数据在）；无 touch.json 模型
  （bulaimodun_5/mao_pro/oppai_bunny/yichui_2）走启发式兜底，不在本轮范围。
- 有意偏离项 D2（body 连点递进）/ D4′（0 轴排除）不得当 bug「修回」（spec §9）。
- ⚠️ **范围变更（2026-09-17 用户裁定）**：guanghui_9 drag4 三档分模式（Touchidle17/4/
  1+22）属动作链条必还原部分——spec-l2d-touch-engine.md §10 原「明确不做」中
  relationParameter 相关边界对其不再适用；研究阶段照常取证，但**修正实施前须按流程
  更新该规格并经人工批准**，其余 §10 不做项（type12/listenerData type7 等）维持原状。
- 已知未决不复研：C4（光辉 TouchIdle17 视口外 BLOCKED）、D5（slide 闸门边界）、
  D6/D7（棘轮三函数未取证，入口见 research_live2d-hotzone-touch-r4.md）——只引用不重查。
- 站点取证允许（浏览器对照），必要时停下请求人工协助（用户已授权）。
- 静态断言全绿 ≠ 可用：结论必须附实测/数据证据（spec §12 教训）。
- l2d.ts 1030 行技术债已知，本轮不提拆分建议。

## 5. 疑点确认记录（2026-09-17 用户已答复，全部闭环）

1. 「只隐约出现 touch_drag4/5 对应的滑块」= **模型画面本身**（绘画件半显，非调试 UI）
   → 已并入 Q1/Q5。
2. xinnong_6「未操作自动进 idle10」= **清空 localStorage/全新加载后仍复现** → 排除持久化
   残留，已并入 Q3。
3. guanghui_9 三档分模式 = **动作链条必还原部分** → 已并入 Q5 + §4 范围变更（修正前需
   更新 spec §10 并经人工批准）。
