# 规格书汇总 · 仓库整理与上游切割（git_stage1~3）

> 本文是 `temp_spec_git_stage1~3.md` 与 `impl_report_git_stage1~3.md` 六份文件的**合并终版**。
> 原文已删除；过程性叙述不复述，只留**结论、契约与踩坑**。事实以代码与 `git log` 为准。
> 施工期：2026-09-14。三个阶段的规格书与实施报告合并于此。

---

## 0. 三阶段总览

| 阶段 | 主题 | 关键提交 |
|------|------|---------|
| git_stage1 | 项目文件归位 + git 索引整理 | `e4d10cf` `.gitignore` → `39980b4` 同步本地定制（6 条） |
| git_stage2 | 与上游项目切割 | 6 条，含 `refactor: 剥离 run_server.py 对 upgrade_codes 的依赖` |
| git_stage3 | 收尾清理（lint / 悬空引用 / 上游残留） | `5008564` `83044b9` `c453e9e` |

**最终状态**：无 remote、`push.default = nothing`、工作区干净、ruff 归零。

---

## 1. 不可搬移目录（红线，移走 = 服务器起不来）

启动时被 import 或 mount，**永远留在原位**：

| 路径 | 依赖点 |
|------|--------|
| `web_tool/` | `server.py` mount 为 `/web_tool` |
| `models/` | `run_server.py:21` 设为 `HF_HOME`；`conf.yaml` 指向其下 sherpa-onnx 模型 |
| `Spine-models/` | `server.py:150` 存在性检查后 mount（有守卫） |
| `frontend/` | `server.py:172` catch-all mount（**无守卫**）+ `run_server.py` 启动检查；已非子模块，被忽略、不在索引、仅保磁盘 |
| `config_templates/` | `run_server.py:138` conf.yaml 缺失守卫读 `config_templates/conf.ZH.default.yaml`（stage3 新增，**推翻了 stage2 报告"已无引用"的误判**） |

> `frontend/` 是唯一没有 `os.path.exists` 守卫的 mount：文件不能删（删了启动直接抛错），
> 却又不该入库（44 MB，含嵌套 `.git`）。日后真要删，**必须先给 `server.py:172` 补守卫**。

---

## 2. 已完成的变更（按类型）

### 2.1 忽略与索引

- `.gitignore` 补全五段：模型资产（`live2d-models/*` + `!mao_pro/!shizuku/`、`models/`、`voices/`、
  `avatars/`、`backgrounds/`）、运行时产物、本地配置与备份、逆向临时产物、Python 缓存；另加 `frontend/`、
  `.zcode/`、`docs/context/temp_spec_*.md`、`docs/context/impl_report_*.md`。
- **`.gitignore` 是声明式的**：已追踪文件即使被规则命中仍保持追踪，无需 `git rm --cached`。
  但**想提交该类文件的修改**会被拒（ignored），须 `git add -f`。
  排查：`git ls-files -i -c --exclude-standard`（实测命中约 20 项，刻意保留追踪）。

### 2.2 上游遗留 → `legacy/`（保留非删除）

`.cursor/`、`.gemini/`、`doc/sample_conf/`、`scripts/run_bilibili_live.py`、`pixi.lock`、`dockerfile`、
`.github/`、`CLAUDE.md`、`CONTRIBUTING.md`、`周期性检查…ps1`。清单见 `legacy/README.md`。

### 2.3 删除的临时/冗余物

`Temp/`、3 个 `temp_root_*.txt`、`ZCODE_CONTEXT.zip`、两处 `备份.zip`、`conf.yaml.bak/.backup`、
`model_dict.json.bak`、`live2d_scan_report.md`（可重生成）、`upgrade.py`、`upgrade_codes/`、
`.gitmodules`、`README.md`、`README.CN.md`。

### 2.4 与上游切割

- `run_server.py` 剥离 `UpgradeManager` 5 处 → 副作用：**启动不再自动创建/备份/合并 `conf.yaml`**，
  该文件必须预先存在（stage3 已补缺失守卫给出复制指引）。
- `pyproject.toml`：`name` → `open-llm-vtuber-zh-local`、`description` 改中文、删悬空 `readme` 字段；
  `uv.lock` 自引用条目同步改（**只改自身条目，不动第三方依赖名**），改完须 `uv sync --dry-run`。
- `git remote remove origin`；`.git/config` 的 `http.<github>.extraheader`（含 token）与
  `branch.v1-release.vscode-merge-base` 均已清除。
- **`LICENSE`、`LICENSE-Live2D.md` 绝对不许动**（MIT 许可，法律义务，与切断上游无关）。

### 2.5 lint 归零（stage3）

`launcher/OpenLLMVTuber_GUI.py`：删未用导入 `QSplitter`/`QSizePolicy`；`short = lambda …` → 嵌套 `def`。
`single_conversation.py`：删未用 `import requests`（第 171 行同名注释保留，非引用）。
`requirements.txt`：23 处 `via open-llm-vtuber` → `via open-llm-vtuber-zh-local`。
> 替换命令在 PS 5.1 下 `Set-Content -Encoding UTF8` **会加 BOM**，须追加剥离步骤。

---

## 3. 施工踩坑（复现已验证）

| 坑 | 现象 | 正解 |
|----|------|------|
| `git mv` 不建父目录 | `fatal: renaming 'doc/sample_conf' failed` | 先 `New-Item -ItemType Directory` 建目标父目录 |
| `git mv` 目标已存在 | 嵌套成 `legacy/scripts/scripts/` | 目标目录不要预建同名 |
| 分批提交用 `git reset` | **丢掉 `git mv` 的 rename 暂存**，仓库同时存在新旧两份 | 改用 `git restore --staged <path>` 逐项撤 |
| 删 `.git/modules/<name>` 单做 | 留悬空 `gitdir`，此后**任何** git 操作都报 `not a git repository`；一次普通 `git reset` 会连带回滚已暂存改动 | 必须成对删除 `<name>/.git` 指针文件 |
| 子模块解除的验收 | 看 `git status` 显示 `D frontend` 以为完成 | **唯一真相是索引**：`git ls-files -s frontend` 输出为空 |
| PowerShell `.Count` | 单行输出计为 5，`-eq 6` 必然误报 | 用 `(… \| Measure-Object).Count` 或改 `-ge 1` |
| `-notmatch '^160000'` 判空 | 空串不匹配任何模式 → 把正确结果报成 FAIL | 判定"为空"而非"不等于" |
| `git check-ignore` 对已删路径 | 不存在的路径无输出，T1 必然 5/6 | 用 `--no-index` 或探虚拟子路径 |
| `Test-Path` 受字节码干扰 | `git rm -r` 后目录仍在（未追踪 `.pyc`） | 清 `__pycache__` 后再验 |

---

## 4. 归档测试断言（合并后去重）

| 用例名 | 命令 | 预期 |
|--------|------|------|
| `ignore_rules_hit` | `git check-ignore -v models live2d-models/aerbien_3 Spine-models logs` | 逐项有命中 |
| `sample_models_tracked` | `git ls-files live2d-models/mao_pro live2d-models/shizuku` | 非空 |
| `runtime_dirs_intact` | `Test-Path web_tool, models, Spine-models, frontend/index.html` | 全 True |
| `frontend_untracked` | `git ls-files -s frontend` | 空输出 |
| `upgrade_removed` | `Test-Path upgrade_codes, upgrade.py, .gitmodules` | 全 False |
| `no_upgrade_refs` | `rg -n "upgrade_codes\|upgrade_manager\|UpgradeManager" run_server.py` | 无输出 |
| `conf_required` | `Test-Path conf.yaml` | True |
| `template_intact` | `rg -n "config_templates/conf.ZH.default.yaml" run_server.py` | 1 行 |
| `remote_gone` | `git remote -v` | 空 |
| `push_guard` | `git config --local push.default` | `nothing` |
| `identity_clean` | `rg -n '^name = "open-llm-vtuber"' pyproject.toml` | 无输出 |
| `license_intact` | `Test-Path LICENSE, LICENSE-Live2D.md` | 全 True |
| `ruff_clean` | `uv run ruff check .` | `All checks passed!` |
| `req_renamed` | `rg -c "via open-llm-vtuber-zh-local" requirements.txt` | `23` |
| `no_dangling_temp` | 见 §5 复核命令 | 无"会扑空"的裸引用 |
| `server_boots` | 启动 20 秒看日志 | 含 `Starting server on` 且无 `ModuleNotFoundError` |

> **安全网**：`runtime_dirs_intact`、`frontend_untracked`、`license_intact`、`server_boots`
> 任一失败**立即停下报告**。

`clean_tree` 类断言有天然盲区：规格书与实施报告本身常未追踪，判"工作区为空"必然误报。
→ 应改为排除已知未追踪文件，或把它们纳入 `.gitignore`（stage3 已采纳后者）。

---

## 5. 已丢失资产与悬空引用订正

**`Temp/` 逆向产物不可找回**：`.gitignore` 含 `Temp/`，该目录**从未入库**，`git log --all` 全空。
丢失清单（记录见 `docs/assets/README.md`）：`su_touch_rules_skin9.json`、`su_touch_geometry.json`、
`su_ships-CN.json`、`su_site_model3.json`、`su_decoded_strings.json`、`su_sparseRuntime*.js`、
`su_modelRuntime_deob.js`、`xinnong_*.json`、`stage2_ctx.txt`、`stage2_tests.ps1`。

stage3 已把 `live2d.md`、`spec-l2dsu-engine.md`、`research_plan_live2d.md`、`research_live2d_stage1.md`
四份文档的 `Temp/` **路径引用**订正为"已丢失"表述（**技术结论一字未改**）。
`temp_spec_*.md` / `impl_report_*.md` 中的引用保持原样 —— 那是当时的真实状态，不是悬空引用。

复核命令：
```powershell
rg -n "Temp/" docs/context/live2d.md docs/context/spec-l2dsu-engine.md docs/context/research_plan_live2d.md docs/context/research_live2d_stage1.md
```
剩余命中应均在头部声明或表格注的覆盖范围内，不含"会让人扑空"的裸引用。

---

## 6. 关键判断留痕（J1~J6 类）

| 判断 | 结论 |
|------|------|
| 是否跑 `ruff format` | **不跑**，只手工改 3 处（避免改动无关行） |
| `legacy/` 是否需 ruff `extend-exclude` | **不需要**，`legacy/` 零报错 |
| `frontend/` 重新入库还是忽略 | **忽略**（实测 44 MB 且含嵌套 `.git`，规格书 10~20 MB 估算偏低一倍以上） |
| `mcp_servers.json` / `.pre-commit-config.yaml` | **保留原位**（运行时读取、本地可用，非上游专属） |
| `config_templates/` 去留 | **保留**，是运行时依赖（见 §1） |
| `docs/assets/`（仅损失记录无实物） | **保留**，是"证据已丢失"的正式记录 |

---

## 7. 遗留待办（不在本系列范围）

1. **Live2D 模型补齐**：37 个模型 Idle/Talk 组大小写不匹配、40 个 `emotionMap` 为空；用哪个补哪个。
2. **`.gitattributes`**：`git add` 有 "LF will be replaced by CRLF" 警告，仓库无 `.gitattributes`，
   未来某次 checkout 可能批量改写行尾。
3. **`pyproject.toml` 的 pixi 段**（第 50~57 行）：本项目用 uv，pixi 段无用途但保留至今。
4. **`frontend/` 最终去留**：删前须补 `server.py:172` 守卫（见 §1）。
5. **`docs/context/` 历史规格书堆积**：可考虑归入 `docs/context/archive/`，但会牵动 AGENTS.md 索引表。
6. **`uv.lock` 与 `requirements.txt` 的同步**：改项目名后二者需一致，改动须 `uv sync --dry-run` 验证。
