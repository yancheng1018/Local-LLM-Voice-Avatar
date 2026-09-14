## Git 与仓库维护

> 做文件搬移、`.gitignore` 调整、分批提交、模型资产管理前读这里。
> 本仓库是**本地定制版**，`push.default = nothing`，默认不推送互联网。

### 忽略规则与已追踪文件的冲突（重要）

`.gitignore` 是**声明式**的，它只影响未追踪文件。已经进入索引的文件即使后来
被规则命中，**依然保持追踪**——这是设计如此，不是 bug，也无需 `git rm --cached`。

| 现象 | 真相 |
|------|------|
| 加了 `voices/` 规则后 `voices/加藤惠/voice.json` 仍被追踪 | 正常，它本就在索引里 |
| 想提交该类文件的**修改**，`git add voices/...` 被拒（ignored） | **这才是真问题**，须 `git add -f` |

自查有哪些已追踪文件落进了忽略范围：

```bash
git ls-files -i -c --exclude-standard
```

当前实测命中约 20 项（`avatars/`、`backgrounds/`、`voices/加藤惠/*` 等），
都是**刻意保留追踪**的：改它们要 `git add -f`。

### 本仓库的忽略策略

- `live2d-models/*` 整体忽略，仅 `!mao_pro/`、`!shizuku/` 两个上游示例模型入库。
- `models/`、`Spine-models/`、`voices/`、`avatars/`、`backgrounds/` 忽略但**保磁盘**。
- `conf.yaml` 忽略，入库模板是 `config_templates/conf.ZH.default.yaml`。
- 根目录 `conf.yaml.bak` / `.backup`、`model_dict.json.bak` 属脚本自动备份，一并忽略。

### 可搬移性红线（移走 = 服务器起不来）

以下目录被代码在启动时 import 或 mount，**永远留在原位**：

| 路径 | 依赖点 |
|------|--------|
| `upgrade_codes/` | `run_server.py:11` import + `:24` 模块级实例化 |
| `web_tool/` | `server.py` mount 为 `/web_tool` |
| `models/` | `run_server.py:21` 设为 `HF_HOME`；`conf.yaml` 指向其下 sherpa-onnx 模型 |
| `Spine-models/` | `server.py` 存在性检查后 mount 为 `/Spine-models` |
| `frontend/` | Git 子模块，`server.py` catch-all mount + `run_server.py` 自动初始化 |

其余上游遗留件已移入 `legacy/`（见 `legacy/README.md`）。

### 施工习惯（踩过的坑）

- `git mv` **不会**自动创建目标父目录，批量搬移前先确认父目录存在。
- 为分批提交而做全量 `git reset` 会**丢掉 `git mv` 的 rename 暂存**，导致旧路径
  删除未入暂存、仓库同时存在新旧两份。改用 `git restore --staged <path>` 逐项撤。
- 删除**已追踪**文件要用 `git rm`（才进暂存区）；未追踪的临时产物用普通删除即可。
- 提交前跑 `git diff --cached --stat`，确认没有 `models/`、`live2d-models/` 大文件混入。

### 相关工具

- `scan_live2d_models.py`：只读扫描 `live2d-models/`，生成 `live2d_scan_report.md`
  （该报告已忽略，属可重生成产物）。
- `fit_live2d_scale.py`：按 moc3 画布尺寸自动标定 `model_dict.json` 的 `kScale`
  （自动备份 `.bak`）。
