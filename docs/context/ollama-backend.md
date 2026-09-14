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

