# ZCode 项目上下文

> 本文档为 ZCode (Z.ai) 编程代理提供项目背景信息。
> 在 ZCode 中打开本项目后，将此文件内容粘贴给它作为初始上下文。

---

## 项目概述

Open-LLM-VTuber v1.2.1-zh 是一个**完全离线运行**的语音交互 AI 伴侣，支持 Live2D 虚拟形象。
跨平台 Python 应用，支持实时语音对话、视觉感知和 Live2D 角色动画。

### 硬件环境
- GPU：RTX 3070 Ti (8GB VRAM)
- LLM：Ollama + qwen3.5:9b（Q4_K_M 量化，32 layers）
- TTS：GPT-SoVITS v4 DPO

### 关键端口
| 服务 | 端口 |
|------|------|
| Ollama | 11434 |
| GPT-SoVITS | 9880 |
| Open-LLM-VTuber | 12393 |

---

## 已做的自定义修改（重要）

### 1. Ollama 改用原生 /api/chat

**修改文件：**
- `src/open_llm_vtuber/agent/stateless_llm/ollama_native_llm.py`
- `src/open_llm_vtuber/agent/stateless_llm/ollama_llm.py`

**原因：** 原项目的 `/v1/chat/completions` 不支持 `num_gpu` 等 Ollama 原生参数。
改用 `/api/chat` 后可以控制 GPU 卸载层数，让 Qwen 和 GPT-SoVITS 共享 GPU。

**关键参数：**
```python
num_gpu=16      # 53% CPU / 47% GPU，避免与 GPT-SoVITS 争显存
num_ctx=4096    # 控制上下文长度，减少显存占用
think=False     # 禁用 Qwen thinking，避免额外延迟
keep_alive=-1   # 模型永久驻留，避免每轮重新加载
```

### 2. conf.yaml 新增字段

`ollama_llm` 配置段新增了以下字段（不在原项目默认配置中）：
```yaml
ollama_llm:
  base_url: 'http://localhost:11434/v1'  # 程序内部自动转为 /api
  model: 'qwen3.5:9b'
  temperature: 0.7
  num_gpu: 12          # GPU 卸载层数
  num_ctx: 4096        # 上下文长度
  think: false         # 禁用 thinking
  keep_alive: -1       # 永久驻留
  unload_at_exit: true # 退出时卸载
  preload: true        # 启动时预加载
```

### 3. streaming_mode 必须是字符串

`gpt_sovits_tts.streaming_mode` 必须保持为字符串 `'false'`，不能变成布尔值 `false。
GUI 启动器中有强制保护逻辑。

---

## 项目结构

```
├── run_server.py                    # 入口
├── conf.yaml                        # 用户配置（已自定义）
├── CLAUDE.md                        # 项目架构说明
├── ZCODE_CONTEXT.md                 # 本文件
│
├── src/open_llm_vtuber/
│   ├── server.py                    # FastAPI WebSocket 服务器
│   ├── service_context.py           # 依赖注入容器
│   ├── websocket_handler.py         # WebSocket 消息路由
│   ├── routes.py                    # 路由定义
│   │
│   ├── agent/                       # Agent 系统
│   │   ├── agent_factory.py
│   │   ├── agents/                  # basic_memory, hume_ai, letta, mem0
│   │   └── stateless_llm/           # LLM 实现
│   │       ├── ollama_native_llm.py # ★ 已修改：改用 /api/chat
│   │       ├── ollama_llm.py        # ★ 已修改：改用 /api/chat
│   │       ├── openai_llm.py
│   │       ├── claude_llm.py
│   │       └── ...
│   │
│   ├── asr/                         # 语音识别引擎
│   │   ├── asr_factory.py
│   │   ├── sherpa_onnx_asr.py
│   │   ├── faster_whisper_asr.py
│   │   └── ...
│   │
│   ├── tts/                         # 语音合成引擎
│   │   ├── tts_factory.py
│   │   ├── gpt_sovits_tts.py
│   │   ├── edge_tts.py
│   │   └── ...
│   │
│   ├── vad/                         # 语音活动检测
│   │   ├── vad_factory.py
│   │   └── silero_vad.py
│   │
│   ├── config_manager/              # 配置管理
│   │   ├── main.py
│   │   ├── character.py
│   │   ├── agent.py
│   │   ├── asr.py
│   │   ├── tts.py
│   │   └── vad.py
│   │
│   └── conversations/               # 对话系统
│       ├── conversation_handler.py
│       ├── single_conversation.py
│       ├── group_conversation.py
│       └── tts_manager.py
│
├── launcher/                        # GUI 启动器
│   ├── OpenLLMVTuber_GUI.py         # PySide6 GUI (v1.9)
│   └── launcher_config.json         # 启动器配置
│
├── characters/                      # 角色配置
│   ├── mao_pro.yaml
│   ├── ja_test.yaml
│   └── ...
│
├── config_templates/                # 默认配置模板
│   ├── conf.default.yaml
│   └── conf.ZH.default.yaml
│
├── live2d-models/                   # Live2D 模型
├── frontend/                        # 前端（Git 子模块）
├── chat_history/                    # 聊天记录
└── cache/                           # 缓存
```

---

## 常用命令

```bash
# 安装依赖
uv sync

# 启动服务器
uv run run_server.py

# 启动（详细日志）
uv run run_server.py --verbose

# 更新项目
uv run upgrade.py

# 代码检查
ruff check .
ruff format .
```

### 启动 GUI 启动器（推荐）

双击项目根目录的 **`启动器.bat`** 即可，会以无控制台方式打开启动器窗口。

```bat
启动器.bat          :: 静默启动（双击用这个）
启动器.bat debug    :: 调试模式，保留控制台窗口以便查看报错
```

该 bat 会自动使用 `.venv-gui` 虚拟环境；若环境缺失会给出创建命令。
启动失败（例如缺依赖）时会弹窗提示完整 traceback，不会出现"双击没反应"。

> **为什么不打包成 exe**：启动器 exe 不需要包含 Open-LLM-VTuber 项目本身
> （它只读 conf.yaml 并 `uv run run_server.py`），所以改 `src/`、`conf.yaml`、
> 模型、声音都**不需要重新打包**；但**改 `launcher/OpenLLMVTuber_GUI.py` 就需要**。
> 由于启动器仍在频繁迭代，且 PySide6 打包产物通常 150MB+、每次打包耗时较长，
> 现阶段用 bat 更划算。等功能稳定后再考虑 PyInstaller 打包。
>
> bat 文件以 **GBK 编码**保存、不加 `chcp`。因为本机控制台默认代码页是 936，
> GBK 能被 cmd 原生解析；若用 UTF-8 + `chcp 65001` 会导致 cmd 按字节重读批处理，
> 出现「注释里的中文被当成命令执行」的错误。

### GUI 启动器
```bash
# 激活 GUI 虚拟环境后运行
.\.venv-gui\Scripts\python.exe launcher\OpenLLMVTuber_GUI.py
```

GUI 依赖：`PySide6-Essentials`、`ruamel.yaml`、`psutil`

---

## 配置管理

### 配置层级
1. `conf.yaml` — 主配置（用户自定义）
2. `characters/*.yaml` — 角色配置（**部分配置**，只写要覆盖的字段，启动/切换时 merge 到主配置之上）
3. `config_templates/` — 默认模板（参考用）

### 默认角色：指针方案（v2.6 起）

`conf.yaml` **只存一个指针**，不存角色内容：

```yaml
system_config:
  default_character: 'zh_米粒.yaml'   # 空 = 直接用本文件的 character_config
```

启动时 `apply_default_character()` 读取该文件并 `deep_merge` 到基础
`character_config` 之上再校验。`service_context.handle_config_switch` 的
`conf.yaml` 分支同样套用，所以 Web UI 切回「基础配置」时也尊重该默认角色。

**为什么用指针而不是把角色内容写进 conf.yaml**：运行时 merge 永远是以「当前配置」为底，
就地合并会在反复切换角色时逐步累积上一个角色的残留，把 `conf.yaml` 污染掉。
指针方案下 `conf.yaml` 永远保持干净，每次启动只 merge 一次。

指针为空或指向不存在的文件 → 忽略该指针、原样使用 `conf.yaml` 自身配置（只告警，不阻断启动）。

### 角色语言（v2.6 起）

`character_config.language` 可选，取值 `''` / `zh` / `ja` / `en` / `ko` / `yue` / `auto`。
**启动器里是纯下拉，不需要手写**；后端 pydantic 只放行白名单取值，手写错误会直接报错。

它驱动两处：

| 作用点 | 实现 |
|--------|------|
| LLM 回答语言 | `construct_system_prompt()` 在 persona 提示词**最前面**注入 `[Language Requirement]` 指令，要求无论用户说什么语言都只用该语言回答 |
| TTS 语音语言 | `init_tts()` 用角色语言覆盖 TTS 引擎配置的 `text_lang`（仅当该引擎有此参数，如 `gpt_sovits_tts`） |

- **不覆盖 `prompt_lang`**：那是参考音频的语言，属于声音模型的属性
- 空值或 `auto` 均表示不限制
- **参数必须显式传递**：`load_from_config` 里 `self.character_config` 是在**最后**才赋值的，
  `init_tts` / `init_agent` 执行时它还是上一次的配置。所以这两个方法都加了
  `language` 参数并由调用方传入（见 `init_tts`、`init_agent`、`construct_system_prompt`）
- 语言变化会触发 TTS/Agent 重建（比较时纳入了 language），否则只改语言不会生效
- `init_tts` 的重建判断用 `self._tts_language` 记录上次使用的语言

### 语言兜底：检测 + 重试（`utils/language_guard.py`）

**问题**：小模型（实测 `qwen3.5:9b`）即使 system prompt 明确要求"只用日语回答"，
在"用户说中文 + 人设是中文"时仍会以约 **4%** 的概率跟随输入语言改用中文。
实测调优**都无法把它降到 0**：

| 手段 | 实测结果 |
|------|----------|
| 语言指令放**末尾**（近因效应） | 小样本 6/6 vs 5/6 看似有效，放大到 12 次后两边都是 12/12，**无法证明** |
| **降低温度** 0.7 → 0.3 | **反而出现 1 次失败**，温度不是有效杠杆 |

所以改用应用层确定性兜底：

- `detect_language_mismatch(text, target)` —— 字符种类启发式。目标日语时「出现假名即正确、
  全是汉字即中文」；样本不足 6 字符返回 `None`（不干预，避免误杀）。
  `[joy]` 这类表情关键词与 `<think>` 内容不参与判定。
- `build_retry_reminder(target)` —— 追加到 system prompt **末尾**的强提醒（近因效应），
  含该语言的祈使句 + 中文说明。
- `single_conversation._language_checked_stream()` —— 包装 agent 回复流：
  1. **先扣住开头几句**做判定，通过后原样转发（正常情况仍是流式，不增加延迟）。
     这是必需的：回复会实时送到前端与 TTS，转发出去就来不及了。
  2. 判定不符 → 丢弃该版（它**不会进记忆**，因为 assistant 文本只在流结束时写入），
     临时把强提醒追加到 `agent._system` 后重试一次。
  3. **重试那一版是先完整收完再还原提示词，之后才转发** —— 代价是重试时失去流式，
     换来确定的还原时机。这一点很关键：async generator 被提前中断时 `finally`
     **不会立即执行**（异步生成器延迟终结），直接在 `yield` 之间还原会导致
     加强过的提示词泄漏到后续轮次。已有专门用例覆盖。
  4. 只重试一次；若第二次仍不符，**放行并记 error**，不能静默吞掉回复。
- 通过 `getattr(agent, "_system")` 读写系统提示词（而非 `set_system`），
  避免后者在 `interrupt_method == "user"` 时重复追加中断提示。
  不支持 `_system` 的 agent 会自动降级为不重试。

**实测效果**：把**人设故意写成「无论用户说什么语言，你都必须只用中文回答」**这种对抗情况下，
guard 仍能触发重试并让最终回复变成日语（日志有
`Language guard: detected a reply not in 'ja'; discarding it and retrying once`）。

**作用范围**：目前只覆盖**单聊**（`single_conversation`）。群聊有独立的消费循环，未接入。

**排查提示**：每个新的 WebSocket 连接都会**重新克隆启动时的默认上下文**，
所以改完 `conf.yaml` 的 language 后必须**重启服务**才对客户端生效；
用 `switch-config` 只能影响当前那一个连接。

**优先级**：角色语言 > 声音模型的 `text_lang`。
在启动器点「应用声音」时，若该声音的语言与当前角色语言不一致（或角色语言为空），
会弹窗询问是否把角色语言同步过去，确认后立即保存角色文件。

### ⚠️ 关键事实：角色的「自我认知名」来自 persona_prompt，不是 character_name

**`character_name` 从未进入 system prompt。** `construct_system_prompt()` 只拼接
`persona_prompt` + `[User]` 段 + `[Language Requirement]` 段 + 工具提示词，
**没有任何一处注入 `character_name`**。它的用途全是"显示"：

1. Web UI 角色列表的标签，以及前端反查配置文件的键
2. AI 回复气泡上的名字（`conversation_utils.py` → `display_text.name`）
3. 聊天记录 JSON 的 `name` 字段
4. 群聊里的参与者名单（且只传"别人"的名字，AI 学不到自己叫什么）

**LLM 只从 `persona_prompt` 里手写的文本认识自己。**

**设计取舍（v2.7 决定）：两者互相独立，不做同步。**
`persona_prompt` 决定角色自称什么，`character_name` 只是界面显示名，
**允许不一致**（这是上游的原始行为）。例如 `mao_pro.yaml` 的
`character_name: 'Mao'` 配人设里自称 `Mili`，属**正常状态**，不是 bug。

排查"角色自称不对"这类问题时，**改 `persona_prompt` 里的文本**，
不要去改 `character_name`（改了也不会影响 LLM，只会改界面标签）。

> 历史：v2.6 曾把各角色人设里的自称统一成 `character_name`（如 `Mili` → `Mao`），
> v2.7 已全部还原。若以后想根治"改名即生效"，可在 `construct_system_prompt()`
> 里新增身份注入（类似 `[Language Requirement]` 的做法），或提供
> `[<insert_character_name>]` 占位符 —— 但那样会让 `character_name` 覆盖人设文本，
> 与当前"以文本人设为主"的取舍相反，需要先想清楚再动。

### 用户名（human_name）的现状

`human_name` 曾长期**完全无效**（设为任意值对 LLM 都没有影响），现已修复：

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 单聊 | 赋给 `input_types.TextData.from_name`，但 `_to_text_prompt()` 只读 `content`，该字段**全仓库无读取方**，等于丢弃 | `construct_system_prompt()` 注入 `[User]` 段告知 LLM 用户的名字 |
| 群聊 | `init_group_conversation_contexts()` 把 `human_name` **硬编码成 `"Human"`**，而同一次群聊的历史行用配置值 → 自相矛盾 | 该函数新增 `human_name` 参数，由调用方传入配置值，提示词与历史行一致 |
| 前端 | 从未发送（前端 0 次引用） | 同左，仍不发前端（属于后端内部字段） |

`[User]` 段的注入规则：`human_name` 为空、或等于默认占位值 `"Human"`（大小写、
首尾空格均忽略）时**不注入**，避免默认配置下往提示词里塞噪音。
常量 `service_context.DEFAULT_HUMAN_NAME = "Human"`。

`human_name` 与 `language` 一样**必须显式传参**给 `init_agent` /
`construct_system_prompt`：`load_from_config` 里 `self.character_config` 最后才赋值。

**已知无效字段（保留未动）**：`input_types.TextData.from_name` —— 设置了但没有任何读取方。
它是上游内部管道而非用户可见参数，故未清理，仅在此记录。

### 角色标识方案（v2.5 起：废弃 conf_name）

| 字段 | 作用 | 约束 |
|------|------|------|
| `conf_uid` | **唯一标识**。同时用作 `chat_history/<conf_uid>/` 的目录名，并传给各 agent 做记忆隔离 | 必填、唯一、不可含 `\ / : * ? " < > \|` |
| `character_name` | **角色自己的名字**。既是对话中的 AI 名称，也是**前端角色列表的显示名** | 必填、**必须唯一** |
| `language` | 回答语言（见上） | 白名单取值，可空 |
| ~~`conf_name`~~ | **已删除** | — |

**为什么 `character_name` 必须唯一**：前端（打包产物，无法重新构建）把列表项的
「显示标签」与「身份标识」绑成同一个字段，并用它反查配置文件：

```js
label: $.name, value: $.filename          // 下拉显示 name，值用 filename
getFilenameByName(confName)               // 用 conf_name 反查当前角色的 filename
```

其中 `name` 由后端 `scan_config_alts_directory` 提供，取值 `character_name`
（回退 `conf_uid` → 文件名）。前端按名字反查时**取首个匹配**，所以重名会导致切错角色。

**WS 协议里的 `conf_name` 键名必须保留**：前端硬编码读取这个键名，但后端发送的
**值已是 `character_name`**（见 `websocket_handler.py`、`service_context.py` 三处，
均附有注释）。YAML 里已经没有这个字段了。

**`scan_config_alts_directory` 的去重规则**：先扫描 `characters/*.yaml`，只有当
`conf.yaml` 的角色没有被任何角色文件代表时，才额外插入 `conf.yaml` 条目。
否则列表会出现两个同名条目（例如 conf.yaml 与 mao_pro.yaml 同为 `Mao`），
导致前端反查到错误配置。

**启动器与 Web UI 的一致性**：两边都显示 `character_name`，数据同源。启动器
「形象」等分组用 `conf_uid` 定位当前角色。

### 启动器里「选择角色」的实际效果（重要）

后端**不会**用角色名去加载对应的角色文件 —— 真正切换角色是 Web UI 通过
WebSocket 发 `switch-config` 完成的（见 `service_context._handle_config_switch`）。
启动器写进 `conf.yaml` 的只有 `character_name` 与 `conf_uid`，
**不会改变实际运行的人设**（人设来自 `conf.yaml` 自己的 `character_config`）。

若希望「在启动器里选角色」能真正生效，需要额外把所选角色文件 merge 进
`conf.yaml` 的 `character_config`——这是可选的后续改进。

### 配置加载逻辑
角色配置会合并到主配置中。角色 YAML 中的字段会覆盖 `conf.yaml` 中的同路径字段。

### GUI 启动器配置
- `launcher/launcher_config.json` — 保存 GPT-SoVITS 路径、权重选择、预设等
- 使用 `ruamel.yaml` 读写 `conf.yaml`，保留注释和引号格式

---

## 开发注意事项

### 修改配置时
- 必须同时更新 `config_templates/conf.default.yaml` 和 `conf.ZH.default.yaml`
- `streaming_mode` 等字段必须保持为字符串类型
- 使用 `ruamel.yaml` 的 `SingleQuotedScalarString` 保证格式
- 新增角色时**不要**再写 `conf_name`；`character_name` 与 `conf_uid` 必填且各自唯一

### 添加新引擎
1. 在对应目录创建接口文件（如 `asr_interface.py`）
2. 实现具体类，遵循现有模式
3. 添加到工厂类（如 `asr_factory.py`）
4. 更新 `config_manager/` 中的配置类
5. 在默认 YAML 中添加配置选项

### WebSocket 消息处理
1. 在 `websocket_handler.py` 的 `MessageType` 枚举中添加消息类型
2. 创建 `_handle_*` 方法
3. 在 `_init_message_handlers()` 字典中注册

---

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

## GUI 启动器功能（v2.4）

6 个标签页布局（服务 → 模型 → 角色 → LLM → TTS → ASR / VAD）：

| 标签 | 内容 |
|------|------|
| **服务** | 一键启动/停止 + 自动打开浏览器选项 + 运行日志 |
| **模型** | 模型选择（LLM/TTS/ASR/VAD）+ 配置预设 |
| **角色** | 角色列表 + 头像 + Live2D 预览 + 角色编辑器 |
| **LLM** | Ollama 专用参数 + 模型信息 / 通用 LLM 参数 |
| **TTS** | 声音模型（voices/）增删改查 + 试听 + GPT-SoVITS 启停 / 通用 TTS 参数 |
| **ASR/VAD** | ASR 参数 + VAD 参数 |

始终可见：顶部状态条 + 项目目录 + 底部保存按钮

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

### 「角色」页布局

左列自上而下：
1. **角色列表** — 下拉选择 + 头像预览（96px）+ 新建/删除
2. **Live2D 预览**（210px）— 跟随所选角色的 `live2d_model_name` **自动刷新**，
   下方一行提示该模型的格式兼容性（✔ Cubism 3/4 / ⚠ Cubism 2.1 不支持）

右列：角色编辑器（显示信息 / 形象 / 人设 / 内部标识 四组）

### Live2D 模型管理（「形象」分组）

| 控件 | 行为 |
|------|------|
| 模型下拉 | `model_dict.json` 中的模型名 ∪ `live2d-models/` 下的文件夹名，可编辑 |
| **↻** | 刷新下拉 |
| **📂** | 在资源管理器中打开 `live2d-models/` 保存目录 |
| **导入...** | 弹出菜单：导入文件夹 / 导入压缩包 |

**导入功能**（`_import_live2d_menu`）：
- **导入文件夹** — 选中的目录若本身含入口文件则按单个模型导入；
  否则把其中每个含入口文件的子目录各当一个模型导入。因此
  「单个文件夹」和「多个文件夹」用同一个入口即可。
- **导入压缩包** — 可多选 `.zip`，各自解压为 `live2d-models/<zip名>/`
- 重名会询问是否覆盖；解压带 zip slip 防护（`_safe_extract`）
- 导入后**自动**查找入口文件（`.model3.json` 优先，取层级最浅的）并写入
  `model_dict.json`（自动备份 `.bak`），前端刷新即可选用
- Cubism 2.1 模型会被拒绝登记并说明原因

### 角色编辑器

| 分组 | 字段 |
|------|------|
| 显示信息 | 角色名（character_name）、用户名（human_name） |
| 形象 | Live2D 模型（下拉+刷新+打开目录+导入）、头像（下拉+刷新+**导入...**） |
| 人设 | persona_prompt |
| 内部标识（一般无需修改） | conf_name、conf_uid |

- Live2D 模型与头像均为可编辑下拉，自动扫描 `model_dict.json` ∪ `live2d-models/`、`avatars/`，支持手输
- 「导入...」会复制所选图片到 `avatars/` 并自动选中
- `conf_uid` 留空保存时自动补为 `{conf_name}_001`；空的可选字段不会写入 YAML

### Live2D 贴图预览的实现与限制

**不做骨骼渲染**：真正的 Live2D 渲染需要 Cubism Core 专有原生 DLL + `live2d-py` + OpenGL 上下文；
本项目只有 Web 版 `frontend/libs/live2dcubismcore.js`（供前端用），Python 侧无原生运行时，
因此启动器只显示**模型贴图**作为静态预览（零依赖、无 GPU 开销）。

贴图查找顺序（`_find_model_texture`）：
1. `texture_*.png`（Cubism 3/4）
2. 模型主目录下的 `*.png`
3. `.zip` 内的贴图（Cubism 2.1 打包格式）
4. 兜底：子目录 `*.png`

三种情况都**排除** `images/`、`css/`、`js/`、`sounds/`、`voice/`、`motions/`，
避免把 `info.png` 这类 UI 按钮图标误当模型贴图。

模型目录定位（`_resolve_model_dir`）带逐级回退，因为角色配置里的 `live2d_model_name`
未必等于文件夹名（例：`shizuku-local` → `live2d-models/shizuku/`）：
精确匹配 → 去 `-local`/`_zh` 等后缀 → 忽略大小写与分隔符 → 前缀匹配。

### 声音模型（voices/）

GPT-SoVITS 每次请求都需要参考音频 + 提示文本，因此把「权重对 + 参考音频」打包成一个**声音模型**，
它同时充当 TTS 的**预设**。**参考音频统一放在 `voices/` 下，不再使用 GPT-SoVITS 根目录的 ref.wav**：

```
voices/
└── 加藤惠/
    ├── ref.wav       # 参考音频
    └── voice.json    # {
                      #   "prompt_text": "参考音频中说的原话",
                      #   "prompt_lang": "ja",   # 参考音频语言
                      #   "text_lang":   "ja",   # 合成语言
                      #   "gpt_weight":    "GPT_weights_v4/xxx.ckpt",
                      #   "sovits_weight": "SoVITS_weights_v4/xxx.pth"
                      # }
```

TTS 页「声音模型」区：

| 控件 | 行为 |
|------|------|
| **当前使用：xxx ✓** | 由 conf.yaml 的 `ref_audio_path` 反查是哪个声音模型；不在 voices/ 中则黄色提示 |
| **应用声音** | 写 conf.yaml（ref_audio_path / prompt_text / prompt_lang / text_lang）并在 GPT-SoVITS 运行时切权重；未运行时只写配置，启动时自动切换 |
| **新建...** | 选权重对 + 参考音频 + 提示文本，建目录、复制音频、写 voice.json |
| **编辑...** | 复用同一对话框并预填 voice.json；改名会重命名 `voices/` 子目录 |
| **删除** | 确认后移除 `voices/<名称>/`（不影响 GPT-SoVITS 权重文件） |
| **▶ 试听参考音频** | 播放该声音的 ref.* |

**GPT / SoVITS 权重选择已移入「新建/编辑声音」对话框**，TTS 主面板不再有独立权重下拉，
只保留只读的「当前权重」标签。

注：`ref_audio_path` 必须是**绝对路径**，因为该值会通过 HTTP 传给 GPT-SoVITS 服务，
由它按自己的 CWD 解析。

试听实现：`.venv-gui` 只装了 PySide6-Essentials，`QtMultimedia` 仅有 `.pyi` 存根无二进制，
因此用标准库 —— WAV 走 `winsound` 异步播放（`SND_PURGE` 停止），其他格式交给系统默认播放器。

`gpt_weight` / `sovits_weight` 支持两种写法，`find_weight_path` 均可解析：
- 路径式 `GPT_weights_v4/xxx.ckpt`（相对 GPT-SoVITS 根目录）
- 显示式 `xxx.ckpt  [GPT_weights_v4]`

### GPT-SoVITS 权重扫描

扫描**所有** `GPT_weights*` / `SoVITS_weights*` 版本目录，下拉条目带 `[目录名]` 版本标签。
当前 API 以 v4 DPO 启动（`start_v4_dpo.py`），应用非 v4 权重时会弹窗警告。

### 启动后自动打开浏览器

服务页有「启动完成后自动打开浏览器」复选框（默认勾选，状态存 `launcher_config.json`
的 `auto_open_browser`），旁边有「立即打开界面」按钮。

`_start_llm` 启动进程后会起一个守护线程轮询 12393 端口，就绪后经 `web_ready_signal`
回到主线程调用 `webbrowser.open("http://localhost:12393")`。用 `_web_open_token`
递增令牌避免重复打开；点击「停止」会使等待中的线程失效。

### Ollama 参数生效链路（v2.7 修）

**`_save_config()` 的触发点**：底部「保存配置」按钮、应用声音、**以及启动前自动保存**。
启动前自动保存是在 v2.7 补的——此前 `_start_llm()` / `_oneclick_start()` 都不保存配置，
所以「在 LLM 页换完模型直接点启动」不会生效：后端读的是磁盘上的旧 conf.yaml。
（`_oneclick_start` 运行在主线程，保存放在那里而不是 worker 线程里，
因为 `_save_config` 会读写 Qt 控件，跨线程不安全。）

**`num_gpu`/`num_ctx`/`think`/`preload` 必须两处都声明/转发才生效**（v2.7 修）：
1. `config_manager/stateless_llm.py` 的 `OllamaConfig` **声明**这 4 个字段
2. `agent/stateless_llm_factory.py` 的 ollama 分支**转发**给 `OllamaLLM`

此前两处都缺，pydantic 会静默丢弃 conf.yaml 里的同名字段（`I18nMixin` 未设
`extra="forbid"`），一直落在 `ollama_llm.py` 的构造默认值上。
**症状**：conf.yaml 写 `num_gpu: 12`，日志却是 `num_gpu=16` —— 为 GPU 共存做的
调优完全没生效。新增字段的默认值与构造函数保持一致，老配置缺字段时行为不变。

**排错提示**：后端只在进程启动时读一次 conf.yaml。服务已在运行时保存配置不会生效，
`_save_config` 会记一条提醒；`_start_llm` 遇到"已在运行"也会提示需先停止。

### 停止时自动卸载 Ollama 模型（v2.7 新增）

**为什么需要**：启动器停止服务用 `taskkill /F /T`（`:3391`/`:3766` 两处），
Windows 强制终止**不会执行 Python 的 atexit / `__del__`**，所以后端
`ollama_llm.py` 里 `atexit.register(self.cleanup)` 注册的卸载永远不跑；
加上 `keep_alive: -1`，Ollama 自己也不会过期 → 模型永久驻留显存。
（实测：强杀后 `/api/ps` 里模型仍在。）

**做法**：启动器侧主动卸载，零新依赖（纯 `urllib`）：

| 部件 | 说明 |
|------|------|
| `unload_ollama_model(model, timeout)` | `POST /api/generate`，`{"prompt":"", "stream":false, "keep_alive":0}`，与后端 `cleanup()` 同一接口；返回 `(ok, msg)`，永不抛异常 |
| `_ollama_model_in_use()` | 取本项目配置的模型名；**当前 provider 不是 `ollama_llm` 时返回空串**，避免误卸其他程序加载的模型 |
| `_unload_ollama_best_effort(wait=False)` | daemon 线程里卸载，成功失败都只记日志，不阻塞 UI、不弹窗 |

**三个调用点**（都在 taskkill **之后**——反之后端仍存活，预加载或下一轮对话会立刻把模型拉回来）：

| 位置 | wait | 说明 |
|------|------|------|
| `_stop_llm()` | False | 覆盖「一键停止 / 单独停止」 |
| `closeEvent()` | **True** | 关窗退出；**必须同步等**，否则进程结束会掐掉 daemon 线程、卸载请求发不出去 |
| `_on_llm_finished()` | False | 后端自行退出/崩溃时兜底；正常退出时 atexit 已卸过，重复调用无害 |

注意 `_stop_all` 走 `_stop_llm()`，而 `closeEvent` 走 `_terminate_sync()` ——
**两条停止路径不共用函数**，两处都要覆盖。

---

## 当前需求

> （在这里写你接下来要让 ZCode 帮你做的事）

### 已完成记录（2026-09-10，ZCode 会话）
- 遗留修复：`gpt_sovits_tts.py` 的 `streaming_mode` 注解改为 `str = "false"`；MCP 无害警告与诊断版 `openai_compatible_llm.py` 的 🧪 埋点日志降为 debug 级
- GUI v2.0：「预设」改名「模型」并移到服务后；Live2D 模型管理；角色编辑器 Live2D/头像下拉
- GUI v2.1：Live2D 独立标签页 + 贴图预览；角色编辑器四组字段 + 头像导入；权重扫描全部版本目录；voices/ 声音模型体系
- GUI v2.2：参考音频试听；权重选择移入声音对话框 + 声音模型增删改查（即预设）；Live2D 页并入角色页；修复贴图预览误取 UI 图标与模型名回退
- GUI v2.3：移除 Live2D 模型管理模块；TTS 显示「当前使用」的声音；启动完成后自动打开浏览器
- GUI v2.4：Live2D「打开保存目录」按钮 + 「导入...」（文件夹/多文件夹/zip，自动登记 model_dict.json）；预览下方提示模型格式兼容性；确认前端只支持 `.model3.json`
- 新增根目录 `启动器.bat`（GBK 编码，静默启动/`debug` 参数），GUI 启动失败时弹窗报错
- conf.yaml 的 `ref_audio_path` 已改为指向 `voices/加藤惠/ref.wav`，不再使用 GPT-SoVITS 根目录的 ref.wav
- 加藤惠live2d（Cubism 2.1，前端不支持）已弃用，其 `model_dict.json` 条目已移除；
  其余 41 条 url 全部核对有效

### 已完成记录（2026-09-10，ZCode 会话 · Live2D 动作表现优化）
- xinnong_6.model3.json 新增 `Idle`（15 个 idle 动作）/`Talk`（main_1~5）别名组，
  model_dict.json 补 tapMotions —— 默认角色（ja_test.yaml 指向它）从完全静止变为有
  待机/说话/点击反应；该模型无表情文件，情绪关键词对它天然无效
- mao_pro.model3.json 新增 `Talk`（mtn_02/03/04）组；emotionMap 修正三处错误映射
  （fear/sadness 原指开心笑脸、anger 原指闭眼）并扩充至 50 键（含中文同义词），
  启用闲置的悲伤(4)/害羞(5)/不安(6)/愤怒(7)表情
- transformers.py：`<think>` 内句子不再提取表情（原只跳过边界句，思考内容会误触发
  表情）；display_processor 接收 live2d_model 并剔除显示文本中的 `[关键词]`
  （remove_emotion_keywords 由死代码转正，字幕/聊天记录不再显示）
- 重写 live2d_expression_prompt.txt（每句最多一个关键词且放句首、自然使用）
- 新增只读扫描脚本 `scan_live2d_models.py` 与报告 `live2d_scan_report.md`：
  41 个模型中 37 个存在 Idle/Talk 组大小写不匹配，mao_pro 是唯一有 HitAreas 的模型

### 已完成记录（2026-09-11，ZCode 会话 · 尺寸自适应与关键词显示）
- 新增 `fit_live2d_scale.py`：解析 moc3 CanvasInfo（u32@0x44 → 5 个 float）计算
  kScale，41 个模型全部重算写回；mao_pro 保持 0.5（标定自洽）
- 画布适配对游戏系模型偏小（画布含动画余量），追加游戏系 ×1.5 目测倍率
  （逻辑画布高 > 5 触发），现值如 xinnong_6=0.0543、shizuku=0.67
- 尝试过解析 moc3 顶点自动求人物包围盒（全自动方案），因 keyform 间接索引无果
  放弃，结论已存档于尺寸自适应一节
- `construct_system_prompt`：模型 emotionMap 为空时跳过 live2d_expression_prompt，
  杜绝「空关键词列表 + 示例」诱导 LLM 编造 `[curiosity]` 之类关键词
- `display_processor` 在 remove_emotion_keywords 后用正则兜底剔除显示文本中
  所有剩余方括号 token（与 TTS 侧 ignore_brackets 一致），自创关键词不再漏进字幕
- 顺带修复：construct_system_prompt 在 Live2D 初始化失败时不再因 None 崩溃
- TTS 卡顿排查结论（用户选择先不改）：后端改动未影响 TTS 速度，异常为重启后
  首次合成 65.34s（GPT-SoVITS 冷启动/权重装载）；每句 3~8s 合成与历史一致，
  首音频延迟高还与 `faster_first_response=false`（整段回复完才开始合成）有关。
  若复现可加 GPT-SoVITS 启动预热 + 将 faster_first_response 改 true

### 待处理
- 其余模型按需处理：37 个 Idle/Talk 组大小写不匹配（见 live2d_scan_report.md），
  40 个 emotionMap 为空；两者都只影响对应模型被使用时的表现，用哪个补哪个
 
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