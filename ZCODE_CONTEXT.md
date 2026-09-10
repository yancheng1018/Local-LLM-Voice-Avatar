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
2. `characters/*.yaml` — 角色配置（可覆盖主配置的任意字段）
3. `config_templates/` — 默认模板（参考用）

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

### 待处理
- 无（原「加藤惠live2d 格式不兼容」一项已通过弃用该模型解决）
