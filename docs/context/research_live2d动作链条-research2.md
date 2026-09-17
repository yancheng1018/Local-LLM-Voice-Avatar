# 研究报告 · live2d动作链条-research2（type12 门控 / 结束后恢复 / idle 生命周期 / 无绘画件热区 / 验收仪表）

> 2026-09-18，按 `research_plan_live2d动作链条-research2.md` 大纲执行的**只读研究**（未改源码）。
> 基线：阶段 0/A/B + v2 修复轮已完成并验收（2026-09-18，archive.md）。站点侧证据三级来源：
> ①站点引擎快照 `docs/assets/su_modelRuntime-BDk3g7Pb.js`（201,926 字节，rg 可复核）；
> ②逆向记录 `spec-l2dsu-engine-v2.md`；③站点数据缓存 `docs/assets/_ships_cache/`。
> 置信度标注：**A**=源码/数据直证；**B**=多源推断；**C**=待运行时验证。

## 1. 结论速览（问题定义：站点在「播放期门控/结束后恢复/idle 生命周期/无绘画件热区」四场景的真实语义，与本地的差距根因）

1. **type12 值源已定案（A）**：站点 type12 读**参数目标表**（`live2DOfficialParameterTargets`），
   非 core 实际值；半开区间 `lo<v<=hi`，判定**优先于** ATA enable/ignore，且**同样约束默认区**
   （TouchHead/Body/Special）。guanghui_9 规则 23703161 = 「drag3 手势进行期禁头/身/特触」，
   配合 circle 翻转（到 10 回落 0）窗口自动关闭——是**有意设计**非缺陷。本地零实现。
2. **touchhead 卡死场景站点不发生（A→B）**：站点在 drag3∈(0.01,10] 时 type12 先拦 touch_head，
   本地无 type12 且伪规则直连 playAction（main.ts:162）连 ATA 名单都不查 → 播放了一个站点
   永远不会播的动作，进入站点不存在的状态。
3. **站点 idle 是循环的（A，推翻 stage5 记录）**：全部抽查模型 idle*.motion3.json `Meta.Loop=true`；
   站点 bundle rg `Loop|setIsLoop|idleMotionGroup` **零命中**（不禁循环、不禁库自动 idle）。
   stage5「站点播一次即冻结终帧」与本轮证据冲突。本地 idle 单发是**不可自愈**的根源：
   动作曲线残留参数（drag3=2.61 候选解释）无人每圈重写。
4. **shengluyisi_4 是数据错配非引擎之谜（A）**：本地 _4 的 touch.json ≡ 本地 _5 ≡ 站点 _5
   （54 规则逐字节相等），而**站点根本没给 _4 挂规则**（rules=0）；_4 的 moc3 零 TouchDrag
   绘画件。站点不需要「为无绘画件规则定热区」——它不给 _4 规则。_5 本地完全可用。
5. **仪表缺口定位（A）**：叠加层 `paramValue` 只显 ParamDriver **内部值**（l2d.ts:464），
   core 实际值无处可看——本阶段两次验收栽点正是这两层混淆。补 core 列的方案见 §6-Q5。

## 2. 症状与复现基线（含本轮数据核验记录）

| # | 症状（current-work 遗留原文） | 本轮核验 |
|---|---|---|
| S-a | guanghui_9 touchhead：播放期应门控（嫌疑 type12）；结束后无热区+模型卡死+drag3 滞留 2.61 | type12 规则/名单/值源全部取证（§3.1）；2.61 归因列候选（§5-Q2） |
| S-b | aerbien_3 清缓存静置数秒动态停止（视线跟随正常） | idle Loop=true 数据直证 + 站点无禁用代码（§3.3） |
| S-c | shengluyisi_4/5 moc3 零 TouchDrag 绘画件、TouchDrag14 等不可达 | **仅 _4 成立**；_5 有 30 绘画件 34 规则 0 缺失（§5-Q4） |
| S-d | 验收仪表缺 core 写入值列 | 现状锚定 l2d.ts:464 只读内部值（§5-Q5） |

## 3. 站点行为基准取证

### 3.1 type12 = 「参数区间全局动作裁决」，读目标表（A）

- 源码（v2 spec §3.2，`live2DExtendActionDecision`）：遍历全部 type12 规则，
  `v = live2DOfficialParameterTargetValue(at.parameter)`，`lo<v<=hi` 时该规则 ATA 的
  `ignore` 命中即拒 / `enable` 命中即放行；在 `officialLive2DActionAllowed` 中**最先**执行。
- **值源 = 参数目标表**（v2 spec §4.1：所有写入经 `setOfficialLive2DParameterTarget` 进表，
  每帧 Tween 回写）。这同时回答前研究 §8-1 双路径疑点的一半：**type12 与面板读同一条目标表**。
- **默认区同受约束**（v2 spec §2.5）：非规则区 `!officialLive2DActionAllowed(area.action)` 即不可点。
- guanghui_9 数据（A，touch.json 直读）：规则 23703161 =
  `{type:12, num:[0.01,10], parameter:"touch_drag3"}` + ATA.ignore **15 项**
  （main_1..5/mission/mission_complete/complete/login/home/mail/touch_body/touch_head/
  touch_special/wedding）+ `drawAbleName` 缺失（**纯监听器，无热区**）+ ignoreAction/ignoreReact:1。
- 配套数据（A）：TouchDrag3 = 23703103 `{circle:true, target:10, type:2}` + range[0,10] +
  `revertIdleIndex:"1"` + `revertActionIndex:1`。circle 翻转（值到 10±0.05 回落 startValue=0，
  站点 §3.1 ⑥⑧ / stage2 §2 type2）使 type12 窗口在手势完成后**自动关闭**。
  ⚠ 细节：站点 `revertActionIndex` 复位仅在 `action_list` 非空的链步进分支内
  （v2 §3.1 ⑩⑪）——TouchDrag3 无 action_list，其 `revertActionIndex:1` **在站点也是死字段**；
  唯一复位路径是 revertIdleIndex（idle 变到 1 时）。
- 旁证（A）：TouchIdle1..N 的 ATA.ignore 均含 `touch_head/touch_body`（23703119..23703146）
  ——点过任一 TouchIdle 后头/身在站点同样被名单拦。

### 3.2 站点「动作结束后」恢复链（A，v2 spec §3.1/§3.2 汇总）

动作结束 → `playLive2DIdleMotion(idleAfter)`（ATA 应用返回值）→ 循环 idle（见 §3.3）持续
重写全量动画参数；idleIndex 变化 → `resetLive2DRulesForIdle`（revertIdleIndex 规则参数回
startValue）；ATA 应用即 `updateLive2DHitAreaFrame()` 重算热区；提示显隐走 tips
（idleBlackList/animWhiteList）。**没有**「结束后专门清理」步骤——恢复靠 idle 循环 + 复位钩子。

### 3.3 站点 idle = 库自动路径 + 动作数据循环标志（A）

- 数据（A）：guanghui_9/aerbien_3/shengluyisi_4/shengluyisi_5 的 `motions/idle*.motion3.json`
  `Meta.Loop=true`（直读）；guanghui_9 model3.json 有大写 `Idle` 组（1 条 → idle.motion3.json）。
- 站点 bundle（A，代码缺席证据）：`rg -a "Loop|setIsLoop|idleMotionGroup"
  docs/assets/su_modelRuntime-BDk3g7Pb.js` → **0 命中**。站点不禁循环、不传 idleMotionGroup
  → 库默认 `groups.idle="Idle"` 自动播放保持活跃（v2 spec §9.1：动作结束
  `startRandomMotion("Idle", IDLE)`），循环由动作数据 Loop 标志驱动。
- 对照 stage5 记录（l2d.ts:814-818 注释引「站点播一次即冻结终帧」）：**与本轮两项 A 级证据
  冲突**，判定为误观察（B；原始观察上下文待用户确认，见 §8-2）。

### 3.4 无绘画件规则的热区：站点根本不挂（A）

站点皮肤数据（`docs/assets/_ships_cache/site_10213.json`，2026-09-17 缓存）：
`shengluyisi_4` 的 skin 条目 `live2dTouch` 缺失（rules=0，dynamicType=None）→ 站点 _4 只有
默认 TouchHead/Body/Special 三区；`shengluyisi_5` rules=54。站点「为无绘画件规则定热区」
的机制**不存在也不需要**——规则与模型版本天然配套，错配只发生在本地数据侧。

## 4. 本地实现现状（行号重新锚定，阶段 0/A/B 后）

| 部件 | 位置 | 现状与差异 |
|---|---|---|
| 动作闸 | `l2d_touch.ts:112-116` `isActionAllowed` | 仅 ignore/enable 两闸；**无 type12**（rg `type===12` 全仓 0 命中） |
| 交互门槛 | `l2d.ts:300-315` `isRuleInteractive` | OE_TYPES:304 + ATA.idle 防重复:308-309 + 白名单:314；无 type12/条件门槛 type9/11/15 |
| 伪规则直连 | `main.ts:162-164` | TouchHead/Special **绕过 TouchChain** 直连 playAction——不查任何名单（站点 §3.1 默认区要过闸） |
| 链状态机 | `l2d_touch.ts:77-109` resolve | 形态A 目标 idle 查表:170（阶段B 修正）；链步循环:100；冷却**成功后记**:103-105（站点先记，阶段C 已列） |
| idle 单发 | `l2d.ts:690`（`idleMotionGroup:'__no_auto_idle__'`）、`:804-812` playIdleOnce、`:819-829` disableIdleLoop `setIsLoop(false)` | 三重禁循环；动机=stage5 区集漂移+「站点冻结终帧」记录（§3.3 已推翻后者） |
| 复位队列 | `l2d_params.ts:220-232` syncChainState（`l2d.ts:934` 每帧下传） | 只对 **idleIndex 变化**敏感；伪规则路径不改变 idleIndex → 队列不触发 |
| 仪表读数 | `l2d.ts:464` paramValue=`paramDriver.getValue()`（内部值，`l2d_params.ts:234-238`） | 无 core 值列；`window.__vtuber` 暴露 renderer（`main.ts:420-428`）可控制台深查 |
| 叠加层 | `l2d_touch_debug.ts`（stage7 拆分达标）+ `l2d_touch_debug_helpers.ts:79-106` | 标签 readout=内部值/动作名；每帧现读可见性:127-130 |

数据事实（本轮 python 直读）：guanghui_9 `motions/idle.motion3.json` 与 `touch_head.motion3.json`
的 Curves **均驱动 touch_drag3**（另 drag1/2/4/5/15、touchdrag10/11 共 8 个 drag 参数）——
动作播放/循环会写 drag3，参数恢复与动作循环强耦合。

## 5. 逐问题归因

### Q1 type12 门控（S-a 前半）
本地两处缺口叠加：①`isActionAllowed`/`isRuleInteractive` 无 type12；②伪规则直连连基本
名单闸都绕过。→ drag3∈(0.01,10] 时本地头/身/特照样触发，站点全部拒绝。「guanghui 点名
5 区」候选解释：type12 名单中本地可感知的恰是 touch_body/head/special 三默认区 + TouchIdle
自身名单对 touch_head/body 的重复点名（main_* 为 UI 动作本地无消费）；「5 区」原始观察
待复核（§8-1）。**落地注意**：type12 读目标表 → 依赖参数权威层值源，与阶段C-8/§8-1 同前置。

### Q2 结束后恢复（S-a 后半）
恢复链四环节本地三缺一残：type12 缺（前提不发生）、idle 循环缺（参数残留无人重写）、
复位队列残（伪规则不触发 idle 变化）。drag3=2.61 候选解释（B，待运行时定案）：
(a) touch_head/idle 曲线终值残留——循环缺失使其永驻；(b) poke 中断——poke 爬坡中点头部
触发动作，翻转到 0 需值先到 10±0.05，单发 idle 后续写竞争致停在中途；(c) 内部值 vs core
值分层混淆——正是仪表缺口。「无热区」与 drag3 残留强相关：drag4/5 需 drag3≈10 才进画布
（前研究 §5.0.3），中间值同样使位置偏离。「模型卡死」= idle 单发播完无后续（Q3 同根）。

### Q3 idle 生命周期（S-b）
本地三重禁循环 vs 站点数据 Loop=true + 无禁用代码（A）。aerbien_3 静置停止 = playIdleOnce
播完 setIsLoop(false) 后无任何后续排程（`l2d.ts:803` 注释自认「无 setInterval 等循环排程」）。
方案对比见 §6-Q3；循环化会连带改变 Q2 的自愈能力（循环 idle 每圈重写 drag 系参数）。

### Q4 shengluyisi（S-c）
字节级定案（A）：本地 _4/touch.json ≡ 本地 _5/touch.json ≡ 站点 _5 rules（json 相等）；
站点 _4 无规则；_4 moc3 零 TouchDrag 绘画件（仅 TouchBody/Head/Special）、_5 有 30 个且
34 规则 0 缺失。→ _4 症状 =「_5 的规则 + _4 的旧 moc3」数据错配（shi_3 同型）；
_5 无任何问题。「站点如何定热区」之问消解（§3.4）。

### Q5 仪表（S-d）
缺口 = 只有 ParamDriver 内部值（`l2d.ts:464`），core 值无列。本阶段两次验收栽点
（guandao_3 恒表[0] 靠清缓存才定位、蛇形字段假绿）均属「层间混淆」类。

## 6. 修正方向候选（仅方向；新契约只列候选，实施另行立项）

### Q1/Q2（type12 + 恢复链，阶段C-8 前置取证已齐）
1. 实现 type12 裁决（读参数目标层值，接入 `isActionAllowed` 链最前端）+ 伪规则区过同一闸
   （main.ts:162 改走 resolve 或前置闸检查）。
2. 伪规则播放也推进链状态（站点默认区动作同样参与名单/冷却体系）。
3. drag3 死字段处置：`revertActionIndex` 对无 action_list 规则在站点即死——本地实现复位时
   按站点口径（仅链步进分支）或明确扩展（需裁决）。
- *契约候选 R2-a：type12 判定值源 = 参数目标层（权威层值），不得读 core 实时值。*
- *契约候选 R2-b：默认热区（伪规则）动作必须过与规则区相同的动作闸（type12 + ATA 名单）。*

### Q3 idle 循环化（需人工裁决）
- 方案 A：移除 `disableIdleLoop`，尊重 motion3.json `Meta.Loop=true`（站点同款，改动最小）。
- 方案 B：保持 setIsLoop(false)，motionFinish 后重排程重播（等效循环，保留单次化挂点）。
- 副作用评估：命中判定每点击现读（`l2d.ts:323-341`）+ 叠加层每帧重画（`l2d_touch_debug.ts:127`），
  stage5 的「区集漂移」在现架构下影响面已收缩；循环化使 idle 每圈重写 drag 系参数 = Q2 自愈
  机制恢复。风险：152 测试中 stage5 相关断言需随裁决更新（规格变更流程）。
- *契约候选 R2-c：idle 循环语义以站点+数据为准（Loop=true 应被尊重）；禁循环需站点同款
  A 级证据。——待裁决后入档。*

### Q4 数据处置（需人工裁决）
- 本地 _4 touch.json 为错数据（站点 _4 无规则），候选：清空规则仅留默认区 / 按既有
  「站点无规则者保持现状并标注」原则标注（但现状是错配非旧版，建议前者）；修复脚本沿用
  A1 契约口径（prefab 精确匹配 + rules 非空）。全库可按同法复核（对照 su_ships-CN.json）。
- *契约候选 R2-d：touch.json 必须与「站点同 prefab 且带规则的皮肤」同源；站点无规则者本地
  不得保留他版规则数据。——待裁决后并入 A1。*

### Q5 仪表补强方案（只出设计）
1. `TouchZoneState` 增 `coreValue?: number`：`touchZoneStates()` 已逐帧持有 core（`l2d.ts:455`），
   对 hasParam 区增读 `core.getParameterValueById(param)`（paramId→index 用 Map 载入时建缓存；
   Cubism4 coreModel 支持，前研究 §5.0.3 浏览器探针已验证同 API）。
2. 标签 readout（`l2d_touch_debug_helpers.ts:99-104`）：`group=内→核`，|内-核|≤ε 时只显一个，
   >ε 双显——层间分歧一眼可见。
3. 固定读数行（`l2d_touch_debug.ts:110` idleText）增聚合标志：任一注册参数内≠核持续 N 帧 →
   `⚠写入失效`。
4. 复用：Q2 的 2.61 溯源、type12 验收（目标表/core/面板三值对拍）、既有「参数写入生效性」
   断言的可视化补充。

## 7. 验收协议（证伪方法）

1. **type12**：guanghui_9 清缓存 → 点 drag3（值爬坡中）→ 点头/身/特：实现后应无反应；
   值到 10 翻转回 0 后应恢复可点。对照站点同步骤（T 系流程，UA+Referer 约束同前）。
2. **恢复链**：复现 touchhead 场景 + 新 coreValue 列 → drag3=2.61 判层（内部值→poke/翻转
   逻辑故事；仅 core→动作曲线残留故事）；循环化落地后复测应自愈（数秒内参数回 0、热区恢复）。
3. **idle**：aerbien_3 清缓存静置 5 分钟：动态应持续（对照 T8：修复前 14 次自动动作属库路径，
   修复后应为本地循环路径，idleIndex 不得自发变化）；guanghui_9 同测。
4. **shengluyisi**：_4 叠加层无 TouchDrag 区（数据清空后仅默认区）；_5 34 条全注册、可交互面正常。

## 8. 未决疑点与需人工协助清单

1. **「guanghui 点名 5 区」原始观察**（hotzone-arch ②）：具体 5 区名单与观察方式待用户补充；
   本轮候选解释见 §5-Q1。
2. **stage5「站点播一次即冻结终帧」观察上下文**：与本轮 A 级证据冲突，若有当时记录/截图请提供。
3. **idle 循环化方案 A/B 裁决**（§6-Q3，连带 152 测试中 stage5 断言的规格变更）。
4. **shengluyisi_4 数据处置裁决**（§6-Q4：清空 vs 标注保留；是否全库复核）。
5. 站点 `ruleHasLive2DSlide`/`playLive2DIdleMotion` 函数体仍未取证（沿袭 v2 spec §10，本轮无增量）。
6. drag3=2.61 精确归因（待 Q5 仪表落地后一次复现定案，§7-2）。
