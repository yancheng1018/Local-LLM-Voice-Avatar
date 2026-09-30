## Git 与仓库维护

> 做文件搬移、`.gitignore` 调整、分批提交前读这里；忽略与资产出库策略见 repo-ignore-policy.md。
> 默认不推送互联网（push 需用户明确要求）。

### 可搬移性红线（移走 = 服务器起不来）

以下目录被代码在启动时 import 或 mount，**永远留在原位**：

| 路径 | 依赖点 |
|------|--------|
| `web_tool/` | `server.py` mount 为 `/web_tool` |
| `models/` | `run_server.py:21` 设为 `HF_HOME`；`conf.yaml` 指向其下 sherpa-onnx 模型 |
| `Spine-models/` | `server.py` 存在性检查后 mount 为 `/Spine-models` |


> 变更记录（git_stage2）：`upgrade_codes/` 与 `upgrade.py` 已于本阶段移除，
> 不再需要升级能力。`run_server.py` 中的 `UpgradeManager` 依赖已剥离。
> 副作用：启动不再自动创建/备份/合并 `conf.yaml`，该文件必须预先存在。
> 善后（已收尾）：`run_server.py` 现在会在缺失时打印复制模板的命令并退出，
> 因此**无需**为此在 `AGENTS.md` 增设根级契约 —— 错误信息自身已承载全部指引。

其余上游遗留件已移入 `legacy/`（见 `legacy/README.md`）。

- `.venv` 与 `.venv-gui` 内嵌绝对路径：项目文件夹改名/搬移后必须重建——
  `rm -rf .venv && uv sync`；`rm -rf .venv-gui && uv venv .venv-gui --seed` 再装
  PySide6-Essentials ruamel.yaml psutil（启动器.bat 环境缺失提示已含 `--seed`）

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

- `git mv` **不会**自动创建目标父目录，批量搬移前先确认父目录存在；目录级整移相反——目标已存在
  会嵌套成 B/A，应目标缺席时整移（批 c 实操）。
- 为分批提交而做全量 `git reset` 会**丢掉 `git mv` 的 rename 暂存**，导致旧路径
  删除未入暂存、仓库同时存在新旧两份。改用 `git restore --staged <path>` 逐项撤。
- 删除**已追踪**文件要用 `git rm`（才进暂存区）；未追踪的临时产物用普通删除即可。
- 提交前跑 `git diff --cached --stat`，确认没有 `models/`、`live2d-models/` 大文件混入。
- Git Bash 下 grep 输出反斜杠路径（`docs\context\...`），`grep -v "^docs/context/..."` 这类
  正斜杠前缀过滤**恒不命中**、形同虚设；要按路径排除用 `grep -rn --exclude="<模式>"`。
- grep pattern 以 `/` 开头（如 `/finalize`）会被 Git Bash 的 MSYS 路径转换改写成
  Windows 路径，结果**伪 0**；用 `[/]finalize` 写法或 `MSYS_NO_PATHCONV=1` 规避。
- 普通 `grep -r` 在本环境会静默漏扫（github-p2-release 同日两实测：`-rln` 命中 1/8 文件、
  `-rn` 命中 0/8，find+xargs 实为 8）；全仓递归检索一律 `find -name "*.md" -print0 | xargs -0 grep` 口径
- 活引用排查排除文档自身时用 `rg --glob='!<文件名>'` 或 `grep -rn --exclude=<文件名>`；用路径子串
  做 `grep -v` 会把正文里引用该文件名的**内容引用**一并误伤（distill-b1 审查实证）。
- git log 机读解析须用消息体不可能含的字节作条目分隔（如 format=%x01%H%x00%B）；%H%x00%B 的 \0 只分隔 hash 与消息体、条目间无分隔符，按 \0 切分会错位致白名单失效（github-p2-precheck-a 实踩，tests/test_repo_privacy_guard.py）。
- 删 NamedTuple/dataclass 字段或整个模块时，用 rg "<类名>(" / rg "import <模块>" 审全部调用点——裸位置参数对按删除关键字的 rg 清扫不可见（批 b CharEntry 5 参残留致启动器启动即崩，rg/ast/ruff 三层全漏、人工验收实踩；运行守卫=tests/test_gui_smoke.py 离屏实例化）。
- 删除面的清扫命令路径必须含仓库根入口脚本（run_server.py），删模块后补导入冒烟（uv run python -c "from src.open_llm_vtuber.config_manager import Config"）——批 b 的 run_server.py enable_proxy 与 main.py live_config 两处漏网同源于此。
- git ls-remote 对附注 tag 返回 tag 对象 sha；校验提交指向须加 ^{} 解引用后缀——github-p2-release 实踩（规格断言照抄 ls-remote refs/tags/<t> 得到对象 sha，险误判不一致）

### 相关工具

- `scripts/scan_live2d_models.py`：只读扫描 `live2d-models/`，生成 `live2d_scan_report.md`
  （该报告已忽略，属可重生成产物）。
- `scripts/fit_live2d_scale.py`：按 moc3 画布尺寸自动标定 `model_dict.json` 的 `kScale`
  （自动备份 `.bak`）。
- `scripts/fix_live2d_idle_groups.py` / `scripts/fix_live2d_touch_data.py`：补 Idle/Talk 别名组 /
  从 l2d.su 站点数据回填触摸链（用法见各脚本头注释）。
- `scripts/gpt_sovits/start_gsv_api.py`：GPT-SoVITS API 启动适配器（GUI 与 CLI 共用，
  目标版本 v2pro-20250604，用法见同目录 README）。

### Temp/ 悬空引用订正（git_stage3）

`Temp/` 于 stage1 删除且从未入库，产物不可找回（记录见 `docs/assets/README.md`）。
本阶段已把 `live2d.md`、`spec-l2dsu-engine.md`、`research_plan_live2d.md`、
`research_live2d_stage1.md` 四份文档中对 `Temp/` 的**路径引用**订正为"已丢失"表述。
`docs/context/temp_spec_*.md` 与 `impl_report_*.md` 中的引用**保持原样** —— 它们是历史
规格书与报告，其中的路径是当时的真实状态，不是悬空引用。

本阶段同时清零了全部 ruff 错误（`launcher/OpenLLMVTuber_GUI.py` 的 2 个未使用 Qt 导入
与 1 处 lambda 赋值、`single_conversation.py` 的未使用 `requests` 导入）。

### 整理与切割的完整记录（git_stage1~3）

三阶段的规格书与实施报告已合并为 `docs/context/spec-git-reorganize.md`，原文删除。
该文含：不可搬移目录红线、忽略与索引策略、上游切割清单、**施工踩坑表**（`git mv` 父目录、
`git reset` 丢 rename 暂存、删 `.git/modules/<name>` 留悬空 gitdir、PowerShell `.Count` 误报等）、
归档测试断言与遗留待办。**做仓库级改动前先读它对表。**

### docs/context 文档体系维护

分工与检查点：

| 内容 | 谁写 | 什么时候 |
|------|------|---------|
| 新结论、新契约、踩坑记录 | Agent（/doc-record） | 每次会话结束，由你指示 |
| 当前进展、待处理遗留 | 强模型（/plan-feature、/review-spec） | 阶段开始/收尾 |
| 模块边界调整、索引表增删 | 你 | 归属不对/新建删除文件时 |
| 删除过时内容 | 你 | 定期扫一眼时 |

存量研究文档处置口径（distill 系列，2026-09-29）：大纲/分诊类计划文档随执行完成删除；成品取证
记录保留作证据链（教训：r3 研究文档删除后其裁决证据不可复核）；成品提炼后文首加处置行标注结论去向（distill-b3 起）。

关键提醒：Agent 不会自动更新文档，这是特性。若 Agent 在代码任务后静默更新文档，
任务有 bug 时错误行为会被记成「预期行为」，下个会话就会把错误当规则。
你是检查点：先确认代码正确，再指示记录。

周期性检查（每周或每阶段收尾跑一次）：

```bash
echo "===== 行数检查 ====="
for f in AGENTS.md docs/context/*.md; do
  n=$(wc -l < "$f"); limit=200
  [ "$f" = "AGENTS.md" ] && limit=100
  if [ "$n" -gt "$limit" ]; then flag=超标; else flag=OK; fi
  printf "%-42s %4d 行  %s\n" "$f" "$n" "$flag"
done
echo "===== 索引表一致性 ====="
grep -o 'docs/context/[A-Za-z0-9._-]*\.md' AGENTS.md | tr -d '\r' | sort -u > /tmp/idx.txt
ls docs/context/*.md | tr -d '\r' | sort -u > /tmp/act.txt
echo "索引提到但不存在：";  comm -23 /tmp/idx.txt /tmp/act.txt
echo "存在但索引未提：";      comm -13 /tmp/idx.txt /tmp/act.txt
```

> 「存在但索引未提」列出 temp_spec_* / impl_report_* / finalize_exec_* / distill_draft_* / 本规格
> 与存量归档（research_* / verify_* / manual_* / l2dsu抓取模型说明.md）属正常（临时产物与研究
> 归档，不入索引）。其余即为索引欠账，须补。
> 行数检查中 docs/context 的研究/规格归档类（research_*、manual_*、verify_*、l2dsu抓取模型说明.md、spec-*）超 200 行属容忍口径，不计欠账（先例 r4=948、l2dsu=601）。

（并入自原 docs/context/MAINTENANCE.md，doc-lifecycle stage1 合并；
其「文件体系总览」表因与 AGENTS.md 索引双头维护且已过时而废止，
「日常流程」节因已被 /doc-record 等命令取代而不迁移。）
