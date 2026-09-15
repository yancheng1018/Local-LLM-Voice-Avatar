# 极简前端 · 模型切换（同角色切换 Live2D，后端驱动）

> 拆分自 minimal-frontend.md（2026-09-15）。总入口与遗留 → minimal-frontend.md；兄弟分册：基础管线 →
> minimal-frontend-foundation.md、Live2D → minimal-frontend-live2d.md、Spine → minimal-frontend-spine.md。
> 预留落点：stage5（一角色多模型 allowlist）与模型消息安全类契约候选

**stage4 已完成**（2026-09-15，同角色切换 Live2D 模型，后端驱动）：

- 顶栏新增模型下拉：`fetch-live2d-models` / `switch-live2d-model` / `live2d-models` 三个 WS 消息；
  后端按名称白名单查表（排除 Spine `.skel` 与畸形条目），前端只在收到 `set-model-and-conf`
  回推后才加载新模型，`conf_name`/`conf_uid` 取自切换前的局部快照。切换失败回滚不变量与
  WS 互斥模式见 `live2d.md` 硬性契约第 8/9 条
- 测试 `frontend-minimal/tests/test_live2d_model_switch.py`：13 用例（静态契约 + 运行时白名单
  过滤 + 构建产物）。运行命令在本机为 `uv run --with pytest python -m pytest`（venv 无 pytest，
  见 current-work.md 待办）
- ⚠️ **静态源码断言测试的书写纪律**：先跑 `ruff format` 再写断言。`method_body()` 辅助函数
  以 `\n    def ` 四空格缩进为锚点，整个静态契约框架建立在「源码已格式化」之上；format 把
  带尾注释的调用折成多行就会让单行字符串断言假红（stage4 实际发生过）。断言必须对空白
  不敏感（`re.search` + `\s*`），不得断言单行书写或精确缩进；切片断言先证非空再切，
  防止空切片让断言恒真
