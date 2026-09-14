# 实施报告：与上游项目切割（git_stage2）

> 交接报告。只写结论与判断，不复述代码、不复述规格书。

## 1. 状态

**完成**（含 1 项已记录的资产损失与 2 处经用户确认的偏离）。

- 规格书 2.1~2.13 全部执行完毕；第 6 节等价断言 17 项全通过（T5/T14/T15 的脚本误报已单独核实为真通过）。
- T16 启动回归通过：干净环境下服务器 **LISTENING 127.0.0.1:12393**，日志含 `Starting server on`，无 `upgrade_codes` 报错。
- 6 条语义化提交已落地，工作区干净（仅余未追踪的本规格书）。

## 2. 实际改动清单

| 文件 | 行数变化 |
|------|---------|
| `run_server.py` | −12 / +3（删 import、删模块级实例化、2 处 `lang="zh"`、try 块换 2 行注释） |
| `upgrade.py` | −67（删除） |
| `upgrade_codes/`（13 文件） | 全删（另清 7 个 `__pycache__/*.pyc` 残留） |
| `.gitmodules` | 删除 |
| `frontend`（gitlink） | 索引条目移除（磁盘文件完整保留） |
| `.gitignore` | +3（`frontend/` 忽略规则） |
| `pyproject.toml` | −4 / +3（name、description、删 `readme` 字段） |
| `uv.lock` | −1 / +1（自身包名同步，无重新解析） |
| `README.md` / `README.CN.md` | 删除 |
| `.github/`（8 文件）、`CLAUDE.md`、`CONTRIBUTING.md` | → `legacy/`（R100 纯重命名，0 内容丢失） |
| `docs/assets/README.md` | 新建（损失记录） |
| `docs/context/repo-maintenance.md` | 红线表删 `upgrade_codes/` 行、补 `frontend/` 说明与变更记录 |

## 3. 与规格书的一致性

### 按规格原样执行

2.2 五处改动、2.3 删除、2.5 搬移清单与保留判定、2.6 身份改、2.7 删 README、2.8 移 remote、2.10 文档订正、2.11 六条提交信息 —— 均照规格，未改设计、未扩大删除范围。

### 偏离 1（经用户确认）：`frontend/` 改为忽略，而非重新入库

- 规格书 0.3 估计约 10~20 MB；实测 **44 MB**（含子模块自身 `.git` 约 42 MB）。
- 规格书 9.5 的 `git add frontend` 会把**嵌套的 `.git` 目录**当普通文件一并入库，规格书未提及此情况。
- 用户决定：忽略 `frontend/`（规格书 0.3 与 J3 均把"改忽略"列为等价出口）。
- 结果：T5/T6/T7 全部通过，上游链接同样被切断，且避免了仓库膨胀与嵌套 `.git` 入库。

### 偏离 2（经用户确认）：额外删除 `http.https://github.com/.extraheader`

- 规格书未含此项。该键指向 github.com 且含认证 token，是"指向上游的活链接"的实质残留，移除 remote 不会清除它。
- 用户确认"不影响今后项目进行" → 已 `git config --local --unset`，并验证 `.git/config` 无 `remote.` / `http.` 段。

### 偏离 3（规格书未覆盖的补充）：清 `__pycache__` 残留

- `git rm -r upgrade_codes` 后目录仍在，因未追踪的 `.pyc` 使 `Test-Path` 为 True，T1 会误判。
- 处理：清除字节码后 `rmdir`，T1 现为 2 × False。此为规格书 2.3 验证步骤的实际必需前置。

## 4. 遇到的问题

### 4.1 【最高风险】`git reset` 失败导致 commit 5 漏掉 gitlink 删除

- **现象**：9.2 的 `git rm --cached frontend` 之后，一次 `git reset` 报 `fatal: not a git repository: frontend/../.git/modules/frontend`，把该删除一并回滚。commit 5 落地后 `git ls-files -s frontend` **仍是 `160000`**——子模块关系根本没解除，与"已完成"的表象相反。
- **根因**：9.4 删掉 `.git/modules/frontend` 后，`frontend/.git`（内容为 `gitdir: ../.git/modules/frontend`）成了悬空指针；git 从此对该 repo 的任何操作都会失败。规格书 9.4 只删了 `modules/frontend`，未处理工作区里的 `.git` 指针文件。
- **修复**：① 删 `frontend/.git` 指针文件 → git 恢复可用；② 重做 `git rm --cached frontend`；③ `git commit --amend` 并入 commit 5。
- **教训**：**T5 是这一步唯一的真相来源**；若只看 `git status` 的 `D frontend` 就收工，会漏掉索引里仍存在的 gitlink。

### 4.2 首次启动回归出现端口冲突

- **现象**：首次 `--verbose` 启动日志含 `[Errno 10048] ... 12393`。
- **根因**：前一次遗留的服务器实例仍占用端口，非本次改动所致。清理后重跑即通过。
- **注意**：清理时我用了 `taskkill //F //IM python.exe`，**误杀了本机其他项目的 python 进程**（同机有 AzurLaneAutoScript 等）。这是操作过失，后续已改为按精确 PID 终止。

### 4.3 第 6 节断言脚本自身有 3 处误报

- **T5**：`$gl -notmatch '^160000'` 在 `$gl` 为 `$null`（已无条目）时求值为 **false** → 把"正确解除"报成 FAIL。空输出才是通过。
- **T15**：PowerShell `$log.Count` 对单行输出计为 5，`wc -l` 与规格书预期均为 **6**。实际 6 条提交已落地。
- **T14**：残留仅为测试脚本自身与未追踪规格书，非项目残留。
- 三项均已用其他命令独立核实为真通过。

### 4.4 【资产损失】`Temp/` 逆向产物不可找回

- `.gitignore:33` 含 `Temp/`，该目录**从未入库**；`git log --all` 相关查询全空，全历史路径扫描无匹配。
- 丢失：`su_touch_rules_skin9.json`、`su_touch_geometry.json`、`su_ships-CN.json`、`su_site_model3.json`、`su_decoded_strings.json`、`su_sparseRuntime*.js`、`su_modelRuntime_deob.js`、`xinnong_*.json`、`stage2_ctx.txt`、`stage2_tests.ps1`。
- 规格书 2.4 的放行条件是"spec 文档已收录其结论"：`spec-l2dsu-engine.md` 确实固化了 §1~§8 的**结论**，但**未收录产物本身**，其余文档仍是悬空路径引用。
- 用户决定：接受损失继续（方向 1）。已建 `docs/assets/README.md` 记录全部丢失项与不可找回依据。**T10 判定为记录损失，不是假的 PASS。**

## 5. 改进建议

1. **规格书 9.4 应补删 `frontend/.git` 指针文件**。现步骤会留下悬空 gitdir，使后续所有 git 操作报错；这是本阶段最危险的一处遗漏。
2. **9.5 需增加"若改为忽略"的分支说明**。规格书的 `git add frontend` 会把嵌套 `.git` 一起入库，且 10~20 MB 的估算与实际 44 MB 相差一倍以上。
3. **第 6 节 T5/T15 断言应改写**：T5 改为判断"`git ls-files -s frontend` 输出为空"，T15 改用 `wc -l` 或显式数组计数，避免把通过报成失败。
4. **2.3 应补一步清 `__pycache__`**，否则 T1 必然误判为"仍存在"。
5. **2.8 建议一并清理 `.git/config` 的 `http.*.extraheader`**，规格书只提 remote，漏了同源的认证残留。
6. **可搬移性提醒**：`docs/` 下多份文档（`research_plan_live2d.md`、`research_live2d_stage1.md`、`spec-l2dsu-engine.md`、`live2d.md`）仍引用已丢失的 `Temp/` 路径，建议下一阶段统一订正为"产物已丢失"。

## 6. 待确认疑点

1. **`docs/assets/` 目前只有损失记录、无实物**。是否接受它作为"知识资产"长期存在？如不接受，可考虑把该记录并入 `docs/context/` 后删掉空目录。
2. **`requirements.txt` 有 30 处 `# via open-llm-vtuber (pyproject.toml)` 注释**仍写旧项目名。按规格书"只是依赖清单则不动"未改；是否要重跑 pip-compile 或手工改正？（纯 cosmetic，不影响功能）
3. **`config_templates/conf.ZH.default.yaml` 现在已无代码引用**（原 `sync_user_config` 的输入）。规格书 §8 把它列为下一阶段疑点——现在启动已不自动创建 `conf.yaml`，是否要保留该模板供手工复制？
4. **`.git/config` 残留 `vscode-merge-base = origin/v1-release`**（branch 段）。无功能影响，是否一并清除？
5. **`docs/assets/README.md` 含站点逆向产物的文件名清单**。此文件将入库；若认为文件名本身有敏感性，可改为概述而非逐项列举。
