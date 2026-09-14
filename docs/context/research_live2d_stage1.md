# 研究报告 · l2d.su 热区分区与命中判定（stage1）

> 2026-09-13，按 `research_plan_live2d.md` 执行的只读研究（未改任何代码）。
> 方法：①modelRuntime 混淆 JS 全文去混淆（Node 解码字符串表 → `Temp/su_modelRuntime_deob.js`、`Temp/su_decoded_strings.json`）；
> ②l2d.su 线上 guanghui_9（skin 237031）实测：挂钩 `Live2DCubismCore.Model.fromMoc` 捕获核心模型，
> 逐 drawable 顶点实测几何（`Temp/su_touch_geometry.json`）+ 站点自带热区叠加层/点击行为黑盒验证。
> 置信度标注：〔证实〕=去混淆代码或运行时实测直接证据；〔推断〕=行为反推。

> ⚠️ 本文引用的 `Temp/*` 产物已丢失（stage1 删除、从未入库），详见 `docs/assets/README.md`。
> 以下路径仅记录当时的取证过程，无法再复核。

## 1. 结论速览（一页）

- **l2d.su 没有「分区」引擎**：命中判定 = 指针转模型局部坐标 → **drawable 包围盒包含测试**
  （非逐像素 alpha），按**最大 drawable 渲染序**取最上层，同 id 组扩展；不可见/零尺寸包围盒直接不参与。〔证实〕
- **guanghui_9 的 28 个规则绘画件只有 4 个在画布内**（TouchDrag1/2/3/15），其余 24 个
  全部悬浮在画布外（y 36~149 或 x≈-43）——是数据载体（链定义/参数映射），**不是空间热区**，
  l2d.su 引擎下永远无法被点中。〔证实，运行时实测〕
- **当前线上 l2d.su 的 touch 规则根本没有加载**：`/data/ships/CN/237031.json` 返回 SPA HTML
  （站点自身请求同样如此），`currentSpec.live2dTouch` 为空。站点实际行为退化为
  7 个默认画布内热区（TouchSpecial/TouchHead/TouchBody + TouchDrag1/2/3/15），
  点身体播 `touch_body`，其余点击/拖动无 touch 动作——**与本地前端的「画布内过滤+头身兜底」行为等价**。〔证实〕
- 前端「上下二分」的直接原因不是过滤逻辑错，而是：**本地 touch.json 的规则全部不落在画布内，
  且 4 个画布内规则的 parameter（touch_drag1/2/3/15）不是动作组**，`l2d.ts` 的
  `valid.has(param)` 校验把它们也滤掉 → touchAreas=0 → 纯头身启发式。〔证实〕
- `tips`/`dragRate`/`ignoreDrag` 是**死数据**：全站 6 个 JS chunk 无 `tips`/`tipsOffset` 字符串，无消费方。〔证实〕
- 对 stage2 规格书的一处修正：`Ve()` 里展开的键是 **aliases**（区域别名表），不是 shipSkinId。〔证实〕
- 可落地改动见 §7；与 spec-l2dsu-engine.md 的矛盾点见 §8。

## 2. 指针命中链路实证（SQ1）〔全部证实，去混淆代码〕

链路（modelRuntime，去混淆后函数名均为原名）：

1. **pointerdown** → `pickLive2DArea(model, x, y)`（`[0x388]`）：调 `hitAreasAt` 取命中组，优先带
   slide/offset 的规则区，其次有 action/motionGroup 的区，最后首个。
2. `hitAreasAt(model, x, y)`：`worldTransform.applyInverse` 把指针转到**模型局部坐标** →
   过滤 `officialLive2DHitAreaInteractive(a) && visibleLive2DHitAreaDrawIndex(a, pt) >= 0` →
   按 `live2DHitAreaRenderOrder`（区域内 **最大 drawable 渲染序**）降序排序 → 返回与最上层同 id 的全部区域。
3. 几何测试 `visibleLive2DHitAreaDrawIndex`（`[0x1bc]`）：候选 = 区域 `drawIndices`（回退 `[drawIndex]`）
   中 `isLive2DDrawableVisible && hasUsableDrawableBounds`（有限且 w>0、h>0）者；
   命中判据 = `live2DDrawableContainsDisplayPoint` → **包围盒 x/y/w/h 包含指针**，无 alpha 逐像素。
4. `officialLive2DHitAreaInteractive(area)`：规则区需 `live2DRulePointerEnabled(rule)`
   （type ∈ {1,2,3,4,6,8,9,11,14,15} + 链允许 + 不重复当前 idle）；无规则区需有 action/motionGroup
   且动作被放行；播放中仅放行 official 且非 ignoreAction、且当前链步 `focus===1` 的区域。
5. `relatedLive2DTouchAreas(area)`（`[0x195]`）：把命中区**扩展为同 id 的全部规则区**（可见+可交互者），
   回退 `[area]`；随后 `startLive2DTouchInteraction` 建 `live2DTouchInteraction`，type ∈
   {2,6,9,11,14} 的规则**按下即触发**（`updateLive2DPressedRules` 每帧续处理 type3 长按/type4 等）。
6. **与 pixi 的关系**：pixi-live2d-display 原生 `InternalModel.hitTest` 同样是包围盒判据
   （`live2dRuntime` 证实），但站点另把全部区域注入 `currentLive2d.hitAreas`
   （`Object.fromEntries(live2dHitAreas.flatMap(a=>a.aliases.map(...)))`）； Pixi EventBoundary/
   containsPoint 只做**整模包围盒**一级门槛。`Ve(drawables, area)` = 小写归一后的集合成员测试
   （比对 `area.name/id/drawAbleName/aliases`），无顺序语义。
7. **区域注册来源**（`live2dHitAreas` 构建）：①model3.json `HitAreas`（guanghui_9 无）；②默认表
   `['TouchSpecial'/'TouchHead'?,'TouchBody']`（推断前者为 TouchSpecial/TouchHead，实测叠加层两者都在）；
   ③touch.json 规则逐条注册，`getDrawableIndex ?? -1`，**不做画布内过滤**——但画布外者因几何测试
   永不命中，等效于被丢弃。

## 3. guanghui_9 热区几何实测（SQ2）〔证实〕

画布：`canvasinfo` 9999×6599 px / PixelsPerUnit 399.94 → 模型坐标画布 **x∈[-12.5,12.5], y∈[-8.25,8.25]**（y 向上）。
角色主体可见包围盒约 x∈[-3,3]，y∈[-3,5.5]。31 条规则分类（完整表原存 `Temp/su_touch_geometry.json`，已丢失）：

| 分类 | 数量 | 明细 |
|------|------|------|
| 画布内（实体热区） | 4 | TouchDrag1（胸口 y0.1~2.2）、TouchDrag2（下摆 y-2.9~0）、TouchDrag3（身侧左 x-8.3~-5.3）、TouchDrag15（头部 y2.2~4.4） |
| 画布外（虚拟标记） | 23 | TouchIdle1~10/12/13、TouchDrag6~14 全部 y 36~149（头顶上方 4~18 倍画布高）；TouchDrag8 y59.6 |
| 画布外+不可用 | 2 | TouchDrag4/5：x≈-43，且 opacity=0、不可见（双重不可达） |
| 模型缺 drawable | 1 | TouchIdle11（规则存在，模型无此绘画件） |
| 非 touch.json 默认区 | 3 | TouchSpecial/TouchHead/TouchBody（站点默认注册，均在画布内） |

**站点交叉验证**：开启站点「显示→触摸区域」叠加层，画出的正是
TouchSpecial/TouchHead/TouchBody/TouchDrag1/2/3/15 这 7 个——与实测几何完全一致。〔证实〕

## 4. 虚拟标记的触发语义（SQ3）

- **l2d.su 引擎内不存在「画布外标记的空间触发」**：每个规则触发都必须先过 §2.3 的包围盒几何
  测试，画布外标记不可达。TouchIdleN 规则的作用是**数据载体**：其 ATA（idle:N/enable 表）、
  relationParameter（TouchDrag1/2 的 type103 查表 [0..5,4..0]）、listenerData 被其他规则的
  触发与空闲链消费。〔证实〕
- 游戏本体的「点身体计数触发 touch_idleN」语义在 l2d.su 引擎中**没有对应实现**
  （无计数器代码路径；type3=长按计时、type1/4=拖动，都要求先空间命中）。〔推断，行为反推〕
- `touch_dragN` 是**模型参数名**而非动作组（核心模型 parameters.ids 实测含
  touch_drag1/2/3/4/5/15 与 Paramtouch_idle1/2/4）——TouchDrag3/15 是 circle 型参数手势
  （逼近 target=1 回落），TouchDrag1/2 由 relationParameter 按拖动值查表驱动。〔证实〕
- `ids`（207037xx）= 规则 id；**注意本地 touch.json 所有规则 `shipSkinId=207037`（guanghui_7）**，
  而 guanghui_9 的 skinId 是 237031——本地文件是从 guanghui_7 的数据下载的（疑点见 §8）。

## 5. mode2 位置反应分区（SQ4）〔证实〕

- `updateLive2DReactRule`：mode===2 的规则**不做空间命中**，按
  `Σ (reactPosition.x×reactPosX + reactPosition.y×reactPosY)`（同 parameter 的全部 mode2 规则求和，
  id 更小者存在则跳过）写参数，再走 range/dragDirect/smooth 钳制链。
- 坐标系：全局 pointermove 监听里 `reactPosition = clamp(-1,1, (clientX-rect.left)/rect.width*2-1)`
  与 y 反向同理——**画布矩形归一化 [-1,1]**，非模型局部坐标、无作用区域限制（全模型）。
- guanghui_9 的 3 条 Param3 规则：reactPosX = -7 / +10 / -7，reactPosY 全 0，range [-10,10]，
  shopAction=1；Param3 参数存在（parameters 下标 268）。效果 = 指针左右移动时 Param3 摆动。

## 6. tips 气泡锚定（SQ5）〔证实：死数据〕

- `tips`（tipsOffset/tipsScale/tipsIcon/idleBlackList/animWhiteList）：全站 6 个 chunk
  （index/modelRuntime/live2dRuntime/spineRuntime/lib/resourceProgress）`tips` 字符串 **0 命中**
  ——引擎与 app 层都不读取；id=207037 与 shipSkinId 同源，是游戏侧数据残留。
  **不能**作为「站点知道热区屏幕位置」的旁证。
- 站点数据管道现状：`/data/ships/CN/<skinId>.json`（skinId 237031，由 `gt()` 生成、无静态域回退）
  当前返回 SPA HTML——**站点自己的 live2dTouch 也没加载**（性能条目 transferSize≈3.2KB HTML，
  站内复取同样 HTML）。历史记录的「index 在 /data/ships-CN.json」仍有效，但逐舰数据已失效。

## 7. 现实现差距与替换路径（对照 spec-l2dsu-engine.md §7/§8 增量）

先澄清「上下二分」成因链（修正研究计划里的假设）：本地 touch.json 31 条规则中，
3 条 Param3 无 drawAbleName、24 条画布外被 onCanvas 过滤、TouchIdle11 无 drawable、
剩余 4 条画布内（TouchDrag1/2/3/15）又因 **parameter 不是动作组** 被 `valid.has(param)` 滤掉
→ `touchAreas=0`，`hasTouchRules=false`，整个交互退化为头/身 30% 分界启发式（l2d.ts:113）。
l2d.su 当前行为与我们等价（§1），因此**追平站点不需要大改**；要超越站点（还原游戏语义）才需要规则引擎。

| 改动 | 落点 | 价值 |
|------|------|------|
| A. 修复规则被全滤掉：动作组校验放宽——rule.parameter 不是动作组但**是模型参数**（coreModel._parameterIds）时也注册 | `l2d.ts loadTouchRules`（l2d.ts:178） | 让 TouchDrag1/2/3/15 生效，行为追平并超过站点 |
| B. 命中择一改「最大渲染序」优先（现按包围盒最小）+ 不可用包围盒（非有限/零尺寸）剔除 | `l2d.ts` emitInteraction/hit 过滤（l2d.ts:117-126） | 与 l2d.su 判据一致 |
| C. mode2 reactPosX/Y 位置反应：画布归一化 [-1,1]（y 反向）×增益求和写参数 | `l2d.ts loadTouchRules` 放行无名规则 + 帧循环写入 | 补上「手掌跟随」类反应（stage2 gap 表已列） |
| D. 触发链/冷却/持久化/白名单（stage2 §8 的 4 件事） | `l2d.ts`+`main.ts` | 还原游戏语义；注意 touch_idleN 永不空间触发，链推进只能靠 ATA 消费（如 TouchDrag3/15 触发后 idle:N） |
| E. `parameterRange`（ParamAngleX [-20,20]）全局钳制 | 参数写入处 | 低成本防超幅 |
| F. tips/dragRate/ignoreDrag | 不实现 | 站点也无消费方 |

不建议：逐像素 alpha 命中（站点没有）、为 TouchIdleN 建空间区域（数据上就不在画布内）、
解析 moc3 顶点自建几何（本次已用 core 顶点验证，仅研究用途）。

## 8. 附录：与 spec-l2dsu-engine.md 的矛盾点 + 疑点 + 复现命令

矛盾点（合并由主模型决定）：
1. §5.1「`Ve` 展开 shipSkinId」→ 应为 **aliases**（`_0x3d2` 解码 = aliases）。
2. §5.1「Pixi EventBoundary/hitTest 走到哪层」→ 命中**不经过** pixi hitTest；站点用自己的
   `hitAreasAt`（模型局部包围盒+渲染序），pixi 只做整模 containsPoint 门槛。
3. §1「`tips` 推断为 app 层消费」→ 证实为**无消费方（死数据）**。

疑点（未决）：
1. 本地 touch.json 是 guanghui_7（shipSkinId 207037）的数据配在 guanghui_9 模型上——当年批量
   下载是否错配？36 个模型需逐一核对 shipSkinId（影响所有碧蓝航线模型的规则语义）。
2. `/data/ships/CN/<id>.json` 失效是临时还是永久？若永久，站内未来也不会再有规则行为，
   「追平 l2d.su」目标自动达成，「还原游戏语义」只能依赖既有离线数据。
3. 站点默认注册表的第一个元素（0x391，实测叠加层显示 TouchSpecial 与 TouchHead 同时存在，
   推断 he=['TouchSpecial','TouchHead','TouchBody']）未逐字解码。

## 9. stage1b · 站点行为核验（阶段0，2026-09-13，按 stage2 研究规格执行；规格已并入 spec-l2d-touch-engine.md）

> 方法：浏览器重开 https://l2d.su/cn/skins/237031/ 实测（XHR 钩子 + performance 资源条目 + 核心模型
> `Model.prototype.update` 捕获 + 逐帧参数/drawable 采样器 + 动作「参数活动签名」比对 + 站点「动作」面板按组名触发）；
> deob 复核 `Temp/su_modelRuntime_deob.js`（已丢失）。置信度标注同前。产物：`Temp/su_touch_rules_skin9.json`（已丢失；站点
> guanghui_9 全部 62 条规则）。

### 9.1 Q1 规则数据加载 —— stage1 §1/§6 需修正〔证实〕

- **touch 规则有加载**。真实数据 URL 是**舰船级** `/data/ships/CN/20703.json`（200, application/json, 337KB,
  generatedAt 2026-09-11），`live2dTouch` 位于 `ship.skins[N].model.live2dTouch`。stage1 测的
  `/data/ships/CN/237031.json`（皮肤级）确实仍返回 SPA HTML（本次复测 8079B text/html），但那不是站点
  实际请求的 URL —— 「数据管道失效」结论**作废**。
- skin 237031（幽影徘徊之夜）= **62 条规则**（ids 23703101+）；skin 207037（二人的学习时间）= 31 条
  （ids 207037xx）。**本地 touch.json 的 31 条 207037xx = 站点 guanghui_7 规则集**，§8 疑点1「错配」坐实；
  本地却配在 guanghui_9 模型上。要按 guanghui_9 对齐须用站点 62 条集（原存 `Temp/su_touch_rules_skin9.json`，已丢失）。
- 62 条要点：TouchDrag1/2/3/15 = type2 + `circle:true,target:1` + 无 action（参数手势）；TouchDrag4/5 =
  **无 actionTrigger** + offsetY=-15/-20（slide 类）；TouchIdleN = type2 + action touch_idleN +
  `actionTriggerActive.idle = N`（idle 索引门槛，见 9.2）；另有 type12×1（touch_drag3 num 监听）、type7×1
  （Limit_box14 listenerData 联动 TouchIdle 组）。tips/ignoreDrag/parameterRange（ParamAngleX [-15,15] 等）
  都在数据里；tips 仍无代码消费方（§6 维持）。

### 9.2 Q2 重叠区优先级 + 规则区门槛 —— 修正规格书 §0.1〔证实〕

- deob 复核（`[0x388]`/`hitAreasAt`）：`hitAreasAt` 实时过滤（interactive + 命中包围盒）→ 按**实时渲染序**
  降序 → **只返回与最上层区域同 id 的组**；`pickLive2DArea` 的「规则区→动作区→首个」择一**只在同 id 组内**
  生效。跨 id（如 TouchHead vs TouchDrag15）**完全由实时渲染序定胜负**。规格书 §0.1「跨候选区按类择一」
  表述不成立；stage1 §7B「渲染序择一」基本正确但漏了同 id 组内择一。
- `live2DRulePointerEnabled`：无 actionTrigger 的规则 → 须 `ruleHasLive2DSlide`（offset≠0）；有 actionTrigger
  的 → type ∈ Oe 集合 + reactCondition/ATA 检查 + 非「重复当前 idle」+ 动作放行。
- **新发现：ATA idle 索引门槛**〔证实〕。每条 TouchIdleN 规则 `actionTriggerActive.idle = N`（TouchIdle1→1,
  TouchIdle4→4…），要求引擎当前 `live2dOfficialIdleIndex == N` 才可触发。站点加载后永远停在 idle 0
  （idle1~30 从未被请求）→ idle≥1 的 TouchIdleN 全部**永久死锁**。TouchIdle31~42 虽是 idle:0，但其
  drawable 不在画布内 → 同样不可达。规格书完全没提这个门槛；「还原游戏语义」需要 idle 索引状态机。
- 实测：会话1 头部（TouchHead 叠加层矩形内）点击 → `touch_head` 播放〔证实，touch_head.motion3.json
  网络加载 + 时长 7.88s 吻合〕；身体 → `touch_body`（6.62s 吻合）✓；TouchDrag15 条带点击 → 无动作、
  touch_drag15 参数不动〔证实〕。会话2 重载后画布内的 TouchIdle4/TouchDrag4/5：点击与拖动**全部无响应**
  （touch_drag4/5 全程为 0）〔证实〕→ 站点当前实际可交互面 = **3 个默认区（TouchSpecial/TouchHead/TouchBody）**，
  规则区实际不可交互。

### 9.3 Q3 连点链 —— 无递进〔证实〕

- 头/身点击各播 touch_head/touch_body（时长指纹精确匹配 Meta.Duration）；整个观测期
  **touch_idleN.motion3.json 与 idle1~30 从未被请求** → 站点无 touch_idleN 递进、无 idle 链推进。
  stage1 §4「引擎无点击计数器」维持；§2.4.3 body 连点链确认为「超越站点、还原游戏语义」。
- **站点 idle 只在加载时播一次，播完模型完全冻结**〔证实〕：397 个参数 1.2s 内零变化；观测 40+ 分钟
  仅加载 motions/idle.motion3.json 一次。官方触摸动作结束后自动回放一次 idle 组（deob finally 块
  `playLive2DIdleMotion(idleIndex)` + 会话1 实测 touch_head 播完后活动延续）；idle 组 Meta.Loop=true
  但引擎不循环。→ 规格 §2.4.2「app 层 idle 循环」若要对齐站点应为「结束后播一次」而非循环。

### 9.4 Q4 播放门控〔部分证实〕

- 面板路径（playMotionGroup）：播放中触发新动作 → **立即打断**（FORCE），播完**不回 idle**（非官方路径
  无 finally 回链）〔实测：main_1 播放 5s 时触发 touch_body，main_1 即断，touch_body 6.6s 后全场静止〕。
- 官方触摸动作结束 → 回放 idle（见 9.3）。播放期间区点击无响应与 deob 官方门控一致（受会话2规则区
  全死限制，直接实测证据有限，标〔推断〕）。

### 9.5 Q5 拖动/circle〔部分证实〕

- TouchDrag4/5 条带（画布内、opacity=1）点击与竖向拖动 → touch_drag4/5 参数全程 0〔证实〕——规则区
  手势在站点实际状态无效（与 9.2 门槛一致）。
- circle 翻转（TouchDrag1/3/15）本次姿态不可达（画布外），未实测；仅有 deob 语义（`circle:true,target`
  翻转）与数据佐证。DRAG 增益无法从站点校准——实现时按数据 range/smooth 自定，标〔推断〕。

### 9.6 Q6 动态热区 —— 最重要发现〔证实〕

- **热区集合与边界随「冻结姿态」巨变**：会话1 冻结姿态 = 7 区画布内（TouchSpecial/Head/Body +
  TouchDrag1/2/3/15，叠加层截图）；会话2 重载后同模型冻结姿态 = 头/胸/身全部区跑到 y≈41~57（画布上方
  5~7 倍画布高，画布 y∈[-8.25,8.25]），仅 TouchDrag4/5 + TouchIdle4 在画布内且 opacity=1 ——
  stage1 §3「TouchDrag4/5 永远画布外+不可见」只是**当时姿态的快照**，不成立为恒定结论。
- 同一姿态内，各动作播放期间 Touch* drawable 位置基本恒定（TouchDrag4/5 在 main_1/touch_body/login
  期间 x 恒定）；跨姿态状态则位置大变（TouchDrag4: -6.7→-9.0，TouchIdle4: 画布内→y43.9）。
- 会话间冻结姿态**不确定**（同一 idle.motion3.json 两次冻结在不同帧，疑 RAF 节流打断动作求值）〔推断〕；
  login/touch_body 播完后区不回到身体位。
- 实现含义：§2.2 实时包围盒+可见性+透明度剔除方向正确且**必要**；透明度阈值 0.01 在 deob
  `isLive2DDrawableVisible` 旁证实（`opacity<=0.01` 剔除）。但「叠加层区数 ≈7」的验收口径不可靠——
  站点自身就在 0~7 区间波动，验收应改为「区集合随姿态实时变化、与站点同姿态一致」。

### 9.7 deob 补充复核（规格 §2.3 相关）

- `playMotionGroup(action)`：`motions.filter(motionMatchesAction)` 全量过滤 → reduce 顺序连播
  （`activeMotionSequence` 守卫）〔证实〕。`motionMatchesAction(entry, action)` = `K(entry).some(n =>
  n === action || G(n) === G(action))`；**K(entry)** = 去重集合 {group, name, file 剥扩展名, 以及三者的
  G() 归一化}；**G(s)** = `W(s).toLowerCase().replace(/[-\s]+/g, '_')`（W 剥路径与 `.motion3.json` 等扩展名）。
  → 规格书 §2.3 的归一化函数**少了 lowercase 与扩展名剥离**；引擎实际是大小写不敏感 + 文件名主干匹配。
  另有 `Fe(name)`：支持 `组名_N` 后缀解析到 {index, subIndex}。
- `playLive2DIdleMotion(i)`：组名 = `i>0 ? 'idle'+i : 'idle'`，`motionGroupExists` 后播放〔证实〕；
  官方动作 finally 中回放。`scheduleLive2DHitAreaRefresh(3)`：rAF 递减 3 帧周期重建热区表与叠加层，
  另有 120ms setInterval 兜底刷新〔证实〕。

### 9.8 对 stage2 规格书的修正清单（供修正阶段使用，本次未改代码）

1. §0.1：择一优先级改为「跨 id 实时渲染序定胜负；同 id 组内才按 规则区→动作区→首个」。
2. 新增规则区交互门槛语义：slide 放行 / type∈Oe+reactCondition+**ATA.idle 匹配**；若只「追平站点」，
   规则区可不做交互；「还原游戏语义」需 idle 索引状态机（TouchChain idleIndex 概念恰好接上）。
3. §2.3 归一化补 lowercase + 扩展名剥离（或双端同归一化即可等价）。
4. §2.4.2 idle：站点为「官方动作结束回放一次」，非循环。
5. §5 验收第 1 条「区数 ≈7」改为「区集合随姿态实时变化（站点本身 0~7 波动）」。
6. 数据对齐：按 guanghui_9 对齐需换用站点 62 条规则集；parameterRange 以站点数据为准（ParamAngleX
   [-15,15]）。

### 9.9 遗留疑点

1. 会话间冻结姿态差异的根因（RAF 节流 vs 其他）未定——影响本地复现「热区随动作变化」的测试方法设计。
2. Oe 集合是否含 type2 未逐字解码；若含，则 TouchDrag1（reactCondition idle_on:[0]，当前 idle 0 满足）
   理论可交互但实测未响应（当时画布外）——两说并存，实现按 deob 全套门槛做即可。
3. TouchSpecial 默认区点击未成功实测（姿态漂移后无机会），按 deob 默认区语义（有 motionGroup 即可触发）处理。

复现（PowerShell；浏览器自动化要点：XHR 钩子+performance 资源条目记动作文件；核心模型经
`Model.prototype.update` 捕获；逐帧参数/drawable 采样；动作识别用「时长指纹（Meta.Duration）+参数活动
签名」；站点「动作」面板可按组名直接 playMotionGroup）：

```powershell
# 站点规则集（本次新证）：浏览器打开 https://l2d.su/cn/skins/237031/ 后在控制台执行
#   fetch('/data/ships/CN/20703.json').then(r=>r.json()).then(j=>console.log(JSON.stringify(j.ship.skins[9].model.live2dTouch)))
# 结果原存 Temp/su_touch_rules_skin9.json（已丢失）
# 旧产物（stage1）仍有效，但文件均已丢失：Temp/su_modelRuntime_deob.js、Temp/su_site_model3.json、Temp/su_touch_geometry.json
```
stage1 复现（PowerShell 语法与 temp 系列一致；产物原存 `Temp/su_*`，已丢失）：
```powershell
# 1) 抓站点 chunk（本次新解禁 l2d.su）
curl.exe -s -o Temp\su_index-LGceUR3e.js https://l2d.su/assets/index-LGceUR3e.js
curl.exe -s -o Temp\su_spineRuntime-CwB63JJC.js https://l2d.su/assets/spineRuntime-CwB63JJC.js
# 2) 去混淆：Node 解码 _0x1cdf/_0x25d3 + 轮转 IIFE，替换 _0xXXXX(0xHEX) 调用 → Temp\su_modelRuntime_deob.js
# 3) 运行时实测：浏览器开 https://l2d.su/cn/skins/237031/ ，domcontentloaded 后 evaluate 轮询
#    window.Live2DCubismCore 并包一层 Model.fromMoc 捕获；SPA 内切皮肤再返回触发模型重建；
#    遍历 drawables.ids/vertexPositions[i]/renderOrders/dynamicFlags/opacities 逐件算包围盒；
#    开「显示→触摸区域」叠加层交叉验证；点击观察 motions/* 的资源加载
```

## 10. stage1c：双模型诊断与拖拽管线实测（2026-09-13，stage3 v2 阶段A）

> 环境：本地 frontend-minimal（server.py 挂载 /m）+ l2d.su 站点对照。诊断工具：
> `[Touch]` 注册汇总日志、`renderer.touchZoneStates()`（ok/H/T/O/G 逐区状态）、
> 站点「显示→触摸区域」叠加层 + 「参数 437」实时滑杆面板。

### 10.1 本地快照（加载 → idle 播完冻结后）

- **guanghui_9**：注册 13 区（62 条规则中 10 条有绘画件+参数，+3 默认区）。状态：
  `ok` 7 = TouchDrag1/2/3/15（circle）+ TouchSpecial/Head/Body；`T`（透明度≤0.01）2 =
  **TouchDrag4/5（slide 区，当前冻结姿态下透明）**；`O`（画布外）4 = TouchDrag10、
  TouchIdle31/37/41。与 stage1b §9.6「站点 0~7 区波动」一致（ok 区数=7）。
- **wuqi_3**：注册 12/34（`[Touch] wuqi_3 注册 12/34：无绘画件名2、参数空23、drawable缺失0、
  画布外0（参数规则 9 条）`）。冻结姿态下 12 区全部 `ok`（slide 区 TouchDrag2/3/6/7 全可用）。
  23 条「参数空」规则（TouchIdle* 等链/ATA 数据载体）本地不注册——见 §10.3 差异 2。
- **默认区**：两模型 TouchSpecial/TouchHead/TouchBody 绘画件均存在，无缺失日志。

### 10.2 拖拽管线端到端实测（wuqi_3，真实鼠标事件）

- 合成 PointerEvent 逐级探针：命中（downHit=TouchDrag2#39904202）→ beginHold → holdAcc 累积
  （8×20px → 820.5 模型单位）→ 状态机 value 逼近 → writeParam 全链通。
- **关键坑 1**：v1 只在 40px 拖拽阈值后才累积 → 已改为按下即累积（阈值只派发 drag 交互）。
- **关键坑 2（测量陷阱）**：pixi-live2d-display 帧序 = motion 写参数 → physics →
  `beforeModelUpdate`（我们写参数）→ `coreModel.update()`（**渲染用我们的值**）→
  `loadParam()`（把参数缓冲还原为动作保存值）。因此 `getParameterValueById` 恒读 0
  **不代表写入失效**——判定一律以 `paramDriver.states` 内部 value / 渲染差异为准。
- **关键坑 3**：模型本地空间 y 向下；wuqi_3 TouchDrag2（offsetY=-150, dragDirect=1,
  range[0,1]）向上拖 → yv=acc/-150 为正 → 钳到 1。真实 cua.drag 实测 dragAccum=1（触顶）✓。
- circle 画圈循环实测：hold 中 value 0→0.92（逼近 target=1）→到位翻转→0.50（回落
  startValue 中）→松手 endHold→归 0。循环与回落均按 §3.1.4 工作。

### 10.3 站点对照（l2d.su，2026-09-13 时点）

| 项 | 站点 | 本地 | 判定 |
|----|------|------|------|
| 叠加层绘制范围 | 全部有 drawAbleName 的区都画，**含模型外浮动框**（wuqi_3：TouchIdle1/8/9/11/13/20 悬浮在场景空白处） | 全部**已注册**区都画+状态标记（O/T/G/H） | 同款思路；差异 2 见下 |
| 触摸区语义（wuqi_3 参数面板中文名） | touch_drag1=眼镜、2/3=丝袜有无L/R、4/5=高跟鞋R/L、6=明暗、7=时间（**默认 180=夜景**）、8=显示UI | 相同数据 | 这些是**外观开关型**参数，非位移动画；拖动=切换外观 |
| touch_drag7（时间）初值 | 180（夜景） | 180（range 钳制上限同 180） | 一致 |
| 站点 TouchDrag2 区真实拖拽 | 参数滑杆无变化（0.00）、无可见反应 | 修复前同样无反应 | 站点当时也未响应（位置/姿态/手势判据存疑），**非本地单侧缺陷** |
| TouchIdle* 数据载体区 | 画出但不可交互（stage1b §0.3 ATA 死锁结论不变） | 不注册（parameter 为空） | 交互等价 |
| 站点稳定性 | 复测时「正在读取舰船数据...」长时间卡死（舰船数据接口限流/失效，与 stage1b §9.4 结论一致） | 不依赖站点 | guanghui_9 站点复测未完成，引用 stage1b §9 记录 |

### 10.4 结论（对应规格书 §2.4 判定）

1. **症状①（拖拽无反应）**：根因为 v1 参数管线缺口，已按 §3.1 补全并实测通过；
   「拖拽=外观开关」语义（丝袜/眼镜/高跟鞋/明暗）已可驱动。
2. **症状②（背景互动热区缺失）**：站点同款行为——区集合随姿态波动（guanghui_9 冻结姿态
   ok 区恰为 7）、数据载体区不可交互；叠加层已全区可视化并标注剔除原因，「缺失」可解释。
   本地与站点无单侧差异，无需再改注册逻辑。
3. 遗留：站点侧 TouchDrag2 拖拽当时未响应的判定未定（位置/手势判据），后续可在站点恢复时
   用「参数面板滑杆联动」法复测；本地 DRAG_VALUE_SCALE=1 观感待人工验收微调。

## 11. stage1d：stage5 实测协议记录（2026-09-13，T1~T13 逐行）

> 环境：frontend-minimal stage5 构建 + 本地 server.py + ZCode 内嵌浏览器自动化。
> 测试集 guanghui_9 / wuqi_3 / xinnong_6；叠加层仪表盘模式（区标签带参数实时读数）。
> ⚠️ 环境事故：会话中后段内嵌浏览器 **rAF 完全停摆**（visibility=visible 但 1.5s 0 帧，
> ticker.update 亦挂起——与此前 l2d.su 页卡死同款，判定为 IAB 合成器/GPU 层问题，非应用缺陷）。
> 受影响项用「手动 ticker 泵帧 / 状态机直调」补救，已在对应行标注。

| # | 模型 | 实测 | 判定 |
|---|------|------|------|
| T1 | 光辉 | 加载静置后两帧姿态一致；idle 终帧冻结；**代码级铁证：`motionGroups.idle[0].isLoop()===false`**（setIsLoop 生效） | PASS（附机制证据） |
| T2 | 光辉 | TouchDrag5 本冻结姿态投影 x≈-2123（视口外，站点同款姿态波动，stage1c §10.4） | BLOCKED（记录原因） |
| T3 | 光辉 | TouchDrag4 同上（x≈-2043） | BLOCKED（记录原因） |
| T4 | 光辉 | 转盘公式单点精确验证：按下 TouchDrag1 中心命中，指针移至右上 45° → holdValue=0.1266（期望 0.125，投影取整误差）；整圈连续采样受「写入参数驱动姿态漂移 + rAF 停摆」双重干扰未完成（3 次上限） | PARTIAL（公式 PASS，长序列未完成） |
| T5 | 光辉 | 同 T4（单点机制同源已证；整圈采样同因未完成） | PARTIAL |
| T6 | 光辉 | 依次单击头/身/特殊：playAction('touch_head',-2) 等三次全部 resolved=true、motionManager.playing=true（动作确实播放）。注：单条目动作启动后播放门即释放（stage3 设计），门状态≠播放状态 | PASS |
| T7 | 吾妻 | TouchDrag2 下拖 150px → **0.9995**（期望 1，150/150）；上拖 150px → **0.0003**（dragDirect=1 钳制） | PASS（误差 <0.1%） |
| T8 | 吾妻 | TouchDrag7 上拖 90px → **135.02**（期望 180−90/2=135） | PASS（误差 0.02%） |
| T9 | 吾妻 | TouchDrag6 下拖 100px → **9.995**（期望 10） | PASS（误差 0.05%） |
| T10 | 吾妻 | TouchDrag8 单击 → 面板出现（截图证据：屏幕右侧双悬浮按钮栏）且 **≥5s 保持**；后续 30→0→30 翻转经状态机+手动泵帧验证（poke 入口翻转、到位停留均按 §2.3）；连续真实点击复测受 rAF 停摆限制 | PASS（含环境注记） |
| T11 | 吾妻 | 数据实况：TouchIdle1 的 ATA 为 `{idle:11}`（非规格书预估的 1），且吾妻 touch.json **无 touch_idleN 参数规则**可推进链 idleIndex（TouchIdleN 自身 parameter='empty'）→ 本地与站点同样处于门槛后（叠加层正确标 G）。按规格「不做自动解锁」保持现状 | BLOCKED（数据受限，非缺陷） |
| T12 | 信浓 | 新数据注册 29 区（26 drawable 规则+3 默认区）、控制台零报错；touch_idle1~20 链组齐全（链路径与既往阶段同代码） | PASS |
| T13 | 全部 | 光辉：T1 两帧含全区叠加层+读数；信浓：叠加层显示 TouchIdle4/9 [G] + TouchDrag1 ok 框（截图）；吾妻：zoneStates 文本记录（35 区） | PASS |

补充发现（对后续有价值的引擎事实）：
1. 本栈 pixi-live2d-display 0.5.0-beta 的 coreModel **不存在** `getDrawableVisibility`/
   `getDrawableRenderOrder`（仅 `getDrawableOpacity` 存在）——stage3 起的 `?? true/?? 0` 兜底
   一直生效，renderOrder 恒 0、命中择序实际靠包围盒面积平局决断。如需真实渲染序，可读
   `coreModel.drawables.renderOrders` 数组（原生属性）。
2. wuqi_3 的链推进引擎语义存疑：链进度（idleIndex）仅能由带 ATA 的规则推进，而该模型链规则
   缺位、TouchIdle1 要求 idle==11——怀疑站点侧由游戏内连点语义直接递增 idleIndex（未在 deob
   定义体中定位到），留待后续复现站点行为时核实。
3. 内嵌浏览器 rAF 停摆的复现特征：页面 visible、evaluate 正常、截图正常，但 rAF/ticker 停；
   手动 `app.ticker.update()` 一度可泵帧后亦挂起。真实用户浏览器（非 IAB）未复现过。

## 12. stage1e：stage6 实测协议 v2 记录（2026-09-14，C1~C9 逐行）

> 环境：frontend-minimal stage6 构建 + 本地 server.py(12393) + ZCode 内嵌浏览器（IAB）。
> 测试集 guanghui_9 / wuqi_3 / xinnong_6；每轮先清 `l2d-touch:*`/`l2d-param:*` 持久化后刷新或重选角色。
> 叠加层仪表盘开启（区标签 + 左上角 `idleIndex=N` 读数）。
> ⚠️ 环境事故复现：IAB 面板首次打开时 `visibility=hidden` → rAF 0 帧；`visibility.set(true)` 后恢复
> 60fps。中途再次停摆（frames=0/1.2s），与 stage1d 同款，但不阻塞 evaluate/点击/参数读取。
> 另一环境特征：区位置随姿态（idle 播完冻结 + 参数写入）漂移，跨单元格缓存坐标会失效——
> 凡拖拽/点击类用例均在**同一单元格内即时重扫命中点**再操作。

| # | 模型 | 实测 | 判定 |
|---|------|------|------|
| C1 | 光辉 | 清持久化 + 刷新后仪表盘左上角读数 `idleIndex=0`；`touchRules=62` 条原始规则、区 63 个 | PASS |
| C2 | 光辉 | 连点身体区 5 次（每次即时重扫 TouchBody 命中点）：`touch_idle1#0`→`touch_idle5#0` 逐个播放，idleIndex 1→2→3→4→5 | PASS |
| C3 | 光辉 | 继续连点至 idleIndex=17；连续段动作 `touch_idle4…touch_idle17` 逐个播放；`isRuleInteractive(TouchIdle17)` **false→true**（门槛解锁）；对照 `TouchIdle20` 仍 false（interactive）、`TouchIdle5` 亦 false（门槛为等值判定非 ≥） | PASS |
| C4 | 光辉 | 门槛已解锁（interactive=true），但 TouchIdle17 绘画件投影屏幕矩形 y≈−4654~−4426（视口外，`status=O`），物理不可点 → 无法补播动作取证 | BLOCKED（几何受限，同 stage1d T2/T3 类） |
| C5 | 吾妻 | 单击身体区 1 次 → idleIndex **0→11**（TouchIdle1 `ATA.idle=11`）；第二次点击链推进到 touch_idle1 并播 `touch_drag1#0` | PASS |
| C6 | 吾妻 | TouchIdle1 区 `status=G` + `blockedEnable=true`，`actionAllowed('touch_drag12')=false`；enable 全文已录：含 touch_idle1~22、idle~idle18、touch_drag1~8/11/16~19，**不含自身 action `touch_drag12`** → 数据疑点，按规格不改代码绕过 | BLOCKED（数据疑点留证） |
| C7 | 信浓 | 单击身体区 3 次：`touch_idle1#0`→`touch_idle3#0`→`touch_idle6#0`，idleIndex 1→3→6。**非连续 1→2→3**：xinnong_6 的 model3.json 缺 touch_idle2/4/5/14 组，链组列表跳过缺失号（数据事实，非缺陷） | PASS（含数据注记） |
| C8-T1 | 光辉/信浓 | `motionGroups.idle[0].isLoop()===false`（setIsLoop 生效，idle 单次化不回退） | PASS |
| C8-T6 | 光辉 | 单击头 → `touch_head#0`；单击特殊 → `touch_special#0`；单击身体 → `touch_idle1#0` + idleIndex=1（走 findChainRule 链）。注：需待前一动作播完，播放门控期间异区点击被正常拦截（stage3 设计） | PASS |
| C8-T7 | 吾妻 | TouchDrag2 下拖 150px → **0.9992**（期望 1） | PASS（误差 0.08%） |
| C8-T8 | 吾妻 | TouchDrag7 上拖 90px → **135.34**（期望 180−45=135） | PASS（误差 0.25%） |
| C8-T9 | 吾妻 | TouchDrag6 下拖 100px → **9.936**（期望 10） | PASS（误差 0.64%） |
| C8-T10 | 吾妻 | TouchDrag8 单击 → 参数 0→**30**（circle target 到位停留）；可见绘画件 466→**472**（面板出现）；6s 后仍 472 且值仍 30（≥5s 保持、无自动回落）。截图：`sess_b9ee8125…/call_00_3h8DjcPAqG5Iyvbzq2b17131-…png` | PASS |
| C9 | 光辉 | 重叠区取证点 (488,248)：日志 `[Touch] 命中重叠 2 区：TouchSpecial=1319 / TouchDrag15=1317`，`hitZoneAt` 返回 **TouchSpecial**（ro=1319 高者）。**决定性反例**：按包围盒面积序应选 TouchDrag15（674924 < 690757）——渲染序修复确实改变了择序结果。全画布 530 个可命中点 renderOrder 全部非 0（取值 1313~1321，7 个不同值） | PASS（含修复前对照） |

补充发现（对后续有价值的引擎事实，**修正 stage1d 补充 1 与规格书 §0**）：

1. **真实渲染序 API 名称**：0.5.0-beta 的 coreModel **有** `getDrawableRenderOrders()`（复数、无参、
   返回整条 `Int32Array`，长度 = drawable 数，实测取值 0..N−1 互不相同），**没有** `getDrawableRenderOrder(i)`；
   规格书 §0/§2.2 所写 `coreModel.drawables.renderOrders` 亦不成立（`core.drawables === undefined`）——
   原始数组实际在 `core._model.drawables.renderOrders`。当前读取链已按实测更正为：
   `getDrawableRenderOrder(i) ?? getDrawableRenderOrders()[i] ?? _model.drawables.renderOrders[i] ?? drawables.renderOrders[i] ?? 0`。
2. **可见性方法存在但未启用**：`getDrawableDynamicFlagIsVisible(i)` 实测存在且返回 boolean（另有
   `getDrawableDynamicFlagVisibilityDidChange` 等同族方法）。规格书 §3 要求「不启用 dynamicFlags 可见性」，
   故维持 `?? true`，此项留给后续阶段决策。
3. **ATA.enable=[] 语义（本轮修复）**：光辉/信浓的 TouchIdleN 规则 ATA 形如 `{enable: [], idle: N, ignore:[...]}`。
   TouchChain 形态 B 原用 `if (ata.enable)` 把空数组当**空白名单** → 所有动作被拒（连点只涨 idleIndex 不播动作）。
   站点 deob `officialLive2DActionAllowed` 为 `enableActions.length > 0 && !Q(enable, name)`，即**空数组 = 无白名单放行**；
   TouchChain 自身形态 A 也是 `en.length ? new Set(en) : null`。已按站点语义修正形态 B（用户批准），
   与既有测试 `test_l2d_hotzone_stage5.py` **无冲突**（该文件未断言形态 B 写法）。
4. wuqi_3 链推进：C5 证实「单击身体区 → TouchIdle1 触发 → ATA.idle=11 → idleIndex 跳 11」通路成立，
   stage1d 补充 2 的「链推进缺位」疑问解除；C6 的 `touch_drag12 ∉ enable` 是纯数据疑点。
5. 区位置随姿态漂移的自动化测试要点：同一姿态下 `hitZoneAt` 复现性良好，但**任何一次动作/参数写入
   都会改变后续区位置**；自动化脚本必须在动作前即时重扫命中点，不可跨步骤缓存坐标。
