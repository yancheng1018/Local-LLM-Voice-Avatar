# 研究报告 · frontend-minimal Live2D 动作链条修正（四模型症状归因）

> 2026-09-17 只读研究（未改任何代码/测试）。
> 2026-09-29 distill-b3：可复用结论已提炼入 `minimal-frontend-live2d.md`「动作链条域结论提炼」节；本文保留作证据链。
> **本轮新增决定性证据源**：站点引擎 JS 成功下载并**完整反混淆**（`modelRuntime-BDk3g7Pb.js`，201,926 字节），
> 逆向记录见 `spec-l2dsu-engine.md`（同批产出，含可复现解码方法与归档产物清单）。
> **证据等级**：A=站点源码直证 · B=数据直证（可脚本复现）· C=用户观感 · D=推断。
> 症状编号沿用用户报告原文（G=guanghui_9、S=shi_3、X=xinnong_6、F=feiteliedadi_3）。

## 1. 结论速览

> **状态更新（2026-09-17 晚）**：T1~T8 人工实测 + 本地浏览器复现已完成。
> **G1/G3/T6 的真根因已定案**：参数写入挂点被框架帧末 `loadParameters()` 还原（§5.0），
> 不是「参数算错」而是「参数完全无法影响模型」。下表主因列已按实测定案更新。

| 症状 | 根因分类 | 主因（证据等级） |
|------|---------|----------------|
| S1「初始缺 TouchIdle27」 | **数据错配（非代码，系统性问题）** | 本地 `shi_3/touch.json` 实为站点 **shi_2** 皮肤数据（33 条），站点 shi_3 皮肤有 **71 条**（含 TouchIdle1~45）；**全库普查 9/36 模型存在同类错配**（B）。**T4 实测确认**：站点初始即显示 TouchIdle27（C） |
| S2「TouchIdle1 后旧热区不消失、新热区组不出现」 | **同上（数据错配）** | 同上：本地只有 TouchIdle1/2 两条 Idle 规则，站点有 45 条（B）。**T4 实测**：站点 TouchIdle1 后出现 TouchIdle2/32/17/19/26/8/37（C） |
| S3「touchhead 后 touch_drag10 从 0.0→4.0」 | **站点同款行为，非缺陷** | **T3 实测：站点同样变成 4.0**，且站点模型也无变化——用户指出站点面板与模型脱钩。本地模型会变化是因为**本地参数真正生效**（写入挂点不同）。故此项**不是本地 bug**（C+A） |
| G1「drag3 点击后 drag4/5 半显、无热区、不可互动」 | **实现缺陷：参数写入失效** | **§5.0 定案**：`ParamDriver` 挂点 `beforeModelUpdate` 的写入被同帧 `loadParameters()` 还原 → 参数恒 0 → drag4/5 停在画布外（x≈−9500）不可交互（A+B） |
| G2「touchhead 播放中点 drag3 → 全屏无热区，死锁」 | **实现缺陷：参数写入失效 + 门槛** | **T7 实测**：`isPlayingTouchAction=false`（门控已清）、`idleIndex=0`、全屏仅 TouchDrag2/TouchBody 为 ok，其余 O/G。非真死锁，是**模型几何在动作后漂移**（drag 区全部移出画布 O）+ 白名单 G（B+C） |
| G3「站点三档模式（TouchIdle17 / 4 / 1+22）」 | **实现缺陷：参数写入失效** | **T2 实测修正**：站点实为**连续渐变**（17→4→1+22→4→17），非三档跳变；本地因参数不生效完全无此表现（C+A） |
| X1「未点击自动进 idle10」 | **宿主库默认行为未关闭** | pixi-live2d-display 自带 `groups.idle="Idle"` 自动随机播放；xinnong_6 的 `Idle` 组含 15 条动作。**T8 实测确认**：静置 3 分钟出现 14 次自动动作，**`idleIndex` 恒为 0**（链状态未变）→ 纯库行为（A+B+C） |
| F1「touch_drag6 无法互动」 | **站点同款行为，非缺陷** | **T5 实测**：站点初始**根本没有 TouchDrag6 热区**（点 TouchDrag1 后才出现）→ 本地「不可互动」与站点一致，无需修（C） |
| F2「drag3 点击后 drag4 短暂弹出即复位、drag3 变不可互动」 | **实现缺陷：缺 type104 + 参数写入失效** | 站点 type104（`rel.idle===idleIndex` → 设 relation 参数）维持画面。**T5 实测**：站点 drag3 后剩 TouchDrag2/TouchDrag4 且长时间保持、drag3 消失不可再点——**与本地「短暂弹出即复位」不同**，本地缺 type104 维持（A+B+C） |

**一句话结论（实测修正版）**：四模型的症状分三类——①**数据错配**（shi_3 等 9 个模型，换数据即解）；
②**宿主库 idle 未关**（xinnong_6，一处配置）；③**参数写入失效**（G1/G2/G3/F2 的共同根因，§5.0 定案：
`beforeModelUpdate` 挂点被同帧还原）。第 ③ 类是最高优先级，修复后 G1/G3 与 F2 的「维持」部分应一并解决。
另有 S3/F1 两项经实测确认**与站点行为一致，不是缺陷**。

## 2. 症状清单与复现条件（用户报告原文对齐）

| # | 模型 | 现象 | 用户补充 |
|---|------|------|---------|
| G1 | guanghui_9 | 初始点 touch_drag3 后应出现 touch_drag4/5；实际只「隐约出现滑块」，无热区、不可互动 | 已澄清「滑块」=**模型画面本身** |
| G2 | guanghui_9 | touchhead 动作播放中点 touch_drag3 → touchhead 结束后**屏幕无任何热区**，死锁 | — |
| G3 | guanghui_9 | l2d.su 上 drag3 点击后出现 drag4/5，且人物身上热区随 drag4 拖拽值呈**三档**（TouchIdle17 / TouchIdle4 / TouchIdle1+22） | 用户裁定：**属链条必还原部分** |
| S1 | shi_3 | 初始未出现应有的 TouchIdle27 | — |
| S2 | shi_3 | 点 TouchIdle1 后旧热区不消失、应有的 TouchIdle2/32/17/19/26/8/37 不出现 | 对照 l2d.su |
| S3 | shi_3 | touchhead 后 touch_drag10 从 0.0→4.0 | — |
| X1 | xinnong_6 | 频繁未点击自动进 idle10 | 已澄清：**清空 localStorage/全新加载仍复现** |
| F1 | feiteliedadi_3 | touch_drag6 无法互动 | — |
| F2 | feiteliedadi_3 | drag3 点击后 drag4 短暂弹出即复位，drag3 随之不可互动；drag9 类似 | l2d.su 正确行为=只剩 drag2/drag4 且不复位 |

## 3. 站点行为基准（l2d.su 对照，全部 A 级源码直证）

> 完整逆向见 `spec-l2dsu-engine.md`。以下仅列与四症状直接相关的机制。

### 3.1 参数权威层（`setOfficialLive2DParameterTarget` + 每帧 Tween）

站点加载时 `applyLive2DOfficialInitialParameters`：遍历**全部规则**，把 `rule.parameter → startValue`、
`relationParameter[].name → start/startValue` 写入 `live2dOfficialParameterTargets`；随后每帧（`beforeModelUpdate` 挂点）
`updateLive2DOfficialParameterTweens()` 对表内每个参数**强制回写**。

**时序关键**：库的 `InternalModel.update()` 顺序为 `motion.update()`（写动作曲线）→ … → `emit('beforeModelUpdate')`
（站点写参数）→ `model.update()`。因此**站点参数永远压过动作曲线**；本地同一挂点写入，但**只覆盖注册进 `ParamDriver` 的参数**。

### 3.2 type12 = 参数区间全局裁决（`live2DExtendActionDecision`）

```js
at.type===12 && lo<当前参数值<=hi  →  ignore 列表命中即拒 / enable 列表命中即放行（优先于全局白名单）
```
guanghui `23703161`：`touch_drag3 ∈ (0.01,10]` 时禁用 `main_1..5/mission/mission_complete/complete/login/home/mail/
touch_body/touch_head/touch_special/wedding` 共 15 个动作。**本地完全未实现**。

### 3.3 ATA 应用（`applyLive2DActiveData`）三处与本地不同

1. **形态A 用「新 idle」查表**：站点先 `Ue(ata.idle, 当前idle, repeat_flag)` 得目标 idle，再用它查 `idle_enable/idle_ignore`；
   本地 `l2d_touch.ts:143-144` 用**应用前的** `this.idleIndex` 查表 → 语义错（当前数据样本少，未暴露）。
2. **`revertIdleIndex` 复位**：idle 变化时对 `revertIdleIndex===1|'1'|数组含该idle` 的规则执行
   `resetLive2DTouchRuleParameters`（`parameter→startValue`、relation 参数→start）。本地未实现（spec §11 遗留）。
3. **`active_list[si]` 按链步覆盖 ATA**：本地仅透传 action（`l2d_touch.ts:20` 注释自认 stage3 透传）。

### 3.4 链步进是**循环**且冷却**先记**

`triggerLive2DTouchArea`：链步 `(si+1)%list.length`（无终止步）；`limitTime` 冷却**在白名单判定之前**登记
（被拒也吃冷却）。本地 `l2d_touch.ts:83-86` 冷却仅在 dispatch 成功后记；body 链走完进 60s 冷却（本地偏离 D2）。

### 3.5 热区提示显隐（`officialLive2DHitAreaHintVisible`）

空闲时按 `tips.idleBlackList[].idle.includes(当前idleIndex)` 隐藏；播放中按 `tips.animWhiteList[].white_list` 显示。
**这是「热区随状态增删」的正式机制**，本地未实现（本地叠加层只按可交互/几何判定着色）。

### 3.6 可见性判定含 `getDrawableDynamicFlagIsVisible`

站点 `isLive2DDrawableVisible`：**先用 `getDrawableDynamicFlagIsVisible`**，再判 `opacity<=0.01`。
本地 spec §4 记「位义未核实故不启用」，仅用 opacity。

### 3.7 宿主库 idle 自动播放（本地栈特有）

`pixi-live2d-display` 默认 `groups.idle="Idle"`，动作结束后若 `shouldRequestIdleMotion()` 则
`startRandomMotion("Idle", IDLE)`。**xinnong_6 的 `Idle` 组有 15 条**（idle、idle1~idle13、idle16）→ 随机播。
本地自研的 `playIdleOnce()` 走小写 `idle` 组（站点语义），**没有关掉库的这条路径**。

## 4. 现实现四路径梳理（含行号）

| 路径 | 位置 | 职责 | 与站点的结构差 |
|------|------|------|---------------|
| 规则注册 | `l2d.ts:496-603` | 按 `drawAbleName` 注册空间热区；原始 rules 全量挂 `touchRules` | 缺「全部 parameter 登记进参数层」 |
| 命中判定 | `l2d.ts:316-385`、门槛 `l2d.ts:293-308` | 实时包围盒/可见性/透明度/渲染序 + 门槛 | 门槛缺 type9/11/15 条件与 type12 裁决；可见性缺 dynamicFlag |
| 链状态机 | `l2d_touch.ts:68-184`（resolve/dispatch/applyActive） | ATA 两形态、冷却、白名单、localStorage | 形态A 查表用旧 idle；缺 revertIdleIndex/active_list；链终止非循环 |
| 参数驱动 | `l2d_params.ts:180-206`（update）、`606-643`（toParamRule） | circle/slide/type1,6,7/mode2/type103 | **仅覆盖部分规则**（见 §5.3），非权威层；type104/type5/type13 未实现 |

## 5. 逐症状归因

> **2026-09-17 晚：人工实测（T1~T8）+ 本地浏览器复现已完成**，结论见 §5.0（新根因）与各节「实测修正」。
> 人工操作记录见 `manual_live2d动作链条验证.md`；本轮复现日志见 §5.0.3。

### 5.0 【实测定案】G1/T6 真根因：参数写入挂点被框架帧末还原

**T6 实测**（用户）：点击 touch_drag3 后 `touch_drag3=0.00`、drag4/drag5 仍 `O`（画布外），
无任何滑块出现——**与用户最初报告的「隐约出现滑块」不同**（后者是站点表现或早期版本）。

**本地浏览器复现（我执行，2026-09-17 晚）**：装探针读 `ParamDriver` 内部状态机，点击 drag3 后：

| 读数 | 值 | 说明 |
|------|----|----|
| `ParamDriver.states[23703103].value` | **3.57**（pokeTarget=10） | 驱动器**内部值正常推进** |
| `core.getParameterValueById('touch_drag3')` | **0** | 模型实际参数**恒为 0** |
| `touchZoneStates()` 中 drag4/drag5 | **O**（画布外，x≈−9500） | 绘画件未进入画布 |

**决定性实验**（同参数、不同挂点）：

| 挂点 | 写入后模型读数 |
|------|--------------|
| `beforeModelUpdate`（**本地 ParamDriver 当前挂点**） | **0**（被还原） |
| `afterMotionUpdate`（更早挂点） | **7**（生效） |

**机制**（库源码 `cubism4.es.js:10289-10311`，逐字）：
```js
update(dt, now) {
  this.emit("beforeMotionUpdate");
  const motionUpdated = this.motionManager.update(this.coreModel, now);  // ← 动作曲线写入参数
  this.emit("afterMotionUpdate");
  model.saveParameters();                        // ← 快照当前参数值
  ...eyeBlink/focus/physics/pose...
  this.emit("beforeModelUpdate");                // ← 本地 ParamDriver 在此写入
  model.update();
  model.loadParameters();                        // ← 用快照覆盖，本帧写入被丢弃
}
```
`saveParameters()` 在 `beforeModelUpdate` **之前**执行，`loadParameters()` 在其**之后**执行
→ **在 `beforeModelUpdate` 写入的参数，会在同一帧末尾被 `_savedParameters` 还原**。
`idle.motion3.json` 每帧把 `touch_drag3/4/5` 写为 0（实测 Segments `[0,0,0,8.533,0]`），
故 ParamDriver 的写入每帧都被动作曲线 + loadParameters 联手清掉。

**推论**：
- 这不是「参数值算错」，而是**写入时机错误**——参数**完全无法影响模型**（G1 的「滑块不出现」、
  T6 的「参数恒 0」、G3 的「三档模式无反应」全部由此解释）。
- **站点为何没这个问题**：站点引擎的 `beforeModelUpdate` 挂点是在**它自己的渲染栈**里
  （站点未用 pixi-live2d-display 的 InternalModel 更新循环，或挂点时序不同）；
  且站点面板读数（T3）显示 4.0 但模型不变，说明**站点的面板与模型也是脱钩的**（用户已指出）——
  即：**两边都存在「面板 ≠ 模型」现象，但站点有另一条真正驱动模型的路径**（待补证，见 §8-6）。
- **l2d.ts 的其它写入同受影响**：`attachLipSync` 的口型（`l2d.ts:883-889`）也在同一挂点，
  但口型参数不被动作曲线写（多数模型 LipSync 参数无曲线），故未暴露。

**修复方向**（候选，需人工裁决）：
- **方案 A（推荐）**：把 `attachParamDriver` 的挂点从 `beforeModelUpdate` 改为
  `afterMotionUpdate`（动作曲线之后、`saveParameters` 之前写入，可存活到 `model.update()`）。
  最小改动，与实验验证的生效挂点一致。
- **方案 B**：保留挂点，但在 `beforeModelUpdate` 中同时更新 `_savedParameters`（侵入库内部，不推荐）。
- **方案 C**：改用库的 `motionManager` 参数覆盖机制（若存在）——需进一步逆向。

> ⚠️ 方案 A 的副作用需评估：口型/呼吸/物理等其它 `beforeModelUpdate` 消费者不受影响
> （它们各自参数不同），但**眨眼/物理在 ParamDriver 之后执行**的顺序会变，需实测回归。

### 5.0.2 【实测定案】G1 站点表现与本地差异（T2 结果）

用户 T2 实测（站点 guanghui_9）：
- 点 drag3 → 出现 **TouchDrag5、TouchDrag4、TouchIdle4** 三个热区，**人物身上是 TouchIdle4（不是滑块）**，
  人物左边出现两个滑块（对应 TouchDrag4/TouchIdle4）。
- 拖 drag4 从上到下：**TouchIdle17 → TouchIdle4 → TouchIdle1+TouchIdle22 → TouchIdle4 → TouchIdle17**
  （**连续渐变，非三档跳变**——修正我此前「三档阈值」的推断）。
- 松手不复位。

**修正结论**：站点「三档」实为**参数连续驱动**（drag4 值变化 → 模型美术层平滑切换 TouchIdle* 显示）。
本地因 §5.0 的参数写入失效，**完全无此表现**。

### 5.0.3 复现日志（可复核）

```
# 本地 http://localhost:12393/m/ → guanghui_9，清 localStorage，复位模型
# 点击 TouchDrag3 屏幕坐标 (289, 225)

before: { drag3:0, drag4:0, drag5:0, idle:0,
          zones: TouchDrag1=ok:0.00, TouchDrag2=ok:0.00, TouchDrag3=ok:0.00,
                 TouchDrag4=T:0.00, TouchDrag5=T:0.00 }
after : { drag3:0, drag4:0, drag5:0, idle:0,
          zones: TouchDrag1=O:0.00, TouchDrag2=ok:0.00, TouchDrag3=O:2.37,
                 TouchDrag4=O:0.00, TouchDrag5=O:0.00 }
# ↑ 注意：ParamDriver 内部值 2.37（后续采样 3.57），模型读数恒 0

# 挂点对照实验
beforeModelUpdate 写入 3 → 读回 0
afterMotionUpdate 写入 7 → 读回 7

# drag3 参数扫描（经 beforeModelUpdate 写入）与 drag4/5 可见性
drag3=0    → drag4/5 在 x≈-11800（画布外）T 状态
drag3=2/4/5.81/6/8 → 仍在画布外 O
drag3=9.9  → drag4 x=2186（进入画布）ok
drag3=10   → drag4 x=2329 ok, drag5 x=1800 ok
# ↑ 证明：drag3 需接近 target=10 才能让 drag4/5 进入画布
#   而本地单击 poke 收敛值仅 3.57（因写入失效 + 每次点击后 idle 曲线清零）
```

### 5.1 S1/S2：shi_3 数据错配（决定性，且为系统性问题）

**证据（B）**：站点 `https://l2d.su/data/ships/CN/20516.json`（shipGroupId=20516「狮」）含三个皮肤：

| 皮肤 | prefab | 规则数 | shipSkinId |
|------|--------|--------|-----------|
| 205160 | shi | 0 | — |
| 205161 | shi_2 | 33 | 101170 |
| **205162** | **shi_3** | **71** | 205162 |

本地 `live2d-models/shi_3/touch.json`：**33 条，`shipSkinId: 101170`，id 段 `205151xx`** ——
**与站点 shi_2 皮肤（205161）逐字节同构**，与 shi_3 皮肤（205162，id 段 `205162xx`）完全不同。

站点 shi_3 皮肤规则含 `TouchIdle1`~`TouchIdle45` 与 `TouchDrag1`~`TouchDrag23`；
本地只有 `TouchIdle1`/`TouchIdle2` 两条 Idle 规则、`TouchDrag1/16` 与 6 条同名 `TouchDrag10` 等。

→ **S1（缺 TouchIdle27）与 S2（缺 TouchIdle2/32/17/19/26/8/37 等）直接由数据缺失解释**，
与代码无关；`shi_3` 的模型 motions 里 `touch_idle27.motion3.json` 等**存在**（动作齐全，只缺规则数据）。

#### 5.1b 全库普查：9 个模型存在同类错配（本轮新发现，决定性）

对全部 36 个本地模型，按 `ships-CN.json` 的 `prefab → shipGroupId` 反查站点数据、
筛「有 `live2dTouch.rules` 的 live2d 皮肤条目」后逐字节比对：

**25/36 一致；9/36 错配；2/36 站点无对应规则。**

| 模型 | 站点 shipGroup | 本地数据实际来源皮肤 | 本地规则数 | 站点应有规则数 |
|------|---------------|--------------------|-----------|--------------|
| shi_3 | 20516 | shi_2（205161） | 33 | **71** |
| feiteliedadi_4 | 49902 | feiteliedadi_3（499022） | 12 | **66** |
| feiteliekaer_4 | 40314 | feiteliekaer_3（403142） | 26 | **107** |
| mojiaduoer_4 | 90107 | mojiaduoer_2（901071） | 10 | **87** |
| wuzang_4 | 30510 | wuzang_3（305102） | 33 | **86** |
| ougen_8 | 40303 | ougen_6（403035） | 1 | **47** |
| tiancheng_cv_3 | 30715 | tiancheng_cv_2（307151） | 20 | **44** |
| dafeng_7 | 30707 | dafeng_3（307074） | 2 | **35** |
| guandao_3 | 11802 | guandao_2（118021） | 10 | **24** |
| chaijun_4 | 29903 | （站点该 prefab 无规则） | 17 | 0 |
| shengluyisi_4 | 10213 | （站点该 prefab 无规则） | 54 | 0 |

**错配模式**：9 例**全部**是「本地数据 = 站点同名皮肤的**前一个编号**皮肤」，
且本地 `shipSkinId` 字段如实记录了真实来源皮肤号（如 shi_3 的 `101170`）——
说明**下载脚本当年按近似名/顺序匹配，未校验 prefab 精确相等**，且 `shipSkinId` 校验未做。

**旁证**：`live2d-models/guanghui_9/touch.json.bak`（31 条，`shipSkinId: 207037` = guanghui_7 皮肤）
证明历史上存在过按皮肤号落盘的中间产物。

**影响面**：这 9 个模型的热区集合、链条数据、参数规则**全部错位**——
凡涉及这些模型的动作链条问题，都应先排除数据因素再查代码。

### 5.2 S3：touch_drag10 被动作曲线改写（决定性）

**证据（A+B）**：
- 数据：`shi_3/motions/touch_head.motion3.json` 与 `touch_body.motion3.json` 均含参数曲线
  `touch_drag10`，Segments `[0, 4, 0, 7.317, 4]`（**末值 4**，7.317s 处）；`touch_idle27` 曲线末值亦为 4。
- 站点：`touch_drag10` 是规则 `20516271`（type7 主控，`range [0,4]`, `startValue 0`）的 parameter，
  **进入参数目标表** → 每帧回写 0 → 动作曲线写 4 被覆盖。
- 本地：`l2d.ts:606-643 toParamRule` 对 `205151xx` 的 TouchDrag10 系列（`parameter:'empty'` 或 type2 带 action）
  **一律返回 null** → 该参数不在 `ParamDriver` → 无每帧覆盖 → **动作曲线 4 直接生效**。

→ **S3 根因 = 缺参数权威层**。用户「从 0.0 变成 4.0」的读数与曲线末值 4 精确吻合。

### 5.3 G1/G3：guanghui 参数层与 type12 缺口

**数据事实（B）**：
- `TouchDrag3`（23703103）：`{circle:true, target:10, type:2}`，`range [0,10]`，`rangeAbs 1`，`revert -1`，
  `revertActionIndex 1`，`revertIdleIndex "1"`，`limitTime 0.1`，**无 ATA**。
- `TouchDrag4`（23703104）：`actionTrigger: null`，`offsetY: -15`，`range [-10,30]`，`revert -1` → **slide 型**。
- `TouchDrag5`（23703105）：`actionTrigger: null`，`offsetY: -20`，`range [0,30]`，`rangeAbs 1`，`dragDirect 1` → slide 型。
- type12 规则 `23703161`：`touch_drag3 ∈ (0.01,10]` → ignore 15 个动作（§3.2）。

**站点行为链**：点 drag3 → circle 型参数规则（`at.circle`）把 `touch_drag3` 目标设为 10（或翻转回 0）
→ **参数目标表持有 10，每帧回写** → 模型美术层据 `touch_drag3` 值显示 drag4/drag5 滑块；
同时 type12 裁决生效，`touch_head/touch_body/touch_special/main_*` 等动作被禁 → 屏幕提示只剩 drag/idle 类。
拖动 drag4 → slide 型 `touch_drag4` 参数在 `[-10,30]` 内变化（`revert:-1` 保留），**参数目标表每帧维持** →
模型据该值切换 TouchIdle* 绘画件显隐 → 用户观察到的「三档模式」。

**本地缺口（实测修正）**：原判「缺参数权威层」**方向正确但不够根本**——真正的问题是
**参数写入挂点被同帧还原**（§5.0），故连「drag3 自身的 circle 值」都没进到模型里。
type12 裁决与 type104/type5 确为缺口（阶段 B/C），但在阶段 0 修复前它们不是主要症状来源。

**「半显」的实测定案**：本地**根本没有任何滑块出现**（T6 + 我的复现：drag4/5 停在画布外 x≈−9500，
`touchZoneStates()` 显示 `O`）。用户最初报告的「隐约出现滑块」应来自**站点**观察（T2 实测站点有滑块）。
本地 `hitZoneAt`（`l2d.ts:331`）对画布外区（`O`）直接剔除 → 「不可互动」。

### 5.4 G2：实测为「几何漂移 + 白名单」，非死锁

**T7 实测**：touchhead 播放中点 drag3，动作结束后：
`isPlayingTouchAction=false`（门控已正确清除）、`idleIndex=0`、
`touchZoneStates()` 中仅 `TouchDrag2=ok`、`TouchBody=ok`，其余全为 `O`（画布外）或 `G`（白名单拒），
叠加层只剩上方两个区的下边框——**与用户「屏幕中无任何热区」一致**。

**判定**：① **不是死锁**（门控与链状态都正常）；② 原因是 touchhead 动作把模型姿态改变后，
**绝大多数热区绘画件被投影到画布外**（`O`），而少数仍在画布内的区被 `ATA.idle`/白名单判为 `G`；
③ 本地因参数写入失效（§5.0），模型无法通过参数回到「可交互姿态」，故用户感觉「卡住」。

**修复后的预期**：阶段 0 修复后，touchhead 结束会按 ATA 把参数设回可交互状态（`revertIdleIndex` 等机制，
阶段 B/C），热区应恢复。**该预期需在阶段 0+ 修复后按 §7 复测**。

### 5.5 X1：宿主库 idle 自动播放（决定性，T8 实测确认）

**证据（A+B）**：`pixi-live2d-display/dist/cubism4.es.js:10106` `groups = { idle: "Idle" }`；
`:8729` 动作结束且无后续时 `startRandomMotion("Idle", IDLE)`。
xinnong_6 `model3.json` 的 `Idle` 组 15 条（`idle`、`idle1`…`idle13`、`idle16`）；
其余三模型 `Idle` 组仅 1 条（与 `idle` 组同文件）→ 只有 xinnong 会随机跳。
本地 `l2d.ts:793-801 playIdleOnce()` 播的是小写 `idle`+index 组，**没有禁用库的 `Idle` 路径**。

→ **X1 根因 = 库默认行为未关闭**；用户澄清「全新加载仍复现」与此完全一致（与 localStorage 无关）。

### 5.6 F1/F2：feiteliedadi 的 ATA.idle 与 type104

**F2（决定性）**：`TouchDrag3`（49902204）`ATA {enable:[], idle:2, ignore:[]}` +
`relationParameter.list` 四条 **type104**（`idle:2` → `touch_drag15=0, touch_drag16=1, touch_drag17=1, touch_drag18=0`）。
站点 type104 语义（`spec-l2dsu-engine.md` §4.4）：**`rel.idle === 当前 idleIndex` 时把 `rel.name` 设为 `target`**。
点 drag3 → idleIndex=2 → 这四个参数被设为 `0/1/1/0` → 模型显示 drag2/drag4 且**参数目标表每帧维持** → 「不复位」。
本地：type104 未实现（`l2d_params.ts:13` 只认 103；`toParamRule` 只提取 `list[0]` 的 type103）→ 参数不设 → 画面不保持。

**F1（实测已裁决：站点同款，不是缺陷）**：`TouchDrag6`（49902203）`ATA {idle:0}`；初始 `idleIndex=0` →
`l2d.ts:301-302` 的 `ataIdle===chainIdleIndex()` 判定为真 → 规则被拒（不可互动）。
**T5 实测**：站点初始**根本没有 TouchDrag6 热区**（点 TouchDrag1 之后才出现 TouchDrag6/TouchDrag3）
→ 与本地一致。**结论：F1 无需修复**，本地行为正确。

**F2 实测补充（T5）**：站点点 TouchDrag3 后剩 `TouchDrag2`、`TouchDrag4`，**长时间等待保持不复位**，
且 TouchDrag3 消失不可再点。本地因 §5.0（参数写入失效）+ type104 未实现，无法维持该状态。

## 6. 修正方向候选（仅方向与优先级，不含实现；新硬性契约列「契约候选」）

> **优先级已按 2026-09-17 实测定案重排**：阶段 0（参数写入挂点）是 G1/G2/G3/F2 的共同根因，
> 必须先做；否则阶段 B 的参数权威层做了也不生效。

### 6.0 阶段 0（**最高优先级**：修复参数写入挂点，一处改动解锁四个症状）

1. **把 `ParamDriver` 的挂点从 `beforeModelUpdate` 改为 `afterMotionUpdate`**（§5.0 实验验证的生效挂点）：
   - 改动点：`l2d.ts:903-932 attachParamDriver()` 里的 `im.on('beforeModelUpdate', ...)`。
   - 依据：`cubism4.es.js:10289-10311` 的 `saveParameters()`（在 `beforeModelUpdate` 前）与
     `loadParameters()`（在其后）会把该挂点的写入还原；`afterMotionUpdate` 写入可存活。
   - 验证：修复后点击 guanghui_9 的 touch_drag3，`core.getParameterValueById('touch_drag3')` 应达 ~10，
     drag4/drag5 进入画布（x>0）且 `touchZoneStates()` 为 `ok`。
   - ⚠️ 需评估副作用：口型（`l2d.ts:871-890`）与参数驱动共用挂点，改后口型写入时序也变（但口型参数
     通常无动作曲线，预期无影响）；眨眼/物理在库内位于 `beforeModelUpdate` 之前，不受影响。**须实测回归**。
   *契约候选 0：参数写入必须发生在动作曲线之后、`loadParameters()` 之前；挂点变更需有运行时数值断言*
   *（`test_l2d_*_runtime.py` 已有先例：clampChain 的运行时对拍）。*

2. **补一条「参数写入生效性」运行时回归**：断言「ParamDriver 写入值 == 下一帧模型读数」，
   防未来库升级或挂点调整再次静默失效（这类失效无报错、无视觉提示，纯静态断言抓不到）。

### 6.1 阶段 A（数据与库，改动小、收益确定）

3. **重下错配的 9 个模型规则数据**（+ 2 例站点无规则者按「保持现状并标注」处理）：
   按 `skins[].prefab === <模型名>` **且**该皮肤 `model.live2dTouch.rules` 非空、`dynamicType==='live2d'` 提取，
   写入 `live2d-models/<name>/touch.json`；请求需带 `User-Agent` + `Referer: https://l2d.su/`（否则 403）。
   清单：`shi_3`、`feiteliedadi_4`、`feiteliekaer_4`、`mojiaduoer_4`、`wuzang_4`、`ougen_8`、
   `tiancheng_cv_3`、`dafeng_7`、`guandao_3`；`chaijun_4`/`shengluyisi_4` 站点无规则，保留旧数据但需标注。
   *契约候选 A1：`touch.json` 必须来自 `prefab` 精确匹配且带规则的 live2d 皮肤，
   下载脚本需输出 `prefab/skinId/ruleCount` 校验行；`shipSkinId` 字段与皮肤号不符即报错。*
4. **关闭宿主库 idle 自动播放**：`Live2DModel.from(url, { idleMotionGroup: <不存在组名> })` 或等效手段，
   并补测试断言；同时确认不影响 `playIdleOnce()`。**T8 实测依据**：静置 3 分钟 14 次自动动作、`idleIndex` 恒 0。
   *契约候选 A2：库的 idle 自动播放必须关闭，idle 只能由 `playIdleOnce()` 按 `idleIndex` 驱动。*

### 6.2 阶段 B（参数权威层，收益最大、影响面最广）

> ⚠️ **前置依赖**：阶段 0（挂点修复）必须先完成，否则本阶段的「每帧回写」同样会被 `loadParameters()` 吃掉。

5. **引入参数权威层**：加载时把**全部有效 parameter**（含 `relationParameter[].name`）登记为「目标值」，
   每帧统一回写（**挂点须与阶段 0 一致：`afterMotionUpdate`**），使动作曲线无法改写受管参数。
   需同时保留现有 circle/slide/mode2 交互语义（它们变成「设置目标值」的入口）。
   *契约候选 B1：受管参数集合 = touch.json 全部非 empty parameter ∪ relationParameter 名；
   写入必须发生在 motion 更新之后（`afterMotionUpdate`），且每帧执行（非仅交互时）。*
6. **type104 实现**（idle 关联预设）：`rel.idle===idleIndex → 目标值 = rel.target ?? rel.start ?? startValue`。
   *契约候选 B2：type104 语义为「idle 匹配即设目标」，随 idleIndex 变化即时生效。*
7. **`revertIdleIndex` / `revertActionIndex` 复位**（站点 §3.3；guanghui drag3 同时带两者）。

### 6.3 阶段 C（链条语义对齐，需逐项实测）

8. **type12 参数区间裁决**（`live2DExtendActionDecision`）接入 `actionAllowed` 链。
9. **形态A 查表改用「目标 idle」**（修 `l2d_touch.ts:143-144` 的语义错）+ `active_list[si]` 覆盖 ATA。
10. **冷却先记 + 链步循环**语义（注意：与本地偏离项 D2「body 连点冷却」冲突，**须先裁决**）。
11. **条件门槛 type9/11/15**、**type5/type10/type13**、**dynamicFlag 可见性**、**tips 显隐**——
    按 `spec-l2dsu-engine.md` §6 对照表逐项评估；其中 tips 显隐直接关系 G1「无热区」的观感。

### 6.4 不建议

- 不要为提高「可点率」放宽 `opacity`/门槛判定（r2 已证 D1 超越项是净伤害）。
- **不要修 F1**（TouchDrag6 不可互动）：T5 实测站点同款（初始无该热区），本地行为正确。
- **不要修 S3**（touch_drag10=4.0）：T3 实测站点同样变 4.0，属数据/美术设定，非缺陷。

## 7. 验收协议（本报告结论的证伪方法）

> **阶段 0 修复后的专项验证（最高优先）**：
> 载入 guanghui_9 → 清 localStorage → 点 touch_drag3 →
> ① `core.getParameterValueById('touch_drag3')` 应达 **~10**（修复前恒 0）；
> ② drag4/drag5 的 `getDrawableBounds` x 应 **> 0**（进入画布），`touchZoneStates()` 为 `ok`；
> ③ 拖动 drag4 时人物身上 TouchIdle* 应**连续变化**（对照 T2 站点实测的 17→4→1+22 序列）。
> 三条全部满足才算阶段 0 有效；任一条不满足说明挂点方案需再议。

1. **S1/S2**：替换数据后，叠加层应显示 TouchIdle1~45 全部注册；`[Touch]` 诊断行规则数 33→71。
2. **S3**：**无需验证（已实测为站点同款行为，非缺陷）**。
3. **X1**：清 localStorage → 载入 xinnong_6 → 静置 5 分钟，`idleIndex` 与播放组名不得自发变化
   （修复前 T8 实测：14 次自动动作 / idleIndex 恒 0）。
4. **G1/G3**：见上方「阶段 0 专项验证」。
5. **G2**：touchhead 播放中点 drag3 → 动作结束后重扫叠加层；修复后应比 T7 记录（仅 2 区 ok）明显改善，
   与站点同步骤对照。
6. **F1/F2**：F1 无需验证（实测同款）；F2 修复后 drag3 后应剩 TouchDrag2/TouchDrag4 且**保持不复位**（对照 T5）。

## 8. 未决疑点与需人工协助清单

> **T1~T8 已全部完成**（记录见 `manual_live2d动作链条验证.md` 与 §5.0/§5.4/§5.6 实测段）。
> 剩余疑点如下：

1. **站点真正的参数驱动路径未取证**（新增，最重要）：T3 显示站点面板参数变 4.0 但模型不变，
   而 T2 显示站点**确实**有参数驱动的三档渐变 —— 说明站点存在**两条路径**：面板读的是「目标表」，
   模型吃的是另一条（可能是站点自己的 `applyLive2DParameterFrame` 之外的第二处写入）。
   需在站点侧进一步取证（下钻其 chunk），才能确定本地「参数权威层」应模仿哪条。
   **这是阶段 B 开工前的前置调研项**。
2. **阶段 0 的挂点改动的副作用**：需实测回归口型/眨眼/物理（`manual_live2d动作链条验证.md` §3 的 T6 可复用）。
3. **G2 修复后的预期**（§5.4）需在阶段 0+ 完成后复测确认。
4. **数据普查**：已完成（36/36，见 §5.1b）。复核用 `python docs/assets/su_survey_touch_json.py . --fetch`。
5. **D2 冲突裁决**：站点链步循环 vs 本地「走完冷却 60s」——阶段 C 第 10 项落地前需人工裁决保留哪一方。
