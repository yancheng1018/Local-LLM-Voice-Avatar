# 极简前端 · 基础管线（工程 / WS 协议 / 聊天历史 / 口型同步）

> 拆分自 minimal-frontend.md（2026-09-15）。总入口与遗留 → minimal-frontend.md；兄弟分册：Live2D 手势/触摸引擎/复位 →
> minimal-frontend-live2d.md、Spine 渲染 → minimal-frontend-spine.md、模型切换 → minimal-frontend-model-switch.md

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

**stage1~2 调试栏期间的工程教训（2026-09-14，蒸馏自规格书）**：

- ⚠️ **npx tsc 陷阱（本机）**：`npx tsc` 会拉到 npm 垃圾包 tsc@2.0.4（输出
  「not the tsc command」且**退出码 0**，掩盖真实类型错误）；且仓库根 npx 解析不到
  项目内 typescript（impl stage3 实际踩过）。一律走
  `frontend-minimal/node_modules/.bin/tsc --noEmit -p .`
- **三层测试体系**（tests/）：L1 静态正则（接线链/旧路径根除）→ L2 运行时行为 →
  L3 dist 构建产物断言。L2 是核心：把被测模块用 tsc 单文件编译到 `tests/__tsout__/`
  （package.json type=module，产物为 ESM），配假模型 + ~90 行 mini-DOM 垫片，
  `node --test` 直接驱动类逻辑，零新依赖。适用于任何「功能可跑」类模块——
  纯静态子串断言无法发现路径/逻辑错误（stage1 九用例全绿但功能坏）
- **假模型必须镜像真实结构**：形状照真实核心结构造，并带反断言（不得含错误属性，
  如 `assert !('model' in coreModel)`）——假模型焊死错误形状时，测试与错误代码
  双向自洽、全绿但功能坏（stage2 v1 实际发生）。修完做反向验证：把代码改回错误路径应红
- **第三方库 API 面必须运行时验证**：规格书写「已核实」的库内部路径可能只是静态推断
  （调试栏取数路径连错两轮）；引用「先例」须确认该行在生产路径上执行（l2d.ts 的
  canvasinfo 兜底从未执行却被当先例照抄）。`?.` 链会把路径错误退化为空数组
  **静默失败**——取库内部结构取不到时应 console.warn/显示占位，转成可见失败
