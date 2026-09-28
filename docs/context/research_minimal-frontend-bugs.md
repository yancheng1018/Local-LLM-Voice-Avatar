# 研究：minimal-frontend 现存两个 bug 的成因（research）

> 生成于 2026-09-15，/research-doc 产物。
> 本文只查成因，不含修复设计；修复另走 fix_instruction 流程。
> 方法：纯代码走查 + 静态数据取证（未起服务、未占 GPU/端口）。所有结论均附文件:行号。

---

## 1. 问题定义

minimal-frontend 的两个已知缺陷：**①** GUI 角色编辑器把人设（persona_prompt）留空保存后，服务器启动失败；
**②** 选择 shizuku 模型无法正常显示，且从 shizuku 切回正常模型后也无法显示。

两 bug **不共享根因**，是两条独立的缺陷链。

---

## 2. 现状：相关代码/配置/数据位置

| 层 | 位置 | 与本 bug 的关系 |
|----|------|----------------|
| GUI 写回 | `launcher/OpenLLMVTuber_GUI.py` `_save_character_inline()` | bug1 的写入端 |
| 配置校验 | `src/open_llm_vtuber/config_manager/character.py` | bug1 的抛错端 |
| 配置加载入口 | `run_server.py`、`config_manager/utils.py` `validate_config()` | bug1 的报错呈现端 |
| 模型登记表 | `model_dict.json`（仓库根，43 条） | bug2 的查找表 |
| 模型资产 | `live2d-models/shizuku/runtime/` | bug2 的被加载对象 |
| 渲染层 | `frontend-minimal/src/renderer/l2d.ts` | bug2 的加载/待机端 |
| 前端切换流程 | `frontend-minimal/src/main.ts` | bug2b 的状态机所在 |
| 后端切换 | `src/open_llm_vtuber/websocket_handler.py`、`service_context.py` | bug2 的后端侧（经查无缺陷） |

---

## 3. 关键发现

### Bug 1 —— GUI 人设留空致启动失败

**F1.1 抛错点确定：空字符串触发 pydantic 校验器。**

`persona_prompt` 是必填字段（`character.py:25`），且带显式非空校验器（`character.py:90-96`）：
`if not v: raise ValueError("Persona_prompt cannot be empty...")`。
空字符串 `''` 为 falsy，必然抛出。**这是有意设计**——角色自我认知名来自 persona_prompt（见 AGENTS.md 硬性契约），
人设不允许为空是规格要求，不是缺陷。

**F1.2 GUI 写入端确实无空值拦截（bug1 的直接成因）。**

`_save_character_inline()` 对 `conf_uid` 和 `character_name` 都做了留空兜底
（`OpenLLMVTuber_GUI.py:1648` 补 `{name}_001`；`:1651` 用 conf_uid 兜底并写日志），
但相邻的人设写回**没有任何判断**：

```
OpenLLMVTuber_GUI.py:1657:  cc["persona_prompt"] = self.char_edit_persona.toPlainText()
```

`toPlainText()` 在控件为空时返回 `''`，随即无条件写入 YAML。这是「同文件内两个必填字段有兜底、
第三个没有」的一致性缺口——正是 bug 的形态。

**F1.3 人设不走 `char_edit_fields` 通道，所以通用循环的「空值不写」保护也拦不住它。**

通用写回循环（`OpenLLMVTuber_GUI.py:1633-1639`）有意跳过「原本不存在且当前为空」的字段
（`:1637` `if not value and key not in cc: continue`）。但 `persona_prompt` 不在 `char_edit_fields` 里
（它是独立的 `char_edit_persona` QPlainTextEdit，见 `:1009`），因此在 `:1657` 被单独写回，
**绕过了通用循环的唯一一处空值保护**。

**F1.4 报错呈现：进程级终止，用户看到的是服务起不来（无 GUI 提示）。**

`validate_config()`（`config_manager/utils.py:133-139`）捕获 `ValidationError` 后
`logger.critical` + `logger.error` 再 `raise e`；调用点 `run_server.py:151` 处在 try 内，
`:165-167` 捕获后 `sys.exit(1)`。即**启动流程整体中止**，不是降级运行。
GUI 的「运行日志」只是转发子进程输出，未见针对性提示文案，故用户感知为「保存后服务器启动失败」而非
「人设不能为空」。

**F1.5 触发面比预想窄。** 只有**用户主动清空人设并点保存**才会命中：
新建角色模板已预填人设（`OpenLLMVTuber_GUI.py:1594` `f"You are {name}, a friendly AI assistant."`），
读取时也有默认空串回退（`:1536`）。所以这是「清空即坏」的边界，不是普遍性故障。

### Bug 2a —— shizuku 无法显示

**F2a.1 计划中的「四层路径解析断链」假设被证伪。** 逐层核查均正常：

| 层 | 结论 | 证据 |
|----|------|------|
| model_dict 登记 | 正常 | `model_dict.json:471-479`，url=`/live2d-models/shizuku/runtime/shizuku.model3.json`，与 mao_pro 等同款嵌套写法 |
| HTTP 静态路由 | 正常 | `server.py:126-129` 把 `live2d-models` 整目录挂到 `/live2d-models`，嵌套子目录自然可达 |
| 后端 switch | 正常 | `service_context.py:344-354` 先构造 candidate，失败回滚；无路径假设 |
| 前端加载 | **成功** | `l2d.ts:666` `Live2DModel.from(url)` 对合法 URL 正常返回 |

即入口文件嵌套在 `runtime/` 下**不是**问题——仓库内全部 43 个模型都是这个结构。

**F2a.2 moc3 / 贴图格式也被排除。** shizuku 的 `moc3` 版本字节为 **v3**，但仓库内
v1（shengluyisi_4、yichui_2）、v2、v4、v5 模型**全部在 `model_dict.json` 中登记且正常使用**，
故版本号本身不构成拒绝条件。5 张贴图均为标准 8-bit RGBA PNG（1024×1024），
`physics3/pose3/cdi3` 与 4 个 `motion3.json` 全部解析通过。

**F2a.3 真正成因：待机动作组名大小写不匹配 —— 前端查小写 `idle`，shizuku 只有大写 `Idle`。**

- shizuku 的动作组为 `['FlickUp','Tap','Flick3','Idle']`（`live2d-models/shizuku/runtime/shizuku.model3.json:15-36`），
  **只有大写 `Idle`，没有小写 `idle`**。
- 前端待机组名由 `idleGroupName()` 生成（`l2d.ts:776-779`）：
  `return idx > 0 ? 'idle' + idx : 'idle';` —— **产出小写 `idle`**。
- `playIdleOnce()` 用**精确相等**筛选（`l2d.ts:784`）：
  `this.motionEntries.filter((e) => e.group === gname)`，且组为空时静默 `return`（`:785`）。

于是加载成功后无任何待机动作播放，模型停在绑定姿势。

**F2a.4 反证：同为小写/大写混用的模型为何正常？**
`mao_pro` 的动作组是 `['Idle','Talk','']`（同样只有大写），却能正常工作。
原因在 `model_dict.json` 的 `idleMotionGroupName` 字段——但该字段**前端 0 次引用**，
`docs/context/live2d.md:79` 已把它标记为「死字段，改它无效」。
mao_pro 之所以看起来正常，是因为它另有 50 条 `emotionMap` 与 2 条 `tapMotions`（说话伴随 `Talk` 组、
表情切换）维持视觉活动；**shizuku 的 `emotionMap` 与 `tapMotions` 均为空**
（`model_dict.json:471-479`），没有任何替代动作路径，缺陷因此完全暴露。

对照 `guanghui_9 / feiteliedadi_3 / aerbien_3` 等碧蓝航线系模型，动作组里**同时**有小写 `idle`
与小写 `idle1..N`，恰好与前端小写约定吻合，所以一直没暴露这个问题。

**F2a.5 结论**：shizuku 属**模型资产与本项目前端动作组命名约定不匹配**，
而非路径登记/后端/路由问题。用户「直接删除 shizuku」在 bug2a 层面**成立**。

### Bug 2b —— 从 shizuku 切回正常模型后仍不显示

**F2b.1 后端侧无缺陷（已排除）。** 切换失败时后端**不发送** `set-model-and-conf`，
只发 `error`（`websocket_handler.py:685-691` 白名单拒绝、`:699-706` 加载异常），
前端因此保留原模型，不会进入半坏状态。白名单解析（`resolve_allowed_model_names`）
对不可用条目是 `warning` + 忽略，不会让切换失败。

**F2b.2 前端有一处真实缺陷：模型名在加载成功前就被记为「当前模型」，导致失败后无法重选同一模型。**

- `main.ts:90` 在收到 `set-model-and-conf` 时**立即**赋值
  `currentLive2DModelName = modelInfo.name;`——此时 `renderer.load()`（在 `:256` 才调用）**尚未完成**。
- `main.ts:394-395` 的重选守卫按该变量早退：
  `if (!modelName || modelName === currentLive2DModelName) return;`
- 加载失败时 `.catch`（`main.ts:266-271`）只做三件事：打日志、`ui.setStatus(...失败...)`、
  `ui.setLive2DModelEnabled(true)`。**它不回滚 `currentLive2DModelName`，也不恢复原模型。**

由此产生状态错位：变量声称「当前是 shizuku」，画面上却没有可用模型。
若用户再次选择 shizuku，会被 `:395` 守卫直接吞掉，**连请求都不会发出**——
表现为「怎么点都没反应」。

**F2b.3 「切回正常模型后也不显示」的机制：旧模型已被销毁，新模型从未建立。**

`l2d.ts:645-680` 的 `load()` 采用「先销毁、后加载」顺序：

```
l2d.ts:653:  this.model?.destroy();
l2d.ts:654:  this.model = null;
l2d.ts:666:  const model = await Live2DModel.from(modelInfo.url, {...});   // ← 此处才可能抛错
```

销毁（`:653`）发生在 `await` 之前，且**没有任何回滚**。因此一旦 `Live2DModel.from` 失败，
舞台必然处于「旧模型已删、新模型未加」的空场景状态。

需要说明的是，就 shizuku 而言 `Live2DModel.from` 本身**大概率不抛错**（F2a.3 的缺陷是静默的——
加载成功但无动作）。因此 bug2b 的「空画面」还叠加了前端**画布尺寸/布局**因素：
`layout()` 依赖新模型的尺寸信息，而 `kScale=0.6716` 等参数在 `:646-648` 已先行赋值给实例，
失败后这些状态残留会污染后续布局。**此路径本次未实测复现**（见第 7 章疑点 U2），
但其代码事实是确定的：**加载失败不恢复旧模型**，这一点独立于 shizuku 是否抛错。

**F2b.4 潜在交叉点：spine/实例切换。** `main.ts:41-51` 的 `ensureRenderer()` 在
Spine 与 Live2D 之间切换时会 `renderer.dispose()` 重建实例。shizuku 是 Live2D 模型，
不触发此分支，故与本 bug 无关；但它与 F2b.2 属同一类「先销毁、后建立、无回滚」模式，
**是同一处设计缺口的另一个出口**。

---

## 4. 可选方案对比

> 仅列候选方向，不展开设计（修复走 fix_instruction 流程）。

### Bug 1（人设留空）

| 方向 | 要点 | 评价 |
|------|------|------|
| A. GUI 侧拦截（保存时校验非空） | 与 `conf_uid`/`character_name` 既有兜底同构，给出明确提示 | **推荐落点**：缺陷在 GUI，同在 `_save_character_inline` 内已有两处先例 |
| B. 后端放宽校验 | 允许空人设 | **不可取**：违反硬性契约（自我认知名来自 persona_prompt），大纲已明令排除 |
| C. 启动时报错文案友好化 | 把 ValidationError 渲染成可读提示 | 可作 A 的补充，但不解决「坏配置已落盘」 |

### Bug 2a（shizuku 不显示）

| 方向 | 要点 | 评价 |
|------|------|------|
| D. 删除 shizuku 模型 | 从 `model_dict.json` 与磁盘移除 | 用户已接受；**仅治 bug2a**，不能解释 bug2b（F2b.2 独立存在） |
| E. 给 model3.json 补小写 `idle` 别名组 | 引用原有动作文件 | 与 `live2d.md:95` 记载的 `Idle`/`Talk` 缺失修复方式同构；治本但改资产 |
| F. 前端组名匹配改为归一化/容错 | 复用既有 `normalizeMotionName()`（`l2d.ts:36`） | 一处修全体受益；但会影响所有模型行为，需回归验证 |

### Bug 2b（切除回失败）

| 方向 | 要点 | 评价 |
|------|------|------|
| G. 失败时回滚 `currentLive2DModelName` | 在 `main.ts:266` 的 catch 中复位 | 直接对治 F2b.2，改动最小 |
| H. `currentLive2DModelName` 改到 load 成功的 then 里赋值 | 移动 `:90` 的赋值时机 | 从根上消除「未成功即视为当前」，但需核对 `:312` 等依赖点 |
| I. `load()` 改为「先建后销毁」或失败保留旧模型 | `l2d.ts:645-680` 顺序调整 | 治 F2b.3；改动面较大，涉及 destroy 语义与 touch/param 解绑 |

---

## 5. 结论与建议

**结论**：两 bug 根因独立，均非路径/配置加载等基础设施问题。

1. **Bug 1（高置信）**：`OpenLLMVTuber_GUI.py:1657` 无条件写入空人设，绕过通用循环的空值保护；
   后端按规格拒绝空人设（`character.py:90-96`），`run_server.py:165-167` 直接 `sys.exit(1)`。
   缺陷在 **GUI 写入端缺校验**，后端行为符合设计。

2. **Bug 2a（高置信）**：**不是**路径登记问题。shizuku 动作组只有大写 `Idle`，
   前端待机组名硬编码为小写 `idle`（`l2d.ts:778`）且精确匹配（`:784`），
   叠加 `emotionMap`/`tapMotions` 皆空，导致加载成功但完全静止。
   计划中「四层路径解析」的四层**全部正常**，该假设应作废。

3. **Bug 2b（高置信，含一处待实测）**：`currentLive2DModelName` 在加载成功前赋值（`main.ts:90`）
   与重选守卫（`:395`）组合，使失败后**无法重选同一模型**；
   `l2d.ts:653` 的「先销毁后加载、无回滚」使失败后画面必然为空。
   这两点独立于 shizuku 是否存在。

**对「删除 shizuku 是否足够」的判定**：**不足够**。
删除仅消除 bug2a 的触发源；bug2b 的机制（守卫吞掉重选请求 + 加载失败不恢复旧模型）
在与 shizuku 无关的模型上同样会发作——最典型的是 **Spine/Live2D 混切**（`main.ts:41-51`）
或任何一次偶发的资源加载失败。**建议 bug2b 单独立项。**

**建议优先级**：Bug 1 的 GUI 校验（改动小、用户可感知、有既有先例）→ Bug 2b 的状态回滚
→ Bug 2a 的资产/前端组名决策（需在 D/E/F 间做一次裁决）。

---

## 6. 遗留候选（不在本次范围）

- `idleMotionGroupName` 已是死字段（`live2d.md:79`），但 `model_dict.json` 与
  `OpenLLMVTuber_GUI.py:2015` 仍在写它。是否清理属独立议题。
- `main.ts:41-51` 的 `ensureRenderer()` 与 F2b.2/F2b.3 同属「先销毁后建立无回滚」模式，
  是否一并收敛为统一的重建回滚策略，需单独评估。
- 仓库内 17 个已登记模型的 moc3 为 v1/v2/v4（非 v5），本次确认它们可正常工作，
  但**未逐个实测**；若后续出现个别模型异常，此清单可作为排查起点。

---

## 7. 附录

### 7.1 涉及文件与行号清单

| 文件 | 行号 | 内容 |
|------|------|------|
| `launcher/OpenLLMVTuber_GUI.py` | 1029 | 保存按钮绑定 `_save_character_inline` |
| | 1009 | 人设控件 `char_edit_persona`（独立于 `char_edit_fields`） |
| | 1594 | 新建角色模板预填人设 |
| | 1633-1639 | 通用写回循环；`:1637` 空值保护（不覆盖 persona） |
| | 1648 / 1651 | conf_uid / character_name 留空兜底（persona 缺失对应处理） |
| | **1657** | **无条件写入 persona_prompt（bug1 根因）** |
| | 2015 | 启动器另写 `idleMotionGroupName`（死字段） |
| `src/open_llm_vtuber/config_manager/character.py` | 25 | `persona_prompt` 必填 |
| | 90-96 | 非空校验器抛 `ValueError` |
| `src/open_llm_vtuber/config_manager/utils.py` | 133-139 | `validate_config` 捕获后 `raise e` |
| `run_server.py` | 151 / 165-167 | 调用校验；异常 `sys.exit(1)` |
| `model_dict.json` | 471-479 | shizuku 条目（含空 `emotionMap`/`tapMotions`） |
| `live2d-models/shizuku/runtime/shizuku.model3.json` | 15-36 | 动作组仅含大写 `Idle` |
| `src/open_llm_vtuber/server.py` | 126-129 | `/live2d-models` 静态挂载（正常） |
| `src/open_llm_vtuber/service_context.py` | 344-391 | `switch_live2d_model` 候选构造 + 回滚 |
| `src/open_llm_vtuber/websocket_handler.py` | 33-59 | `resolve_allowed_model_names` |
| | 623-718 | 切换处理；失败只发 error 不发 `set-model-and-conf` |
| `frontend-minimal/src/main.ts` | **90** | **加载前赋值 `currentLive2DModelName`（bug2b 根因之一）** |
| | 41-51 | `ensureRenderer` 销毁重建（同类缺口） |
| | 256-271 | load().then/.catch；catch 不回滚状态 |
| | **395** | **重选守卫（bug2b 根因之一）** |
| `frontend-minimal/src/renderer/l2d.ts` | 36 | `normalizeMotionName()`（潜在修复可复用） |
| | 645-680 | `load()`；`:653` 先销毁无回滚 |
| | 776-779 | `idleGroupName()` 产出**小写** `idle` |
| | 782-790 | `playIdleOnce()`；`:784` 精确匹配、`:785` 静默返回 |
| `docs/context/live2d.md` | 79 / 84-95 | `idleMotionGroupName` 死字段 + 硬编码组名约定 |

### 7.2 取证方法与证据强度

- **直接读取**：源码、`model_dict.json`、model3/motion3/physics3/cdi3/pose3、PNG 头、moc3 头字节。
- **排除性证据**：moc3 版本分布统计（v1:2, v2:5, v3:1, v4:12, v5:23）证明版本号非拒绝条件；
  各模型动作组大小写对照表证明缺陷为 shizuku 与前端约定的个案不匹配。
- **未采用的路径**：`Live2DCubismCore` 在 Node 下无法初始化 WASM（所有模型同样报
  `Cannot read properties of undefined`），无法据此区分，故改用字节级/JSON 级取证。

### 7.3 待确认疑点（供裁决）

- **U1**：bug2a 的修复落点选 D（删模型）/ E（补别名组）/ F（前端归一化）？
  涉及「改资产 vs 改前端」的取向，建议由强模型裁决。
- **U2**：F2b.3 中「shizuku 加载失败是否真的抛错」未实测。若 shizuku 实际加载成功（F2a.3 为静默缺陷），
  则 bug2b 的「空画面」还需一次实测复现来确认是否由布局/尺寸残留导致。
  **本次未实测**（避免占 GPU/端口）。建议在修复验证阶段补一次带 DevTools 的实测。
- **U3**：`currentLive2DModelName` 的赋值时机改法（G 回滚 vs H 移动赋值点）
  可能影响 `main.ts:312` 的 `live2d-models` current 回退逻辑，需在修复设计中一并核对。
