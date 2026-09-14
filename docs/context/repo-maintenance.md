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
- `frontend/` 忽略且**不在索引中，仅保磁盘**：旧官方前端，服务器仍 catch-all mount 它
  （`server.py`），删了服务器起不来。stage2 已解除其子模块关系（gitlink 移除、`.gitmodules`
  删除），不再指向上游；磁盘文件保留但不入库。
- `conf.yaml` 忽略，入库模板是 `config_templates/conf.ZH.default.yaml`。
- 根目录 `conf.yaml.bak` / `.backup`、`model_dict.json.bak` 属脚本自动备份，一并忽略。

### 可搬移性红线（移走 = 服务器起不来）

以下目录被代码在启动时 import 或 mount，**永远留在原位**：

| 路径 | 依赖点 |
|------|--------|
| `web_tool/` | `server.py` mount 为 `/web_tool` |
| `models/` | `run_server.py:21` 设为 `HF_HOME`；`conf.yaml` 指向其下 sherpa-onnx 模型 |
| `Spine-models/` | `server.py` 存在性检查后 mount 为 `/Spine-models` |
| `frontend/` | `server.py:172` catch-all mount（**无存在性检查**）+ `run_server.py:52` 启动检查；已非子模块（`.gitmodules` 已删），被 `.gitignore` 忽略、不在索引中，仅保磁盘 |

> `frontend/` 是本表里**唯一没有 `os.path.exists` 守卫**的 mount：`Spine-models`（`server.py:150`）
> 与 `frontend-minimal/dist`（`server.py:158`）都在 mount 前做了存在性判断，`frontend` 没有。
> 因此该目录一旦缺失，`CORSStaticFiles(directory="frontend")` 直接在启动时抛错，服务器起不来。
> 日后若真要删除它，**必须先给 `server.py:172` 补守卫**；这也是它"忽略但保磁盘"的根本原因 ——
> 文件不能删（无兜底），却又不该入库（44 MB，含嵌套 `.git`）。

> 变更记录（git_stage2）：`upgrade_codes/` 与 `upgrade.py` 已于本阶段移除，
> 不再需要升级能力。`run_server.py` 中的 `UpgradeManager` 依赖已剥离。
> 副作用：启动不再自动创建/备份/合并 `conf.yaml`，该文件必须预先存在。

其余上游遗留件已移入 `legacy/`（见 `legacy/README.md`）。

### 解除子模块关系（危险操作）

把子模块转成普通目录/忽略项时，**删 `.git/modules/<name>` 与删工作区里的
`<name>/.git` 指针必须成对进行** —— 只做前者会留下悬空 `gitdir`：

- `<name>/.git` 是个**文件**，内容为 `gitdir: ../.git/modules/<name>`。
- 一旦 `../.git/modules/<name>` 被删，该指针即失效，此后 git 对这个仓库的**任何**
  操作都报 `fatal: not a git repository: <name>/../.git/modules/<name>`。
- 失败的不只是子模块相关命令：一次普通的 `git reset` 也会连带回滚已暂存的改动
  （git_stage2 就因此把 `git rm --cached frontend` 偷偷撤掉了，`git status` 看着像已完成，
  实际索引里 gitlink 还在）。

**唯一可靠的验收断言**是索引本身，不是 `git status`：

```bash
git ls-files -s frontend          # 期望：无输出（不是"首列非 160000"）
```

> 注意 `git ls-files -s frontend` 已无条目时输出为空字符串；用 `-notmatch '^160000'`
> 这类写法反而会把"正确解除"判成失败（空串不匹配任何模式）。判定"为空"而不是"不等于"。

### 项目身份的耦联字段

改 `pyproject.toml` 的项目身份时，以下字段是**联动**的，漏改会导致 `uv sync` 失败
或行为与预期不符：

| 字段 | 位置 | 同步要求 |
|------|------|---------|
| `name` | `pyproject.toml` + `uv.lock` 的自引用条目 | 两处必须一致，否则 `uv sync` 报错 |
| `version` | `pyproject.toml` + `uv.lock` 同一自引用条目 | 两处必须一致 |

- `uv.lock` 中该项目自身条目形如 `source = { virtual = "." }`：**只改这一条**，
  不要动第三方依赖名。
- `version` 另有一处运行时用途：`run_server.py:24` 的 `get_version()` 从
  `pyproject.toml` 读 `version` 并打进启动横幅。它**不读 `name`**，
  所以"改了 `name` 但启动横幅没变"是正常现象，不是改名失败。
- 改完必须跑 `uv sync --dry-run` 验证（期望 `Would make no changes`）。

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
