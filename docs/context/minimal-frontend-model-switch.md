# 极简前端 · 模型切换（同角色切换 Live2D，后端驱动）

> 拆分自 minimal-frontend.md（2026-09-15）。总入口与遗留 → minimal-frontend.md；兄弟分册：基础管线 →
> minimal-frontend-foundation.md、Live2D → minimal-frontend-live2d.md、Spine → minimal-frontend-spine.md。
> stage5（一角色多模型 allowlist）与模型消息安全知识已于 2026-09-15 蒸馏并入本文件

**stage4 已完成**（2026-09-15，同角色切换 Live2D 模型，后端驱动）：

- 顶栏新增模型下拉：`fetch-live2d-models` / `switch-live2d-model` / `live2d-models` 三个 WS 消息；
  后端按名称白名单查表（排除 Spine `.skel` 与畸形条目），前端只在收到 `set-model-and-conf`
  回推后才加载新模型，`conf_name`/`conf_uid` 取自切换前的局部快照。切换失败回滚不变量与
  WS 互斥模式见 `live2d.md` 硬性契约第 8/9 条
- 测试 `frontend-minimal/tests/test_live2d_model_switch.py`：19 用例（stage4 13 + stage5 5 +
  fix1 1；静态契约 + 运行时白名单/allowlist 过滤 + 构建产物）。运行命令在本机为
  `uv run --extra test python -m pytest`（pytest 已入 pyproject test 组，2026-09-16）
- ⚠️ **静态源码断言测试的书写纪律**：先跑 `ruff format` 再写断言。`method_body()` 辅助函数
  以 `\n    def ` 四空格缩进为锚点，整个静态契约框架建立在「源码已格式化」之上；format 把
  带尾注释的调用折成多行就会让单行字符串断言假红（stage4 实际发生过）。断言必须对空白
  不敏感（`re.search` + `\s*`），不得断言单行书写或精确缩进；切片断言先证非空再切，
  防止空切片让断言恒真

**stage5 已完成**（2026-09-15，一角色多模型 allowlist；fix2 切换角色 merge 底契约见
config-system.md「指针方案」节，Agent 重绑定见 live2d.md 硬性契约第 8 条）：

- 角色 YAML 可声明 `live2d_model_names: list[str]`。**allowlist 语义**（`resolve_allowed_model_names()`，
  websocket_handler.py 模块级同步 helper，查询与切换共用）：
  - 缺失或 `[]` = 未配置 → 回退全局名单（stage4 行为不变，旧 YAML 零迁移）
  - **查询时过滤，不在配置加载时校验**：对 `Live2dModel.list_frontend_models()` 名单过滤；
    不可用条目 `logger.warning` 后忽略，不让配置加载失败（model_dict 可后补）
  - **当前模型兜底**：过滤后 current 仍在名单内则 append 到末尾，保证下拉始终显示当前模型；
    current 是 Spine（不在名单）则不补
- ⚠️ **`live2d-models` handler 内不得发送任何 WS 消息**（防无限循环）。`fetch-live2d-models`
  只在 `set-model-and-conf` 成功 load 的 then 分支发送——保证角色切换/模型切换/重连后 current
  都会刷新，且回包时角色上下文已切换完成（在 switch-config 后立即发会有回包顺序竞争）；
  load 前 disabled / 成功后 enabled 门控防连续选择竞争
- ⚠️ **模型消息安全**：前端只传模型名（不传 URL/条目），后端查 model_dict 白名单校验；
  `live2d-models` 只回 `[{name}]`，绝不泄露 model_dict 条目或本机路径；对话生成中后端拒绝
  切换并发 error，不自动中断（切模型会重建 agent.chat 生成器管线，须防改写正在迭代的管线）
- 编辑器侧 list 字段通道契约见 gui-launcher.md「角色编辑器」；字段定义见 config-system.md

**stage6 已完成**（2026-09-15，bug 修复；成因与研究结论见 research_minimal-frontend-bugs.md）：

- ⚠️ **`currentLive2DModelName` 语义 = 最近一次成功加载的模型名**：赋值只在
  `set-model-and-conf` handler 的 `.then()`（load 成功后）进行，`.catch()` 中清空。
  加载前不得提前赋值——失败后该名若仍是刚失败的模型，`switch-live2d-model` 因
  `modelName === currentLive2DModelName` 直接 return，重选同一模型无法恢复；
  清空后重选**任何**模型（含刚失败那个）都会发出 switch 请求并收到 `set-model-and-conf`
  回推触发完整重载，一步恢复（后端同名切换是 no-op 但仍回发，故无需改动后端）

**live2d_model=None 降级契约（github-p3-public-h）**：init_live2d 容错失败后
live2d_model=None，连接不拒、降级服务。所有 set-model-and-conf 发送点
（_send_initial_messages / handle_config_switch）守卫 None、model_info 发 null——前端
main.ts 对空值现成降级（未配置模型）；switch_live2d_model None 态视为可切换（含成功
尾部日志用 old_model_name 不解引用模型对象），下拉重选任意已登记模型即恢复。新模型
入库须走登记（GUI 模型页扫描补录/导入流程），只放目录不登记=查表必失败（未登记名抛
KeyError）。
