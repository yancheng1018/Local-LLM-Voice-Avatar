# legacy/ — 上游遗留部件

本目录存放从 Open-LLM-VTuber 上游继承、但本项目（v1.2.1-zh 定制版）当前不使用的部件。
集中放在此处是为了保持根目录整洁，并非删除。若日后需要，可原样移回根目录。

| 条目 | 原路径 | 说明 |
|------|--------|------|
| `.cursor/` | 根目录 | Cursor 编辑器规则；本项目用 ZCode |
| `.gemini/` | 根目录 | Gemini 编辑器规则；本项目用 ZCode |
| `doc/sample_conf/` | `doc/` | 上游标注 deprecated 的 sherpa-onnx 示例配置 |
| `scripts/run_bilibili_live.py` | `scripts/` | B 站直播接入脚本 |
| `pixi.lock` | 根目录 | pixi 包管理器锁文件；本项目用 uv |
| `dockerfile` | 根目录 | 容器构建文件；本项目在 Windows 本地运行 |
| `周期性检查（建议每周或每阶段一次）.ps1` | 根目录 | 行数 + 索引表一致性检查脚本；内容已收录于 docs/context/MAINTENANCE.md §四 |

> ⚠️ 不要放入 `upgrade_codes/`、`web_tool/`、`models/`、`Spine-models/`：
> 它们是运行时依赖，移走会导致服务器无法启动。
