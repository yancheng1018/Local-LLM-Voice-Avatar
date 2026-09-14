### 新项目：极简自研前端（阶段一~三已完成 2026-09-11）

背景：现有前端功能大量冗余（用户不用麦克风/群聊/聊天历史/配置切换 UI），
且需要支持 Spine 模型（现有 Cubism 专属前端无法加载）。决定从零写极简前端，
起步只做基础功能，架构保留扩展性。

**阶段一已实现并联调通过**（WS + 文本输入 + 语音播放 + 字幕 + L2D 表情/动作）：

- 工程：`frontend-minimal/`，Vite + TypeScript 无框架，Node 已升级 v24.21.0
  （新装未进 Git Bash PATH，需 `export PATH="/c/Program Files/nodejs:$PATH"`）
- 依赖：`pixi.js@^7` + `pixi-live2d-display@0.5.0-beta`（唯一支持 pixi v7 的版本）
- 构建产物挂载：`server.py` 在 `/` catch-all 之前把 `frontend-minimal/dist`
  挂到 `/m`（目录存在才挂）；访问 `http://localhost:12393/m`
- 构建：`cd frontend-minimal && npm run build`（含 tsc 类型检查）；改完必须重建才生效
- Cubism Core 复用 `/libs/live2dcubismcore.min.js`（由原 frontend/ 挂 `/` 暴露）
- 结构：`src/ws.ts`（按 type 可插拔注册，断线 2s 自动重连）、`src/audio.ts`
  （顺序播放队列 + 打断 + 回执）、`src/renderer/types.ts`（CharacterRenderer
  接口）、`src/renderer/l2d.ts`、`src/renderer/spine.ts`、`src/ui.ts`、`src/main.ts`
- 控制台调试句柄：`window.__vtuber = { ws, audioQueue, renderer }`

**实现要点（踩过的坑）**：

- **kScale 换算**：pixi `model.scale = kScale × 屏高 / PixelsPerUnit`，
  模型 anchor(0.5,0.5) 居中。mao_pro 实测 72% 屏高，与原前端标定一致。
  PixelsPerUnit 从 `internalModel.pixelsPerUnit` 读
- **打断**：服务端被打断后**不补发 conversation-chain-end**，前端必须本地
  维护 `turnActive` 状态复位 UI；新消息发送前若上一轮活跃需先发
  `interrupt-signal`（服务端不支持同 client 并发对话）
- **v1.2.1 协议子集**（收）：`full-text`（状态）、`set-model-and-conf`
  （model_info 原样透传）、`control`（`conversation-chain-start/end`、
  `start-mic` 忽略）、`audio`（base64 WAV / null 纯字幕句，字幕在
  `display_text.text`，表情在 `actions.expressions[0]`，数字=索引/字符串=名）、
  `backend-synth-complete`、`error`；发：`text-input`、`interrupt-signal`、
  `frontend-playback-complete`（播完必须回，否则服务端等超时）
- 表情：`model.expression(索引|名)` 均支持；Talk 动作在每句播放时触发
  `model.motion('Talk')`（模型无该组自动跳过）；Idle 由库自动播放
- dev 模式 `npm run dev`（5173）经 Vite 代理转发 `/client-ws`、
  `/live2d-models`、`/avatars`、`/libs` → 12393

**阶段二已完成**（Spine 渲染，2026-09-11）：

- 模型：`Spine-models/`（注意大写 S，与用户放入的目录一致）下的
  cutscene_char061404 / cutscene_char067603，均为 **Spine 4.1 格式**
  （.skel 二进制头版本号 4.1.-），过场 rig，动画只有 loop/loop_2/
  loop_water/cut_A/cut_B 系列
- 运行时选型：**@esotericsoftware/spine-webgl@4.1.56（精确锁定）**。
  弃用原计划 spine-pixi（要求 pixi v8，与 L2D 的 v7 冲突）；
  spine-webgl 用独立 canvas + WebGL，与 pixi 零冲突。**版本必须与
  skel 格式匹配**，4.3 运行时读不了 4.1 skel
- `server.py` 挂载 `/Spine-models`（目录存在才挂）；model_dict.json 已登记
  两个模型（emotionMap 的值 = **Spine 动画名**，复用后端关键词管线，
  前端把 expressions[0] 当动画播放）
- `src/renderer/spine.ts`：SpineRenderer，main.ts 按 url 后缀分流
  （`.skel` → Spine，否则 Live2D），切换类型时销毁旧渲染器释放上下文
- 相机适配：按「待机动画首帧」的**网格顶点实算 AABB**（SkeletonData 的
  x/y/w/h 含未显示的场景件，偏大；ClippingAttachment 要排除）居中并
  zoom = max(W/屏宽, H/屏高) / 0.9
- ⚠️ **spine OrthoCamera 语义**：可见世界尺寸 = viewport × zoom
  （zoom 越大看得越广，与 pixi/常识相反）
- ⚠️ **最大的坑**：gl.viewport 永远是 WebGL 上下文创建时 canvas 的默认
  300×150，spine 运行时不会更新；必须每帧/尺寸变化时手动
  `gl.viewport(0,0,canvas.width,canvas.height)`，否则画面缩成左下角一小块
- AssetManager 用 pathPrefix='' + 完整 URL（拼 pathPrefix 会出双斜杠 404）
- ManagedWebGLRenderingContext 没有 dispose()：换模型时直接丢弃旧 canvas 由
  GC 回收 WebGL 上下文
- 表情验证通过：setExpression('loop_2') → 播完 complete 回调自动回待机；
  真实对话 LLM 输出 [开心]/[joy]（日志 306 次 joy + 109 次开心）→
  动画切换生效；字幕中关键词被后端剔除
- 联调用 `characters/spine_test.yaml`（edge_tts，避免起 GPT-SoVITS）
- **角色切换下拉**（右上角）：连接后发 `fetch-configs`，收 `config-files`
  （`[{filename, name}]`，name 即 character_name）；选择后发
  `switch-config {file}`，服务端推新的 `set-model-and-conf`，前端按
  conf_name 同步选中项并清空音频队列/字幕。切 Live2D ↔ Spine 双向验证通过
- ⚠️ **/m 必须带尾斜杠才 404 之外可用**：Starlette 不为 mount 自动补斜杠，
  server.py 已加 `/m` → `/m/` 307 重定向
- **聊天记录含用户气泡**：前端把用户发送的消息也加进字幕区（右侧蓝色
  `.sentence.mine`），与 AI 句子（左侧）共存，保留最近 8 条
- **启动器前端选择**（v2.7）：服务页「自动打开浏览器」旁新增下拉
  原版前端 / 极简前端，存 `launcher_config.json` 的 `frontend_choice`
  （default/minimal，默认 minimal），「立即打开界面」与自动打开共用；
  改 launcher 代码需重启启动器（bat 直跑 .py 无需打包）

**阶段四已完成**（2026-09-12，手势互动 + 目光跟随 + 心跳保活）：

- **互动区域判定来源（重要）**：头/身区域是**前端自己估计的**（模型显示
  包围盒顶部 30% 为头，其余为身）——碧蓝航线模型**没有** Live2D HitAreas，
  游戏和 l2d.su 的区域判定都在各自代码里，不存在于模型文件中。
  唯 mao_pro 有真实 HitAreas（但其热区绘画件位置与视觉位置不重合，
  命中区在胸口一带）；tapMotions 热区表只对它的非空热区名生效
- **真实互动区域数据已接入（2026-09-12 第二轮）**：l2d.su 的互动配置在
  `https://l2d.su/data/ships/CN/<shipGroupId>.json` 的
  `ship.skins[].model.live2dTouch`（rules 含 drawAbleName 热区绘画件名、
  parameter 动作组、actionTrigger、dragDirect 等；索引在
  /data/ships-CN.json，按 prefab 匹配）。已批量下载 36 个模型写入
  `live2d-models/<name>/touch.json`（缺 bulaimodun_5、yichui_2——
  非 L2D+ 皮肤；mao_pro/shizuku 非碧蓝航线源）。
  ⚠️ 大部分 TouchIdle/TouchDrag 绘画件是**画布外虚拟标记**（y -12000~
  -56000），不做区域定位，游戏按点击次数/方向触发——前端已过滤画布外
  规则，这些模型退化到递进链/头身启发式（行为与 l2d.su 等价）；
  部分模型（吾妻 wuqi_3）的规则绘画件在画布内，点中即播对应动作。
  touch.json 加载失败/缺失不影响功能（启发式兜底）
- ⚠️ **递进链动作组必须交互时实时取**：处理器赋值发生在新模型 load 完成
  前，赋值时 getMotionGroups() 返回上一个模型的组（切吾妻→Mao 后链里
  还是吾妻的 touch_idle，导致 Mao 点身播不出动作）
- **完整手势互动（仅 L2D）**：canvas 层手势状态机区分三种手势——
  单击 / 拖动（位移>40px 即触发一次）/ 长按（按住≥800ms）。选组链：
  单击头→`touch_head`→touch_special→touch_*；单击身→**touch_idle 递进链**
  （复刻碧蓝航线连续触摸：把 touch_idleN 组按编号排序，连点依次推进，
  闲置 10s 重置回开头，走完一轮冷却 60s，冷却期播 touch_body/touch_*；
  缺某些编号的模型自动跳过）；拖动→`touch_drag*`；tapMotions 热区表
  仅对有真实非空热区命中的模型生效；全部 FORCE 优先级。
  递进链逻辑参考 l2d.su 查看器（其 JS 解析动作组名为 type+number 并按
  编号排序推进，互动数据来自游戏 Lua 衍生的 /data/ships/CN/<shipid>.json，
  该文件只有台词/语音映射，不含区域数据；区域判定站点也是前端自己做的）。
  实测：光辉 tap@head→touch_head、tap@body→touch_idle1→3→6→7→8→9
  （跳号因模型缺编号）、drag→touch_drag10、longpress→touch_special；
  信浓（tapMotions 合并）、mao_pro（空串组）均正常
  - 碧蓝航线模型没有 Live2D HitAreas（游戏用屏幕区域判定），头身区域是
    前端按包围盒估计的；互动语音/台词不在模型资源里，无法还原
- **目光跟随**：`autoHitTest:false, autoFocus:true`（0.5.0-beta 中
  autoInteract 已废弃，且其 hit 事件只在命中时才发会挡死兜底，故
  hitTest 由 canvas 手势层自己做）
- ⚠️ **pixi v7 必须设 `stage.eventMode='static'` + `stage.hitArea=app.screen`**，
  否则模型上的指针事件时有时无（pixi-live2d-display 只把 model 设为
  interactive，stage 不可命中时事件派发不稳定）
- **心跳保活**（ws.ts 内部）：30s 发 `heartbeat`，90s 没收到任何服务端
  消息则主动断开走 2s 重连。注意 WSClient 内部 `this.ws` 是原生 WebSocket，
  页面侧包 `__vtuber.ws.send` 拦不到心跳，要在 `WebSocket.prototype.send`
  上埋点（实测 65s 两跳）
- **mao_pro 表情肉眼验收完成**：真实对话 LLM 输出情绪 → expressions[0]
  应用（exprLog: 1→7）；肉眼确认表情 1=眯眼笑、7=瞪眼怒，差异清晰

**阶段三已完成**（2026-09-11，聊天历史持久化 + L2D 口型同步）：

- **聊天历史**：新增 `src/history.ts`。每次收到 `set-model-and-conf`
  （连接/重连/切角色）后 `fetch-history-list` → 取最新（列表已倒序）→
  `fetch-and-set-history` → `history-data` 还原气泡（role 为
  `human`/`ai`，human 是右侧蓝泡）；恢复的气泡不受实时 8 条上限约束。
  状态栏「✚ 新对话」按钮发 `create-new-history`，服务端会同步把 LLM
  记忆切到空历史。切换历史/新建历史时服务端都调用 set_memory_from_history
- **口型同步（仅 L2D）**：`audio.ts` 暴露 `volumeLevel` getter——按
  AudioContext 时钟算当前播放位置，取该句 `volumes[]`（20ms RMS）对应值，
  起音即时、释放 ~70ms 衰减；`l2d.ts` 挂 `internalModel.on('beforeModelUpdate')`
  每帧把音量写进 LipSync 参数组（`coreModel.setParameterValueById`）
- ⚠️ **pixi-live2d-display 0.5.0-beta 没有 `internalModel.lipSyncIds`**，
  参数 id 要从 `internalModel.settings.groups` 里找 `Name==='LipSync'`
  的 `Ids`（mao_pro=`ParamA`；有的模型是 `ParamMouthOpenY`；
  `im.lipSync` 只是布尔开关）。无 LipSync 组的模型自动跳过
- ⚠️ **audio.ts 播放循环的打断竞态**（已修）：旧实现用 `interrupted` 标志，
  interrupt 后立刻 enqueue 的新消息会被尚在 sleep/decode 的旧循环
  「退出前最后一次检查」吞掉，队列卡死。已改为代际计数（generation）：
  interrupt 自增代际，旧循环发现代际不符自行退出，且旧循环的 finally
  不覆盖新一代的 playing 状态
- ⚠️ **CORSStaticFiles 对 html 加了 `Cache-Control: no-cache`**：入口页
  引用带 hash 的 assets，不加的话浏览器启发式缓存会拿旧 index.html、
  加载不到新构建（「改了没生效」的常见元凶）
- 40/41 个 L2D 模型 model3.json 有 LipSync 组（Groups 是**顶层键**，
  不在 FileReferences 下）；仅 oppai_bunny 没有。Spine cutscene 模型
  嘴为贴图附件切换式，不做口型
- 调试手段：页面控制台 `__vtuber.audioQueue.volumeLevel`（当前音量）、
  `renderer.model.internalModel.coreModel.getParameterValueById('ParamMouthOpenY')`
  （嘴型参数实时值）；用「合成 WAV + 假 volumes 数组」enqueue 可在
  不起 TTS 的情况下验证口型链路
- 验收记录：刷新后气泡自动还原且 AI 记得「你好」；新对话后清空；
  播放期间嘴型参数 0→0.998 连续变化
- **历史功能默认关闭**（2026-09-12，用户实测发现长历史拖慢语音合成）：
  状态栏「🕘 历史：开/关」切换，状态存 localStorage（`history_enabled`），
  关闭时不拉取历史、前端每次从空白对话开始；「✚ 新对话」仅在开启时可用。
  **性能问题根因**（诊断记录，供以后优化）：basic_memory_agent 把全部历史
  无上限发给 LLM（`_memory.copy()`）→ 长历史使 Ollama prefill 变慢、回复
  变长（实测 16 句）→ 与 GPT-SoVITS 争用 8GB GPU，紧跟 LLM 生成高峰的
  第一次 TTS 请求被饿死，120s 读超时（gpt_sovits_tts.py:51 写死
  timeout=120）语音被丢。修复方向（届时二选一或都做）：① basic_memory_agent
  加记忆截断（最近 N 条，可配置）；② gpt_sovits read_timeout 提到 300s。
  日志佐证：8 字短句在长历史轮次等满 120s，新对话轮次每句仅 2.5~8s

**遗留**：
- mao_pro 表情的肉眼视觉验收未完成（管线已验证：expressions[0] 正确传入、
  表情文件 exp_08 按需加载成功）；下次起服务后发一条带情绪的消息看效果即可
- 联调时出现 TTS 120s 超时（GPU 100% 被 Ollama+GPT-SoVITS 争用），
  属已知环境性能问题，与前端无关
- 默认角色 zh_米粒（xinnong_6）无表情文件，表情验证需切 mao_pro
  （`switch-config` file=mao_pro.yaml）
- 两个 cutscene 模型只有环境循环动画，emotionMap 的映射（joy→loop_2 等）
  只是占位；等有带表情动画的 Spine 模型再补有意义的映射

**阶段二（Spine）接手要点已并入上文**；当前无待启动阶段。后续可考虑：
- 有带表情动画的 Spine 模型后补全 emotionMap 映射

**stage2 参数驱动引擎（2026-09-13，热区/动作链升级）**：

- `src/renderer/l2d_params.ts`：l2d.su 同款规则驱动参数引擎（mode1 circle/drag 状态机 +
  mode2 指针反应 + type103 查表 + localStorage 持久化）。契约与测试口径见
  `temp_spec_stage2.md`，逆向结论见 `spec-l2dsu-engine.md`
- ⚠️ **行数上限例外：该文件 220 行封顶（规格书原定 ≤200，实现 215 行）**。
  理由：4 轮压缩（242→215）已删尽全部可删排版，剩余超标全是逆向语义契约注释，
  删了丢可读性；拆分方案已否决——纯函数与状态机共享 ParamRule 域模型，
  且 test_params_module_exists 按文件路径断言四个 export function 位置（测试语义不得改）。
  若 stage3 后续给引擎加 listenerData 等新职责导致明显超限，再按职责拆分（数学纯函数 vs 状态机）

**stage3 一键复位（2026-09-14，Live2D 模型复位）**：

- `index.html` 顶栏「↺ 复位模型」→ `ui.onResetModel` → `L2DRenderer.resetToInitialMotion()`。
  复位序列：停全部 motion → 清 `touchPlay` 播放门控 → `resetExpression()` →
  `TouchChain.reset()` → `playIdleOnce()`。文案固定 `模型已复位` /
  `当前模型不支持复位`；契约见 `temp_spec_minimal-frontend_stage3.md`
- **复位是纯视觉操作**：不发 `interrupt-signal`（会取消角色正在生成的对话，超出需求），
  只打断前端音频队列并清本地 `turnActive`/busy
- ⚠️ **`resetTouchChain` 可空，且注入是「每模型一次」而非一次性**：L2DRenderer 不持有
  TouchChain 实例（实例在 main.ts 的 `set-model-and-conf` 处理器里按模型闭包创建，
  键 `l2d-touch:<角色名>`），链归零必须经注入的只写回调 `resetTouchChain: (() => void) | null`。
  三处推论：
  1. **可空即未就绪**：模型未加载、当前是 Spine 模型时该字段为 `null`，复位必须在链缺席时
     仍完成表情与初始 idle——故 `this.resetTouchChain?.()` 包 try/catch，且
     `resetExpression()` 放在它之前（注入回调由 main.ts 提供，抛错不能连带吞掉表情与 idle）
  2. **每次换模型都重新注入**：renderer 实例会被 `ensureRenderer()` 销毁重建，
     旧实例的回调指向上一个模型的 TouchChain；依赖「重新赋值」而非「注入一次永久有效」
  3. **`playIdleOnce()` 依链状态选组**：`chainIdleIndex()` 为 0 才播初始 `idle` 组，
     否则播 `idleN`——链归零失败时复位会退化为播当前递进组的 idle（可接受降级，不报错）
- 复位调用的是模块级 `renderer`，而注入发生在 `activeRenderer` 上：二者恒为同一实例
  （`ensureRenderer()` 只改 `renderer` 自身并原样 return，无第二处赋值）。
  后续若引入多 renderer 实例缓存（预加载）必须重新审视这条隐性依赖
