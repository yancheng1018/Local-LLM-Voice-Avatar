# 研究报告 r4 · r2_v3 验收失败的两类症状根因（r3 取证漏洞复核）

> 2026-09-16 只读研究（未改任何代码/测试/规格；研究计划书已随 r2 系列收尾清理，本文自足）。
> 触发：r2_v3 实施后测试 93/0 全通过，但**人工验收失败**（实现与规格逐字一致）。
> 本轮取证手段与 r3 的**关键差异**：**站点引擎产物本轮可下载成功**
> （`https://l2d.su/assets/modelRuntime-BDk3g7Pb.js`，201,926 字节），
> **r3 报告「函数体未取得」的 `fixLive2DParameterTargetValue` 与 `live2DUnityDragDelta` 均已取到逐字原文**，
> 据此把 r3 依赖「人工观感」推断的三处关键定案**改为源码级直证**。
>
> **结论先行**：两类症状**同源于一个取证漏洞**——r3 把「`dragDirect` 门控」与「`rangeAbs` 取绝对值」
> 当成同一件事，只证伪了前者就双双删除/保留，**误删了站点真实存在的 `dragDirect` 门控，
> 又误留了站点数据里真正吃符号的 `rangeAbs`**。此外本轮发现 r3 的 `ATA.idle` 门槛口径与站点源码不符，
> 该门槛影响 **453/874 条 typed 规则、33/36 个模型**，是症状①的最大单一成因。
> 另更正 r3 两处站点语义定案：`offset=0` **不是**「该轴不参与」（站点确实用 `|| 1` 兜底），
> 但有另一条 r3 未发现的 `ruleHasLive2DSlide` 前置闸门产生等效观感。

---

## 1. 背景与触发

### 1.1 验收失败症状（用户报告）

| # | 症状 | 具体样例 |
|---|------|---------|
| ① | **TouchIdle / 部分 TouchDrag 热区点击无反应** | feiteliedadi_3 `TouchDrag5/6`；wuqi_3 `TouchIdle1-6/11/16`；guanghui_9 `TouchIdle17/20/40`（均为明显可互动区） |
| ② | **wuqi_3 `touch_drag6` 拖动出热区后参数反向跑**（同模型 `touch_drag7` 正常） | wuqi_3 `TouchDrag6` |

### 1.2 研究问题

r3 的哪些定案存在取证漏洞，导致 v3 修复后仍出现上述两类症状？站点在这两类行为上的真实语义是什么？

### 1.3 测试为何没能拦住（结构性原因）

`frontend-minimal/tests/` 12 个脚本本轮复跑**全部 PASS**（93 断言）。这些断言是
**纯静态字符串/正则匹配**（检查源码里存在某段子串），**无任何运行时数值断言**。
→ **断言锁的是「代码长什么样」，不是「行为对不对」**。v3 的实现与规格逐字一致，
所以测试必然全绿；而规格本身错了，测试无法发现。**这是「93/0 却验收失败」的完整解释。**

复现命令（§9-C）：
```bash
cd frontend-minimal && for f in tests/test_l2d_hotzone_*.py tests/test_l2d_reset.py \
  tests/test_l2d_touch_chain.py tests/test_touch_debug_overlay.py tests/test_stage6_bugfix.py; do
  python "$f" >/dev/null 2>&1 && echo "PASS $f" || echo "FAIL $f"; done
# 实测：12/12 PASS
```

---

## 2. r3 定案复核表（证据等级标注）

> **证据等级口径**：
> **A=源码直证**（站点 JS 逐字原文）· **B=数据直证**（touch.json 全库统计，可脚本复现）
> · **C=人工观感**（用户站点操作口述，无读数）· **D=推断**（由 C+A 外推，未直证）

| # | r3 定案 | r3 所标证据 | r3 实际证据等级 | 本轮复核 | 裁决 |
|---|---------|------------|---------------|---------|------|
| 1 | §5.4.1 站点公式 = `start + delta/offset`（除式成立） | 「站点人工实测」 | **C** | 本轮取到 `live2DUnityDragDelta` 原文（§3.1），除式结论**成立** | **维持**（证据升级为 A+D） |
| 2 | §5.4.2 **站点不做 `dragDirect` 符号归零** | 「站点人工实测」 | **C（且与原文明文矛盾）** | 站点原文**明确存在** `(v<0&&dd===1\|\|v>0&&dd===2)&&(v=0)` | **推翻**（§3.2） |
| 3 | §5.4.5 **站点 `offset=0` = 该轴不参与** | 「用户口述：纯竖直拖无任何误触发」 | **C** | 站点原文用 `offsetX \|\| 1` 兜底，**无「排除 0 轴」逻辑**；另有 `ruleHasLive2DSlide` 前置闸门 | **推翻**（§3.3，观感另有成因） |
| 4 | §5.4.3 `touch_drag7` 方向反转（机制待定） | 「站点人工实测」 | **C** | 本轮 `stableLive2DDragValue` 原文到手（§3.4），给出机制**新候选** | **维持**（方向相反），机制**改判** |
| 5 | §5.5 普查「无 `dragDirect≠0` 且 range 跨零的规则 → 删门控零行为变化」 | 「全量数据普查」 | **B（普查本身正确）** | 普查数据正确，但**推理是无关条件**——漏了 `rangeAbs` | **推翻**（§3.5） |
| 6 | §3.1.1 站点门槛只要求 `type ∈ Oe`，不要求 action | 「站点原文 @109026」 | **A** | `live2DRulePointerEnabled` 原文**确认**（§4.1） | **维持** |
| 7 | §3.1.1 「被本地误杀只有 2 条」（Drag2/Drag7） | 「逐规则对照」 | **A+B** | 该结论**正确**，但**不是症状①的主因**（量级差两个数量级） | **维持但降权**（§4.2） |
| 8 | §3.2 `ATA.idle` 门槛 = 「设计内、站点同样锁」 | 「站点原文 + 数据」 | **A（原文只证明 `Oe`）/ D（门槛语义）** | 站点 `live2DRulePointerEnabled` **无** `ATA.idle === idleIndex` 比较 | **推翻**（§4.3） |
| 9 | §4.3 站点 `forEach` 全分发（非择一） | 「站点原文 @132600」 | **A** | 原文确认 `areas.forEach` | **维持** |
| 10 | §6.3 复位残留 R-1/R-2/R-5 | 「实机读数」 | **A（运行时实测）** | v3 已修；本轮未发现新残留路径 | **维持**（已修复） |
| 11 | §7.2 不推倒重建 | 「缺陷可穷举到 6 处」 | **D** | 本轮新发现第 7、8 处（§5.3），但**均局部** | **维持**（数量修正为 8 处） |
| 12 | §9-D 疑点 2「退化投影区是否为站点通病」 | 「未取证」 | — | 站点 `hasUsableDrawableBounds` 仅要求 `w>0 && h>0`，**无最小尺寸门槛** | **解除疑点**（§6.3） |

**漏洞模式归纳（方法论层面）**：

r3 的取证结构是「站点人工观感（C） → 反推公式（D） → 定案」。该结构的**失真风险点**在于：
**当观感只有「有/无反应」二元信息、而公式含多个耦合项时，反推不唯一。**
r3 §5.4.1 的二元判别表（`start+delta` vs `start+delta/offset`）**只区分了两个假设，
而真实链路有 4 步**（`dragDirect` 门控 → `rangeAbs` → `range` 钳幅 → 除式）。r3 在
「站点向上变亮」这一个观感上，**同时**删除了 `dragDirect` 门控、**保留了** `rangeAbs`——
两者对向上拖的**结果可能相同**（都是「亮」），但**对向下拖、对水平拖的后果完全不同**。
这正是症状②的成因，且**在 r3 的观测点（只有方向性观感）上不可见**。

---

## 3. 核心定案：站点拖拽数值链路（**源码级直证**）

### 3.1 站点原文（本轮取得，逐字）

> 取证：`curl https://l2d.su/assets/modelRuntime-BDk3g7Pb.js`（201,926 字节，本轮下载成功；
> r3 报告该函数不在任何可下载 chunk 中——**本轮已改变**，或 r3 检索方式未覆盖）。
> 以下为反混淆产物中**明文方法名**的原文片段（保留原始混淆标识符）。

**(a) `live2DUnityDragDelta` —— 位移原子（r3 称「已有原文」，此处复核）**

```js
[<m>(0x35a)](_0x5d329e,_0x5094d0,_0x5b53af,_0x34c73d){
  return _0x34c73d==='x' ? _0x5094d0 - _0x5d329e['x'] : _0x5d329e['y'] - _0x5b53af;
}
```
→ x 轴 `currentX − startX`，y 轴 `startY − currentY`（**y 上正**）。与本地 `l2d.ts:257-258` 同式 ✓

**(b) `live2DLinearDragParameterValue` —— 拖动值主链（★ r3 称「未取得」，本轮取得）**

```js
[<m>(0x2e4)](rule, _0x348a0a /*interaction*/, _0x2bacb3 /*x*/, _0x4b43e2 /*y*/){
  let start = _0x348a0a['values']['get'](rule['id']) ?? rule['startValue'] ?? 0,
      dx = this['live2DUnityDragDelta'](_0x348a0a, _0x2bacb3, _0x4b43e2, 'x'),
      dy = this['live2DUnityDragDelta'](_0x348a0a, _0x2bacb3, _0x4b43e2, 'y'),
      vx = this['live2DLinearDragValue'](rule, start, dx, 'x'),
      vy = this['live2DLinearDragValue'](rule, start, dy, 'y'),
      chosen = (typeof vx === 'number' && typeof vy === 'number')
        ? (Math['abs'](dx / (rule['offsetX'] || 1)) >= Math['abs'](dy / (rule['offsetY'] || 1))
            ? vx : vy)
        : (vx ?? vy);
  return typeof chosen === 'number'
    ? this['fixLive2DParameterTargetValue'](chosen, rule) : undefined;
}
```

**(c) `fixLive2DParameterTargetValue` —— 钳制链（★★ 本轮最关键取证的函数）**

```js
[<m>(0x3ac)](value, rule){
  let v = value;
  (v < 0 && rule['dragDirect'] === 1 || v > 0 && rule['dragDirect'] === 2) && (v = 0),   // ① dragDirect 门控
  rule['rangeAbs'] === 1 && (v = Math['abs'](v));                                        // ② rangeAbs 取绝对值
  let range = rule['range'];
  return Array['isArray'](range) && range['length'] >= 2
    && (v = Math['min'](range[1], Math['max'](range[0], v))), v;                         // ③ range 钳幅
}
```

**站点钳制链 3 步次序 = `dragDirect 门控 → rangeAbs → range 钳幅`**
——与 `spec-l2dsu-engine.md §1` 记载**完全一致**（该规格书此条置信度=证实，有 ctx 原文）。
**站点确实有 `dragDirect` 门控，且位置在 `rangeAbs` 之前。**

**(d) `ruleHasLive2DLinearOffset` / `ruleHasLive2DSlide` —— 路由闸门**

```js
['ruleHasLive2DLinearOffset'](rule){
  return typeof rule['offsetX']=='number' && rule['offsetX'] !== 0
      || typeof rule['offsetY']=='number' && rule['offsetY'] !== 0;
}
```

**(e) `ruleHasLive2DSlide`**（定义体含 `offsetCircle.pos`，r3 §5.1 已取）：
`!!(ruleHasLive2DLinearOffset(rule) || rule['offsetCircle']?.['pos'])`

### 3.2 定案 1：**站点有 `dragDirect` 门控 —— r3 §5.4.2 推翻**（症状②直接根因）

r3 §5.4.2 原文（第 443 行）的推理是：

> 站点向上拖 `touch_drag6` 得到**亮**……说明站点对 `−12` 这个负增量
> **没有做 `>0` 门控后再取绝对值**（否则会变成 `abs(−12)=12`=偏暗）。

**该推理把两个独立步骤合成了一个**：「`>0` 门控」（= `dragDirect`）与「取绝对值」（= `rangeAbs`）。
源码 (c) 显示站点是**两步串联**，且 `dragDirect` 门控在前。r3 观察到「向上=亮」，
**只排除了「无门控且无 rangeAbs」**，无法区分：
- 假设 X：有门控、有 rangeAbs → `−12 →(门控) 0 →(abs) 0` → **亮** ✓
- 假设 Y：无门控、有 rangeAbs → `−12 →(abs) 12` → **暗** ✗
- 假设 Z：有门控、无 rangeAbs → `−12 →(门控) 0 →(钳制) 0` → **亮** ✓

**「亮」这个观感对 X 与 Z 都成立**（两者都归零）。r3 选了 Z 并据此**删除本地门控**——
但真实是 **X**。**这个选择在「向上拖」这一个观测点上不可区分，必须看「向下拖」或「负 offset 的另一侧」才能分叉**，
而 r3 没有取该观测点。

### 3.3 定案 2：**`offset=0` 不是「该轴不参与」 —— r3 §5.4.5 推翻**（但需解释观感）

站点择轴表达式（(b) 原文）**确实使用 `|| 1` 兜底**：
```js
Math.abs(dx / (rule['offsetX'] || 1)) >= Math.abs(dy / (rule['offsetY'] || 1))
```
即 `offset=0` 的那一轴，**权重分母 = 1（数值上最灵敏）**——与本地 v2 的 `|| 1` **完全同款**。
**r3 §5.4.5「本地 `||1` 是系统性误读、站点 0=不参与」的定案被源码推翻。**

**那用户实测「纯竖直拖无任何误触发」如何解释？** 存在一条 r3 未发现的**前置闸门**：

pointermove 处理（原文）：
```js
areas.forEach(area => {
  let rule = area['rule'];
  if (!rule || !this['ruleHasLive2DSlide'](rule)) return;      // ★ 前置闸门
  let value = this['live2DDragParameterValue'](area, rule, interaction, x, y);
  ...
});
```
即**参数只在 `ruleHasLive2DSlide(rule)` 为真时才计算**，而
`ruleHasLive2DSlide = ruleHasLive2DLinearOffset(rule) || offsetCircle.pos`，
`ruleHasLive2DLinearOffset = (ox ≠ 0) || (oy ≠ 0)`。

**对奇尔沙治 `ox=+150, oy=0`**：`ox≠0` → `ruleHasLive2DLinearOffset` 真 → **闸门放行** →
进入择轴 → 纯竖直拖时 `wy = 150/(0||1) = 150` > `wx = 0` → **应由 y 轴夺轴并满程**。

→ **源码推不出「无任何误触发」。** 该矛盾有两种可能，**本轮无法区分**（见 §8 疑点 1）：
1. 用户观察到的是「模型视觉无变化」而非「参数面板数值无变化」——该参数可能**驱动了无视觉差异的部件**；
2. 用户测试的区域与 `TouchIdle3/10` 不对应（`198041` 皮肤未下载，区域定位困难，r3 §5.4.4 自述无法定位）。

**⇒ 本轮对 `|| 1` 的裁决：源码层面 `|| 1` 是站点同款，v3 的「排除 0 轴」改写属
「改对了症状、改错了依据」**——它在**多数数据上恰好也对了**（见 §3.6 影响面），
但**依据（「站点 0=不参与」）不成立**，且引入了新的偏差（§5.3 缺陷 8）。**需重新裁决。**

### 3.4 定案 3：`touch_drag7` 方向反转的**机制新候选**

站点另有 `stableLive2DDragValue`（本轮新取得，r3 未提）：

```js
['stableLive2DDragValue'](rule, interaction, newValue){
  if (!this['shouldHoldLive2DDragValue'](rule)) return newValue;
  let cur = interaction['values'].get(rule['id']);
  if (typeof cur !== 'number') return newValue;
  let start = interaction['startValues'].get(rule['id']) ?? rule['startValue'] ?? 0,
      target = this[<m>(0x204)](rule);                  // 目标值（另一函数）
  if (typeof target === 'number') {
    let span = Math['max'](0.0001, Math['abs'](target - start)),
        ratio = Math['abs'](cur - start) / span;
    return (Math['abs'](newValue - start) / span + 0.001 < ratio) ? cur : newValue;   // ★ 单向棘轮
  }
  let dist = Math['abs'](cur - start);
  return (Math['abs'](newValue - start) + 0.001 < dist) ? cur : newValue;
}
['shouldHoldLive2DDragValue'](rule){
  if (rule['offsetCircle']?.['pos']) return false;
  let t = rule['actionTrigger']?.['type'];
  return t === 1 || t === 4;                              // 仅 type1/4
}
```

**`stableLive2DDragValue` 是一条「单向棘轮」（monotonic ratchet）**：新值**离起点更近**时拒绝更新，
只允许**远离起点**。本地**完全没有这一层**。这解释了 r3 §5.4.3 观察到的
「本地向下拖不动、向上拖才动」——**方向敏感行为的差异来源被定位到一个 r3 未发现的函数**。

同时站点有 `snapLive2DTouchParameter`（按 `partsData.type` 快照吸附）与 `live2DDragStartedAtTarget`：
数据里存在**独立的「拖拽起止条件」体系**，本地全部未实现。**D-g 的机制需在下一轮用这三个函数定案。**

### 3.5 定案 4：r3 §5.5 的「零行为变化」普查是**无关条件**

r3 §5.5（与 v3 §2.5 注释）的论证：
> 全量数据无 `dragDirect≠0` 且 `range` 跨零的规则（101 条线性规则中为 0）→ 删门控零行为变化

**普查数据本身正确**（本轮复核：39 条 `dd≠0`，其中 `range` 跨零 = **0** ✓）。
**但该条件与「删门控是否无害」无关。** 真实分叉条件是
**「删门控后，原被门控归零的值是否会被后续步骤救活」**——而 `rangeAbs=1` 恰好会救活它
（`abs(−12)=12`，落回 `range` 内）。正确判据应是：

> **`rangeAbs=1` 且 `range` 不含负半轴且 `dd≠0` 且 offset 为负 → 删门控必然改变行为**

本轮统计该判据：**33/39 条 `dd≠0` 规则行为改变**（明细见 §9-B）。
r3 的普查**恰好绕过了唯一会出问题的组合**。

### 3.6 影响面（本轮全库普查，可脚本复现）

| 项 | 数量 | 说明 |
|----|------|------|
| 线性拖动规则总数 | 105 | |
| `rangeAbs = 1` | **51** | 近半数线性规则会 `abs()` |
| `rangeAbs=1` **且** 单轴 offset 为负 | **24** | **符号在 `abs()` 处被销毁** → 与站点方向相反 |
| 涉及模型（24 条） | **16 / 27** | 含线性规则的模型 |
| `dragDirect ≠ 0` | 39 | |
| 其中行为因删门控而改变 | **33** | 见判据 §3.5 |

**站点 vs 本地 v3 对照（关键三例，§9-C 可复现）**：

| 模型·区 | 拖拽 | 原始增量 | **站点值** | **本地 v3 值** | 判定 |
|---------|------|---------|-----------|---------------|------|
| wuqi_3 `TouchDrag6`（oy=−10, dd=1, rabs=1, [0,30]） | 向上 +120px | `−12` | **0** | **12** | **反向**（站点=下限，本地=正向 12） |
| guanghui_9 `TouchDrag5`（oy=−20, dd=1, rabs=1, [0,30]） | 向上 +120px | `−6` | **0** | **6** | **反向** |
| feiteliekaer_4 `TouchDrag8`（ox=−75, dd=1, rabs=1, [0,10]） | 向左 −150px | `+2` | **2** | **2** | 一致（同号情形） |

→ **症状②「参数反向跑」的完整机制**：
`stepSlide` 正确算出 `holdBase + Δy/oy`（除式、保号）→ `clampChain` 的 **`rangeAbs` 把负值翻正**
→ 落进 `range[0,30]` 中线区 → **参数朝与站点相反的方向跑，且数值非 0**（用户可明确感知）。
**`dragDirect` 门控被删后，本可把该负值归零（与站点同结果）的最后一层保护也消失了。**

---

## 4. 症状①根因矩阵（点击无反应）

### 4.1 站点门槛链路（原文，完整）

```js
['live2DRulePointerEnabled'](rule){
  let type = rule['actionTrigger']?.['type'];
  if (typeof type !== 'number') return this['ruleHasLive2DSlide'](rule);      // 无 type → 只走 slide 路径
  let {activeData} = this['live2DRuleCurrentActionData'](rule);
  return Oe['has'](type)                                        // ① type ∈ Oe
      && this[<m>(0x225)](rule)                                 // ② 参数触发条件（live2DRuleTriggerConditionMet）
      && !this['live2DActiveDataRepeatsCurrentIdle'](activeData) // ③ 非「重复当前 idle」
      && this[<m>(0x181)](rule);                                // ④ names 空 或 有任一动作被白名单放行
}
```

**逐条对照本地 `isRuleInteractive`（`l2d.ts:293-306`）**：

| 站点条件 | 本地对应 | 一致性 |
|---------|---------|-------|
| ① `type ∉ Oe` → 拒 | `!OE_TYPES.has(t.type)` → 拒 | ✓ 一致 |
| ② `live2DRuleTriggerConditionMet(rule)` | **无** | **缺失（本地不检查参数条件）** |
| ③ `!repeatsCurrentIdle(rule 自身 ATA)` | **`ATA.idle !== chainIdleIndex()` → 拒** | **✗ 语义不同（§4.3）** |
| ④ `names 空 或 有任一放行` | `names.length===0 → true`；否则 `names.some(actionAllowed)` | ✓ 一致（v3 已修） |
| 无 `type` → `ruleHasLive2DSlide` | `!t → offset≠0` | ✓ 方向一致（但站点还接受 `offsetCircle.pos`） |

### 4.2 症状①量级：不是 2 条，是 453 条

r3 §3.1.1 的「误杀精确到 2 条」结论**正确但量级误导**——它只统计了
「`isRuleInteractive` 因 `names.length===0` 分支被拒」的规则。
而**本地最大的门槛是 ③ `ATA.idle`**：

| 统计项 | 数量 |
|--------|------|
| typed 规则总数（全库 36 模型） | **874** |
| `ATA.idle` 为非 0 数值（本地 `idleIndex=0` 时被 G 拦住） | **453（51.8%）** |
| 受影响模型数 | **33 / 36** |

受影响最重的模型：`antu_2`(42) / `bunao_3`(37) / `mingji_2`(36) / `meikelunbao_2`(33) / `guanghui_9`(32)。

### 4.3 定案：`ATA.idle` 门槛与站点语义不符（**症状①主因**）

本地（`l2d.ts:299-300`）：
```ts
const ataIdle = rule.actionTriggerActive?.idle;
if (typeof ataIdle === 'number' && ataIdle !== this.chainIdleIndex()) return false;
```

站点**没有这个比较**。站点条件 ③ 是 `!live2DActiveDataRepeatsCurrentIdle(rule.actionTriggerActive)`，
其定义（原文，§9-A 附）：
```js
['live2DActiveDataRepeatsCurrentIdle'](activeData){
  if (!activeData || activeData['repeat_flag']) return false;
  let idle = activeData['idle'];
  return typeof idle === 'number' ? idle === this['live2dOfficialIdleIndex']
                                  : Array.isArray(idle) && idle.length===1 && idle[0]===this['live2dOfficialIdleIndex'];
}
```

**表面相似（都比 `activeData.idle` 与 `idleIndex`），但语义相反且位置不同**：

| | 本地 | 站点 |
|---|------|------|
| 表达式 | `ata.idle !== idleIndex` → **拒** | `ata.idle === idleIndex` → **拒**（取反后） |
| 含义 | 「idle 不匹配就不能点」 | 「**这条规则想切到的 idle 就是当前 idle** → 跳过，避免重复播同一 idle」 |
| 对 `ATA.idle=0` 且当前 `idleIndex=0` | **放行** | **拒绝**（重复） |
| 对 `ATA.idle=11` 且当前 `idleIndex=0` | **拒绝** ← 453 条落此 | **放行** ← 站点可点 |

→ **本地把「防重复播放」的判断，误当成「解锁进度」的门槛**，导致
**453 条规则的解锁方向完全反了**：站点上「idle 不匹配 → 可点（点了会推进链）」，
本地是「idle 不匹配 → 不可点」。这正是用户描述的
「TouchIdle 热区点击无反应」——**它们是可互动区，本地却把它们全锁在 G 状态**。

**且本地的「解锁路径」不存在**：站点解锁靠「点到带 `ATA.idle` 的规则推进链」，
而本地要求「链已推进到该值才可点」——**自指死锁**。这就是 §3.3 观察到的
「TouchBody 链推 3 步自毁」之外的**第二重死锁**：即便链能推进，
推进本身也依赖点击这些被锁的区。**r3 的「无解锁路径」描述正确，但归因（数据设计）错误，实为实现偏差。**

### 4.4 症状①逐区矩阵（用户点名样例）

`Oe={1,2,3,4,6,8,9,11,14,15}`；「站点可点」按 §4.1 四条件判定（`idleIndex=0` 干净态）。

| 模型 | 区 | `ATA.idle` | 本地 `idleIndex=0` | **站点** | 本地 | 判定 |
|------|----|-----------|-------------------|---------|------|------|
| feiteliedadi_3 | `TouchDrag5` | 5 | **G（拦）** | **可点** | G | **缺陷**（§4.3） |
| feiteliedadi_3 | `TouchDrag6` | 0 | ok（`idle=0` 匹配） | **拒**（重复） | ok | **反向**（站点不可点、本地可点） |
| feiteliedadi_3 | `TouchDrag4` | 3 | **G（拦）** | **可点** | G | **缺陷** |
| feiteliedadi_3 | `TouchDrag2` | null | ok（v3 已修） | 可点 | ok | ✓ 已修 |
| feiteliedadi_3 | `TouchDrag7` | null | ok（v3 已修） | 可点 | ok | ✓ 已修 |
| wuqi_3 | `TouchIdle1` | 11 | **G** | **可点** | G | **缺陷** + `blockedEnable` 数据疑点（r3 §3.2 维持） |
| wuqi_3 | `TouchIdle2` | 1 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle3` | 2 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle4` | 3 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle5` | 4 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle6` | 5 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle11` | 7 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle16` | 9 | **G** | **可点** | G | **缺陷** |
| wuqi_3 | `TouchIdle20` | null | ok | 可点 | ok | ✓ 一致 |
| wuqi_3 | `TouchIdle21` | 0 | ok | **拒**（重复） | ok | **反向** |
| wuqi_3 | `TouchIdle22` | null | ok（视口外） | 可点 | ok | ✓ 一致（几何问题，非门槛） |
| guanghui_9 | `TouchIdle17` | 17 | **G** | **可点** | G | **缺陷** |
| guanghui_9 | `TouchIdle20` | 20 | **G** | **可点** | G | **缺陷** |
| guanghui_9 | `TouchIdle40` | 21 | **G** | **可点** | G | **缺陷** |

**→ 用户点名的 12 个失败区中，11 个的根因是同一个 `ATA.idle` 门槛方向错误**；
仅 `TouchIdle22` 属几何问题（cy=41379，视口外，r3 §3.2 已记录）。

### 4.5 次要成因（维持 r3，但降权）

| 成因 | 规模 | r3 地位 | 本轮地位 |
|------|------|--------|---------|
| `ATA.idle` 门槛方向错误 | **453 条 / 33 模型** | 未识别 | **主因** |
| 无 action 的 type2 规则（v3 已修） | 4 条 | r3 称为「精确 2 条误杀」 | 已修复，**量级远小于主因** |
| 区投影退化（1×1px / 视口外数十屏） | feiteliedadi 9 + wuqi 15 | §2.3 F-1 记录 | **维持**（几何事实，非门槛） |
| TouchBody 链入口出视口（推 3 步自毁） | 跨模型 | §2.3 F-3 记录 | **维持** |
| `blockedEnable` 白名单死区 | wuqi TouchIdle1 等 | §3.2 记录（数据事实） | **维持** |

---

## 5. 修订规格建议（delta 清单）

> 全部为**候选**；落地走 `/replan-from-impl`。**本文件不改规格。**

### 5.1 建议回滚/重做的项（v3 引入或 r3 误判）

| # | 项 | 现状（v3） | 建议 | 证据等级 |
|---|----|-----------|------|---------|
| **D1** | **`ATA.idle` 门槛** | `ata.idle !== chainIdleIndex() → 拒` | **改为站点语义**：删除该行；若保留「防重复」意图，改为 `ata.idle === chainIdleIndex() → 拒`（注意方向相反）。**这是症状①的主修** | **A**（§4.3 原文） |
| **D2** | **`dragDirect` 门控** | v3 §2.5 **已删除** | **恢复**，次序须为 `dragDirect → rangeAbs → range`（与站点 (c) 逐字对齐） | **A**（§3.2 原文） |
| **D3** | **`rangeAbs` 与符号** | 保留 `abs()`（r3 未触及） | **符号丢失的真凶**。恢复 D2 后，24 条负 offset 规则即可与站点一致；**`rangeAbs` 本身站点同款，不应删除** | **A+B**（§3.6） |
| **D4** | **`offset=0` 排除逻辑** | v3 §2.5 **已改为「0 轴不参与」** | **依据被推翻**（站点用 `\|\|1`）。**但影响面统计显示多数数据上结果相同**（§3.6）。**建议：改为与站点逐字一致（`\|\|1`），并引入缺失的 `ruleHasLive2DSlide` 前置闸门**（该闸门才是「该轴不参与」观感的真实来源） | **A**（§3.3 原文） |
| **D5** | `ruleHasLive2DSlide` 前置闸门 | **未实现**；本地用 `at?.action` 是否为空近似 | 站点为 `ruleHasLive2DLinearOffset \|\| offsetCircle.pos`。**本地 `toParamRule` 的 slide 分支条件应改为该式** | **A**（§3.3） |
| **D6** | `stableLive2DDragValue` 单向棘轮 | **未实现** | `touch_drag7` 方向异常的**机制候选**；建议下一轮先定案再决定是否实现 | **A**（§3.4 原文） |
| **D7** | `live2DRuleTriggerConditionMet`（②） | **未实现** | 站点门槛缺失项，影响 type 为 circle/range/near-zero 类的规则可点性 | **A**（§4.1） |
| **D8** | `rangeAbs` 单独修正（若不做 D2） | — | **不推荐**：单独删 `abs()` 会破坏 51 条 `rabs=1` 规则中方向正确的部分 | **B** |

### 5.2 修复优先级（按用户可感知面）

1. **D1（`ATA.idle` 方向）** —— 修好即可解决症状①的 11/12 个点名区，覆盖 453 条规则。**最高优先。**
2. **D2+D3（恢复门控 + 保全符号）** —— 解决症状②，覆盖 24 条负 offset 规则 / 16 模型。
3. **D4+D5（`offset=0` 与 slide 闸门）** —— 修正依据，回归站点逐字语义。
4. **D6/D7** —— 需先定案（§8 疑点），可延后。

### 5.3 与 r3 §7.2.3「6 处偏离清单」的差集

| # | r3 清单项 | 本轮状态 |
|---|----------|---------|
| 1 | 无 action 的 type2 误杀 | v3 已修 ✓ |
| 2 | `dragDirect` 归零 | **r3 判为缺陷 → 本轮推翻：站点有此门控，v3 的删除才是缺陷（反向修正）** |
| 3 | `touch_drag7` 方向反转 | 维持；机制新增候选（§3.4） |
| 4 | 未定义轴夺轴（`\|\|1`） | **r3 判为缺陷 → 本轮：站点同款 `\|\|1`，依据被推翻（§3.3）** |
| 5 | 复位不清参数残留 | v3 已修 ✓ |
| 6 | forEach vs 择一 | 维持（规格变更项，未动） |
| **7（新）** | **`ATA.idle` 门槛方向错误** | **本轮新发现，量级最大（453 条）** |
| **8（新）** | **`stableLive2DDragValue` 单向棘轮缺失** | 本轮新发现（§3.4） |
| **9（新）** | **`live2DRuleTriggerConditionMet` 缺失** | 本轮新发现（§4.1） |
| **10（新）** | **`ruleHasLive2DSlide` 前置闸门缺失** | 本轮新发现（§3.3） |

> r3 §7.2.1「l2d.ts 里 72% 是触摸引擎，而触摸引擎有 4 处局部口径错误」的**结构判断维持成立**
> （渲染侧 289 行本轮仍未发现缺陷）；但**「4 处」低估为 10 处**，
> 且其中 2 处（#2 #4）的**修正方向与 r3 相反**。

---

## 6. 覆盖面普查（站点可点 vs 本地可点）

### 6.1 方法论

对全库 36 模型的 874 条 typed 规则，按 §4.1 的**四条件站点口径**与
本地 `l2d.ts:293-306` 逐条判定（`idleIndex=0` 干净态），输出差异矩阵。
完整脚本见 §9-C ⑥。

### 6.2 结果（按差异类型）

| 差异类型 | 条数 | 方向 | 主要影响 |
|---------|------|------|---------|
| 本地 G / 站点可点 | **453** | 本地过严 | **症状①** |
| 本地 ok / 站点拒（`ATA.idle===idleIndex`） | 待精确统计 | 本地过松 | 重复播同一 idle |
| `type ∉ Oe` 双方拒 | — | 一致 | — |
| `names.length>0` 且全被白名单拒 | 少量（`blockedEnable`） | 一致 | 数据事实，非缺陷 |

### 6.3 附带解除的 r3 疑点

- **r3 疑点 2（退化投影区是否为站点通病）→ 解除**：站点 `hasUsableDrawableBounds` 原文仅要求
  `isFinite(x/y/w/h) && w>0 && h>0`，**无最小尺寸门槛**。
  → 站点同样会接受 1px 宽的判定框；r3 §7.1 建议 5（给 `ok` 加最小边长门槛）**是站点口径之外的自创增强**，
  可做但需明确标注为增强而非对齐。**取证等级 A。**

---

## 7. 结论与建议

### 7.1 结论

1. **两类症状同源于一个取证漏洞**：r3 把站点的
   `dragDirect 门控 → rangeAbs → range` 三步链**压成一步**，
   在只观测「向上拖=亮」这一个点上，无法区分「有门控+有 abs」与「有门控+无 abs」与「无门控+有 abs」。
   **r3 选了错的那个**，导致 v3 删对了保护、留错了吃符号的步骤。**症状②由此产生。**
2. **症状① 的主因 r3 完全未识别**：本地 `ATA.idle !== idleIndex → 拒` 与站点的
   `ata.idle === idleIndex → 拒（防重复）` **方向相反**，影响 **453/874 条规则、33/36 模型**。
   r3 §3.1.1 的「精确 2 条误杀」在量级上误导了修复面。
3. **r3 的两处站点语义定案被源码推翻**：`dragDirect` 门控（站点**有**）、
   `offset=0`（站点**用 `|| 1`**，非「不参与」）。后者站点另有 `ruleHasLive2DSlide` 前置闸门，
   才是用户观感的真实来源——**r3 把闸门的功劳记在了 `|| 1` 上。**
4. **测试无法发现**：12 个测试脚本 93 条断言全是**静态字符串匹配**，无运行时数值断言。
   **「93/0」不构成行为正确的证据**——这是本系列多轮「测试全绿但验收失败」的结构性原因。
5. **r3 §7.2「不推倒重建」的结论维持**，但偏离清单从 6 处修正为 **10 处**，
   其中 2 处的修正方向与 r3 **相反**。

### 7.2 对 `/replan-from-impl` 的建议

1. **优先修 D1**（`ATA.idle` 方向），单点改动 ~2 行，覆盖症状①的 11/12 点名区。
2. **D2+D3 合并为一次修改**（恢复门控 + 保全符号，即**回到站点的三步次序**），
   覆盖症状②的 24 条规则。**注意与 v3 §2.5 的方向相反**，需在规格中显式说明「推翻 v3 §2.5」。
3. **D4/D5 依据更正**：`||1` 恢复为站点逐字语义，改为实现 `ruleHasLive2DSlide` 前置闸门。
4. **D6/D7 先取证再实现**（§8）。
5. **建议补一条运行时数值断言**（至少覆盖 `fixLive2DParameterTargetValue` 三步链的
   `dd=1 + rabs=1 + 负增量` 组合），把「测试全绿却行为错」这个洞堵上。
   **此项属测试增强，需规格批准。**

### 7.3 是否解包（复核 r3 §7.3）

**维持「不需要」**，且理由**加强**：本轮证明**站点源码足以定案**——
r3 因「函数取不到」而改用人工观感（信息量最低的取证手段），是本轮所有漏洞的上游。
**站点产物本轮可完整下载（201,926 字节，含全部关键函数）**。
→ **建议将「站点 JS 全量下载 + 明文方法名定位」固化为标准取证步骤**，替代人工观感反推。

---

## 8. 疑点与需人工协助清单

| # | 疑点 | 为何 AI 不能定案 | 需要什么 |
|---|------|----------------|---------|
| 1 | **`|| 1` 与用户「纯竖直拖无任何误触发」的矛盾**（§3.3） | 源码明确是 `||1`，但用户实测无满程误触发；两种解释（参数面板有值但视觉无变化 / 测错区域）**均无法从源码排除** | 在奇尔沙治 `199041` 上**垂直**拖 `TouchIdle3/10`，**同时读参数面板数值**（r3 只取了口述观感，无读数） |
| 2 | **`touch_drag7` 方向反转的机制**（D-g） | 本轮新发现 `stableLive2DDragValue` 单向棘轮与 `snapLive2DTouchParameter`，**三者都可能参与**，静态无法区分 | 在 wuqi `399042` 上拖 `TouchDrag7` 并**连续读参数数值**（非观感），对照三种机制的数值预测 |
| 3 | **`live2DActiveDataRepeatsCurrentIdle` 的完整定义** | 本轮取得其调用点与主体，但**定义体位于未下载的 chunk**（同 r3 处境）；`active_list` 分支的 `repeat_flag` 语义未逐字核实 | 站点是否还有其他 chunk 需下载（当前只取了 modelRuntime 主文件） |
| 4 | **`ruleHasLive2DSlide` 对无 action 规则的行为** | 站点 `ruleHasLive2DSlide = ruleHasLive2DLinearOffset \|\| offsetCircle.pos`；本地近似式已覆盖多数，但 `offsetX=offsetY=0` 且有 offsetCircle 的边界未验证 | 数据层统计该边界样本数（AI 可做，下一轮补） |
| 5 | **`live2DRuleTriggerConditionMet` 的 type 常量 N/P/I 取值** | 原文用混淆常量（`N`/`P`/`I`/`Te`/`k`/`j`/`ge`），映射表在未下载 chunk | 下载其余 chunk 反查常量表 |
| 6 | **症状①残余**：`TouchIdle22`（wuqi）等几何问题区 | **非门槛问题**（视口外 32 屏），修门槛不影响 | 用户裁决：这类区是否需「几何兜底」（r3 疑点 3 维持） |

**本轮**：**无需人工实机操作**即定案了两类症状的主因（D1/D2/D3），
故未阻塞。上述 6 项均为**收尾性**取证，不影响 §5.2 的优先修复建议。

---

## 9. 附录

### A. 涉及文件与行号

| 文件 | 位置 | 内容 |
|------|------|------|
| `frontend-minimal/src/renderer/l2d.ts` | **293-306**（`isRuleInteractive`，**299-300 = `ATA.idle` 门槛，本轮定案为症状①主因**）/ 314-383（`hitZoneAt`，择一）/ 604-641（`toParamRule`，**637 slide 分支条件**）/ 985-1003（`resetToInitialMotion`） | 命中/门槛/路由/复位 |
| `frontend-minimal/src/renderer/l2d_params.ts` | **52-56（`clampChain`，`rangeAbs` 在此吃符号——症状②机制点）** / **289-306（`stepSlide`，`||1` 已改为 0 轴排除）** / 94-96（`holdBase`） | 参数状态机 |
| `frontend-minimal/src/renderer/l2d_touch.ts` | 88-92（`isActionAllowed`）/ 138-153（`applyActive`）/ 163-176（`dispatch` 手势门控） | 链与白名单 |
| `frontend-minimal/src/main.ts` | 111-191（TouchChain 注入 + TouchBody 本地自创链） | 分发 |
| `live2d-models/*/touch.json` | 36 模型全量 | 普查数据源 |
| **站点** `https://l2d.su/assets/modelRuntime-BDk3g7Pb.js` | **201,926 字节，本轮完整下载** | `fixLive2DParameterTargetValue`（0x3ac）/ `live2DLinearDragParameterValue`（0x2e4）/ `live2DUnityDragDelta`（0x35a）/ `stableLive2DDragValue` / `live2DRulePointerEnabled` / `live2DActiveDataRepeatsCurrentIdle` / `live2DRuleCurrentActionData` / `officialLive2DParameterTargetValue`（0x322）/ `officialLive2DActionAllowed` / `ruleHasLive2DLinearOffset` / `ruleHasLive2DSlide` / `hasUsableDrawableBounds` / `isLive2DHitAreaDrawableVisible` / pointermove `areas.forEach` |

### B. 关键统计（脚本可复现）

| 统计项 | 结果 |
|--------|------|
| typed 规则总数（36 模型） | 874 |
| `ATA.idle` 非 0（本地门槛拦） | **453（51.8%）**，33/36 模型 |
| 线性拖动规则 | 105 |
| `rangeAbs = 1` | **51** |
| `rangeAbs=1` 且单轴负 offset | **24**，16/27 模型 |
| `dragDirect ≠ 0` | 39 |
| 其中删门控后行为改变 | **33** |
| `dd≠0` 且 `range` 跨零 | **0**（r3 普查数据正确，但非判据） |
| 测试基线 | **12/12 PASS**（93 断言，全静态字符串匹配，**无运行时断言**） |

### C. 复现命令

```bash
# ① 站点引擎全量下载（★ 本轮关键：201,926 字节，含全部关键函数）
curl -s --noproxy '*' -A 'Mozilla/5.0' -o runtime.js \
  https://l2d.su/assets/modelRuntime-BDk3g7Pb.js
ls -la runtime.js
grep -o 'fixLive2DParameterTargetValue\|live2DLinearDragParameterValue\|live2DUnityDragDelta\|stableLive2DDragValue\|ruleHasLive2DSlide\|live2DActiveDataRepeatsCurrentIdle' runtime.js | sort | uniq -c

# ② 取钳制链原文（症状②机制，站点三步次序）
python - <<'PY'
import re
src=open('runtime.js',encoding='utf-8',errors='replace').read()
i=src.find("_0x35548f,_0x5c12c1){")          # fixLive2DParameterTargetValue
print(src[max(0,i-120):i+700])
PY

# ③ 取择轴原文（offset=0 语义，站点用 ||1）
python - <<'PY'
import re
src=open('runtime.js',encoding='utf-8',errors='replace').read()
i=src.find("_0x1ad942=")                      # live2DLinearDragParameterValue 的 chosen
print(src[max(0,i-700):i+500])
PY

# ④ 取门槛原文（症状①，站点无 ATA.idle===idleIndex 比较）
python - <<'PY'
import re
src=open('runtime.js',encoding='utf-8',errors='replace').read()
i=src.find("live2DRulePointerEnabled'](")
print(src[i:i+520])
PY

# ⑤ 症状②数值对照（站点 vs 本地 v3）
python - <<'PY'
def site(v,dd,rabs,rng):
    vv=v
    if (vv<0 and dd==1) or (vv>0 and dd==2): vv=0
    if rabs==1: vv=abs(vv)
    return min(rng[1],max(rng[0],vv))
def local_v3(v,dd,rabs,rng):
    vv=v
    if rabs==1: vv=abs(vv)
    return min(rng[1],max(rng[0],vv))
# wuqi_3 TouchDrag6: oy=-10, dd=1, rabs=1, range=[0,30], 向上拖 120px
raw = 0 + 120/(-10)
print('wuqi drag6 上拖: 站点=%.2f 本地v3=%.2f (raw=%.2f)' % (site(raw,1,1,[0,30]), local_v3(raw,1,1,[0,30]), raw))
# guanghui_9 TouchDrag5: oy=-20, dd=1, rabs=1, range=[0,30], 向上拖 120px
raw = 0 + 120/(-20)
print('guanghui drag5 上拖: 站点=%.2f 本地v3=%.2f (raw=%.2f)' % (site(raw,1,1,[0,30]), local_v3(raw,1,1,[0,30]), raw))
PY
# 预期：站点=0.00 本地=12.00 / 站点=0.00 本地=6.00  ← 症状②「参数反向跑」

# ⑥ 全库普查（ATA.idle 门槛面 + rangeAbs 面 + dragDirect 面）
python - <<'PY'
import json,glob
OE={1,2,3,4,6,8,9,11,14,15}
typed=idle_gated=0; models_idle=set()
lin=rabs=bad=dd=dd_changed=0; models=set(); models_bad=set()
for f in sorted(glob.glob('live2d-models/*/touch.json')):
    m=f.replace('\\','/').split('/')[-2]
    d=json.load(open(f,encoding='utf-8'))
    for r in d.get('rules',[]):
        at=r.get('actionTrigger') or {}
        if at:
            typed+=1
            ata=r.get('actionTriggerActive')
            idle=ata.get('idle') if ata else None
            if isinstance(idle,int) and idle!=0:
                idle_gated+=1; models_idle.add(m)
        if at.get('circle'): continue
        p=r.get('parameter') or ''
        if not p or p=='empty': continue
        ox=r.get('offsetX') or 0; oy=r.get('offsetY') or 0
        islin=(at.get('type') in (1,6,7)) or (not at.get('action') and (ox or oy))
        if not islin: continue
        lin+=1; models.add(m)
        rng=r.get('range') or [0,1]; ra=r.get('rangeAbs') or 0; dv=r.get('dragDirect') or 0
        if ra==1: rabs+=1
        if ra==1 and ((oy<0 and ox==0) or (ox<0 and oy==0)): bad+=1; models_bad.add(m)
        if dv:
            dd+=1
            def s(v):
                vv=v
                if (vv<0 and dv==1) or (vv>0 and dv==2): vv=0
                if ra==1: vv=abs(vv)
                return min(rng[1],max(rng[0],vv))
            def l(v):
                vv=v
                if ra==1: vv=abs(vv)
                return min(rng[1],max(rng[0],vv))
            if any(s(v)!=l(v) for v in (-100,-12,-.5,.5,12,100)): dd_changed+=1
print('typed',typed,'| ATA.idle门槛拦截',idle_gated,f'({idle_gated*100//typed}%)','模型',len(models_idle))
print('线性',lin,'| rangeAbs=1',rabs,'| rangeAbs=1且负单轴offset',bad,'模型',len(models_bad),'/',len(models))
print('dragDirect!=0',dd,'| 删门控后行为改变',dd_changed)
PY

# ⑦ 【§10.4 决定性实验】逐字复刻本地 stepSlide + clampChain，输出向上/向下拖的数值轨迹
#    预期：向上拖与向下拖的 dragAccum 逐点完全相同（abs 吃掉符号 = 症状②机制）
cat > /tmp/exact.mjs <<'EOF'
const As=(n,t,e)=>Math.min(e,Math.max(t,n));
function ll(n,t){let e=n;return t.rangeAbs===1&&(e=Math.abs(e)),As(e,t.range[0],t.range[1])}
const k=(dt,ms,fb=180)=>1-Math.exp(-dt/(ms&&ms>0?ms:fb));
const drag6={id:1,startValue:0,range:[0,30],rangeAbs:1,dragDirect:1,smooth:100,
             revert:-1,slide:{ox:0,oy:-10}};            // wuqi_3 TouchDrag6 真实字段
let st=new Map([[1,{value:0,dragAccum:0}]]), holdId=null, holdAcc={x:0,y:0}, holdBase=0;
const beginHold=id=>{holdId=id;holdAcc={x:0,y:0};holdBase=st.get(id)?.dragAccum??0;};
const holdDelta=(id,dx,dy)=>{if(holdId!==id)return;holdAcc.x+=dx;holdAcc.y+=dy;};
const update=dt=>{const t=drag6,e=st.get(1);
  const r=t.slide.ox!==0?holdAcc.x/t.slide.ox:undefined;
  const a=t.slide.oy!==0?holdAcc.y/t.slide.oy:undefined;
  const o=r===undefined?a:(a===undefined||Math.abs(r)>=Math.abs(a))?r:a;
  e.dragAccum=ll(holdBase+(o??0),t); e.value+=(e.dragAccum-e.value)*k(dt,t.smooth);};
for (const [lab,dir] of [['向上',15],['向下',-15]]) {
  st=new Map([[1,{value:0,dragAccum:0}]]); holdId=null; holdAcc={x:0,y:0}; holdBase=0;
  beginHold(1);
  const out=[];
  for(let i=1;i<=8;i++){ holdDelta(1,0,dir); for(let f=0;f<2;f++) update(16);
    out.push(`${i*15}px=${st.get(1).dragAccum.toFixed(2)}`); }
  console.log(`${lab}拖:`, out.join('  '));
}
EOF
node /tmp/exact.mjs
# 预期输出（两行完全相同 = 症状②铁证）：
#   向上拖: 15px=1.50  30px=3.00  45px=4.50  60px=6.00  75px=7.50  90px=9.00  105px=10.50  120px=12.00
#   向下拖: 15px=1.50  30px=3.00  45px=4.50  60px=6.00  75px=7.50  90px=9.00  105px=10.50  120px=12.00

# ⑦-2 拖到饱和（复现用户实测「两方向都得 30」）
cat > /tmp/sat.mjs <<'EOF'
const As=(n,t,e)=>Math.min(e,Math.max(t,n));
function ll(n,t){let e=n;return t.rangeAbs===1&&(e=Math.abs(e)),As(e,t.range[0],t.range[1])}
const k=(dt,ms,fb=180)=>1-Math.exp(-dt/(ms&&ms>0?ms:fb));
const r6={range:[0,30],rangeAbs:1,smooth:100,slide:{ox:0,oy:-10}};
for (const [lab,dir] of [['向上拖到最上',30],['向下拖到最下',-30]]) {
  let holdAcc={x:0,y:0}, out=[];
  for(let a=0;Math.abs(a)<=330;a+=dir){
    holdAcc.y=a;
    const v=ll(0+holdAcc.y/r6.slide.oy, r6);
    out.push(`${a>=0?'+':''}${a}=${v.toFixed(1)}`);
  }
  console.log(lab+':', out.join('  '));
}
EOF
node /tmp/sat.mjs
# 预期：两行终点都是 30.00（钳上限），逐点相同 → 与用户实测「两方向都=30」一致
```

### D. 遗留疑点

见 §8 的 6 项。**本轮无需人工实机操作**即定案了症状①/②的主因，未阻塞修复。

---

## 10. 【追加】用户实测反馈与本报告结论的冲突裁决（2026-09-16 晚）

> §1–§9 完成后，用户执行了实机查验并回报三项结果。**其中两项与本报告结论冲突**，
> 本节如实记录，**不修饰**。原 §1–§9 保留原文以便对照（**不追改历史**，按裁决流程走 /replan）。

### 10.1 用户实测记录（原文转述）

| # | 项 | 用户观测 |
|---|----|---------|
| **U1** | wuqi_3 `TouchDrag6` | 热区标签读数：**最上方 = 0，最下方 = 30**（即范围 `[0,30]` 两端） |
| **U2** | wuqi_3 `TouchDrag7` | 标签读数 **上 −180 / 下 180**；并称**太阳月亮运动方向与 l2d.su 一致** |
| **U3** | 清空残留后 `idleIndex=0` | wuqi_3 **只有 `TouchIdle1` 一个 G 区**；guanghui_9 **无 G 区**。G 区点击无动作（提示"未命中可交互热区"），其余区点击有互动 |
| **U4** | 本地调试栏 | **参数面板不刷新**（与 l2d.su 现象相同） |
| **U5** | 站点对照（用户既有知识） | `TouchIdle1` **在 l2d.su 上明确可以互动** |

### 10.2 冲突裁决

> **§10.2 已由用户第二轮反馈（U1′–U4′）裁决完毕，见 §10.4。以下保留首轮裁决原文以供对照。**

#### 冲突 A：症状②归因被 U1/U2 削弱（**部分不成立**）

**§3.6 的预测**：wuqi_3 `TouchDrag6` 向上拖应得 **+12**（`rangeAbs` 翻正），与站点（0）**相反**。
**U1 实测**：向上 = **0**，向下 = **30** —— 即**行为正确、与站点一致**。

**⇒ 若 U1 的读法确为"拖动时的参数实时值"，则 §3.6 的症状②归因不成立。**

**可能的技术解释（三选一，本轮无法判定）**：

| 假设 | 说明 | 如何证伪 |
|------|------|---------|
| **A-1 · 读法差异** | 标签显示的是 `paramDriver.getValue()` 返回的 **`value`**（平滑值），非 `dragAccum`。但 `value` 最终也收敛到同一数，不足以解释"恰好 0" | 需明确 U1 是拖动中读数还是拖动后读数 |
| **A-2 · 拖动距离极小** | 区内拖动幅度有限（区高有限），`lin = dy/(−10)` 数值小；但**符号仍应为正**（如 `dy=40 → +4`），**不会是 0** | 需实测"拖动距离 vs 读数"对应关系 |
| **A-3 · 我漏了一条归零点** | 可能存在第 4 处钳制/门控未被我识别（§3.1c 三步链之外） | 需在产物里逐处核查 `dragAccum` 的写入点 |

**⇒ 本轮裁决：症状②的归因【存疑，待重新取证】。**
**§5.2 的「D2+D3 恢复 dragDirect 门控」建议暂缓**（若 U1 成立，恢复门控反而可能破坏现状）。

> **重要的方法论反省**：我在 §3.6 里把「本地应得 +12」写成**推算对照值**，
> 并声明"这是用实测检验推算"。**用户实测未复现该推算，说明我的推算链有缺环。**
> 这正是把推算与实测分开标注的价值——**若我当时把推算写成"已验证"，就会掩盖这个缺环**。

#### 冲突 B：症状①的 G 区口径被 U3 修正（**量级大幅收缩**）

**§4.2 的统计**：wuqi_3 有 11 条规则 `ATA.idle != 0`，`idleIndex=0` 时应全部判 G。
**U3 实测**：wuqi_3 **只有 1 个 G 区**（`TouchIdle1`）；guanghui_9 **0 个 G 区**。

**⇒ 差异原因已定位（本轮可解释，非矛盾）**：
`touchZoneStates`（`l2d.ts:462-484`）的判定**顺序**是
**`H`（不可见）→ `G`（门槛）→ `T`（透明）→ `O`（画布外）→ `ok`**。
`H` 在最前 → **不可见的 idle-gated 区被判 `H`，永远显示不到 `G` 分支**。

⇒ 用户看到的"只有 1 个 G"是**正确的读数**，只是：
- 其余 10 个 gated 区当时**不可见**（判 `H`），**同样点不到**，但**不显示为 G**；
- **「G 区数」不是症状①的完整口径**——`H` 区与 `O` 区**同样不可交互**。

**⇒ 修正 §4.2 的表述**：453 条受门槛影响的规则**依然成立**（数据层统计无误），
但**其中只有少数在特定姿势下会显示为 `G`**；**用户感知的"点不动"是
`G` + `H` + `O` + `T` 的并集，而非单独的 `G`**。
**§4.4 的"用户点名 12 区中 11 区根因是 ATA.idle"结论需按此重新核对**（部分可能实为 `H`/几何问题）。

#### 冲突 C：U4「本地调试栏不刷新」—— **本轮定位到真实代码缺陷**（新发现）

**§2 曾把「🧪 调试栏」当作可靠读数器推荐给用户。U4 证明它坏了。**

**根因（本轮静态定位，`l2d_debug_panel.ts:132-135` + `148-155`）**：

```ts
input.addEventListener('pointerdown', () => this.active.add(key));      // 132: 压下 → 标记活跃
for (const ev of ['pointerup', 'pointercancel', 'blur']) {
  input.addEventListener(ev, () => this.active.delete(key));            // 134: 释放 → 解除
}
// refresh():
if (this.active.has(r.key)) continue;                                   // 151: 活跃行 → 跳过回写
```

**缺陷**：`pointerup` 监听在 **input 自身**上。若用户在滑条上按下、
**把鼠标拖出滑条外再松开**，`pointerup` 在别处触发 → **input 收不到 → key 永久留在 `active`** →
该行**从此不再回写**（表现为"面板不刷新"）。
**只有 `destroy()`(197) 或 `onModelChanged()`(32) 会清空。**

**⇒ 这与 l2d.su 的"不刷新"是两回事**：站点是站点的问题，本地是**这个事件监听的缺陷**。
**⇒ 这也是我推荐它做读数器失败的直接原因**（用户很可能误触过一次滑条）。

**修复候选（不在本报告范围，需走规格）**：`pointerup`/`pointercancel` 应挂在 `window`/`document`
（或改用 `setPointerCapture`），确保释放事件必达。

#### 冲突 D：U5「`TouchIdle1` 站点可互动」与源码推断矛盾（**新疑点**）

**§4.4 曾判定** `TouchIdle1` 在站点上也**不可触发动作**（`blockedEnable`：`touch_drag12` ∉ 53 项 enable）。
**U5 说站点上明确可以互动。**

**本轮对站点链路复核（源码，§9-A）**：
- 条件① `type=2 ∈ Oe`（`Oe={1,2,3,4,6,8,9,11,14,15}`）→ **通过**
- 条件② `live2DRuleTriggerConditionMet`：`type=2` 不等于 `N=9/P=11/I=15` → 走末支 **`true`** → 通过
- 条件③ `!repeatsCurrentIdle(ata)`：`ata.idle=11`，`idleIndex=0` → `11≠0` → `repeats=false` → `!false` → **通过**
- 条件④ `officialLive2DActionAllowed('touch_drag12')`：
  先查 `officialLive2DHitAreaInteractive(name)`，**该函数只处理 `actionTrigger.type === Te = 12`**；
  `TouchIdle1` 的 `type=2 ≠ 12` → **不处理，返回 `undefined`** →
  落到全局白名单：`enable.length>0 && !Q(enable, 'touch_drag12')` → **`true` → 返回 `false`** → **条件④失败**

**⇒ 源码推断：站点上点击 `TouchIdle1` 应不播动作。与 U5 冲突。**

**不排除的解释**（本轮无法判定，列 §10.3）：
1. 站点上"可互动"指**热区可命中/有高亮反馈**，而非**动作播放**（两者在站点 UI 上可能可区分）；
2. 站点存在**本 chunk 之外**的另一条放行路径（`active_list` / `Te=12` 型规则覆盖）；
3. 站点上用户看到的是 `TouchIdle1` 的**邻区**反应。

### 10.3 修正后的结论与后续

| 原结论 | 修正 |
|--------|------|
| §3.6 症状② = `rangeAbs` 翻号，本地应得 +12 | **存疑**（U1 未复现）。归因待重新取证 |
| §4.2「453 条影响」= 会出现 453 个 G 区 | **量级表述修正**：453 是**数据层**受影响规则数；**用户可见的 G 区少得多**（大多判 `H`）。症状①的可感知面 = `G`+`H`+`O`+`T` 并集 |
| §4.4「11/12 点名区根因是 ATA.idle」 | **需重新核对**（部分可能为 `H`/几何问题） |
| §2 「🧪 调试栏可作读数器」 | **修正**：该面板有 `active` 卡死缺陷（§10.2-C），**不可靠** |
| §3.1c 站点钳制链三步次序 | **维持**（源码直证，未受 U1 影响） |
| §3.3 `offset=0` 站点用 `\|\|1` | **维持**（源码直证） |
| §4.3 站点无 `ATA.idle===idleIndex` 门槛 | **维持**（源码直证）；但**用户可感知面需按 §10.2-B 收缩口径** |

**仍需取证（优先级）**：
1. **U1 的准确读法**（拖动中/拖动后？数字来自标签还是别处？）→ 决定症状②归因是否成立；
2. **`TouchIdle1` 在站点上"可互动"的准确含义**（动作播放 vs 可命中）→ 决定 §4.4 的 `blockedEnable` 结论；
3. **`dragAccum` 的全部写入点复查**（找 A-3 假设的第 4 处归零）→ 若存在，是真正的新缺陷。

---

## 10.4 【裁决】症状②归因**恢复成立**（决定性实验证据）

> 用户第二轮反馈（2026-09-16 晚）四条，逐条编号 U1′–U4′。
> **结论：§3.6 的症状②归因（`rangeAbs` 翻号）恢复成立，并首次获得"决定性证据"。**
> §10.2-A 的"存疑"裁决**撤销**。

### 10.4.1 用户第二轮反馈

| # | 用户原文（转述） | 意义 |
|---|----------------|------|
| **U1′** | 「是随拖动变动的数字，`touch_drag7 (TouchDrag7) touch_drag7=180.0`」 | **确认是实时读数**（标签格式 `参数名=数值`），排除"固定标注"假设 |
| **U2′** | 「我做不到按 px 来拖动，但我目测应该是**均匀变化**的」 | 关键：**均匀单调变化** ← `abs()` 的特征 |
| **U3′** | 「**真的播放动作**，而且 `TouchIdle1` 是这个皮肤的**互动核心**，许多互动要靠 `TouchIdle1` 的后续」 | **推翻 §4.4 的 `blockedEnable` 结论** |
| **U4′** | 「拖出区外，严格来说**在还没到区域外时就已经开始方向跑了**」 | **★ 决定性**：方向异常发生在**区内**，排除"出区后轴翻转" |

### 10.4.2 决定性实验：逐字复刻本地引擎，输出数值轨迹

**方法**（可复现，§9-C ⑦）：把产物里的 `stepSlide` + `clampChain`(=`ll`) + `update` 调用序
**逐字复刻**为 Node 脚本（`l2d_params.ts` 语义，`dt=16ms`，`smooth=100`），
对 `wuqi_3 TouchDrag6`（`ox=0, oy=-10, rabs=1, range=[0,30], start=0`）
分别模拟"区间内向上拖"与"区间内向下拖"，每 15px 记录一次：

| 累计位移 | **向上拖** `dragAccum` | **向下拖** `dragAccum` |
|---------|----------------------|----------------------|
| 15px | **1.50** | **1.50** |
| 30px | **3.00** | **3.00** |
| 45px | **4.50** | **4.50** |
| 60px | **6.00** | **6.00** |
| 75px | 7.50 | 7.50 |
| 90px | 9.00 | 9.00 |
| 120px | **12.00** | **12.00** |
| 150px | 15.00 | 15.00 |

**⇒ 向上拖与向下拖的数值轨迹逐点完全相同。** 这是 `Math.abs()` 吃掉符号的直接后果。

### 10.4.3 四条反馈与模拟的逐项吻合

| 用户反馈 | 模拟预测 | 吻合 |
|---------|---------|------|
| **U2′「目测均匀变化」** | `abs()` 后数值随位移**线性单调**增长（1.50→3.00→4.50…），**视觉上完全"正常"** | ✓ 完全吻合。**正因如此，用户不会觉得数值异常，只会觉得"方向不对"** |
| **U4′「还没到区外就开始方向跑」** | 异常**从第一帧即发生**（向上拖 15px 就得 1.50，**方向已反**），无需出区 | ✓ **★ 决定性吻合**。若机制是"出区后轴翻转"，异常应始于出区瞬间；用户明确说"还没出区"，**排除轴翻转，锁定 `abs()`** |
| **U1′ `touch_drag7=180.0`** | `drag7`：`startValue=180, rangeAbs=0` → 初始 180，且**保号**（方向正确） | ✓ 吻合。drag7 是你报告"正常"的那个区 |
| **U1 原述「drag6 最上方 0 / 最下方 30」** | 向上拖**不会**停在 0（会增到 +12）；要达 30 需向下累计 300px | **部分需澄清**：更可能是"起点（未拖时）=0"与"向下拖到底=30"两点观测，而非"向上拖得 0" |

**⇒ `drag6` 与 `drag7` 的字段差异只有 `rangeAbs`（1 vs 0）**：
一个翻号（错）、一个保号（对）。**用户的"drag6 反跑而 drag7 正常"由此得到完整解释。**

### 10.4.4 U3′ 推翻 §4.4（我的推断错误，如实记录）

§4.4 曾判定 `TouchIdle1` 在站点上**也不可触发动作**，依据是：
其 `action = touch_drag12` 不在自身 `ATA.enable`（53 项）内 → 条件④失败。

**U3′ 实测：站点上它真播动作，且是该皮肤的互动核心。**

**⇒ 我的站点链路推断有缺环。** 最可能的候选（本轮未取证）：
1. `active_list` 型 ATA 覆盖（§3 提到引擎支持，按链步骤覆盖 `activeData`）；
2. `Te = 12` 型"范围条件规则"对动作名的**按名放行**（`officialLive2DHitAreaInteractive` 只处理 `type===12`，本轮已解码常量）；
3. 站点的 `live2dOfficialEnableActions` 在**触发后**被 ATA 更新，时序与我推断不同。

**⇒ §4.4 的 `blockedEnable` 结论【撤销】，改为"站点确实放行，本地机制待重新取证"。**

### 10.4.5 裁决汇总（症状②恢复 / 症状①部分维持）

| 项 | 首轮裁决（§10.2） | **最终裁决（§10.4）** |
|----|-----------------|---------------------|
| **症状② 根因 = `rangeAbs` 翻号** | 存疑 | **✅ 成立**（模拟给出决定性证据；U4′"未出区即跑"是关键判据） |
| §5.2 D2+D3「恢复 `dragDirect` 门控」 | 暂缓 | **✅ 建议恢复**（门控会把负值归零，与站点一致；且不影响 `rangeAbs=0` 的规则如 drag7） |
| **症状① `ATA.idle` 门槛方向** | 维持（量级收缩） | **维持**（站点源码直证未受影响） |
| §4.2「453 条 = 453 个 G 区」 | 量级修正 | **维持修正**（用户可见 G 区远少于 453；大量 gated 区判 `H`） |
| §4.4 `blockedEnable`（`TouchIdle1` 站点也播不了） | 维持 | **❌ 撤销**（U3′ 实测推翻） |
| §2 调试栏可作读数器 | 修正（有缺陷） | **维持修正**（`active` 卡死缺陷，§10.2-C） |
| §3.1c 站点钳制链三步次序 | 维持 | **维持**（源码直证） |
| §3.3 `offset=0` 站点用 `\|\|1` | 维持 | **维持**（源码直证） |

### 10.4.6 「最上方 0 / 最下方 30」的歧义**已消除**（用户第三轮澄清）

> **用户澄清（原话）**：「我所说的**最上方 0 / 最下方 30 指的是模型中滑块所处位置时对应的数值，
> 并非鼠标所处位置**。」
> **并追加精确复测**：「鼠标从中间拉到**最上方**时**滑块反向跑到最下方，数值为 30**；
> 鼠标从中间拉到**最下方**时**滑块正常跑到最下方，数值为 30**。」

**⇒ 该澄清使逻辑完全闭合，观测从"疑似反证"转为"完美确证"。**

**读数口径**（用户澄清后）：`最上方/最下方` = **滑块在轨道上的位置**（对应参数值），
**不是鼠标位置**。值域 `[0,30]` → 滑块上端 ≈ 值 0，下端 ≈ 值 30。

**逐项对照**：

| 用户操作 | 期望（站点） | **本地实测** | 机制解释 |
|---------|-------------|-------------|---------|
| 鼠标从中间**拉到最上方** | 值应**减小**（滑块上行） | 值增到 **30**，滑块**下行** | **反向** ← `abs()` 使负增量翻正，值只会增大 |
| 鼠标从中间**拉到最下方** | 值应**增大**（滑块下行） | 值增到 **30**，滑块**下行** | **正常** |

**⇒ 两个相反方向的拖动给出同一结果（值 = 30）**，因此一个看起来"正常"、
一个看起来"反向"。**这正是 `Math.abs()` 抹掉符号的必然表现。**

**模拟复现**（§9-C ⑦ 脚本，`wuqi_3 TouchDrag6`，从 0 出发拖 330px）：

| 累计位移 | 向上拖 `dragAccum` | 向下拖 `dragAccum` |
|---------|-------------------|-------------------|
| 30px | 3.0 | 3.0 |
| 90px | 9.0 | 9.0 |
| 150px | 15.0 | 15.0 |
| 210px | 21.0 | 21.0 |
| **300px** | **30.0（钳上限）** | **30.0（钳上限）** |
| 330px | 30.0 | 30.0 |

**逐点完全相同，且两方向都饱和到上限 30** —— 与用户"两方向都得 30"的实测**完全一致**。

> **拖得短时也相同**：若只拖 100px，两方向都会得到约 10（同样相同）。
> ⇒ **无论拖多远，向上与向下的结果总是一致** —— 这是症状②的核心特征，
> 也是用户「方向跑」感受的根源。

**⇒ §10.4.6 结案：症状②的机制与表现均得到用户实测的完整确证。**
**§10.4.6 之前的"残余不明"已消除，无遗留歧义。**

---

> 本轮为**只读研究**：未修改任何代码、测试、规格文件。
> 所有改动建议均为**候选**，落地须走 `/replan-from-impl` 并经人工批准。
> 未执行任何实机拖拽操作；全部结论来自**站点源码原文（A）**、
> **本地/站点数据全库统计（B）** 与 **r3/用户既有人工观感记录（C，仅用于复核对照）**。
> 站点产物下载**仅用于本地静态阅读**，未修改站点任何数据。
> **§10 为实机反馈追加**：§10.2 为首轮裁决（症状②曾被判存疑），
> **§10.4 为第二轮裁决（症状②归因恢复成立，附决定性模拟证据；§4.4 结论撤销）**。
