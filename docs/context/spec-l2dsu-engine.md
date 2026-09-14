# 研究报告 · 复现 l2d.su 互动热区 + 动作链条（精确规则引擎）（stage2）

> 2026-09-13，按 stage2 研究规格（已并入 `spec-l2d-touch-engine.md`）执行的**只读研究**（未访问任何网页，未改源码）。
> 测试脚本为 `stage2_tests.ps1`（§6 原样，加 UTF-8 BOM），T1~T20：19 PASS / 1 FAIL（T12，误报，见下）。
> 符号上下文提取全文原存 `stage2_ctx.txt`（§5.1-B 原样命令产物）——**该产物已丢失，见 `docs/assets/README.md`**。

**T12 失败判定依据**：`Select-String -SimpleMatch` 默认**大小写不敏感**，`"Idle"` 匹配到
FileReferences.Motions 组名小写 `"idle"`。复核：python 原始字节 `raw.count(b'Idle')=0`；
`Select-String -CaseSensitive '"Idle"'` → False。**Groups 段确无大写 Idle/Talk，规格书断言本意成立**，测试未改。

## 1. touch.json 完整 schema 语义（6 顶层键 + 26 rule 字段）

解析命令：§5.1-A python（原样）。输出：`TOP ['ids','rules','tips','dragRate','parameterRange','ignoreDrag']`，
`RULE_KEY_COUNT 26`，`TRIG_TYPES {2:24, 6:2, 1:1, 7:1, None:3}`，`MODE {1:28, 2:3}`。

顶层键：

| 键 | 值（实测） | 语义 | 置信度 | 证据 |
|----|-----------|------|--------|------|
| `ids` | 31 个 part id（20703701…） | 热区 part id 注册表 | 证实 | stage1 |
| `rules` | 31 条 | 热区规则本体 | 证实 | stage1 |
| `tips` | `{id:207037, tipsOffset:[{drawable:[28 个 Touch*], offset:[0,0]}], tipsScale:[…]}` | 首次触摸提示气泡的锚点绘画件与偏移/缩放 | 推断（仅数据；`tipsOffset`/`tipsScale` 在四 JS 均 0 命中 → 属 app 层而非引擎层） | grep `tipsOffset` 四文件全 0 |
| `dragRate` | `[0.8,0.8,0.8]` | 拖动灵敏度倍率（疑似分轴/分段） | 推断 | 四 JS 全 0 命中，**引擎不直接读** |
| `parameterRange` | `{"ParamAngleX":[-20,20]}` | 模型级参数硬范围（覆盖/补充 rule.range） | 证实被消费 | modelRuntime 命中 ×1 |
| `ignoreDrag` | `0` | 模型级「禁用拖动手势」开关 | 推断 | 四 JS 0 命中（可能由 `saveParameter` 同型的解码键读取） |

26 个 rule 字段（分组；「证据列」= modelRuntime 中的明文命中次数 + 关键上下文）：

| 字段 | 语义 | 置信度 | 证据 |
|------|------|--------|------|
| `id` | 规则 id（=热区 part id），状态 Map 的键 | 证实 | `live2dOfficialActionListIndices.get(rule['id'])` 等遍布 |
| `shipSkinId` | 皮肤归属（多皮肤模型按皮肤过滤规则） | 证实（消费方存在，经解码器读） | `Ve()` 里 `..._0xf0dbae[_0x26917f(0x3d2)]`（stage1）；明文 0 次 |
| `drawAbleName` | 命中判定绘画件名 | 证实 | `Ve()` 读 `rule?.['drawAbleName']`；**3 条 rule 无此字段**（Param3 条，见 §5） |
| `parameter` | 该热区驱动的模型参数名（多数=动作组名，guanghui_9 特例：`Param3`） | 证实 | `rule['parameter']` 遍布；`live2DParameterExists()` 校验存在性 |
| `mode` | 1=拖动值驱动，2=指针位置反应驱动 | 证实 | `reactPosX` 消费代码显式过滤 `mode===0x2` |
| `startValue` | 参数初值/复位值 | 证实 | `…??_0x530c7a['rule']['startValue']??0x0` |
| `range` | 参数值域 `[min,max]` | 证实 | `Math.min(range[1],Math.max(range[0],value))` |
| `rangeAbs` | 1=取绝对值（对称参数） | 证实 | `_0x5c12c1['rangeAbs']===0x1&&(value=Math.abs(value))` |
| `relationParameter` | `{list:[{name,mode,smooth,range,range_abs,relation_value[],type,start,drag_direct}]}`：联动参数 | 证实 | `updateLive2DRelationParameters()` 全函数；type 103=按 `relation_value[i]` 查表，type 101(0x65)=按交互区域 |
| `reactPosX`/`reactPosY` | 指针位置→参数的增益系数 | 证实 | `sum += pos.x*Number(reactPosX\|\|0)+pos.y*Number(reactPosY\|\|0)`（同 parameter 的 mode2 规则求和，`id` 小者跳过） |
| `dragDirect` | 方向限制：0=双向，1=仅正值（负值钳 0），2=仅负值 | 证实 | `(v<0&&direct===1\|\|v>0&&direct===2)&&(v=0)` |
| `offsetX`/`offsetY` | 命中区域偏移（微调判定框） | 推断 | 明文 ×2，上下文未直接展示语义 |
| `smooth` / `revertSmooth` | 参数趋近目标/回弹的平滑时间 | 证实（smooth）/ 推断（revertSmooth 明文×1） | `setOfficialLive2DParameterTarget(rule, name, value)` 读 `smooth` |
| `revert` | 归位行为；`-1`=不自动归位（配合 saveParameter 持久化） | 证实 | `rule[0x335]===-0x1&&rule['saveParameter']!==-0x1&&rule['parameter']` → 存 localStorage |
| `revertActionIndex` | 1=动作链索引变化时重置该规则参数 | 证实 | `rule['revertActionIndex']===0x1&&idx!==old&&this['resetLive2DTouchRuleParameters'](rule)` |
| `revertIdleIndex` | 1（或数组）=空闲链回到该状态时复位规则 | 证实 | `revertIdleIndex===0x1\|\|\==='1'\|\|Array.includes(idx)` → 复位 |
| `limitTime` | 触发冷却秒数（另有一处钳到 ≤0.2s 用作动作冷却） | 证实 | `Cooldowns.set(id, now+max(0,limitTime)*1000)`；`min(max(0,limitTime),0.2)*1000` |
| `saveParameter` | ≠-1 时把参数值持久化到 localStorage（按 rule id） | 证实 | `state[0x186][String(rule.id)]=value` + `localStorage.setItem` |
| `ignoreAction` / `ignoreReact` | 跳过动作触发 / 跳过反应参数 | 推断 | 明文 0 次（经解码器读；字段名与行为对仗） |
| `actionTrigger` | 触发器（见 §2） | 证实 | 大量消费 |
| `actionTriggerActive` | 触发后的链状态数据（见 §3） | 证实 | `applyLive2DActiveData(data, rule.id)` |
| `listenerData` | 动作→参数监听器（见 §4） | 证实 | 消费循环原文在 §4 |
| `shopAction` | 商店动作标记 | 推断 | 明文 0 次；Param3 三条 rule `shopAction:1`（见 §5 末） |

## 2. actionTrigger 类型语义

实测分布 `{2:24, 6:2, 1:1, 7:1, null:3}`（type null 的 3 条即 Param3 位置反应规则，无触发器）。
引擎按**常量集合**分发（混淆名 → 由行为反推）：

| type | 语义 | 置信度 | 证据 |
|------|------|--------|------|
| 2 | **触摸即触发**（点下时播 `action`/`action_list[idx]`）；`action` 可为 string 或数组（随机/逐个）；`{circle:true,target:1}` 变体=「画圈」参数型：参数逼近 target 且差 <0.05 时回落 startValue（循环手势） | 证实 | 按下分发处 `L.has(type)`；circle 逻辑：`_0x36fd1c['circle']&&Math.abs(v-target)<0.05&&(v=rule.startValue??0)` |
| 1 | **拖动触发**（拖动中触发 `action`，带 `num`/`time`）；引擎同型还接受 type 4（本模型未用） | 证实 | `maybeTriggerLive2DDragAction`: `_0x57b41f!==0x1&&_0x57b41f!==0x4→return`；`touch_drag13` 唯一 type1，带 `num:1,time:0.1` |
| 6 | **链占位/进度规则**：`action_list:[]` 空，仅参与链索引推进（`action_list.length<=1→triggeredRuleIds.add(id)`） | 推断 | `TouchDrag1/TouchDrag2` 两条 type6，ATA=null；`action_list.length<=0x1\|\|idx>=len-1 ? triggeredRuleIds.add : 记下一步` |
| 7 | **拖动主控规则**：rule[0] `TouchDrag8`，携带 listenerData(type1) + ATA(形态A)，是拖动链的「中枢」 | 推断 | 唯一 type7；`updateLive2DAnimationRule` 处理 `trigger_name==='idle'&&num>0` 分支 |
| `num`/`time` | 重复次数 / 触发时间窗（动作冷却的秒数来源之一） | 推断 | `live2DActionTriggerNum`/`live2DActionTriggerTime`：先读顶层，再按 `action_list[idx]['num'/'time']` 取 |

## 3. actionTriggerActive 语义（链状态机核心）

- **形态B**（13 条）`{enable:[动作名…], idle:7, ignore:[]}`：触发后 `enable` 成为**当前允许动作白名单**
  （`live2dOfficialEnableActions=data['enable']`），`idle` 数字**直接设置链状态** `live2dOfficialIdleIndex`，
  `ignore` 进忽略表。判定函数（ctx 原文）：`Q(ata?.['ignore'],name)→return!0x1; Q(ata?.[0x3e2],name)→return!0x0`
  （0x3e2 解码即 enable 类键）→ **白名单外的动作一律不放行**。
- **形态A**（1 条，TouchDrag8）`{idle_enable:[[state,[动作…]],…], idle_ignore:同构}`：按**当前链状态
  （idleIndex 0/8/9…）** 查表决定白名单/忽略表（`idle_enable.find(e=>e[0]===<idleIndex>)`，ctx 原文截断处）。
  状态 8 → 允许 `touch_idle12`+`touch_drag1~8`；状态 0/9 → 空（回普通）。
- 第三形态 `active_list`：`actionTriggerActive.active_list[idx]` **按链步骤覆盖** activeData
  （ctx：`_0x12c987=ata?.['active_list']?.[idx]||ata`）。guanghui_9 无此字段，引擎支持。
- **持久化**：`saveLive2DOfficialTouchState` 把 `actionListIndices`(Map) / `idleIndex` / `activeRuleId` /
  参数值 / 关系参数写入 **localStorage**（ctx 原文 `window['localStorage']['setItem']…`）——
  **链进度跨刷新保留**（读回时 `applyLive2DActiveData(activeRule 的 ATA, id)`）。
- 状态机还有：`live2DActiveDataRepeatsCurrentIdle(ata)` 防重复播同一 idle；`officialLive2DActionAllowed(name)`
  全局闸门；`Ue(idle, idx, random)` 取下一 idle。

## 4. listenerData 语义

消费循环（ctx 原文，节选）：`rules.forEach(r=>{let ld=r['listenerData']; if(ld?.['type']!==E) return;
ld['change'].forEach(([flag,names,dir,mult=1])=>{ if(!names.some(n=>String(n).toLowerCase()===当前动作名)) return;
…用 r['parameter'] 与 dir 驱动参数…})`
- `type 1`（TouchDrag8）：`apply:[1,[[from,to,state]…]]`+`change:[[1,[动作组…],dir]…]`——**当某动作
  （touch_drag1/5/9 → 0；touch_drag2/6/7 → +1；touch_drag3/4/8 → −1）成为当前动作时**，把关联参数
  设为对应方向值（拖动轨迹→表情/朝向参数的映射表）。`apply` 的 `[from,to,state]` 是状态迁移表（推断）。
- `type 3`（某规则）`{change:[[2,[0],0]]}`：数值型监听（参数值→目标），细节推断。
- 触发时机由动作**结束/切换**事件驱动（`_0x184ad0===E` 分支同时调 `applyLive2DActionCooldowns()`，E≈motion-end）。

## 5. l2d.su 热区判定算法

1. **指针命中**：Pixi 交互层（lib 的 `EventBoundary`×6）→ 命中模型 → 取命中的 **drawable**；
   规则侧用 `Ve(drawables, rule)` 判定：命中集合含 `rule['name']`/`rule['id']`/`rule['drawAbleName']`
   （经小写归一）即视为命中（stage1 证据 + 本阶段 ctx）。
2. **规则过滤**：`currentSpec.live2dTouch.rules` → 逐 rule 建 `live2dHitAreas`；
   `scheduleLive2DHitAreaRefresh`/`updateLive2DHitAreaFrame()` 每帧刷新（ctx：帧回调
   `updateLive2DOfficialRuleStates(); updateLive2DHitAreaFrame()`）。
3. **参数驱动**：命中后按 rule.mode：
   - mode1+type2：把 `parameter` 当动作组播（actionTrigger.type 2）；
   - 拖动（type1/4/M）：`value=当前值+位移 → dragDirect 钳方向 → rangeAbs 取绝对值 → range 钳幅 → smooth 趋近`（§1 表证据）；
   - mode2（Param3 三条，无 drawAbleName）：**不靠区域命中**，`reactPosX/Y × 指针位置` 求和写入参数（§1 证据）——这是「把手掌放到角色上跟随移动」类反应。
4. 多重命中：现有 minimal 前端用「包围盒最小」；l2d.su 引擎按规则遍历全部命中（`areas.forEach`），
   由 trigger 类型与冷却决定实际触发（`triggeredRuleIds` 去重）。

## 6. l2d.su 动作链条状态机

- **链状态** `live2dOfficialIdleIndex`（数字）：由 ATA 形态B `idle:N` 设置；形态A 按状态查 enable/ignore 表。
- **链步骤** `live2dOfficialActionListIndices: Map<ruleId, idx>`：每触发前进一步；到最后一步 →
  `triggeredRuleIds.add(ruleId)`（本轮结束）；否则记下一步并挂起（`action_list[idx+1]`）。步进带
  `num`/`time`/`focus` 字段（per-step 覆盖）。**进度持久化到 localStorage**（§3）。
- **冷却**：`limitTime` 秒 → `live2dOfficialRuleCooldowns`；动作级冷却另一 Map（钳 ≤0.2s）；
  链完成/打断经 `revertActionIndex`/`revertIdleIndex` 复位参数。
- **打断语义**：`live2dOfficialIsPlaying`/`activeMotionSequence` 守卫；`waitForLive2DMotionEnd` 串接；
  打断时 `live2dOfficialGameSequence+=1` 使旧回调失效（序列号守卫，ctx 原文）。
- **游戏机**（本模型未用，引擎有）：type I 触发 → `applyLive2DGameMove` →
  `live2dOfficialGameNextMoveAt=now+1000ms`、`live2DGameFinished()` → 500ms 后 `live2dOfficialGameResult=playerWon`。

## 7. 差距分析（现实现 vs 精确引擎）

现实现（`l2d.ts` + `main.ts`）**已用**：`drawAbleName→parameter` 区域命中（包围盒、可见性、画布内过滤）、
最小包围盒择一、手势分类（tap/drag/longpress）、`touch_idleN` 按编号递进链 + 10s 重置 + 60s 冷却（main.ts `chain`）。
**未消费**（= gap）：

| gap | 影响 | 升级最小改动集 |
|-----|------|---------------|
| `actionTrigger.type` 不分发：TouchIdle 区按 tap 播、TouchDrag 区一律当 drag | 长按/拖动型热区语义错 | `l2d.ts loadTouchRules` 把 `actionTrigger` 一并缓存；`emitInteraction` 用它替代 `name.startsWith` 猜测 |
| `actionTriggerActive` 白名单/链状态完全没用：递进链靠组名编号启发式（`^touch_idle\d*$` 排序推进） | 链顺序/放行与数据不符；忽略表不生效 | `main.ts`：链改为读 rule 的 ATA——触发 rule 时按 `idle:N` 设状态、按 enable 表选下一动作、ignore 表拦截；状态存 localStorage |
| `listenerData` 无 | 拖动轨迹→参数映射缺失（如拖动方向带动视线/身体朝向） | `l2d.ts` 每帧（`beforeModelUpdate` 已有挂点）按 §4 循环写 `setParameterValueById` |
| mode2 + `reactPosX/Y` 无 | Param3 位置跟随反应缺失（三条 rule 现在直接被 `!name` 过滤丢弃） | `loadTouchRules` 放行无 `drawAbleName` 的 mode2 rule；帧循环按 §5.3 求和写入 |
| `dragDirect`/`rangeAbs`/`range`/`smooth`/`relationParameter` 无 | 参数驱动无钳制/平滑/联动 | 在参数写入处加 §1 表的钳制链（一个纯函数即可） |
| `limitTime` 冷却、`revertActionIndex`/`revertIdleIndex` 复位、`saveParameter` 持久化无 | 重复触发不冷却；换页丢状态 | `main.ts` 链状态旁加冷却时间戳；localStorage 存 `{actionListIndices, idleIndex, activeRuleId}` |
| 顶层 `parameterRange` 无 | ParamAngleX 超幅 | 全局钳制表，读入即生效（引擎明文消费 ×1） |

## 8. 复现路径建议（二选一结论）

**结论：升级为「规则驱动为主、启发式兜底」的混合方案，不建议纯启发式也不建议一步到位全量复刻。**

理由：现启发式在 guanghui_9 上「能播但语义不精确」（链顺序、白名单、冷却全靠猜）；
而精确引擎的 90% 行为价值集中在 4 件小事——①ATA 白名单+idleIndex 状态机（§3）、
②actionTrigger 类型分发（§2）、③limitTime 冷却+localStorage 持久化（§6）、④mode2/reactPosX 位置反应（§5）。
这 4 项都有明文字段与清晰消费逻辑可照抄，改动集中在 `l2d.ts loadTouchRules`（多缓存字段）+
`main.ts` 交互处理器（按数据驱动），`listenerData`/`relationParameter`/游戏机可留待后续阶段
（收益低、且 Param3 联动效果需逐参数目测校准）。
