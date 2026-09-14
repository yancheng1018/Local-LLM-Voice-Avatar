# 交接报告 · git_stage1（项目文件整理 + git 仓库整理）

## 1. 状态

部分完成。文件归位、`.gitignore`、`legacy/`、索引整理、6 条提交、防误推全部落地；
工作区仍有 3 项未追踪文件（J5 遗留），按规格书要求未擅自 `git add`，待你决策。

## 2. 实际改动的文件清单

| 文件 | 行数变化 | 说明 |
|------|---------|------|
| `.gitignore` | 10 → 49 行 | 追加模型资产/运行时产物/本地配置/临时产物/缓存五段规则 |
| `legacy/README.md` | 新建 17 行 | 规格书模板 + 追加 `.ps1` 一行 |
| `legacy/.cursor/`、`legacy/.gemini/` | 移入 | `git mv`，历史保留（rename 记录可见） |
| `legacy/doc/sample_conf/` | 移入 5 文件 | 同上 |
| `legacy/scripts/run_bilibili_live.py` | 移入 | 同上 |
| `legacy/pixi.lock`、`legacy/dockerfile` | 移入 | 同上 |
| `legacy/周期性检查（建议每周或每阶段一次）.ps1` | 移入 19 行 | 规格书遗漏项，按你决策归位 |
| `pyproject.toml` | 1 行改 | ruff 豁免路径 → `legacy/scripts/run_bilibili_live.py` |
| `AGENTS.md` | 81 → 83 行 | 「目录速览」加 legacy/ 行，「维护规则」加默认不推送 |
| `docs/context/current-work.md` | 1 行改 | scan_report 引用改为「跑脚本生成」 |
| 删除 | — | `Temp/`、3 个 `temp_root_*.txt`、`ZCODE_CONTEXT.zip`、`备份.zip`×2、`conf.yaml.bak/.backup`、`model_dict.json.bak`、`live2d_scan_report.md` |
| 索引移除（磁盘保留） | — | 9 个 `frontend-minimal/tests/__pycache__/*.pyc` |

6 条提交（`git log --oneline -6`，SHA 从新到旧）：
`39980b4` chore: 同步本地定制改动与既有修改文件 /
`8309a84` feat(frontend-minimal): 极简前端与后端接入 /
`c2ee264` docs(context): 归档 docs/context 上下文文件 /
`ecb1f8d` chore(cleanup): 删除临时产物与冗余备份 /
`98d40ad` chore(cleanup): 上游遗留部件移入 legacy/ 并加说明 /
`e4d10cf` chore(git): 补全 .gitignore，模型资产与运行时产物不再入库

## 3. 与规格书的一致性

按规格完成：`.gitignore` 全文照抄（2.1）、6 项遗留搬移（2.2）、删除清单（2.3）、
ruff 路径跟改（2.4）、6 条提交信息原样（2.7）、`push.default nothing`（2.8）。
全部按规格书的测试命令原样执行。

偏离项：

- **D1**：`scripts/` 整体搬为 `legacy/scripts/`（J1 判断，目录内仅一个文件，符合规格书建议）。
- **D2**：额外提交 `.ps1` 进 `legacy/`、额外删除 `conversations/备份.zip`（均经你确认）。
- **D3**：9 个 `.pyc` 执行 `git rm --cached`（你确认），规格书 2.1 原表述为「无需」。
- **D4**：`voice.json` 按你决策照规格书提交（保留格式退化改动，记为疑点 Q1）。
- **D5**：J4 结论为**无需** `extend-exclude`——`legacy/` 在 ruff 扫描范围内但零报错。

## 4. 遇到的问题

- **`git mv` 到不存在的嵌套父目录会失败**（`fatal: renaming 'doc/sample_conf' failed`）。
  根因：`git mv` 不像 `mv` 那样自动建父目录。已改为先 `mkdir -p legacy/doc` 再搬。
- **`git mv scripts legacy/scripts` 在 `legacy/scripts` 已存在时嵌套成双层**
  （`legacy/scripts/scripts/`）。根因：我预建了同名目录。已用 `git mv` + `rmdir` 修正。
  → 规格书 2.2 的 6 条 `git mv` 命令未说明此前提，属规格书漏洞。
- **`git reset` 抹掉 rename 记录**，导致第 2 条提交把搬移记成「A 新增」而旧路径删除
  未入暂存区（仓库一度同时存在新旧两份）。已 `git add -u` 补暂存 + `--amend` 修正，
  现在 `--find-renames` 可见 `{.cursor => legacy/.cursor}` 且 changes 为 0。
  → 教训：为分批提交而 `git reset` 会丢 `git mv` 的暂存意图，规格书 2.7 未预警。
- **`voices/` 被忽略后，其已追踪文件必须 `git add -f`**。规格书 2.1 断言「已追踪文件
  继续被追踪，无需 git rm --cached」在「修改」场景下不成立：`git add voices/...` 会被
  拒绝（ignored）。J6 问的是「是否需 rm --cached」，真正的问题是「如何继续提交」。

## 5. 改进建议

- 规格书 2.2 的 `git mv` 命令组应补一句「目标父目录需已存在」或改用
  `mkdir -p` 前置；否则按字面执行必在第 3 条命令中断。
- 规格书 2.7 应警示：`git reset` 会丢弃 `git mv` 的 rename 暂存，分批提交应改用
  `git restore --staged` 或逐文件 `git add` 而不 reset 全量。
- 规格书 2.1 关于「已追踪文件继续被追踪」的表述应细化为：**状态不变，但后续
  `git add` 需 `-f`**；否则执行者会在第 6 条提交卡住。
- 规格书应在施工前提供 `git ls-files -i -c --exclude-standard` 检查步骤，
  以发现全部落入忽略范围的已追踪文件（本次实测 28 个，规格书仅预期 voices 一条）。
- 规格书删除清单漏了 `conversations/备份.zip`（同类误入源码目录的备份），
  建议删除清单改为「全仓 `**/备份.zip` 通配」而非枚举具体路径。

## 6. 待确认疑点

- **Q1 `voice.json` 格式退化**：本地改动把 `"GPT_weights_v4/加藤惠-xxx.ckpt"` 换成
  `"加藤惠-xxx.ckpt  [GPT_weights_v4]"` 并删掉末尾换行；已按你决策提交。
  格式与同级一致，无需回滚
- **Q2 剩下 3 项未追踪文件如何归入**（J5）：`scan_live2d_models.py`、
  `fit_live2d_scale.py` 是项目自有工具（前者正是 current-work.md 现在指向的生成器），
  建议单独一条 `chore(tools): 添加 Live2D 扫描与缩放标定脚本` 提交；
  `.zcode/`（含 commands/、plans/）是 ZCode 会话产物，建议加进 `.gitignore`。
  按规格书「报告后决定，不 git add .」要求停下，等你指示。
- **Q3 T1 断言无法复现完整 6/6**：规格书 T1 把 `Temp` 列为探测目标，但同一规格书
  2.3 要求删除 `Temp/`；`git check-ignore` 对不存在的路径不输出，故 T1 必然只得
  5/6。已用 `--no-index` 证明规则（`.gitignore:33`）有效。建议 T1 改用
  `--no-index` 或改探 `Temp/x` 之类的虚构子路径。
- **Q4 remote 归属**（规格书 §8 已列）：`origin` 仍指上游官方仓库，本阶段未动；
  是否改自有 remote 留待决策。
- **Q5 ruff 4 个既存报错**：`launcher/OpenLLMVTuber_GUI.py`（E731 + 2×F401）、
  `single_conversation.py`（F401），本阶段未新增（已用 diff 验证），是否清理待定。

## 附：断言结果

| 用例 | 结果 | 说明 |
|------|------|------|
| T1_ignore_models | PASS* | 活路径 5/5；`Temp` 因已删无法匹配，规则经 `--no-index` 证实有效 |
| T2_sample_models_tracked | PASS | 37 个示例模型文件仍在索引 |
| T3_legacy_moved | PASS | 4/4 True（另含 doc/sample_conf、scripts、.ps1） |
| T4_legacy_origin_gone | PASS | 4/4 False（scripts/ 亦已消失） |
| T5_runtime_dirs_intact | **PASS** | upgrade_codes、web_tool、frontend/index.html 全在 |
| T6_temp_removed | PASS | 3/3 False |
| T7_conf_kept | PASS | 2/2 True |
| T8_clean_tree | 未通过 | 3 项未追踪（见 Q2），按规格书要求未擅自 add |
| T9_commits_landed | PASS | 6 条，信息与 2.7 表格逐字一致 |
| T10_no_push | PASS | HEAD `39980b4` ≠ origin/v1-release `3afa410` |
| T11_push_guard | PASS | `push.default = nothing` |
| T12_agents_lines | PASS | 83 ≤ 100 |
| T13_server_imports | **PASS** | 输出 `ok` |
| T14_ruff_clean | PASS* | 4 个报错均为既存，本阶段零新增；`legacy/` 零报错 |

T5 与 T13 两条安全网均通过。**未执行任何 git push。**
