## Live2D 动作 / 表情实现约定

> 改 Live2D 动作实现前**必读**。前端是**已构建产物**（`frontend/assets/main-*.js`，无源码），
> 只能顺应它的既有契约，改不了它。

### 完整链路（一次表情是怎么发生的）

```
model_dict.json 的 emotionMap（关键词 -> 表情索引/名字）
        ↓  service_context.construct_system_prompt() 注入 emo_str 到 live2d_expression_prompt
LLM 在回复里输出 [joy] 这样的关键词
        ↓  agent/transformers.py 的 actions_extractor 装饰器
   live2d_model.extract_emotion(句子) -> [表情值列表] 填入 Actions.expressions
        ↓  conversations/conversation_utils.py -> utils/stream_audio.prepare_audio_payload()
WebSocket 消息 {"type":"audio", ..., "actions":{"expressions":[...]}}
        ↓  前端取 actions.expressions[0] -> setExpression()
Live2D 模型切到对应表情
```

关键词不会念出来也不会显示在字幕里：TTS 文本由 `tts_filter` 的 `ignore_brackets`
剔除所有括号内容（`utils/tts_preprocessor.py`）；显示文本由 `display_processor`
调用 `live2d_model.remove_emotion_keywords()` 剔除（2026-09-10 修复，此前该方法
从未被调用，字幕会原样显示 `[joy]`）。

### 各文件的职责

| 文件 | 职责 |
|------|------|
| `model_dict.json` | 每个模型的配置（emotionMap / tapMotions / 缩放位移等） |
| `src/open_llm_vtuber/live2d_model.py` | 只在后端**准备数据**，不发送任何东西。`set_model` 构造 `emo_map`/`emo_str`；`extract_emotion` 把 `[key]` 映射成值；`remove_emotion_keywords` 剔除关键词 |
| `prompts/utils/live2d_expression_prompt.txt` | 指示 LLM 用 `[关键词]` 表达表情。其中 `[<insert_emomap_keys>]` 会在运行时被替换为该模型 emotionMap 的键列表 |
| `src/open_llm_vtuber/agent/transformers.py` | `actions_extractor` 装饰器，**逐句**提取表情；带任意 `think` 标签的句子一律跳过（与 TTS 静音条件对齐）。`display_processor(live2d_model=...)` 负责剔除显示文本中的关键词 |
| `src/open_llm_vtuber/agent/output_types.py` | `Actions` 数据类：`expressions` / `pictures` / `sounds` |
| `src/open_llm_vtuber/utils/stream_audio.py` | `prepare_audio_payload()` 组装 WS 的 `audio` 消息 |
| `src/open_llm_vtuber/service_context.py` | `init_live2d()`；`construct_system_prompt()` 里替换 `[<insert_emomap_keys>]`（**emo_map 为空时跳过该提示词**，避免诱导 LLM 编造关键词） |
| `src/open_llm_vtuber/live2d_model.py` | `_lookup_model_info()` 按 `name` 在 model_dict.json 里查表 |

### 硬性契约（改了会崩 / 不生效）

1. **模型必须登记在 `model_dict.json`**，且 `name` 与 `live2d-models/` 下的文件夹名一致。
   查不到时 `_lookup_model_info` 抛 `KeyError`，`init_live2d` 捕获后只记 critical 并继续，
   结果就是**没有 Live2D**（不容易发现，注意看日志 `Unable to find ... in model_dict.json`）。
2. **`emotionMap` 键必须存在**（可以是空对象 `{}`）。`live2d_model.set_model` 直接做
   `self.model_info["emotionMap"].items()`，缺这个键会 `KeyError`。
3. **`url` 必须以 `.model3.json` 结尾**。前端会 `new URL(url)` 后剥掉该后缀推导模型名与
   baseUrl，再拼回 `.model3.json` 去 fetch。嵌套子目录可以（见 `mao_pro` 的例子）。
4. **只支持 Cubism 3/4**（`.model3.json`）。前端用的是 Cubism 4 SDK
   （`CubismModelSettingJson` / `CubismMoc`），**不支持 Cubism 2.1 的 `.model.json`**。
   `frontend/libs/live2d.min.js` 是遗留文件，`index.html` 并未引用，别被它误导。
5. **emotionMap 的键会被转成小写**（`{k.lower(): v}`），`extract_emotion` 也先
   `str.lower()` 再匹配，所以关键词大小写不敏感。
6. **emotionMap 的值**：数字 = 表情**索引**（前端 `getExpressionName(n)` 转名字），
   字符串 = 表情**名字**（直接 `setExpression(name)`）。两种前端都支持。
7. `Actions.expressions` 是**列表**，但前端只取 **`expressions[0]`**。
   想一次触发多个表情需要改前端（做不到，见开头的说明）。

### model_dict.json 字段实测情况

| 字段 | 前端是否使用 | 说明 |
|------|--------------|------|
| `name` | ✅ | 后端查表键 + 启动器下拉显示 |
| `url` | ✅ | 必须以 `.model3.json` 结尾 |
| `emotionMap` | ✅ | 后端必需；关键词→表情值 |
| `tapMotions` | ✅ | 点击热区→动作，配合模型自身的 hit areas |
| `kScale` | ✅ | 前端会 **×2**（`Number(kScale\|\|.5)*2`）；已由 `fit_live2d_scale.py` 按各模型画布尺寸自动计算（见下） |
| `initialXshift` / `initialYshift` | ✅ | 初始位移 |
| `pointerInteractive` | ✅ | 默认开启（`pointerInteractive !== false`） |
| `scrollToResize` | ✅ | 出现在前端默认值里 |
| `idleMotionGroupName` | ❌ **前端 0 次引用** | 死字段，改它无效（前端硬编码 `Idle` 组名，见下节） |
| `kXOffset` | ❌ **前端 0 次引用** | 死字段 |
| `defaultEmotion` | ✅ | 回 IDLE 时 `resetExpression` 优先用它（表情名或索引），不配则回退表情 0；model_dict.json 目前无模型配置 |

> 「前端是否使用」的依据是在 `frontend/assets/main-*.js` 里 grep 字段名。
> 升级前端后需要重新核对，尤其是 `idleMotionGroupName` 这类可能被重新启用的字段。

### 前端动作（motion）触发约定（2026-09-10 实测）

前端只认两个**硬编码动作组名**，与 model3.json 的组名**大小写完全一致**才会播放：

- `Idle`：空闲循环 `startRandomMotion("Idle", 1)`。组名缺失或大小写不匹配 → 空闲时模型静止。
- `Talk`：每播放一个音频分片时 `startRandomMotion("Talk", 2)`。缺失 → 说话无伴随动作。
- 点击：读 model_dict.json 的 `tapMotions`，值格式 `{"热区名": {"动作组": 权重}}`，
  优先级 Force(3)。模型无 HitAreas 或热区未命中时走「合并所有权重随机选组」分支。
  注意 HitAreas 是 model3.json 的**顶层键**（不在 FileReferences 里）。
- **修复方式**：给 model3.json 加 `"Idle"` / `"Talk"` 别名组（引用原有动作文件）即可，
  纯数据改动。xinnong_6、mao_pro 已于 2026-09-10 完成。
- 回 IDLE 状态时前端 `resetExpression` 优先用 `defaultEmotion`，否则表情 0。
- WS `set-model-and-conf` 里的 `model_info` 是 model_dict.json 条目的**原样透传**
  （`websocket_handler.py` 两处），条目新增字段零后端改动直达前端。
- 后端**无法**主动触发 motion：前端不消费 `actions.pictures` / `actions.sounds`，
  也没有 motion 类 WS 消息类型；`window.Live2DDebug.playMotion` 仅控制台可用。
- `volumes` / `slice_length` 前端收下后不用（口型同步走 `_wavFileHandler` 直解 wav），
  属死数据通路。

### 模型显示尺寸（kScale）自适应（2026-09-11）

- 前端渲染缩放 = moc3 **逻辑画布**尺寸 × `CurrentKScale`（= kScale×2）。
  逻辑画布 = CanvasInfo 像素尺寸 / PixelsPerUnit，解析方法：u32@0x44 → CanvasInfo
  文件偏移，该处 5 个 float = PixelsPerUnit, OriginX, OriginY, CanvasWidth(px),
  CanvasHeight(px)（moc3 v3~v5 通用，依据 OpenL2D/moc3ingbird 的格式逆向）。
- 各模型逻辑画布差异巨大（mao_pro 高 1.45 单位、xinnong_6 高 20、碧蓝航线系列
  12~32），共用 kScale=0.5 时大画布模型必然溢出屏幕、只能看到局部。
- **`fit_live2d_scale.py`** 自动计算并写回 model_dict.json（自动备份 .bak）：
  `kScale = 0.724 / 逻辑高`（0.724 = 0.5 × mao_pro 逻辑高 1.448，以其显示正常标定），
  宽度兜底 `kScale ≤ 1.0 / 逻辑宽`，夹在 [0.01, 3]。启动器导入新模型后可再跑一次。
- **游戏系倍率修正**：游戏模型画布含大量动画余量，人物主体只占画布一部分，
  按整画布适配会偏小。逻辑画布高 > 5 的模型额外 ×1.8（2026-09-11 用户目测
  校准）；小画布标准模型（mao_pro 1.45 / shizuku 1.08 / oppai_bunny 0.38）与
  游戏系（12~32）之间有清晰断层。倍率不对时改脚本顶部 `GAME_FACTOR` 或单独
  改某模型 kScale。
- 曾尝试解析 moc3 顶点数据自动求人物包围盒（用户需求「全自动」），因 keyform
  多层间接索引（artMeshKeyforms 数 ≠ artMeshes 数、需经 keyformSourcesBeginIndices
  间接定位）且无可靠格式文档而放弃；如要重试，可考虑在 Node 里加载 Cubism Core
  官方 WASM 用 `drawables.vertexPositions` API——卡点是本地拿不到 core 的 wasm
  二进制（官方 CDN/npm 只发加载器）。

### 后端与前端各自能改什么

- **后端可改**：emotionMap 的关键词表、提示词措辞、提取逻辑（`extract_emotion`）、
  `Actions` 里加新字段（但前端不认就不会生效）、发送时机与消息结构。
- **前端不可改**（没有源码）：表情如何被应用、只取 `expressions[0]`、
  模型加载方式（`.model3.json`）、`kScale ×2` 等。

### 调试建议

- 表情不生效时按链路逐段查：`model_dict.json` 是否登记且 `emotionMap` 有该键 →
  提示词里 `[<insert_emomap_keys>]` 是否被替换（`construct_system_prompt` 的 debug 日志有完整
  系统提示词）→ LLM 是否真的输出了 `[key]` → `extract_emotion` 的返回值 →
  WS `audio` 消息里有没有 `actions.expressions` → 浏览器控制台。
- `logs/debug_*.log` 里有完整系统提示词和 agent 初始化过程，是排查的第一现场。

---

### Live2D 前端格式要求（重要）

前端（`frontend/assets/main-*.js`）用的是 **Cubism 4 SDK**
（`CubismModelSettingJson` / `CubismMoc`），加载逻辑**硬编码 `.model3.json`**：

```js
fetch(modelHomeDir + name + ".model3.json")   // 路径来自 model_dict.json 的 url
```

因此：

| 模型格式 | 入口文件 | 前端能否加载 |
|----------|----------|--------------|
| Cubism 3 / 4 | `*.model3.json` | ✅ 可以 |
| Cubism 2.1 | `*.model.json` | ❌ **不行** |

`frontend/libs/live2d.min.js`（Cubism 2.1 运行时）确实存在，但 `index.html` 并未引用，
属于遗留文件，不要误以为前端支持 2.1。

`model_dict.json` 的 `url` 必须以 `.model3.json` 结尾（前端会剥掉该后缀推导模型名与 baseUrl，
所以模型嵌在多层子目录里也可以）。

**已知不兼容**：`live2d-models/加藤惠live2d/` 是 Cubism 2.1
（入口 `model/katou_01/katou_01.model.json`），前端无法加载。
转换到 `.model3.json` 必须用 Live2D Cubism Editor，无法脚本化。
启动器会在预览下方用黄色提示标出这种模型。

### guanghui_9 / l2d.su 规则引擎（2026-09-13 逆向，详情见 spec-l2dsu-engine.md）

- `Temp/*.js` 四文件是 l2d.su 查看器**运行时**（PixiJS 渲染 ×2 + Cubism4 + 热区规则引擎
  modelRuntime），不含任何模型数据；数据源是模型目录的 `touch.json` + `motions/` + `model3.json`。
- guanghui_9 无 `HitAreas`、无 `Idle`/`Talk` 组、0 条 Expressions——官方前端链路（tapMotions
  点击、Idle/Talk 动作、emotionMap 表情）在该模型上**全部空转**，互动只能走 touch.json 规则引擎路径。
- l2d.su 引擎核心语义：`actionTriggerActive` = 动作白名单 + 链状态机（`enable`/`ignore`/`idle:N`，
  链进度持久化 localStorage）；`actionTrigger` type 1=拖动触发、2=触摸即发、6=链占位、7=拖动主控；
  `limitTime`=冷却秒数、`saveParameter`=持久化参数。
- touch.json 有 3 条**无 `drawAbleName`** 的 mode2 位置反应规则（`Param3` + `reactPosX/Y`，
  指针位置×系数直接驱动参数）——frontend-minimal 现实现会丢弃它们。
- 升级路径结论（混合方案）：优先补 4 项（ATA 状态机 / actionTrigger type 分发 / limitTime
  冷却+localStorage 持久化 / mode2 位置反应），`listenerData`/游戏机缓做。

**stage1 实测修正（2026-09-13，细节见 research_live2d_stage1.md；待合并回 spec-l2dsu-engine.md §1/§5.1，两文档冲突处以本条为准）**：

- l2d.su 命中判据＝模型局部 drawable 包围盒包含＋最大渲染序取上层（无逐像素/无分区），不经过 pixi hitTest；`Ve()` 展开键是 aliases 非 shipSkinId。
- guanghui_9 的 28 个规则绘画件仅 TouchDrag1/2/3/15 在画布内，其余画布外（y36~149）＝链/参数数据载体永不被空间触发；`touch_dragN` 是模型参数名非动作组，故现前端 `valid.has(param)` 会把 4 个画布内热区也滤掉（`[Touch] 0/31`）→「上下二分」真因。
- 站点逐舰数据接口 `/data/ships/CN/<id>.json` 已失效（返回 SPA HTML）→ 线上 l2d.su 当前无 touch 规则，行为＝7 个默认热区＋touch_body 兜底，与本地前端过滤结果等价；`tips`/`dragRate`/`ignoreDrag` 为死数据（全站 JS 0 命中）不实现。
- 【契约候选】本地碧蓝航线 touch.json 可能整体错配皮肤：guanghui_9/touch.json 的 shipSkinId=207037（guanghui_7）≠ 模型皮肤 237031——核对 36 个模型前，勿把 touch.json 规则语义当该模型的精确行为依据。

