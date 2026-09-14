# 规格书：与上游项目切割（git_stage2）

> 目标读者：弱模型执行者。本文件是唯一施工图纸。不要自行发挥、不要扩大删除范围。
> 阶段：git_stage2。前置：git_stage1 已完成（6 条提交已落地，工作区干净，见 `git log`）。
> 本阶段主题：**本项目今后全程独自开发，切断与上游 Open-LLM-VTuber 的一切关系。**

---

## 0. 背景与硬性约束（先读完再动手）

### 0.1 用户已确认的五项决策

| # | 决策项 | 结论 |
|---|--------|------|
| 1 | remote 归属 | **移除**指向上游官方仓库的 remote |
| 2 | `frontend/` 子模块 | **暂时保留旧前端**，日后看需要再删 |
| 3 | `voices/`、`avatars/`、`backgrounds/` 入库 | **不需要入库**（stage1 已忽略，本阶段不反转） |
| 4 | `Temp/` 中 l2d.su 逆向产物 | 日后还需要 → **复制进素材区**后再处理 |
| 5 | `upgrade_codes/` + `upgrade.py` | **不需要升级能力**，与上游切割 → 移除 |

> 总原则：本阶段之后，仓库里**不应再有任何指向 t41372/Open-LLM-VTuber 的活链接**（除 LICENSE 等法律性归属文本）。

### 0.2 前置事实勘误（与 stage1 规格书不同处，务必按本节执行）

stage1 规格书把 `upgrade_codes/` 列为"运行时依赖，禁区"。**本阶段推翻该结论**——用户决定切割升级能力。
但这带来一个真实的代码改动，不能只删目录：

`run_server.py` 有 4 处依赖 `upgrade_codes`，删目录前必须处理：

| 位置 | 代码 | 处理 |
|------|------|------|
| `run_server.py:11` | `from upgrade_codes.upgrade_manager import UpgradeManager` | 删除 import |
| `run_server.py:24` | `upgrade_manager = UpgradeManager()` | 删除（模块级实例化，import 时即执行） |
| `run_server.py:61` | `lang = upgrade_manager.lang`（在 `check_frontend_submodule` 内，仅在 lang is None 时用） | 改为固定 `lang = "zh"` |
| `run_server.py:130` | `lang = upgrade_manager.lang`（`run()` 内） | 改为固定 `lang = "zh"` |
| `run_server.py:137` | `upgrade_manager.sync_user_config()` | 删除整个 try 块 |

**行为变化说明（必须写进交付报告，不要试图"修好"它）**：
`sync_user_config()` 原本在启动时做三件事 —— ①`conf.yaml` 不存在则从 `config_templates/conf.ZH.default.yaml` 复制；②备份 `conf.yaml` 到 `conf.yaml.backup`；③比对默认配置字段并合并。
移除后：**启动不再自动创建/备份/合并 conf.yaml**。
→ 因此 `conf.yaml` 必须**已存在**才能启动。施工前确认 `Test-Path conf.yaml` 为 True；若为 False，**停下报告**，不要自己造配置文件。

### 0.3 `frontend/` 子模块：本阶段只"断链"不"删文件"

`frontend/` 是 git 子模块（gitlink `160000 06a659b…`，`.gitmodules` 指向上游 `Open-LLM-VTuber-Web`）。
用户决定"暂时保留旧前端"，但这与"切断上游关系"冲突——子模块的 remote 就是上游。

**本阶段的处理方式（关键判断，已定）**：
- **保留磁盘上的 `frontend/` 全部文件**（`server.py:173` 仍然 mount 它，删了服务器起不来）。
- **解除子模块关系**，让它变成普通目录：删除 `.gitmodules` 与 `.git/config` 中的 submodule 段，并把 `frontend/` 的 gitlink 从索引中移除后按普通文件重新加入。

**风险提示（写在报告里）**：把子模块转为普通目录会把 `frontend/` 下约 10 个文件（`index.html`、`favicon.ico`、`assets/`、`libs/` 内的 wasm/onnx）**实际入库**，仓库体积增加约 10~20 MB。这是"切断上游"的必然代价。若用户日后不想入库，可改为在 `.gitignore` 忽略 `frontend/`。

> 若施工中发现 `.gitmodules` 或 `.git/modules/frontend` 状态与上述描述不符（例如 gitlink 已消失），**停下报告**，不要凭猜测继续。

---

## 1. 需要修改或新建的文件路径

| 类型 | 路径 | 说明 |
|------|------|------|
| 修改 | `run_server.py` | 移除 `upgrade_codes` 依赖（5 处，见 0.2 表） |
| 删除 | `upgrade.py` | 升级入口脚本 |
| 删除 | `upgrade_codes/` | 整个目录（升级核心） |
| 删除 | `.gitmodules` | 子模块定义 |
| 修改 | `pyproject.toml` | 改 name/description，并删除悬空的 `readme` 字段（见 2.6） |
| 删除 | `README.md` | 上游英文 README，用户确认直接删除（见 2.7） |
| 删除 | `README.CN.md` | 上游中文 README，用户确认直接删除（见 2.7） |
| 修改 | `docs/context/repo-maintenance.md` | 更正 `upgrade_codes/` 红线结论（见 2.9） |
| 修改 | `AGENTS.md` | 每阶段规范要求（不新增内容，仅核对，见 2.10） |
| 新建 | `docs/assets/` 目录 | l2d.su 逆向产物素材区（见 2.4） |
| 移动 | `legacy/` 中的 `.github/` 等 | 见 2.5（上游 CI/协作文件） |
| 检查 | `.github/` | 上游 CI workflow 与协作文档，见 2.5 |
| 检查 | `CLAUDE.md`、`.pre-commit-config.yaml`、`CONTRIBUTING.md`、`mcp_servers.json` | 残留上游内容，见 2.5 |
| 检查 | `requirements.txt`、`uv.lock`、`pixi.lock`（如仍在） | 依赖与上游项目名绑定，见 2.6 |

> `Temp/` 已在 stage1 被**删除**。若 `Test-Path Temp` 为 False，则 2.4 无源文件可复制 ——
> 此时改为从 `git log` 找回或报告用户，**不要跳过不报**。

---

## 2. 核心逻辑分步描述

### 2.1 第一步：确认基线（只读，必须最先做）

```powershell
git log --oneline -3                    # 确认 stage1 的提交在
git status --porcelain                  # 期望空
Test-Path conf.yaml, upgrade_codes, upgrade.py, .gitmodules, frontend/index.html, Temp
git submodule status
```

**期望**：`conf.yaml`=True、`upgrade_codes`=True、`upgrade.py`=True、`.gitmodules`=True、`frontend/index.html`=True、`Temp`=**False**（stage1 已删）。
任一不符 → 停下报告。

### 2.2 第二步：改 `run_server.py`，剥离 `upgrade_codes`

**逐条精确改（共 5 处，不要多改一行）**：

1. **删** 第 11 行整行：`from upgrade_codes.upgrade_manager import UpgradeManager`
2. **删** 第 24 行整行及其上方空行：`upgrade_manager = UpgradeManager()`
3. `check_frontend_submodule` 函数内，把
   ```python
   if lang is None:
       lang = upgrade_manager.lang
   ```
   **改为**
   ```python
   if lang is None:
       lang = "zh"
   ```
4. `run()` 函数内，把
   ```python
   # Get selected language
   lang = upgrade_manager.lang
   ```
   **改为**
   ```python
   # Get selected language
   lang = "zh"
   ```
5. `run()` 函数内，**删除整个 try 块**：
   ```python
   # Sync user config with default config
   try:
       upgrade_manager.sync_user_config()
   except Exception as e:
       logger.error(f"Error syncing user config: {e}")
   ```
   → 在**原位置**加一行注释说明行为变化：
   ```python
   # 已移除上游的配置同步（sync_user_config）：不再自动创建/备份/合并 conf.yaml。
   # conf.yaml 必须预先存在，否则启动失败。
   ```

**验证**：`rg -n "upgrade_manager|upgrade_codes" run_server.py` 必须**无输出**。

### 2.3 第三步：删除升级能力

```powershell
git rm upgrade.py
git rm -r upgrade_codes
```

**验证**：
```powershell
Test-Path upgrade_codes, upgrade.py      # 期望 2 × False
rg -n "upgrade_codes|upgrade\.py|UpgradeManager" --glob '!.git/**' --glob '!logs/**' --glob '!docs/**' --glob '!legacy/**' .
```
期望 `rg` 无输出。若还有输出（例如 `CLAUDE.md` 提到），记下路径留给 2.5 处理，**不要**改 `docs/` 下的历史文档（那是有意保留的记录）。

### 2.4 第四步：l2d.su 逆向产物归档到素材区

用户要求"日后还需要使用"。做法是**先复制、不删源**（源已在 stage1 删除的情况下跳到兜底）。

```powershell
New-Item -ItemType Directory -Force docs/assets
```

**若有 `Temp/`**（本阶段预期没有，但以防万一）：
```powershell
Copy-Item Temp\su_*.json,Temp\*_deob.js docs/assets\
```

**兜底：从 git 历史找回**（stage1 删除的 `Temp/` 文件若从未入库则不可找回）：
```powershell
git log --all --diff-filter=D --name-only -- 'Temp/*'
```
`docs/assets/` 中应包含的内容清单（用于核对）：`su_touch_rules_skin9.json`、`su_touch_geometry.json`、`su_ships-CN.json`、`su_site_model3.json`、`su_decoded_strings.json`、`su_sparseRuntime*.js`、`su_modelRuntime_deob.js`、`xinnong_*.json`。

**判断点**：`git log` 若返回空（文件从未入库、已物理删除），**只能**在报告里写明"逆向产物已不可找回"，并检查 `docs/context/spec-l2dsu-engine.md` 与 `spec-l2d-touch-engine.md` 是否已收录其结论 —— 若已收录，视为可接受；若未收录，**停下报告**这个损失。

**`docs/assets/` 必须入库**（它是知识资产，不是临时产物）：
```powershell
git add docs/assets
```

### 2.5 第五步：清理其余上游协作/CI 文件

**先看清单再决定**：
```powershell
ls .github/, .github/workflows/, .github/ISSUE_TEMPLATE/
Test-Path CLAUDE.md, CONTRIBUTING.md, .pre-commit-config.yaml, mcp_servers.json
```

**处理规则**（按类型逐个 `git mv` 进 `legacy/`，不要物理删除）：

| 路径 | 处理 | 理由 |
|------|------|------|
| `.github/FUNDING.yml` | → `legacy/.github/` | 上游赞助配置 |
| `.github/ISSUE_TEMPLATE/` | → `legacy/.github/` | 上游 issue 模板 |
| `.github/copilot-instructions.md` | → `legacy/.github/` | 上游 AI 指令 |
| `.github/workflows/` | → `legacy/.github/` | 上游 CI（codeql/ruff/release/fossa），本仓库不推送故无用 |
| `CONTRIBUTING.md` | → `legacy/` | 上游贡献指南 |
| `CLAUDE.md` | → `legacy/` | 上游 AI 上下文；本项目用 `AGENTS.md` |
| `.pre-commit-config.yaml` | **保留原位** | 本地开发仍可用（`ruff` 钩子），无上游链接 |
| `mcp_servers.json` | **保留原位** | 运行时可能被读取，非上游专属 |

**注意 `CLAUDE.md` 的判断点**：先确认它是否被引用：
```powershell
rg -n "CLAUDE\.md" --glob '!.git/**' --glob '!legacy/**' .
```
- 有引用 → **停下报告**，不要搬。
- 无引用 → 搬进 `legacy/`。

**`.github/` 整目录搬空后**：若 `.github/` 下已空，`git mv .github legacy/.github` 一次性搬走；否则按文件搬。先 `ls .github/` 看清再决定（这是一次判断）。

### 2.6 第六步：切断项目身份与上游的绑定

**`pyproject.toml`**（第 2-4 行）：
```toml
name = "open-llm-vtuber"
version = "1.2.1"
description = "Talk to any LLM with hands-free voice interaction, voice interruption, and Live2D taking face running locally across platforms"
```

**改法**：
- `name` 改为 `"open-llm-vtuber-zh-local"`（本地定制版标识）
- `description` 改为中文描述，去掉上游营销文案，例如：
  `"本地离线语音交互 AI 伴侣（Open-LLM-VTuber 定制版，已与上游切割）"`

**必须同时检查依赖锁文件是否仍写死上游包名**：
```powershell
rg -n "open-llm-vtuber|Open-LLM-VTuber" requirements.txt uv.lock pyproject.toml 2>$null
```
- `uv.lock` 中若出现自身包名条目，需与 `pyproject.toml` 的 `name` **保持一致**；否则 `uv sync` 会报错。
  改法：只替换**指代本项目自身**的条目，不要动第三方依赖名。改完后**必须**跑 `uv sync --dry-run` 验证（见 5.2 J4）。
- `requirements.txt` 若只是依赖清单（无项目名），不动。

**`version` 字段保持 `1.2.1` 不动** —— 避免触发版本升级逻辑，也与 stage1 报告一致。

### 2.7 第七步：删除 README（含处理悬空引用）

**用户已确认：`README.md` 与 `README.CN.md` 不需要保留，直接删除。**

原因说明（写进交付报告）：这两份文件是上游面向全球用户的英文/中文宣传文档，含大量徽章、
上游仓库与文档站链接、Docker 镜像、赞助与 Star History 图。本项目为本地定制版且已与上游切割，
保留它们没有意义，逐行清理上游链接的成本也高于直接删除。

**⚠️ 删除前必须先处理 `pyproject.toml` 的悬空引用（这是本步唯一的坑）**

`pyproject.toml:5` 当前为：
```toml
readme = "README.md"
```

删除 README 后该字段会指向不存在的文件，导致 `uv sync`、`uv build`、`pip install -e .` 报错。

**改法**：在 2.6 节改 `name`/`description` 的同时，**删除第 5 行整行** `readme = "README.md"`。
`pyproject.toml` 的 `[project]` 表中 `readme` 是可选字段，删掉后合法。

**删除命令**：
```powershell
git rm README.md README.CN.md
```

**验证**：
```powershell
Test-Path README.md, README.CN.md          # 期望 2 × False
rg -n "readme" pyproject.toml              # 期望无输出
uv sync --dry-run                          # 期望成功，无 "README.md not found"
```

**连带影响核对（只读，确认没有别的文件引用它们）**：
```powershell
rg -n "README\.md|README\.CN\.md" --glob '!.git/**' --glob '!legacy/**' --glob '!docs/**' .
```
注意排除 `docs/` —— 里面 `temp_spec_git_stage1.md`、`impl_report_git_stage1.md`、
`repo-maintenance.md` 提到的 `README` 是指 `legacy/README.md`（stage1 新建的归档说明），
与本步删除的两份上游 README 无关，**不要跟着改**。
`AGENTS.md:53` 引用的同样是 `legacy/README.md`，也不动。

**期望结果**：排除 `docs/` 与 `legacy/` 后 `rg` 无输出。若有输出，**停下报告**。

**法律红线**：`LICENSE`、`LICENSE-Live2D.md` **绝对不许动** —— 上游是 MIT 许可，
保留许可声明是法律义务，与"切断上游关系"无关。README 可删，LICENSE 不可删。

### 2.8 第八步：移除上游 remote

```powershell
git remote remove origin
```

**验证**：
```powershell
git remote -v                          # 期望：无输出
git config --get remote.origin.url     # 期望：无输出（非 0 退出码，正常）
```

**保留** `push.default = nothing` 与分支 `v1-release` —— 它们与 remote 无关。
**注意**：移除 remote 后 `origin/v1-release` 引用会消失，stage1 的 `T10_no_push` 断言不再适用，本阶段改用「`git remote -v` 为空」作为等价断言。

**不要**执行 `git branch --unset-upstream` 报错就慌 —— 移除 remote 后 upstream 自动失效，若报错也无害，记下即可。

### 2.9 第九步：解除 `frontend/` 子模块关系（**本阶段最高风险步骤**）

**执行前提**：`git status --porcelain` 为空（先把 2.2~2.8 提交掉再做，或至少确认无冲突改动）。

**做法（按顺序，每步验证）**：

```powershell
# 9.1 确认当前是子模块
git submodule status
git ls-files -s frontend              # 期望首列为 160000

# 9.2 把子模块从索引中移除（同时清 .gitmodules 记录）
#      --cached 只动索引，不删工作区文件
git rm --cached frontend

# 9.3 删除 .gitmodules
git rm .gitmodules

# 9.4 清掉本地 submodule 配置（.git/config 中的 [submodule "frontend"] 段）
git config --remove-section submodule.frontend 2>$null
Remove-Item -Recurse -Force .git\modules\frontend -ErrorAction SilentlyContinue

# 9.5 把 frontend/ 作为普通目录重新入库
#      先确认 .gitignore 没有忽略它！
git check-ignore -v frontend
git add frontend
```

**关键断言**：
```powershell
git ls-files -s frontend | Select-Object -First 3
```
期望：**首列不再是 `160000`**（应为 `100644`/`100755`），即已变成普通文件。

**9.5 的判断点 J3**：若 `git check-ignore -v frontend` **有输出**（被忽略），则 `git add frontend` 会静默失败。
→ 此时改为：在 `.gitignore` 中显式加入反向规则 `!frontend/`，或在用户报告后决定是否干脆忽略整个 `frontend/`。**停下报告，不要 `git add -f` 硬塞 10MB 二进制进仓库。**

**验证 frontend 仍能工作**：
```powershell
Test-Path frontend/index.html, frontend/libs/live2d.min.js
```
期望 2 × True。若 False → 误删了工作区文件，立刻 `git checkout -- frontend`（若已提交则从上一提交恢复），并**停下报告**。

### 2.10 第十步：更新 `docs/context/repo-maintenance.md`

stage1 的红线表把 `upgrade_codes/` 列为"永远留在原位"。本阶段推翻了它，**必须更正**，否则下个会话会按错规则干活。

改法：把「可搬移性红线」表中的 `upgrade_codes/` 那一行**删除**，并在表下追加一段：

```markdown
> 变更记录（git_stage2）：`upgrade_codes/` 与 `upgrade.py` 已于本阶段移除，
> 不再需要升级能力。`run_server.py` 中的 `UpgradeManager` 依赖已剥离。
> 副作用：启动不再自动创建/备份/合并 `conf.yaml`，该文件必须预先存在。
```

**不要修改 AGENTS.md**（约束要求）。只核对它是否仍需引用 repo-maintenance.md —— 若索引表已指向该文件，无需改动。

### 2.11 第十一步：分批提交（**不 push，已无 remote**）

**提交前自检**：
```powershell
git status --porcelain | Measure-Object -Line
Test-Path upgrade_codes, upgrade.py, .gitmodules    # 期望 3 × False
Test-Path frontend/index.html, conf.yaml            # 期望 2 × True
```

**按以下 6 条提交，一条一个 `git add` + `git commit`**：

| # | 提交信息（原样使用） | 暂存内容 |
|---|---------------------|---------|
| 1 | `refactor: 剥离 run_server.py 对 upgrade_codes 的依赖` | `run_server.py` |
| 2 | `chore(cleanup): 移除升级能力 upgrade_codes/ 与 upgrade.py` | `upgrade_codes/`、`upgrade.py` 的删除 |
| 3 | `docs(assets): 归档 l2d.su 逆向产物到 docs/assets/` | `docs/assets/` |
| 4 | `chore(cleanup): 上游 CI 与协作文件移入 legacy/` | `.github/`、`CONTRIBUTING.md`、`CLAUDE.md` 的搬移 |
| 5 | `chore: 解除 frontend 子模块关系，改为普通目录` | `.gitmodules` 删除 + `frontend/` 重新入库（含 9.1~9.5 全部改动） |
| 6 | `chore(identity): 切断与上游项目的身份绑定` | `pyproject.toml`（含删 `readme` 字段）、`README.md` 与 `README.CN.md` 的删除、`uv.lock`、`docs/context/repo-maintenance.md` |

**收尾**：
```powershell
git log --oneline -8
git status --porcelain        # 期望空
git remote -v                 # 期望空
```

残留非空 → 逐条判断归类，**报告后再决定**，不要 `git add .`。

### 2.12 第十二步：启动回归（最关键的一步）

删除 `upgrade_codes` 直接动到启动路径，**必须实测服务器能起来**。

```powershell
uv run python -c "import ast,sys; ast.parse(open('run_server.py',encoding='utf-8').read()); print('syntax-ok')"
uv run python run_server.py --verbose
```
第二个命令会**阻塞**（服务器常驻）。做法：后台启动，等 20 秒，看日志里有没有 `Starting server on 0.0.0.0:12393`，然后杀掉。

```powershell
# 前台跑 20 秒后自动结束
$p = Start-Process -FilePath "uv" -ArgumentList "run","python","run_server.py","--verbose" -NoNewWindow -PassThru
Start-Sleep -Seconds 20
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Get-Content logs\debug_$(Get-Date -Format 'yyyy-MM-dd').log -Tail 40
```

**断言**：日志末尾出现 `Starting server on`，且**没有** `ModuleNotFoundError: No module named 'upgrade_codes'`。
若出现后者 → `run_server.py` 还有残留引用，回 2.2 重查。

### 2.13 第十三步：确认「不推送互联网」策略仍生效

```powershell
git config --local push.default        # 期望 nothing
git config --local --get-regexp remote # 期望无输出
```

在交付报告里说明：remote 已移除，**不可能**误推到上游；`push.default=nothing` 保留作为双保险。

---

## 3. 函数签名与关键变量名

本阶段以文件与代码删改为主。涉及名字（勿改名、勿新增）：

- `run_server.py` 删除：`UpgradeManager`（类引用）、`upgrade_manager`（模块级变量）
- `run_server.py` 保留并改值：`check_frontend_submodule(lang=None)` 的 `lang` 参数、`run(console_log_level: str)` 内的局部 `lang`
- `run_server.py` 保留：`get_version()`、`init_logger(console_log_level: str = "INFO")`、`parse_args()`
- `server.py` 不动：mount 名 `"frontend"`、`"frontend_minimal"`、`"web_tool"`、`"spine_models"`
- 上游常量（随 `upgrade_codes/` 一起消失）：`USER_CONF = "conf.yaml"`、`BACKUP_CONF = "conf.yaml.backup"`、`ZH_DEFAULT_CONF = "config_templates/conf.ZH.default.yaml"`、`select_language()`
- 规格书路径：`docs/context/temp_spec_git_stage2.md`

---

## 4. 测试用例列表

| 用例名 | 输入（命令） | 预期输出 | 断言点 |
|--------|-------------|---------|--------|
| `T1_upgrade_removed` | `Test-Path upgrade_codes, upgrade.py` | 2 × False | 升级代码已删 |
| `T2_no_upgrade_refs` | `rg -n "upgrade_codes\|upgrade_manager\|UpgradeManager" run_server.py` | 无输出 | 启动路径无残留引用 |
| `T3_runserver_syntax` | `uv run python -c "import ast;ast.parse(open('run_server.py',encoding='utf-8').read());print('ok')"` | `ok` | 改动后语法正确 |
| `T4_conf_required` | `Test-Path conf.yaml` | True | 移除自动创建后配置仍存在 |
| `T5_submodule_broken` | `git ls-files -s frontend \| Select-Object -First 1` | 首列非 `160000` | gitlink 已解除 |
| `T6_no_gitmodules` | `Test-Path .gitmodules` | False | 子模块定义已删 |
| `T7_frontend_files_intact` | `Test-Path frontend/index.html, frontend/libs/live2d.min.js` | 2 × True | **前端文件未丢** |
| `T8_remote_gone` | `git remote -v` | 空 | 上游 remote 已移除 |
| `T9_push_guard` | `git config --local push.default` | `nothing` | 防误推仍在 |
| `T10_assets_archived` | `Get-ChildItem docs/assets -File \| Measure-Object` | Count ≥ 1（或按 2.4 兜底说明） | 存档或已记录损失 |
| `T11_legacy_grew` | `Test-Path legacy/.github` 等 | True（或按 2.5 判断说明） | 上游文件已归档非删除 |
| `T12_identity_clean` | `rg -n "open-llm-vtuber" pyproject.toml` | 无上游原值 | 项目身份已改 |
| `T12b_readme_removed` | `Test-Path README.md, README.CN.md` | 2 × False | README 已删 |
| `T12c_no_dangling_readme` | `rg -n "readme" pyproject.toml` | 无输出 | 无悬空 `readme` 字段 |
| `T13_docs_updated` | `rg -n "upgrade_codes" docs/context/repo-maintenance.md` | 命中「变更记录」段 | 红线表已更正 |
| `T14_clean_tree` | `git status --porcelain` | 空 | 工作区干净 |
| `T15_commits_landed` | `git log --oneline -6` | 6 条新提交 | 与 2.11 表格一致 |
| `T16_server_boots` | 2.12 的启动回归 | 日志含 `Starting server on` | **无 ModuleNotFoundError** |
| `T17_license_intact` | `Test-Path LICENSE, LICENSE-Live2D.md` | 2 × True | 法律归属文本未被误删 |

> `T7`、`T16`、`T17` 是安全网。任一失败**立即停下报告**。

---

## 5. 步骤分类

### 5.1 「工具可完成」——给命令，原样执行

| 步骤 | 命令 |
|------|------|
| 基线确认 | `git status --porcelain; git submodule status; Test-Path conf.yaml` |
| 查残留引用 | `rg -n "upgrade_codes\|upgrade_manager" --glob '!.git/**' --glob '!docs/**' .` |
| 删升级代码 | `git rm upgrade.py; git rm -r upgrade_codes` |
| 建素材区 | `New-Item -ItemType Directory -Force docs/assets` |
| 查历史删除记录 | `git log --all --diff-filter=D --name-only -- 'Temp/*'` |
| 看 CI 清单 | `ls .github/, .github/workflows/, .github/ISSUE_TEMPLATE/` |
| 搬归档 | `git mv <src> legacy/<dst>` |
| 改 remote | `git remote remove origin` |
| 解子模块 | `git rm --cached frontend; git rm .gitmodules; git config --remove-section submodule.frontend` |
| 重入库前端 | `git check-ignore -v frontend; git add frontend` |
| 提交 | `git add <path>; git commit -m "<msg>"`（6 组） |
| 启动回归 | 见 2.12 的 PowerShell 块 |
| 最终验证 | 见第 6 节断言脚本 |

### 5.2 「需要判断」——留给弱模型

| # | 判断项 | 依据 | 不确定时 |
|---|--------|------|---------|
| J1 | `Temp/` 是否还在 | `Test-Path Temp` | 不在 → 走 2.4 兜底并报告损失 |
| J2 | 删除 README 后是否还有其他文件引用它们 | `rg -n "README" --glob '!.git/**' --glob '!legacy/**' --glob '!docs/**' .` | 有输出 → **停下报告**（注意 `legacy/README.md` 不算） |
| J3 | `frontend/` 是否被 `.gitignore` 忽略 | `git check-ignore -v frontend` | 有输出 → 停下报告，**不 `git add -f`** |
| J4 | `uv.lock` 是否含自身包名条目 | `rg -n "open-llm-vtuber" uv.lock`，改后 `uv sync --dry-run` | 报错 → 回退 `uv.lock` 改动并报告 |
| J5 | `CLAUDE.md` 是否被引用 | `rg -n "CLAUDE\.md" --glob '!.git/**' .` | 有引用 → 停下报告 |
| J6 | `.github/` 是否已空（可否整目录搬） | `ls .github/` | 非空 → 按文件搬 |
| J7 | 提交后残留文件如何归类 | `git status --porcelain` | 报告后决定，**不 `git add .`** |
| J8 | `mcp_servers.json` / `.pre-commit-config.yaml` 是否被引用 | `rg -n "mcp_servers\|pre-commit" --glob '!.git/**' .` | 有引用 → 保留原位 |

---

## 6. 运行测试（弱模型原样执行，不要修改）

> 本阶段无 pytest 用例（项目未建 `tests/test_git_stage2.py`）。用等价 PowerShell 断言。
> 若项目已引入 `tests/test_git_stage2.py`，改用文末 pytest 命令块。

```powershell
$fail = 0
function Check($name, $cond, $detail) {
    if ($cond) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name  -> $detail" -ForegroundColor Red; $script:fail++ }
}

# T1/T2 升级代码已删且无残留引用
Check "T1_upgrade_removed" (-not (Test-Path upgrade_codes) -and -not (Test-Path upgrade.py)) "升级代码仍存在"
$refs = rg -n "upgrade_codes|upgrade_manager|UpgradeManager" run_server.py 2>$null
Check "T2_no_upgrade_refs" ([string]::IsNullOrWhiteSpace($refs)) "run_server.py 残留引用: $refs"

# T3 语法
$syn = uv run python -c "import ast;ast.parse(open('run_server.py',encoding='utf-8').read());print('ok')" 2>&1
Check "T3_runserver_syntax" ($syn -match 'ok') "语法错误: $syn"

# T4 conf.yaml 必须存在
Check "T4_conf_required" (Test-Path conf.yaml) "conf.yaml 缺失，启动会失败"

# T5/T6 子模块关系已解除
$gl = (git ls-files -s frontend | Select-Object -First 1)
Check "T5_submodule_broken" ($gl -notmatch '^160000') "仍是 gitlink: $gl"
Check "T6_no_gitmodules" (-not (Test-Path .gitmodules)) ".gitmodules 仍在"

# T7 前端文件完好（关键）
Check "T7_frontend_files_intact" ((Test-Path frontend/index.html) -and (Test-Path frontend/libs/live2d.min.js)) "前端文件丢失！"

# T8/T9 remote 与防误推
Check "T8_remote_gone" ([string]::IsNullOrWhiteSpace((git remote -v))) "remote 仍存在"
Check "T9_push_guard" ((git config --local push.default) -eq "nothing") "push.default 未设置"

# T10 素材归档
$assets = (Get-ChildItem docs/assets -File -ErrorAction SilentlyContinue | Measure-Object).Count
Check "T10_assets_archived" ($assets -ge 1) "docs/assets 为空（见 2.4 兜底说明）"

# T11 legacy 增长
Check "T11_legacy_grew" (Test-Path legacy) "legacy 不存在"

# T12/T13 身份与文档
$idref = rg -n '^name = "open-llm-vtuber"' pyproject.toml 2>$null
Check "T12_identity_clean" ([string]::IsNullOrWhiteSpace($idref)) "项目名未改"
Check "T12b_readme_removed" (-not (Test-Path README.md) -and -not (Test-Path README.CN.md)) "README 仍存在"
$rdm = rg -n "readme" pyproject.toml 2>$null
Check "T12c_no_dangling_readme" ([string]::IsNullOrWhiteSpace($rdm)) "readme 字段悬空: $rdm"
$rmdoc = rg -n "git_stage2" docs/context/repo-maintenance.md 2>$null
Check "T13_docs_updated" (-not [string]::IsNullOrWhiteSpace($rmdoc)) "repo-maintenance.md 未更正"

# T14/T15 提交
Check "T14_clean_tree" ([string]::IsNullOrWhiteSpace((git status --porcelain))) "工作区有残留"
$log = git log --oneline -6
Check "T15_commits_landed" ($log.Count -eq 6) "提交数 $($log.Count)"

# T17 许可证
Check "T17_license_intact" ((Test-Path LICENSE) -and (Test-Path LICENSE-Live2D.md)) "LICENSE 被误删！"

Write-Host "`n===== 结果 =====" -ForegroundColor Cyan
if ($fail -eq 0) { Write-Host "ALL PASS" -ForegroundColor Green; "EXIT:0" }
else { Write-Host "$fail 项失败" -ForegroundColor Red; "EXIT:1" }
```

**T16（启动回归）单独执行，因为它会常驻**：见 2.12 的 PowerShell 块，判定标准是日志含 `Starting server on` 且不含 `ModuleNotFoundError: No module named 'upgrade_codes'`。

### 若改用 pytest（本阶段可选）

```powershell
pytest tests/test_git_stage2.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

---

## 7. 交付物清单

- [ ] `run_server.py` 已剥离 `upgrade_codes`（5 处），无残留引用
- [ ] `upgrade_codes/` 与 `upgrade.py` 已删
- [ ] `docs/assets/` 已建并归档逆向产物（或已记录不可找回）
- [ ] 上游 CI/协作文档已移入 `legacy/`（非删除）
- [ ] `frontend/` 子模块关系已解除，文件完好且已入库
- [ ] `pyproject.toml` 已改 name/description 并删除悬空的 `readme` 字段
- [ ] `README.md` 与 `README.CN.md` 已删，`uv sync --dry-run` 通过
- [ ] `origin` remote 已移除
- [ ] `docs/context/repo-maintenance.md` 红线表已更正
- [ ] 6 条语义化提交已落地，工作区干净
- [ ] **T16 启动回归通过**（无 ModuleNotFoundError）
- [ ] **未执行任何 git push**
- [ ] `LICENSE` 未被动过

---

## 8. 留给下一阶段的疑点（本阶段不处理）

1. **`frontend/` 是否彻底删除**：用户说"日后看需要"。若某天删，需同步改 `server.py:173` 的 catch-all mount 与 `run_server.py` 的 `check_frontend_submodule`（该函数可整体删除），并把 `/m` 极简前端提为默认。
2. **`config_templates/conf.ZH.default.yaml` 的去留**：移除 `sync_user_config` 后它不再被代码引用。可保留作为"配置模板"给用户手工复制，也可移入 `legacy/`。
3. **`conf.yaml` 的版本/备份机制**：原 `sync_user_config` 提供自动备份。移除后若需要备份能力，应在新家（如 GUI 启动器）实现，而非恢复 `upgrade_codes`。
4. **`upgrade_codes` 中的 `from_version/v_1_1_1.py` 升级脚本**：随目录删除，本项目不再跨版本升级。
5. **`.github/` 若日后要在自有平台跑 CI**：`legacy/.github/workflows/ruff.yml` 可改造复用（去掉上游仓库引用即可）。
