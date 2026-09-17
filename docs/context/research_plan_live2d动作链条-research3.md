# 研究计划 · live2d动作链条-research3（drag3 写参路径 / 热区消失机制 / poke 复位前提）

> /plan-research 产物（2026-09-18）。触发：research2_v2 人工验收失败（三处规格前提被实测推翻，
> 定性=认知/依据缺失，证据与定性见 current-work.md 阶段状态行 2026-09-18 段）。
> 执行：/research-doc（弱模型）。已载模块文档：spec-l2d-touch-engine.md（§7 ParamDriver 语义）。
> 规划期已核锚点（强模型预检，可信）：poke 翻转门槛 l2d_params.ts:127、注册跳过过滤 :185、
> beginHold 即置 pokeTarget :139-141、tap 命中 poke l2d.ts:425、hold 链 l2d.ts:160-270、
> drag4/5 规则 23703104/05 = mode1/无 actionTrigger/revert=-1/revertIdleIndex=None。

## 1. 研究问题定义

guanghui_9 drag3 触摸链在 v2（idle 显式循环）后的三个实测反常——①单击后 touch_drag3 停在
4~8 随机中值且不复位、②drag4/5 热区从「漂移」变「整体消失」、③type12 门 (0.01,10] 因此永不
释放——的真实机制是什么；本地实现与 l2d.su 站点在写参、复位、热区可见性三处的语义差异各在哪。

## 2. 子问题与查阅位置

### Q1 drag3 单击的完整写参时序与「停中值」根因

待证伪假设（按可能性排序）：
- H1 单击带微小位移：l2d.ts:178/:261 setHoldValue 写入指针派生转盘值 → endHold
  （revert=-1，l2d_params.ts:165-175）按「继续收敛到最后转盘值」处理 → 值停在释放点，
  既非 circleTarget=10 也非 0
- H2 pointerdown 即 beginHold 置 pokeTarget=circleTarget（l2d_params.ts:139-141）与
  tap 命中 poke()（l2d.ts:425）的触发顺序/互斥关系未明，两次目标互相覆盖
- H3 limitTime=0.1 冷却内重复触发改写 pokeTarget
- H4 关系预设 relationWrites（l2d_params.ts:203，type103/104）回写干扰

查阅位置：
- l2d.ts:160-270（pointerdown/move/up 全链）、:413-434（hitTest→poke→onInteraction）
- l2d_params.ts:122-210（poke/beginHold/setHoldValue/endHold/update 与 phase 切换）、
  :295-311（stepPoke 到位停留）、:340-356（stepDrag）
- live2d-models/guanghui_9/touch.json 规则 23703103 全字段（circle target=10、revert=-1、
  limitTime=0.1、rangeAbs=1、saveParameter=0 已预核）
- 仪表：叠加层 core 值列 + ⚠写入失效（research2 已落地）可作运行时取证（见 Q4）

### Q2 drag4/5 热区消失机制（v1 漂移 → v2 整体消失）

待证伪假设：
- H1 touch_drag4/5（mode=1、无 actionTrigger）注册进 ParamDriver 但被 update 跳过
  （l2d_params.ts:185 `mode===2||carrier` continue；l2d.ts:667 带 relations 才 carrier）
  → core 无人每帧钉死 → v2 循环 idle 每圈重写其曲线 → TouchDrag4/5 drawable 被移动/隐藏
- H2 注册且非 carrier → 每帧钉死 startValue=0 → 与「消失」矛盾（证伪即排除 H1）
- H3 叠加层绘制过滤：零面积/状态 H 的区是否根本不画（l2d_touch_debug.ts:96/:155、
  helpers collectHitAreas）

查阅位置：
- l2d.ts loadTouchRules → ParamDriver 注册过滤全链（rg registerRules/carrier）、
  :462-500 touchZoneStates 状态判定（H/G/T）
- l2d_touch_debug.ts:86-160 绘制循环与过滤条件
- guanghui_9/touch.json 23703104/23703105 全字段
- motions/idle*.motion3.json（idle、idle1、idle10、idle12~15…）Curves 参数名清点：
  是否含 touch_drag4/5 及取值（python 只读清点，不改文件）
- 站点对照：docs/assets/_ships_cache/site_<group>.json 的 live2dTouch、站点热区渲染
  是否同源 drawable 顶点（spec-l2dsu-engine.md 索引）

### Q3 poke 复位语义与站点对照

- 本地翻转门槛 |v−circleTarget|<0.05 才回 startValue（l2d_params.ts:127）；
  spec-l2d-touch-engine.md:115-116 已归档站点同款（到位停留、下次 poke 翻回，吾妻
  TouchDrag8 实证）——待证：站点「单击含微位移」后值是否同样停在转盘释放点（r3 §5.1
  hold 续算语义已录一半）；若站点同款，则 v2 §5-2b①「翻回 ≈0」预期错在「值从未到位
  10」，根因收敛回 Q1，H1 获侧证
- 站点 resetLive2DRulesForIdle（revertOnIdle 对应物）触发时机 vs 本地 syncChainContext
  （l2d_params.ts:218-225）：drag4/5 无 revertIdleIndex，站点该类参数靠什么复位/保持
- 与阶段 B 遗留「type2+target 非 circle 点按写参（F2 验收不足）」合并裁决

查阅位置：spec-l2d-touch-engine.md §7/:115-118、spec-l2dsu-engine.md、
research_live2d动作链条修正.md v2 §3.1（站点 type2 语义 ⑧）；不足则按
docs/assets/README 规则反查站点 chunk

### Q4 静态无法确证部分的复现取证

- 用现有叠加层（core 值列/⚠写入失效/idleIndex）设计复现脚本：纯点击（无位移）vs
  带微位移点击 vs 拖拽，各录 touch_drag3 内部值与核值变化时序；drag3 后静置 ≥2 个
  idle 循环观察 drag4/5 热区矩形变化
- 产出「可复现行为表」供研究文档引用；不修改任何代码

## 3. 输出文档结构（research_live2d动作链条-research3.md）

1. 结论摘要（三问各一段，证据级 A/B/C 标注）
2. Q1 写参路径实证：pointerdown→hit→poke→hold 事件时序 + 停中值根因裁决
3. Q2 热区可见性机制：注册/carrier 判定表 + idle 曲线清点表 + 消失机制裁决
4. Q3 poke/复位语义本地 vs 站点对照表
5. v2 规格 §0 前提逐条复核（证伪 / 保留 / 修正）
6. 修复方向候选（供 /plan-feature 裁决，不写实现）
7. 证据索引（文件:行 / 数据快照 / 复现步骤）

## 4. 已知约束和边界

- 只读取证：不改 src/、不改 touch.json、不跑会改工作区状态的命令；motion3.json 用
  python 只读清点
- 站点取证优先已有快照（docs/assets/_ships_cache），补采按 docs/assets/README 规则
- Q4 需浏览器交互：执行档位若无法驱动浏览器，降级为「复现步骤清单交用户记录」，
  行为表留空档注明
- 不做修复实现（后续 /plan-feature）；不改 research2 旧文（§3.3 作废说明已在模块文档）
- 范围锚定 guanghui_9，跨模型泛化结论须抽样后才可写
- 在档遗留只标注关联不展开：[live2d动作链条] 阶段 B「type2 点按写参 F2」、
  [hotzone-arch] ③ 叠加层显示策略
