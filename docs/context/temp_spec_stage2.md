# 规格书 · stage2 v2（修正版）：Live2D 热区动态化 + 动作链引擎语义重建

> 供弱模型执行。v1 规格书已实现但**人工验收失败**（症状：①热区数量/范围/动作链与 l2d.su 完全不同；
> ②点击热区普遍无动作；③l2d.su 热区随模型动作动态变化，本地是静态的）。主模型复核
> `Temp/su_modelRuntime_deob.js` 后确认 v1 有 4 个引擎语义错误（§0），本文件为修正版，**覆盖 v1**。
> 在现有实现上修改：v1 已正确的部分保留（§2.1），错误部分按 §2.2~2.6 重做。
> 阶段0 站点核验**必须先做**（用户已解禁爬取 l2d.su）。
> 红线：不改 AGENTS.md、backend、官方 `frontend/`；不改 `l2d_touch.ts` 既有导出签名
> （`tests/test_l2d_touch_chain.py` 保护）；命令一律 PowerShell。

## 0. v1 失败根因（4 个，均有 deob 代码证据，弱模型可用 Temp/su_modelRuntime_deob.js 复核）

1. **命中择一优先级错了**。引擎 `hitAreasAt` 按渲染序取最上层后，`pickLive2DArea` 再按
   **优先级**跨候选区选择：①带 slide/offset（offsetX/Y≠0）的规则区 → ②有 action/motionGroup
   （可播放）的区 → ③首个。guanghui_9 的 4 个画布内规则区（TouchDrag1/2/3/15）offset 全 0 且
   无 action——被 ② 类的默认区（TouchSpecial/TouchHead/TouchBody，有 motionGroup）压住。
   v1 只按渲染序 → TouchDrag 规则区**永久遮蔽默认区** → 点哪都没有动作（症状②直接原因）。
2. **区域状态被静态化**。引擎每次命中用**实时** `live2DDrawableBounds`（当前顶点包围盒）、
   可见性、透明度判定，`scheduleLive2DHitAreaRefresh`（默认 3 帧）周期重建热区表与叠加层；
   渲染序也是每帧读。v1 在注册时采集 renderOrder/bounds 一次了事 → 热区静态（症状③）。
   模型动作会实时改变 drawable 顶点/透明度 → 站点的区会移动/变形/增减。
3. **动作播放模型错了**。引擎 `playMotionGroup(action)`：按 `motionMatchesAction` 过滤**全部**
   动作条目——条目的 group/名称/文件名（及归一化：trim+`[-\s]→_`）与 action 精确或归一化相等
   即命中——然后**顺序连播**（FORCE）。v1 用「parameter 必须是动作组→组内随机播一个」。
   后果：action 名不在组名集合时 v1 直接不播（`available.includes` 过严）；多命中时不连播。
4. **idle 链缺位**。引擎按 `live2dOfficialIdleIndex` 播 `idle`/`idleN` 组（`idleIndex>0?'idle'+N:'idle'`，
   guanghui_9 有 idle/idle1~30 组）；触摸动作结束后回到链 idle。v1 完全没有 idle 播放
   →「动作链随互动变化」的观感缺失。另：circle 手势的真实语义是**目标翻转**（当前目标值已接近
   target → 目标切回 startValue；否则切到 target），不是 v1 的「到位自动回落」。

> 与 `research_live2d_stage1.md` 冲突处（其 §1「站点行为=7 默认区+兜底」的播动作口径、§7 B 项
> 「渲染序择一」）以本文件 §0 + 阶段0 实测为准。

## 阶段0：站点行为核验（必做研究，先于实现；结论追加到 research_live2d_stage1.md 新章节「stage1b」）

方法：浏览器开 https://l2d.su/cn/skins/237031/ + DevTools（Network/Console，站点已解禁）；
deob 复核用 `Temp/su_modelRuntime_deob.js`。每条给「实测记录 + 与下文契约的异同」。

| # | 问题 | 方法 | 对实现的影响 |
|---|------|------|--------------|
| Q1 | 站点当前是否加载 touch.json 规则？ | Network 过滤 `touch.json`；叠加层区数 | 加载则对齐目标=规则驱动（本文件默认）；未加载则需改从站点静态模型目录取证 |
| Q2 | 头/身重叠处谁赢：TouchHead vs TouchDrag15、TouchBody vs TouchDrag1/2？ | 开叠加层记录边界；逐区点击看动作 | 验证 §2.2 优先级类；冲突以实测为准 |
| Q3 | 连点身体 5 次/头部 5 次，每次各播什么？是否 touch_idleN 递进？ | 逐次记录播放的动作名 | 决定 §2.4 body 链的实现口径 |
| Q4 | 动作播放期间点其他区是否有响应？结束后热区/行为是否恢复？ | 播放中点击+观察 | 验证 §2.4 播放门控 |
| Q5 | 拖动胸口/下摆时参数如何变（叠加层/参数面板）；单击身侧/头的点戳效果 | 逐区操作记录 | 校准 DRAG 增益与 circle 手感 |
| Q6 | 播放不同动作时，哪些 Touch* drawable 的透明度/包围盒变化（尤其 TouchDrag4/5 会不会激活）？ | 复用 stage1 的 fromMoc 钩子逐帧采样 | 确定动态剔除条件（透明度阈值等） |

## 2. 修正实现规格

### 2.1 保留不动（v1 已正确）

- `l2d_params.ts` 的 `clampChain`/`lookup103`/`reactSum`/`canvasNorm`/`ParamDriver` 持久化/`parameterRange`
  （仅 circle 语义按 §2.6 修正）；默认区伪规则注册（TouchSpecial/TouchHead/TouchBody）；
  `l2d_touch.ts` 零改动；`main.ts` 分发结构不动；存储键 `l2d-param:`/`l2d-touch:` 字面量不动。

### 2.2 l2d.ts 命中修正（修症状②③）

1. **实时区域状态**：命中判定时逐 drawable 现读 `getDrawableBounds` / `getDrawableVisibility` /
   `getDrawableOpacity`（防御式可选链，取不到按 1）/ `getDrawableRenderOrder`（取不到按 0）。
   **删除注册期缓存** renderOrder/bounds 的做法。可用包围盒 = 有限且 w>0、h>0、画布内。
2. **择一优先级**（引擎 pickLive2DArea 同款）：
   - 候选集 = 包围盒包含指针 + 可见 + 透明度>0.01 + interactive（TouchChain.isActionAllowed +
     手势类型匹配，沿用现 kind 逻辑）；
   - class1：规则区且 offsetX/offsetY ≠ 0；class2：区内动作名经 §2.3 名字索引能命中 ≥1 动作；
     class3：其余；
   - 类号小者优先；同类内按实时 renderOrder 降序；取第一个的 rule。
3. 透明度剔除阈值 0.01（阶段0 Q6 可校准）。

### 2.3 动作播放（新 `playAction`，修动作映射）

1. 模型加载后构建**动作名索引**：遍历 model3.json `FileReferences.Motions`（经
   `model.internalModel.settings`），展开条目 `{ group, index, name?, fileStem? }`；
   归一化函数 = `s.trim().replace(/[-\s]+/g, '_')`（引擎 G() 同款）。
2. `matchEntries(action)`：条目的 group/name/fileStem 及其归一化与 action **精确或归一化相等**
   即命中，返回全部命中条目（按模型文件顺序）。
3. `playAction(action): boolean`：命中条目**顺序连播**（FORCE 优先级；上一条结束后播下一条，
   用 pixi-live2d-display 的 motion Promise/结束事件；API 不可得时退化为只播第一条并在报告注明）；
   无命中返回 false（不播——TouchDrag1/2/3/15 的参数名不在索引中，与站点一致）。
4. `TouchChain.resolve` 的 `available` 改传「全部可匹配 action 名集」（组名∪动作名∪文件名去重），
   `available.includes(name)` 语义即自动正确，TouchChain 逻辑零改动。
5. `main.ts` 的 `play()` 改调 `renderer.playAction(action)`；`byPattern` 兜底路径同步改为
   `playAction(随机组名)`（组名必在索引中，等价旧行为）。

### 2.4 播放门控 + idle 链（修症状③动作侧 + 动作链观感）

1. **播放门控**：触摸触发的动作播放期间（`isPlayingTouchAction` 状态），新触摸互动只放行
   当前命中区自身的规则链（其余忽略）；动作结束清状态。`onInteraction` 前置此判断。
2. **idle 链**：动作结束后调 `playIdleMotion()`：组名 = `idleIndex > 0 ? 'idle'+idleIndex : 'idle'`
   （idleIndex 从 TouchChain 读，新增 getter；组内随机一条）。当前前端若无 idle 循环
   （pixi-live2d-display 只认大写 `Idle` 组，guanghui_9 没有），实现 app 层 idle 循环：
   模型加载后与每次触摸动作结束后排程 idle 播放，动作结束再排下一个。
3. **body 连点链**（明确标注：超越站点、还原游戏语义——站点引擎无点击计数器，阶段0 Q3 实测
   若发现站点有链行为则改按实测）：TouchBody 伪规则命中时走 main.ts 既有 touch_idleN 编号
   递进链（闲置重置/冷却 + `isActionAllowed` 门控）；TouchHead/TouchSpecial 直播各自动作。

### 2.5 叠加层（修症状③可见侧）

- ticker 每帧重画「当前可用」热区（画布内+可见+透明>0 的实时包围盒），guanghui_9 应 ≈7 个
  且边界随动作移动/变形。UI 按钮与接线不动（`tests/test_touch_debug_overlay.py` 保护）。

### 2.6 ParamDriver circle 修正

- 触发（poke）时目标翻转：`|当前目标值 - circleTarget| < 0.05` → 目标 = startValue，否则目标 =
  circleTarget；smooth 趋近不变；删除 v1 的「到位(<0.05)自动回落」。其余照 v1 §2。

## 3. 测试用例修订（`tests/test_l2d_hotzone_stage2.py`）

保留 v1 的 #1~#5、#8~#15 断言与构建断言，修订/新增：

| # | 用例名 | 断言点 |
|---|--------|--------|
| R1 | test_live_zone_state | l2d.ts 含 `getDrawableOpacity`；`getDrawableRenderOrder?.(` 出现在命中路径而非注册缓存 |
| R2 | test_pick_priority | l2d.ts 含 offsetX/offsetY 非 0 的 class 判断与 class 优先排序 |
| R3 | test_play_action_matching | l2d.ts 含 `playAction`、`fileStem`（或 file 展开）、`replace(/[-\s]+/g, '_')` |
| R4 | test_playback_gate | l2d.ts 或 main.ts 含 `isPlayingTouchAction`（或等价命名）与结束恢复 |
| R5 | test_idle_chain | 含 `'idle'+`（或等价组名选择）与 idle 循环排程 |
| R6 | test_circle_toggle | l2d_params.ts 含 target/startValue 的翻转分支（且删除 v1 自动回落断言 #9 中 `0.05` 语义改为比较分支） |

## 4. 步骤分类

**工具可完成**：rg 定位；`npm --prefix frontend-minimal run build`；三份 pytest；阶段0 的
Network/Console 核验；`Temp/su_modelRuntime_deob.js` 复核（pickLive2DArea/motionMatchesAction/
playLive2DIdleMotion/scheduleLive2DHitAreaRefresh）。

**需要判断**（报告说明取舍）：动作结束事件 API 不可得时的退化策略；优先级类与阶段0 实测冲突时
以实测为准并记录；idle 循环的排程间隔；DRAG 增益与透明度阈值校准；Q6 若 TouchDrag4/5 会被
激活，确认 §2.2 实时剔除天然覆盖（无需特判）。

## 5. 验收口径（对照 l2d.su 逐条）

1. 叠加层区数 ≈7（TouchSpecial/TouchHead/TouchBody/TouchDrag1/2/3/15），边界随动作实时移动。
2. 点头/身/特殊区 → 播放对应动作（touch_head/touch_body/touch_special 路径）；播放期间其他点击
   暂不响应，结束回 idle。
3. 连点身体 → touch_idleN 递进（§2.4.3 游戏语义扩展；与阶段0 Q3 实测对照）。
4. 胸口/下摆拖动 → 摩擦参数；身侧/头点戳 → 参数脉冲（circle 翻转）。
5. 无 touch.json 模型（mao_pro/xinnong_6 等）行为不回归。
6. `tests/` 三份 pytest 全绿 + `npm run build` 通过。

## 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_l2d_hotzone_stage2.py frontend-minimal/tests/test_l2d_touch_chain.py frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
