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

**为什么用指针**：以当前配置为底就地合并会累积上一个角色的残留；指针让 `conf.yaml` 保持干净，每次启动只 merge 一次。

**⚠️ 契约（2026-09-15 fix2 起）**：`handle_config_switch` 角色文件分支的 merge 底只能是
`conf.yaml` 自身的 `character_config`——以当前角色或默认角色（套 `default_character` 指针）
为底，都会把该角色独有的可选键（`live2d_model_names`、`tts_config` 等）泄漏给未定义该键的
目标角色；仅「基础配置」分支（目标即默认角色）合法套指针。fix1 翻车：套指针后默认角色恰带
allowlist，复验全败——静态源码断言抓不住此语义错误，改合并逻辑须配语义级验证。守卫：`test_config_switch_merges_from_base_not_current`。

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

### 修改配置时
- 必须同时更新 `config_templates/conf.default.yaml` 和 `conf.ZH.default.yaml`
- `streaming_mode` 等字段必须保持字符串类型（权威说明与原因：ollama-backend.md §3）
- 使用 `ruamel.yaml` 的 `SingleQuotedScalarString` 保证格式
- 新增角色时**不要**再写 `conf_name`；`character_name` 与 `conf_uid` 必填且各自唯一（入库角色受 tests/test_characters_manifest.py 守卫；默认测试角色=characters/zh_demo.yaml，github-p0-characters 起入库）

