# 规格书：项目文件整理 + git 仓库整理（git_stage1）

> 目标读者：弱模型执行者。本文件是唯一施工图纸，不要自行发挥、不要扩大删除范围。
> 阶段：git_stage1。本阶段**只做文件归位与 git 索引整理**，不改任何业务逻辑。

---

## 0. 背景与硬性约束（先读完再动手）

### 0.1 本项目的三个"看似垃圾、实为运行时依赖"的目录 —— 绝对不许移动/删除

经 `rg` 全仓检索确认，以下目录被代码在**启动时直接 import 或 mount**，移走会导致服务器无法启动：

| 路径 | 证据 | 结论 |
|------|------|------|
| `upgrade_codes/` | `run_server.py:11` `from upgrade_codes.upgrade_manager import UpgradeManager`；`run_server.py:24` 模块级实例化 | **保留原位** |
| `web_tool/` | `src/open_llm_vtuber/server.py:145` `CORSStaticFiles(directory="web_tool", html=True)` | **保留原位** |
| `models/` | `run_server.py:21-22` 把 `models/` 设为 `HF_HOME`；`conf.yaml:263-264` 指向 `./models/sherpa-onnx-.../model.int8.onnx` | **保留原位**（加 gitignore） |
| `Spine-models/` | `src/open_llm_vtuber/server.py` 中 `if os.path.exists("Spine-models")` 后 mount 为 `/Spine-models` | **保留原位**（加 gitignore） |
| `frontend/` | Git 子模块，`server.py:173` 作为 catch-all mount；`run_server.py:55-112` 有自动初始化逻辑 | **保留原位，不许动** |

> 违反此表 = 服务器起不来。这是本阶段最大的坑。

### 0.2 真正可以移走的"上游遗留"（已逐个确认无运行时引用）

仅以下 6 项确认无代码引用，可移入 `legacy/`：

| 原路径 | 性质 | 验证方式 |
|--------|------|----------|
| `.cursor/` | Cursor 编辑器规则，本机用 ZCode | 无引用 |
| `.gemini/` | Gemini 编辑器规则，本机用 ZCode | 无引用 |
| `doc/sample_conf/` | 上游自己标注 deprecated（`doc/README.md:4`） | 无引用 |
| `scripts/run_bilibili_live.py` | B 站直播脚本，本项目不用 | 仅 `pyproject.toml:66` 有一条 ruff 豁免规则（见 2.4） |
| `pixi.lock` | pixi 包管理器锁文件，本项目用 uv | 无引用（`pyproject.toml` 的 pixi 段保留不动） |
| `dockerfile` | 本项目在 Windows 本地跑，不用容器 | 无引用 |

**注意 `upgrade.py` 和 `upgrade_codes/` 不在此列** —— `upgrade.py` 是升级入口脚本，`upgrade_codes/` 是运行时依赖，两者都保留原位。

### 0.3 用户已确认的三项决策

1. **模型资产**：全部写入 `.gitignore` 保留本地磁盘，**不删文件**。
2. **上游遗留**：移入 `legacy/` 目录保留（非删除）。
3. **git 历史**：拆成多条语义化 commit，**只提交到本地，不 push**；并为后续设定「默认不推送互联网」的策略。

### 0.4 通用安全规则

- 任何删除/移动前，先 `git status --porcelain` 记下当前 119 项状态，施工后用同一命令对比。
- 移动文件一律用 `git mv`（保留历史）；未被追踪的文件用普通 `Move-Item`。
- 本阶段**不执行** `git push`、不执行 `git rm --cached` 以外的索引改写。
- 路径含中文（`启动器.bat`、`voices/加藤惠/`），PowerShell 命令一律加引号。

---

## 1. 需要修改或新建的文件路径

| 类型 | 路径 | 说明 |
|------|------|------|
| 修改 | `.gitignore` | 追加模型资产/临时产物规则（当前仅 10 行） |
| 新建 | `legacy/README.md` | 说明 legacy/ 的用途与来源 |
| 移动 | `.cursor/` → `legacy/.cursor/` | 目录整体搬移 |
| 移动 | `.gemini/` → `legacy/.gemini/` | 目录整体搬移 |
| 移动 | `doc/sample_conf/` → `legacy/doc/sample_conf/` | 目录整体搬移 |
| 移动 | `scripts/run_bilibili_live.py` → `legacy/scripts/run_bilibili_live.py` | 文件搬移 |
| 移动 | `pixi.lock` → `legacy/pixi.lock` | 文件搬移 |
| 移动 | `dockerfile` → `legacy/dockerfile` | 文件搬移 |
| 修改 | `pyproject.toml` | 第 66 行 ruff 豁免路径跟改或直接删该行（见 2.4） |
| 修改 | `AGENTS.md` | 目录速览补 `legacy/`，维护规则补「默认不推送」（见 2.6） |
| 删除 | `Temp/` 整个目录 | 临时逆向产物，已确认无引用（见 2.5） |
| 删除 | 根目录 3 个 `temp_root_*.txt` | 同上 |
| 删除 | `ZCODE_CONTEXT.zip` | 旧上下文打包，已被 `docs/context/` 取代 |
| 删除 | `src/open_llm_vtuber/agent/stateless_llm/备份.zip` | 误入源码目录的备份 |
| 删除 | `conf.yaml.bak`、`conf.yaml.backup` | 保留 `conf.yaml` 本身，删两个冗余备份 |
| 删除 | `model_dict.json.bak` | 保留 `model_dict.json` 本身 |
| 删除 | `live2d_scan_report.md` | 可重新生成的扫描产物（`scan_live2d_models.py` 生成） |

> 说明：`logs/`、`.pytest_cache/`、`.ruff_cache/`、`.venv/`、`.venv-gui/`、`__pycache__/`、`chat_history/` **已在 git 忽略范围内或本就不进索引**，本阶段**不删磁盘文件**，只在 2.1 补进 `.gitignore` 声明式覆盖，保持仓库自解释。

---

## 2. 核心逻辑分步描述

### 2.1 第一步：补全 `.gitignore`

**现状**（`.gitignore` 全文 10 行）：
```
# frontend-minimal 构建产物
frontend-minimal/dist/
frontend-minimal/tests/tsout/
frontend-minimal/node_modules/

# 通用产物
*.tsbuildinfo
```

**目标内容**（在文件末尾追加，保留原有段落不动）：

```gitignore
# ---------- 模型资产（体积大，保留本地不入库） ----------
# live2d-models/ 仅入库上游示例模型 mao_pro / shizuku
live2d-models/*
!live2d-models/mao_pro/
!live2d-models/shizuku/
models/
Spine-models/
voices/
avatars/
backgrounds/

# ---------- 运行时产物 ----------
logs/
chat_history/
cache/
*.log

# ---------- 本地配置与备份 ----------
conf.yaml
conf.yaml.bak
conf.yaml.backup
model_dict.json.bak

# ---------- 逆向/扫描临时产物 ----------
Temp/
temp_root_*.txt
live2d_scan_report.md

# ---------- Python 缓存与虚拟环境 ----------
__pycache__/
*.py[cod]
.venv/
.venv-gui/
.pytest_cache/
.ruff_cache/
```

**关键判断点（留给弱模型确认，不要擅自改）**：
- `conf.yaml` 加入忽略后，需要一个入库的模板。检查 `config_templates/conf.ZH.default.yaml` 是否存在——存在则不做任何事；**不存在则停下来报告**，不要自己造模板。
- `avatars/`、`backgrounds/` 是上游 tracked 文件（`git ls-files` 有它们）。把它们加进 `.gitignore` 后 git 不会自动 untrack，**已追踪文件继续被追踪**，无需 `git rm --cached`。这一点是设计如此，不是 bug。
- 若 `git status --porcelain` 施工后仍显示 `voices/加藤惠/voice.json` 有改动（该文件已被追踪），则对该文件执行 `git rm --cached` 并记录，见 2.7。

**验证命令**（工具可完成）：
```powershell
git check-ignore -v models live2d-models/aerbien_3 Spine-models Temp logs
```
期望：6 项全部有输出（命中规则）。若某项无输出，说明规则写错，回退重写。

### 2.2 第二步：建立 `legacy/` 并搬入遗留

**新建** `legacy/README.md`，内容固定为：

```markdown
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

> ⚠️ 不要放入 `upgrade_codes/`、`web_tool/`、`models/`、`Spine-models/`：
> 它们是运行时依赖，移走会导致服务器无法启动。
```

**搬移命令**（工具可完成，按顺序执行）：
```powershell
git mv .cursor legacy/.cursor
git mv .gemini legacy/.gemini
git mv doc/sample_conf legacy/doc/sample_conf
git mv scripts/run_bilibili_live.py legacy/scripts/run_bilibili_live.py
git mv pixi.lock legacy/pixi.lock
git mv dockerfile legacy/dockerfile
```

**判断点（需要判断）**：搬完 `scripts/` 后该目录是否已空？
- 若 `scripts/` 下已无其他文件 → `git mv scripts legacy/scripts` 更干净（先把目标改成 `legacy/scripts/`）。
- 若还有其他文件 → `git mv` 单个文件即可，保留 `scripts/`。
- 执行前先 `ls scripts/` 看清楚，这是一次判断，不要猜。

### 2.3 第三步：删除确认为废的文件

**只删本节列出的条目，不要扩展。**

```powershell
Remove-Item -Recurse -Force "Temp"
Remove-Item -Force "temp_root_01_overview.txt","temp_root_02_commands.txt","temp_root_03_structure.txt"
Remove-Item -Force "ZCODE_CONTEXT.zip"
Remove-Item -Force "src/open_llm_vtuber/agent/stateless_llm/备份.zip"
Remove-Item -Force "conf.yaml.bak","conf.yaml.backup"
Remove-Item -Force "model_dict.json.bak"
Remove-Item -Force "live2d_scan_report.md"
```

**删除前必须确认的两条**（需要判断，逐条执行）：
1. `Temp/` 里的 `su_*.json`、`*_deob.js` 是 l2d.su 逆向产物。若 `docs/context/spec-l2dsu-engine.md` 与 `spec-l2d-touch-engine.md` 已包含其结论，则可删。
   → 确认方式：`rg -c "touch_rules|ship_id|emotionMap" docs/context/spec-l2dsu-engine.md docs/context/spec-l2d-touch-engine.md`，两个文件都有可观命中数即可删；若某文件为空或不存在，**停下来报告**。
2. `live2d_scan_report.md` 由 `scan_live2d_models.py` 重新生成，可删。但 `docs/context/current-work.md` 里引用了它（"见 live2d_scan_report.md"）。
   → 先删文件，再把 `current-work.md` 里的引用改写为「跑 `scan_live2d_models.py` 生成 `live2d_scan_report.md`」。

### 2.4 第四步：修 `pyproject.toml` 的悬空引用

搬走 `scripts/run_bilibili_live.py` 后，`pyproject.toml:65-66` 的豁免规则指向不存在路径：
```toml
# Ignore E402 (module level import not at top of file) for the run_bilibili_live.py script
per-file-ignores = { "scripts/run_bilibili_live.py" = ["E402"] }
```

**改法**：把路径改为 `legacy/scripts/run_bilibili_live.py`，并同步改注释里的路径。
**判断点**：若 `ruff check .` 对 `legacy/` 也生效并报错，则在 `pyproject.toml` 的 ruff 配置里加 `extend-exclude = ["legacy"]`。先跑一次 `ruff check .` 看结果再决定，这是判断项。

### 2.5 第五步：处理 git 索引

**执行顺序固定，不可调换。**

```powershell
# 5.1 查看是否有被追踪的文件落进了新忽略范围
git ls-files --cached | Select-String -Pattern "^logs/|^chat_history/|^models/|^Spine-models/|^Temp/"
```
期望输出为空。若有输出，把命中的路径记下来，逐条 `git rm --cached <path>`。

**判断点（重要）**：以下 8 个已被追踪且有本地改动，**保留追踪**，本阶段只是把它们纳入本次提交：
`launcher/OpenLLMVTuber_GUI.py`、`src/open_llm_vtuber/server.py`、`src/open_llm_vtuber/agent/agents/basic_memory_agent.py`、`src/open_llm_vtuber/agent/agents/letta_agent.py`、`src/open_llm_vtuber/agent/transformers.py`、`prompts/utils/live2d_expression_prompt.txt`、`model_dict.json`、`live2d-models/mao_pro/runtime/mao_pro.model3.json`、`voices/加藤惠/voice.json`。
**不要** `git checkout` 丢弃这些改动——它们是本项目实际工作成果。

另外 `ZCODE_CONTEXT.md` 显示为 `D`（已删除）——这是预期结果，本次提交里体现为删除即可。

### 2.6 第六步：更新 `AGENTS.md`

两处小改，**只改这两处**：

1. 「目录速览」代码块内，在 `config_templates/` 行后加入一行：
   ```
   legacy/                            上游遗留部件（本项目不用，详见 legacy/README.md）
   ```
2. 「维护规则」小节末尾追加一条：
   ```
   - 默认不推送到互联网：本仓库为本地定制版，除非明确要求，不执行 git push
   ```

改完检查行数：`(Get-Content AGENTS.md).Count`，必须 ≤ 100。若超限，压缩其他行（不要删刚加的两条）。

### 2.7 第七步：分批提交（**不 push**）

**提交前自检**：
```powershell
git status --porcelain | Measure-Object -Line
git diff --stat | Select-Object -Last 5
```
确认没有意外的大文件进入暂存区（尤其 `git add` 后若看到 `models/`、`live2d-models/` 大量条目，立刻 `git reset` 回退检查 `.gitignore`）。

**按以下 6 条提交，一条一个 `git add` + `git commit`，不要合并**：

| # | 提交信息（原样使用） | 暂存内容 |
|---|---------------------|---------|
| 1 | `chore(git): 补全 .gitignore，模型资产与运行时产物不再入库` | `.gitignore` |
| 2 | `chore(cleanup): 上游遗留部件移入 legacy/ 并加说明` | `legacy/` 全部 + `pyproject.toml` 改动 |
| 3 | `chore(cleanup): 删除临时产物与冗余备份` | 2.3 节所有删除 + `ZCODE_CONTEXT.md` 的删除 + `docs/context/current-work.md` 引用改写 |
| 4 | `docs(context): 归档 docs/context 上下文文件` | `docs/context/` 全部未追踪文件 + `launcher/launcher_config.json` |
| 5 | `feat(frontend-minimal): 极简前端与后端接入` | `src/open_llm_vtuber/server.py`、`frontend-minimal/`（若仍有未追踪源文件）、`characters/*.yaml` 新增角色 |
| 6 | `chore: 同步本地定制改动与既有修改文件` | 2.5 节列出的 8 个已追踪改动文件 + `AGENTS.md` |

**第 3 条提交的注意事项**：`git rm` 删除已追踪文件时用 `git rm`（不是 `Remove-Item`）才能进入暂存区。`Temp/` 等未追踪目录用 `Remove-Item` 删掉即可，它们本就不在索引里。

**第 6 条之后**：
```powershell
git log --oneline -8
git status --porcelain
```
`git status` 期望输出为**空**（工作区干净）。若还有残留，逐条判断是漏了归类还是有新产物，**报告后再决定**，不要盲目 `git add .`。

### 2.8 第八步：确认「不上传互联网」策略落地

在本地 git 配置里写入提醒（不改变 remote，只做本地约定）：
```powershell
git config --local push.default nothing
```
此设置让裸 `git push` 直接失败，必须显式指定分支或 remote 才能推送，从机制上防止误推。

改完在结尾报告中说明这一点已生效，并提示用户：remote `origin` 仍指向上游 `https://github.com/Open-LLM-VTuber/Open-LLM-VTuber`，**本阶段保持不动**；是否改 remote 留给下一阶段决定。

---

## 3. 函数签名与关键变量名

本阶段为文件与 git 操作，无新增函数。涉及的既有名字（勿改名）：

- `run_server.py:24` 模块级 `upgrade_manager = UpgradeManager()`
- `run_server.py:55` `def check_frontend_submodule(lang=None)`
- `src/open_llm_vtuber/server.py:145` mount 名 `"web_tool"`、`:167` `"frontend_minimal"`、`:174` `"frontend"`
- `pyproject.toml:66` `per-file-ignores` 字典键 `"scripts/run_bilibili_live.py"`
- 规格书路径约定：`docs/context/temp_spec_git_stage1.md`

---

## 4. 测试用例列表

本阶段无单元测试，用「仓库状态断言」代替。**用例名 / 输入 / 预期输出 / 断言点**如下：

| 用例名 | 输入（命令） | 预期输出 | 断言点 |
|--------|-------------|---------|--------|
| `T1_ignore_models` | `git check-ignore -v models live2d-models/aerbien_3 Spine-models Temp logs` | 6 行命中输出 | 每一项都有输出，无遗漏 |
| `T2_sample_models_tracked` | `git ls-files live2d-models/mao_pro live2d-models/shizuku` | 非空列表 | 示例模型仍在索引中（`!` 反向规则生效） |
| `T3_legacy_moved` | `Test-Path legacy/.cursor, legacy/.gemini, legacy/pixi.lock, legacy/dockerfile` | 4 × True | 全部为 True |
| `T4_legacy_origin_gone` | `Test-Path .cursor, .gemini, pixi.lock, dockerfile` | 4 × False | 全部为 False |
| `T5_runtime_dirs_intact` | `Test-Path upgrade_codes, web_tool, frontend/index.html` | 3 × True | **最关键断言**：运行时依赖未被误移 |
| `T6_temp_removed` | `Test-Path Temp, ZCODE_CONTEXT.zip, conf.yaml.bak` | 3 × False | 全部为 False |
| `T7_conf_kept` | `Test-Path conf.yaml, model_dict.json` | 2 × True | 主配置未被误删 |
| `T8_clean_tree` | `git status --porcelain` | 空输出 | 工作区干净 |
| `T9_commits_landed` | `git log --oneline -6` | 6 条新提交 | 提交信息与 2.7 表格一致 |
| `T10_no_push` | `git rev-parse HEAD; git rev-parse origin/v1-release` | 两个不同 SHA | HEAD 不等于 origin，证明未推送 |
| `T11_push_guard` | `git config --local push.default` | `nothing` | 防误推配置生效 |
| `T12_agents_lines` | `(Get-Content AGENTS.md).Count` | ≤ 100 | 根文件行数上限 |
| `T13_server_imports` | `uv run python -c "import upgrade_codes.upgrade_manager; print('ok')"` | `ok` | import 链未断 |
| `T14_ruff_clean` | `ruff check .` | `All checks passed!`（或仅 legacy/ 内豁免） | 无新增 lint 错误 |

> `T5` 和 `T13` 是本阶段真正的安全网。若这两条任一失败，**立即停下报告**，不要继续后续步骤。

---

## 5. 步骤分类

### 5.1 「工具可完成」——给命令，原样执行

| 步骤 | 命令 |
|------|------|
| 看当前状态 | `git status --porcelain \| Measure-Object -Line` |
| 查引用 | `rg -n "web_tool\|upgrade_codes\|Spine-models" --glob '!.git/**' .` |
| 建 legacy 目录 | `New-Item -ItemType Directory -Force legacy` |
| 搬移（见 2.2） | `git mv <src> <dst>` 共 6 条 |
| 删除（见 2.3） | `Remove-Item` 共 8 条 |
| 验证忽略 | `git check-ignore -v models live2d-models/aerbien_3 Spine-models Temp logs` |
| 检查追踪文件 | `git ls-files --cached \| Select-String -Pattern "^logs/\|^models/"` |
| 提交 | `git add <path>; git commit -m "<msg>"` 共 6 组 |
| 防误推 | `git config --local push.default nothing` |
| 行数检查 | `(Get-Content AGENTS.md).Count` |
| lint | `ruff check .` |

### 5.2 「需要判断」——留给弱模型

| # | 判断项 | 依据 | 不确定时 |
|---|--------|------|---------|
| J1 | `scripts/` 搬空后是否整体搬 | `ls scripts/` 的实际内容 | 有其他文件就只搬单文件 |
| J2 | `Temp/` 的逆向产物能否删 | 2.3 节第 1 条的 `rg -c` 命中数 | **停下报告** |
| J3 | `config_templates/conf.ZH.default.yaml` 是否存在 | `Test-Path` | 不存在则**停下报告** |
| J4 | `ruff check .` 是否对 `legacy/` 报错 | 实际输出 | 报错则加 `extend-exclude` |
| J5 | 施工后残留的未归类文件如何归入 6 条提交 | `git status` 实际内容 | 报告后决定，**不 `git add .`** |
| J6 | `voices/加藤惠/voice.json` 是否需 `git rm --cached` | 它在忽略后是否仍显示为已追踪改动 | 改变动文件则保留追踪 |

---

## 6. 运行测试（弱模型原样执行，不要修改）

> 本阶段无 pytest 用例，以下为等价的 PowerShell 断言脚本。
> 若项目后续引入了 `tests/test_git_stage1.py`，改用文末的 pytest 命令块。

```powershell
$fail = 0
function Check($name, $cond, $detail) {
    if ($cond) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name  -> $detail" -ForegroundColor Red; $script:fail++ }
}

# T1 忽略规则
$ig = git check-ignore models live2d-models/aerbien_3 Spine-models Temp logs
Check "T1_ignore_models" ($ig.Count -eq 6) "命中 $($ig.Count)/6"

# T2 示例模型仍被追踪
$sample = git ls-files live2d-models/mao_pro live2d-models/shizuku
Check "T2_sample_models_tracked" ($sample.Count -gt 0) "索引为空"

# T3/T4 legacy 搬移
Check "T3_legacy_moved" ((Test-Path legacy/.cursor) -and (Test-Path legacy/.gemini) -and (Test-Path legacy/pixi.lock) -and (Test-Path legacy/dockerfile)) "legacy 内容不全"
Check "T4_legacy_origin_gone" (-not (Test-Path .cursor) -and -not (Test-Path .gemini) -and -not (Test-Path pixi.lock) -and -not (Test-Path dockerfile)) "原位置仍有残留"

# T5 运行时依赖完好（最关键）
Check "T5_runtime_dirs_intact" ((Test-Path upgrade_codes) -and (Test-Path web_tool) -and (Test-Path frontend/index.html)) "运行时依赖被误移！"

# T6/T7 删除与保留
Check "T6_temp_removed" (-not (Test-Path Temp) -and -not (Test-Path ZCODE_CONTEXT.zip) -and -not (Test-Path conf.yaml.bak)) "临时文件仍存在"
Check "T7_conf_kept" ((Test-Path conf.yaml) -and (Test-Path model_dict.json)) "主配置被误删！"

# T8 工作区干净
$st = git status --porcelain
Check "T8_clean_tree" ([string]::IsNullOrWhiteSpace($st)) "残留 $($st.Count) 项"

# T9 提交落地
$log = git log --oneline -6
Check "T9_commits_landed" ($log.Count -eq 6) "提交数 $($log.Count)"

# T10/T11 未推送 + 防误推
Check "T10_no_push" ((git rev-parse HEAD) -ne (git rev-parse origin/v1-release)) "HEAD 与 origin 相同，疑似已推送"
Check "T11_push_guard" ((git config --local push.default) -eq "nothing") "push.default 未设置"

# T12 行数
Check "T12_agents_lines" ((Get-Content AGENTS.md).Count -le 100) "AGENTS.md 超 100 行"

# T13 import 链
$imp = uv run python -c "import upgrade_codes.upgrade_manager, upgrade_codes.version_manager; print('ok')" 2>&1
Check "T13_server_imports" ($imp -match "ok") "import 失败: $imp"

# T14 lint
$ruff = ruff check . 2>&1 | Out-String
Check "T14_ruff_clean" ($ruff -notmatch "error") "ruff 报错"

Write-Host "`n===== 结果 =====" -ForegroundColor Cyan
if ($fail -eq 0) { Write-Host "ALL PASS" -ForegroundColor Green; "EXIT:0" }
else { Write-Host "$fail 项失败" -ForegroundColor Red; "EXIT:1" }
```

### 若改用 pytest（本阶段可选）

```powershell
pytest tests/test_git_stage1.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

> 若 `EXIT` 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。

---

## 7. 交付物清单（施工完成后逐项打勾）

- [ ] `.gitignore` 已补全，`git check-ignore` 6 项全中
- [ ] `legacy/` 已建立，含 6 项遗留 + `README.md`
- [ ] 2.3 节 8 项临时/备份文件已删
- [ ] `pyproject.toml` 悬空引用已修
- [ ] `docs/context/current-work.md` 中 `live2d_scan_report.md` 引用已改写
- [ ] `AGENTS.md` 两处已更新，行数 ≤ 100
- [ ] 6 条语义化提交已落地，工作区干净
- [ ] `push.default = nothing` 已生效
- [ ] **未执行任何 git push**
- [ ] T5 / T13 断言通过（运行时依赖与 import 链完好）

---

## 8. 留给下一阶段的疑点（本阶段不处理）

1. **remote 归属**：`origin` 仍指向上游官方仓库。本阶段不动；下一阶段需决定是否改为自有 remote 或移除。
2. **`frontend/` 子模块去留**：本项目已有自研 `frontend-minimal/`，上游 `frontend/` 是否保留为默认前端，需你决定。删除子模块需同步改 `server.py:173` 与 `run_server.py:55-112`。
3. **`voices/` 与 `avatars/`、`backgrounds/` 入库策略**：目前按"体积大"整体忽略。若某几个声音/头像希望入库随仓库分发，需加反向 `!` 规则。
4. **`Temp/` 中 l2d.su 逆向产物的长期归档**：若日后还需复用，应在删除前复制进 `docs/context/` 的素材区，而不是留在根目录。
5. **`upgrade_codes/` 与 `upgrade.py` 是否仍需保留升级能力**：本项目已深度定制，上游升级逻辑可能已不适用；但运行时有 import，移除需改 `run_server.py`，属独立改动。
