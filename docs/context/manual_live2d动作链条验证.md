# 人工操作手册 · Live2D 动作链条验证（供用户执行）

> 2026-09-17 产出，配套 `research_live2d动作链条修正.md`（调查报告）。
> 本手册只列**需要人工在浏览器里做**的操作，每条都写明「操作 → 记录什么 → 结论怎么用」。
> 代码侧无需改动；全程只观察与记录。
>
> ## ✅ 执行状态：T1~T8 已于 2026-09-17 全部完成
>
> **结果已回填到 `research_live2d动作链条修正.md`**（§1 结论速览、§5.0 新根因、§5.4/§5.6 实测修正）。
> 本轮实测带来两处重要修正：
> - **G1/G3/T6 的真根因**：参数写入挂点被框架帧末还原（报告 §5.0，我随后用浏览器复现确认）。
> - **S3/F1 实为站点同款行为，不是缺陷**（T3/T5 实测）。
>
> 下方 §0~§5 为**原始手册**，保留供后续复测/回归使用（如阶段 0 修复后的验收）。
>
> ---

## 0. 准备（两条环境）

### 0.1 本地环境

```bash
cd C:\Coding\Application\v1.2.1_Open-LLM-VTuber-v1.2.1-zh
uv run run_server.py            # 后端 12393
```

浏览器打开 **http://localhost:12393/m/**（极简前端；后端已挂载 `frontend-minimal/dist`）。

> 若改过前端源码，先 `cd frontend-minimal && npm run build` 再刷新页面。
> 开发热更新可改用 `npm run dev`（http://localhost:5173，代理已配好）。

**本手册用到的界面控件**（顶栏，从左到右）：

| 控件 | 用途 |
|------|------|
| 角色下拉 / 模型下拉 | 切角色、切 Live2D 外观 |
| `🔍 热区：关` | **热区叠加层开关**（本手册主要工具，点一下变「开」） |
| `🧪 调试栏：关` | 左侧调试面板：显示 / 动作 / **参数滑条** / 部件 |
| `↺ 复位模型` | 停动作 + 清链状态 + 参数复位（**纯视觉操作，不影响对话**） |

**打开控制台**（F12 → Console），本手册用到的两个只读探针：

```js
// ① 当前链 idleIndex（左上角叠加层也有同样读数）
__vtuber.renderer.chainIdleIndex()

// ② 读任意模型参数当前值（把 ParamAngleX 换成 touch_drag3 等）
__vtuber.renderer.model.internalModel.coreModel.getParameterValueById('touch_drag3')

// ③ 当前全部热区状态（ok/H/O/G/T；G=被白名单门槛拦住）
__vtuber.renderer.touchZoneStates().map(z => z.name + '=' + z.status + (z.blockedEnable ? '(blocked)' : ''))
```

> `__vtuber.renderer` 在控制台输入 `__vtuber.renderer` 可确认可用；切模型后该引用仍指向当前实例。

### 0.2 站点环境（l2d.su）

1. 打开 **https://l2d.su/cn/**（中文站）。
2. 顶部搜索框输入**舰船名**（如「光辉」「狮」「信浓」「腓特烈大帝」），进入该船的查看页。
3. 若该船有多个皮肤，**在皮肤列表里选中与本地一致的皮肤名**：

   | 本地模型 | 站点船名 | 站点皮肤名（务必选这个） |
   |---------|---------|----------------------|
   | guanghui_9 | 光辉 | 幽影徘徊之夜 |
   | shi_3 | 狮 | 夜巷中的诱引者 |
   | xinnong_6 | 信浓 | 相融一梦 |
   | feiteliedadi_3 | 腓特烈大帝 | 相会于盛夏之夜 |

4. **站点侧同样先清状态**：F12 → Console → 执行 `localStorage.clear()` → 刷新页面。
   （站点会把链进度/参数存 localStorage，不清会带上次的残留状态，导致对照失真。）

> 站点调试面板：查看页左侧栏可显示热区与参数（若有「显示热区/参数」类开关，请打开）。

## 1. 数据核验（T1：最高优先级，3 分钟，无需操作模型）

**目的**：确认报告 §5.1b 的「9 个模型 touch.json 与站点皮肤错配」结论。

**操作**：

```bash
cd C:\Coding\Application\v1.2.1_Open-LLM-VTuber-v1.2.1-zh
python docs/assets/su_survey_touch_json.py . --fetch
```

**记录**：命令输出的最后一段（`OK: N/36` 与 MISMATCH 清单）。

**判读**：
- 若输出与报告 §5.1b 表格一致（`shi_3`/`feiteliedadi_4`/`feiteliekaer_4`/`mojiaduoer_4`/`wuzang_4`/
  `ougen_8`/`tiancheng_cv_3`/`dafeng_7`/`guandao_3` 共 9 例 MISMATCH）→ **结论成立**，
  这 9 个模型的问题应先修数据再查代码。
- 若站点已更新导致结果不同 → 以新结果为准，报告需订正。

**产出**：把命令输出贴回给我即可（无需截图）。

## 2. 站点基准取证（T2~T5，决定后续修法）

> 每条都要求「先按 0.2 清站点状态，再操作，再记录」。操作时请**录屏**或至少逐步截图，
> 因为动作是瞬时的，事后无法回看。

### T2：guanghui_9 drag3 → drag4/5 与「三档模式」（对应症状 G1/G3）

**站点操作**：
1. 选光辉 → 皮肤「幽影徘徊之夜」→ `localStorage.clear()` → 刷新。
2. 单击模型身上的 **touch_drag3** 热区（若站点有热区显示，先打开确认位置）。
3. 观察并记录：
   - 屏幕里出现了哪些热区？（报告预测：drag4、drag5 出现）
   - 人物身上出现的三个「滑块」/热区分别在**什么位置**？
4. 按住 **touch_drag4** 拖动，从最上拖到最下，分三段记录人物身上的变化：
   - 上段 → 出现什么动作/什么热区？（报告预测：TouchIdle17 类）
   - 中段 → ？（预测 TouchIdle4）
   - 下段 → ？（预测 TouchIdle1 + TouchIdle22）
5. 松开后**等 10 秒**：画面是保持还是自动复位？

**记录表**（请按此填写）：

| 步骤 | 观察项 | 站点表现 |
|------|-------|---------|
| 3 | drag3 点击后出现的热区 | |
| 4-上 | 拖到最上时的动作/热区 | |
| 4-中 | 中段 | |
| 4-下 | 最下 | |
| 5 | 松手 10s 后是否复位 | |

**判读**：报告认为站点靠「参数目标层每帧回写 `touch_drag4`」实现三档切换；
若站点表现为**连续变化**而非三档跳变，则报告的「三档=参数阈值」推断需修正。

### T3：shi_3 touchhead 后 touch_drag10（对应症状 S3）

**站点操作**：
1. 选狮 → 皮肤「夜巷中的诱引者」→ `localStorage.clear()` → 刷新。
2. 打开站点参数面板（若有），找到 `touch_drag10`，记下初值。
3. 单击 **touch_head** 热区，等动作播完。
4. 再看 `touch_drag10` 的值。

**记录**：初值 = ____ ；touchhead 播放后 = ____ 。

**判读**：站点若保持 **0**（或被短暂影响后回到 0）→ 证实「站点有参数权威层」，
本地读到的 4.0 是缺该层所致（报告 §5.2 结论成立）。

### T4：shi_3 初始热区清单（对应症状 S1/S2）

**站点操作**：
1. 同上选狮 shi_3 皮肤，清状态刷新。
2. 打开站点热区显示。
3. 记录**初始状态下屏幕上可见的热区名**（或截图）。
4. 单击 **TouchIdle1**，等动作播完，再记录可见热区。

**记录**：初始可见 = ____ ；TouchIdle1 后 = ____ 。

**判读**：对照报告 §5.1——本地只有 TouchIdle1/2 两条 Idle 规则，
站点应有 TouchIdle1~45 的完整集合；若站点初始就能看到 TouchIdle27 等区，
则「本地缺规则数据」结论成立。

### T5：feiteliedadi_3 drag3 与 TouchDrag6（对应症状 F1/F2）

**站点操作**：
1. 选腓特烈大帝 → 皮肤「相会于盛夏之夜」→ `localStorage.clear()` → 刷新。
2. **先记录**：初始状态下 **TouchDrag6** 是否可点？点一下有无反应？
3. 单击 **TouchDrag3**，观察：屏幕上还剩哪些热区？drag4 是否出现且**保持**（不自动复位）？
4. 松开后等 10 秒，再点一次 TouchDrag3，看是否仍可点。

**记录表**：

| 步骤 | 观察项 | 站点表现 |
|------|-------|---------|
| 2 | 初始 TouchDrag6 可点？ | |
| 3 | drag3 后剩余热区 | |
| 3 | drag4 是否保持 | |
| 4 | 再次点 drag3 是否可点 | |

**判读**：报告 §5.6 推测「TouchDrag6 初始不可点是站点同款行为」。
若站点初始**可点**，则本地 `ATA.idle` 门槛实现有误，需修；若**不可点**，维持现状。

## 3. 本地读数取证（T6~T8，配合修复验收）

> 这些数据在修复实施前后各做一次，用于证明修复有效。

### T6：本地 guanghui_9 drag3 半显现场（对应症状 G1）

1. 本地页面 → 选 guanghui_9 → 顶栏点开 `🔍 热区：开` 和 `🧪 调试栏：开`。
2. F12 Console → `localStorage.clear()` → 刷新（保证初始态）。
3. 单击 touch_drag3。
4. **截图**：①模型画面 ②热区叠加层（含左上角 idleIndex 读数）③调试栏参数区（滚到 `touch_drag3`/`touch_drag4`/`touch_drag5` 附近）。
5. Console 依次执行并记录输出：

```js
__vtuber.renderer.chainIdleIndex()
__vtuber.renderer.touchZoneStates().map(z => z.name + '=' + z.status).join(', ')
__vtuber.renderer.model.internalModel.coreModel.getParameterValueById('touch_drag3')
__vtuber.renderer.model.internalModel.coreModel.getParameterValueById('touch_drag4')
__vtuber.renderer.model.internalModel.coreModel.getParameterValueById('touch_drag5')
```

**判读**：`touchZoneStates()` 里 drag4/drag5 的状态是关键——
`G` = 被白名单拦（门槛问题）；`T` = 透明被剔除；`O` = 几何无效；不在列表 = 未注册。
配合参数读数判断「半显」是参数没到位还是热区判定剔除。

### T7：本地 guanghui_9 死锁现场（对应症状 G2）

1. 本地 → guanghui_9 → 热区叠加层开。
2. 单击 **touch_head**（模型头部）→ **在其动作播放中**（约 1~2 秒内）单击 touch_drag3。
3. 等动作全部结束（约 5 秒），记录：
   - 截图模型画面 + 叠加层。
   - Console 执行：

```js
__vtuber.renderer.chainIdleIndex()
__vtuber.renderer.isPlayingTouchAction
__vtuber.renderer.touchZoneStates().map(z => z.name + '=' + z.status).join(', ')
```

**判读**：`touchZoneStates()` 若返回**空数组或全非 ok**，则「全屏无热区」属实；
结合 `chainIdleIndex()` 判断是链状态卡死（idleIndex 进了异常值）还是门槛全拒。
若 `isPlayingTouchAction` 仍为 `true` → 播放门控未清除（真死锁，代码缺陷）。

### T8：本地 xinnong_6 自动 idle（对应症状 X1）

1. 本地 → 切到 xinnong_6 → `localStorage.clear()` → 刷新。
2. **不做任何点击**，静置 3 分钟。
3. 每 30 秒记录一次：叠加层左上角 `idleIndex` 读数 + 模型是否自行播了动作。

**记录**：是否有自动动作？出现在第几秒？`idleIndex` 是否变化？

**判读**：报告 §5.5 结论是「宿主库 `Idle` 组自动随机播放」（xinnong_6 的 `Idle` 组含 15 条动作）。
若静置时动作自发播放且 `idleIndex` **不变**（仍是 0）→ 证实是库行为而非链状态问题。

## 4. 汇总回传格式

> **2026-09-17 实测结果（原样留档，供后续对照）**：

```
T1 数据核验：OK=25/36；MISMATCH=9 + SITE_NO_RULES=2
   错配：dafeng_7 / feiteliedadi_4 / feiteliekaer_4 / guandao_3 / mojiaduoer_4 /
        ougen_8 / shi_3 / tiancheng_cv_3 / wuzang_4
   站点无规则：chaijun_4(17) / shengluyisi_4(54)

T2 drag3/drag4 站点：点 drag3 后出现 TouchDrag5、TouchDrag4、TouchIdle4（人物身上是 TouchIdle4，非滑块）；
   人物左侧两个滑块（TouchDrag4/TouchIdle4 对应）。
   拖 drag4 从上到下：TouchIdle17 → TouchIdle4 → TouchIdle1+TouchIdle22 → TouchIdle4 → TouchIdle17（连续渐变）
   松手 10s：不复位

T3 shi_3 drag10：初值 0.00；touchhead 后 4.0（与本地相同），但站点模型无变化（面板与模型脱钩）

T4 shi_3 初始热区：TouchHead, TouchSpecial, TouchIdle1, TouchBody, TouchIdle27
   TouchIdle1 后：TouchIdle2, TouchIdle32, TouchIdle17, TouchIdle19, TouchIdle26, TouchIdle8, TouchIdle37

T5 feiteliedadi：初始无 TouchDrag6、无 TouchDrag3（点 TouchDrag1 后才出现两者）；
   点 TouchDrag3 后剩 TouchDrag2、TouchDrag4，长时间保持不复位；TouchDrag3 消失不可再点

T6 本地 drag3：zoneStates 中 drag1/2/3=ok，drag4/5=T；点后 drag3=O:2.37、drag4/5=O；
   模型读数 touch_drag3/4/5 全为 0；idleIndex=0

T7 本地死锁：isPlayingTouchAction=false；idleIndex=0；
   zoneStates 仅 TouchDrag2=ok、TouchBody=ok，其余 O/G（drag 区全 O）

T8 本地 xinnong 静置：3 分钟内 14 次自动动作，idleIndex 恒 0（纯库 Idle 组行为）
```

## 5. 注意事项

- **站点与本地都要先 `localStorage.clear()`**：两边都会持久化链状态与参数，不清会互相污染对照。
- **录屏优先**：动作瞬时性强，截图易漏关键帧；手机拍屏也可接受。
- **不要改任何代码/配置**：本轮是取证，发现异常只记录。
- 若某步在站点上找不到对应热区（例如站点不显示热区名），**记录「找不到」即可**，不要猜测。
- 站点若在操作中弹出登录/广告遮挡，记录后跳过该步，不强行绕过。
