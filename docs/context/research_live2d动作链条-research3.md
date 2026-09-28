# 研究 · live2d动作链条-research3（drag3 写参路径 / 热区消失机制 / poke 复位前提）

> /research-doc 产物（2026-09-18）。
> 触发：research2_v2 人工验收失败（三处规格前提被实测推翻，定性=认知/依据缺失）。
> **本轮新增 A 级证据：在运行中的极简前端（127.0.0.1:12393/m/，dist 含 v2 代码）上做了
> 只读运行时取证**——真实 PointerEvent 序列 + 参数状态机探针 + 值扫描，复现了用户全部三问。
> 未修改任何源码/数据文件；浏览器侧仅内存态赋值（刷新即恢复，与验收操作同性质）。
> 证据级：A=运行时实测或源码直证；B=数据推导；C=推断（标注）。

## 1. 问题定义

guanghui_9 上 touch_drag3 的写入/复位链路与 TouchDrag4/5 热区可见性由同一参数耦合驱动，
三者（单击停中值、热区不出现、复位不可达）实为**一条自反馈链的三个观测面**，非三个独立缺陷。

## 2. 现状（代码/数据位置）

| 环节 | 位置 |
|---|---|
| 按下：命中→beginHold→circle 写转盘值 | `l2d.ts:169-180`（hitZoneAt / beginHold / dialValueFor→setHoldValue） |
| 抬起：endHold→emitInteraction(tap)→poke | `l2d.ts:195-214`、`:409-435`（poke 在 `:424-426`，**依赖当次 hitZoneAt**） |
| circle 状态机（转盘/翻转两分支） | `l2d_params.ts:296-313`；poke `:122-129`；beginHold `:132-143`；setHoldValue `:155-161`；endHold `:165-178` |
| 每帧驱动挂点 | `l2d.ts:944-960`（`afterMotionUpdate`，动作曲线之后） |
| revertOnIdle 复位 | `l2d_params.ts:220-232` + `l2d_params_relations.ts:79-86` |
| type12 门 | `l2d_touch.ts:52-70`（type12Decision）+ `l2d.ts:302-312`（组合闸） |
| 默认区/链入口过闸 | `main.ts:158-183`（touchhead/special 直连、touchbody 链步进前） |
| 数据 | `guanghui_9/touch.json` 规则 23703103（drag3，circle target=10，revert=-1，revertIdleIndex="1"）、23703104/05（drag4/5，无 actionTrigger + offsetY≠0 → **slide 型**） |
| 动作曲线 | `guanghui_9/motions/*.motion3.json`：97 个文件中绝大多数含 touch_drag3/4/5 曲线，**首末值均 0**（线性 0→0） |

## 3. 关键发现

### F1 drag3 单击停中值的完整根因（A，运行时实测复现）

真实事件序列实测（指针落于 TouchDrag3 内 (212,132)，记录参数状态机全轨迹）：

```
pointerdown → beginHold: phase=poke, pokeTarget=10
            → setHoldValue(8.956)        ← 按下点角度派生值，非 0 非 10
   [帧推进]  stepCircle 走 holdValue 分支：value 0 → 7.734（向 8.956 收敛）
pointerup   → endHold: revert=-1 → phase='idle'，holdValue=8.956 **保留**
            → emitInteraction('tap') → hitZoneAt(212,132) → **返回 null**
            → poke 未被调用（l2d.ts:422-426 的 if (hit) 未进入）
   [此后]    phase=idle → stepCircle 直接 return（l2d_params.ts:307）→ 值永久冻结在 7.734
```

**为何 up 时命中失败**：写入 touch_drag3 会立即驱动 TouchDrag3 drawable 位移——实测模型坐标
x 从 1675（值 0）漂到 −10771（值 7.7），画布宽仅 9999 → 指针不动而热区已跑出画布 →
`hitZoneAt` 空手而归。这是**值→几何自反馈**（F2），不是独立 bug。

用户报告的 4.76/7.73/2.48/7.71 = 各次点击的按下点角度派生值附近，随机性来自点击位置。

### F2 touch_drag3 同时驱动三个 drawable 的几何与不透明度（A，值扫描实测）

| touch_drag3 | TouchDrag3 模型坐标 x | TouchDrag4 opacity | TouchDrag5 opacity | drag4/5 区状态 |
|---|---|---|---|---|
| 0 | 1675 | 0 | 0 | T（透明） |
| 2.5 | −2348 | 0.25 | 0.25 | O（画布外） |
| 5 | −6371 | 0.5 | 0.5 | O |
| 7.5 | −10395 | 0.75 | 0.75 | O |
| **10** | −14418 | **1** | **1** | **ok（可交互）** |

美术层实现：drag4/5 的 opacity = 值/10（线性），位置同样随值移动。**值=10 时 drag4/5 落到
画布内（x=2318/1788）且 opacity=1 → 出现两个可交互滑块**（即站点「点 drag3 后出现滑块」）。

### F3 「热区不出现」不是独立缺陷（A）

- 清缓存基线（值=0）：drag4/5 = T（透明）→ 本就不可见——与 v1/v2 观察一致；
- 值卡中值（4~8）：drag4/5 = O（画布外）→ 不可见；
- 仅值=10 时 ok。

v1「漂移」与 v2「整体消失」是同一机制在不同停值/姿态下的两个快照（C 级解释，A 级支撑为
F2 表）。**v2 §0 的「循环 idle 每圈重写治愈热区」前提反向证伪**：idle 曲线写的是
touch_drag3=0（每圈重写 0），但 ParamDriver 每帧把内部值写回（挂点更晚），曲线无效——
真正决定热区是否出现的是**参数值能否到达 10**。

### F4 type12 门与「点哪里都没反应」（A，实测）

值=4.76 时全量区状态计数：`{G:10, O:53, ok:0}` —— **可交互区为零**。
值=0 时：`{ok:7}`（TouchDrag1/2/3/15 + 默认三区）。

即：值卡在 (0.01,10] → type12DecisionOf('touch_head'/'touch_body'/'touch_special') 恒 false
（规则 23703161 的 ignore 15 项）→ 默认区被拒 + gname 兜底被拒 → 用户 finding 3 的
「点哪里都没反应」。**finding 3 是 F1 的连锁，非独立缺陷。**

### F5 复位钩子全不可达 → 死锁（A，源码链 + 实测）

| 复位路径 | 可达条件 | 卡中值时 |
|---|---|---|
| poke 翻回 0 | \|value−circleTarget(10)\|<0.05（`l2d_params.ts:127`） | 值 4~8 → 不可达（再点只会推向 10） |
| revertOnIdle | idleIndex 0→1（`l2d_params.ts:221`） | 需 TouchIdleN 规则 dispatch（`l2d_touch.ts:197-212` 的 ata.idle 推进） |
| 链推进触发上面 | touchbody 链步进 | **门关时 main.ts:168-170 直接 return** → 链无法推进 → idleIndex 恒 0 |
| revertOnStep | 步差 | 同上依赖链推进 |

→ **闭环死锁**：值卡住 → type12 门关 → 链不推进 → idleIndex 不变 → revertOnIdle 不触发 →
值不归零。用户 finding 2c「点什么动作数值都依然固定」由此得解。唯一出路=调试复位
（`resetAll`）或极快点击（F6）。

### F6 poke 语义本身正确（A，实测）

同 tick 完成 down+up（几何未漂移）→ poke 被调用 → pokeTarget=10 → 值到 10 →
drag4/5 status=ok。**证明问题在「up 时重新命中」这一步，不在 poke 翻转语义。**

### F7 v2 的 idle 循环变更已生效（A）

实测 `motionGroups['idle'][0]._isLoop === true`、`_motionData.loop === true`（dur 8.533）。
但**未治愈本问题**：自愈前提（曲线重写生效）被 ParamDriver 钉死层推翻（F3）。

### F8 对照 v2 §0 附带发现（A/B）

- 「mode-1 参数被 ParamDriver 每帧钉死、不自动归零」——**本轮证实**（F5 poke 门槛 + 每帧 writeParam）。
- 「无 mode-1 钉死的参数由循环 idle 治愈」——**本轮证伪**：drag4/5 是 slide 型（mode=1 且
  注册进 ParamDriver，`l2d.ts:658-663`），同样每帧被 writeParam 钉死（实测内部值与 core 值恒等），
  idle 曲线无从介入。

## 4. 可选方案对比（供 /plan-feature 裁决，本命令不做实现）

| 方案 | 改动点 | 依据 | 风险 |
|---|---|---|---|
| **S1 抬起用按下区** | `l2d.ts:421` 的 `hitZoneAt(clientX,clientY)` 改为优先复用 `this.downHitZone`（已存于 `:198`，endHold/type1-4 已用） | 手势语义=作用于按下区；站点 pressedRules 亦按按下记录 | 需确认拖动路径不受影响（emitInteraction 的 drag 分支不用 poke） |
| S2 poke 改用 downRule | `l2d.ts:424-426` 条件从 `hit.rule` 改 `downRule` | 同 S1，改动更小 | 与 S1 重叠，择一 |
| S3 转盘写入延后到首次移动 | `l2d.ts:176-179` 按下不写 dial，改为 pointermove 首帧写 | 消除「单击被按下点角度绑架」 | 与站点「按住转盘」语义对照未取证（Q3） |
| S4 参数权威层对齐（阶段 C） | 目标层 + 每帧 Tween 分离 | research_live2d动作链条修正 §3.1 | 工程量大，前置取证未完成 |

S1/S2 最小且证据充分；S3 需先补站点对照。

## 5. 结论与建议

1. **三问同源**：F1（up 时命中失配）→ 值停中值 → F3（drag4/5 不可见）+ F4（全屏无响应）
   + F5（复位死锁）。修 F1 可一次性解开三问。
2. **v2 §5 验收协议的两处前提作废**：①「§5-2a 循环 idle 治愈 drag4/5 漂移」不成立（F3/F8）；
   ②「§5-2b① 再点 drag3 翻回 ≈0」不成立（值未到 10，`l2d_params.ts:127` 门槛不可达）。
3. **R2-e 修订建议**：其「mode-1 注册参数不自动归零」半句获实证；「分层自愈」半句应删
   （drag4/5 同属 mode-1 钉死，无自愈层）。
4. **建议**：以 S1 为规格主轴规划下一版（含 F4 门释放验证、F5 复位路径验证），
   S3 列入待研究（站点对照）。
5. **遗留关联**：[live2d动作链条] 阶段 B「type2 点按写参（F2 验收不足）」与 F1 同域，
   建议合并裁决；[hotzone-arch] ③ 叠加层显示策略可借 F2 表重估。

## 6. 证据索引

- 运行时取证脚本（内存态，可复现）：PointerEvent 序列 + ParamDriver 探针 + 值扫描，
  命令序列见本轮会话；关键实测点：(212,132)/(220,90) 落于 TouchDrag3。
- 源码：`l2d.ts:169-180/195-214/409-435/658-663`、`l2d_params.ts:122-129/132-143/155-161/165-178/220-232/296-313`、
  `l2d_touch.ts:52-70/197-212`、`main.ts:158-183`。
- 数据：`guanghui_9/touch.json`（23703103/23703161/23703104/23703105）、
  `guanghui_9/motions/*.motion3.json`（97 文件曲线清点）。
- 既有对照：`spec-l2d-touch-engine.md` §7:115-118（站点 poke 语义）、
  `spec-l2dsu-engine.md` §3.1 ⑥⑧/§3.3:280-287（站点 dial 与释放路径）、
  `research_live2d动作链条修正.md` §3.1/§5.2-5.4。
- **未取证（Q3 残留）**：站点实时对照（l2d.su 需登录；stage1 实测记录站点 guanghui 规则区
  当时不可交互）——站点 dial 写入时机与是否同样存在值→几何自反馈，待实机取证。
