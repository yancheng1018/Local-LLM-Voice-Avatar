## GUI 启动器功能（v2.7）

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
| 形象 | Live2D 模型（下拉+刷新+打开目录+导入）、模型允许列表（live2d_model_names，逗号分隔） |
| 人设 | persona_prompt |
| 内部标识（一般无需修改） | conf_name、conf_uid |

- Live2D 模型为可编辑下拉，自动扫描 `model_dict.json` ∪ `live2d-models/`，支持手输
- `conf_uid` 留空保存时自动补为 `{conf_name}_001`；空的可选字段不会写入 YAML
- **list[str] 字段不得走 `char_edit_fields` 通道**（stage5 硬性契约）：该通道按
  `w.text().strip()` 字符串写回，会把 list 写成 str 导致 CharacterConfig 校验失败，
  填充时 `str(cc.get(key,""))` 也会把 list 显示成 Python repr。list 字段（如
  `live2d_model_names`）须用独立控件 + 手工解析（中文逗号归一、剔空白、
  「有值写入；清空且原键存在写 `[]`；清空且原本无键不写」）。
  另：`_save_character_inline` 走 ruamel round-trip（先 load 再改已知键），
  YAML 里的未知自定义键不会被启动器丢弃（有测试守护）

### Live2D 贴图预览的实现与限制

**不做骨骼渲染**：真正的 Live2D 渲染需要 Cubism Core 专有原生 DLL + `live2d-py` + OpenGL 上下文；
本项目只有 Web 版 `static/libs/live2dcubismcore.min.js`（后端挂 /libs 供前端用），Python 侧无原生运行时，
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
└── <声音名>/
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

### ⚠️ launcher 代码维护（stage5 教训）

- `OpenLLMVTuber_GUI.py` 历史上从未被 ruff format 过：对它执行 format 会触发
  **全文件重排**（实测 +332/-181 纯排版 diff），淹没功能改动。format-clean 化须
  单独立项，不得混入功能阶段；功能阶段对它只跑 `ruff check`
  （ruff 不在 Git Bash PATH，用 `uv run ruff`）
- 启动器.bat 为 **GBK 编码 + CRLF 换行**：编辑必须 python `encoding='gbk'` round-trip，
  text 模式读或 UTF-8 工具直写即破坏（cmd 解析错乱，2026-09-29 实踩：LF-only 后全盘乱
  执行报 9009）；CRLF 已由 test_publish_facade.py 守卫，GBK 守护是弱断言（UTF-8 中文常可
  被 GBK 静默乱解），人工编辑须自觉
- `OpenLLMVTuber_GUI.py` 为 **CRLF**（4293 处）：脚本做多行字面量替换时模式须带 `\r\n`
- 一键启动引擎联动（v2.7）：`tts_model != gpt_sovits_tts` 时跳过 GSV 启动与权重自动应用
  （tts_key 在主线程 `_oneclick_start` 捕获后传参 worker，跨线程禁读 Qt 控件）；
  `sherpa_onnx_tts` 配置值含 `/path/to` 占位时中止一键启动并提示
- GUI 门面文案约定：窗口/对话框标题用「Local-LLM-Voice-Avatar 启动器」（带版本号），
  状态/按钮/日志用「主服务」；旧名残留由 test_publish_facade.py 守卫

