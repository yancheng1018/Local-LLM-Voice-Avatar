# github-p3-public-g · 切 public + S9 公开态三项 curl 验证（规格书）

> roadmap v1.0.1 #5（阶段路线图 7/8）。零代码实施型阶段（先例：github-p3-public-d）。
> 门禁裁决（2026-10-09 用户，本阶段授权依据）：
> ① push 授权=本次规划问答即授权，弱模型按本规格执行全部 push；
> ② 分支终态=C 回归 main 单主线——push v1-release+main 双支、本地切回 main 今后在
> main 工作、v1-release 冻结于 eb83117 封存退役（B 切默认/A 双推维持两案均弃）。
> 规划期实证（2026-10-09）：origin/v1-release=1000463（本地领先 12）、origin/main=
> acf9ad1（恰为 tag v1.0.0 解引用点，本地领先 18）、HEAD=eb83117、两支均 fast-forward
> （merge-base=各自远程顶端，零分叉）；直连 github.com 约 21s 超时间歇阻断、
> 127.0.0.1:7890 代理可通（匿名 curl 经代理返回 200）。

## 1. 修改/新建文件

| 文件 | 动作 | 时机 |
|------|------|------|
| docs/context/github-p3-public-g.spec.md | 规划期已新建（本文件） | S1 提交 |
| docs/context/current-work.md | 规划期已改（状态行替换+遗留吸收移除）；S1 再改状态行→实施中 | S1 提交 |
| docs/context/roadmap.md | 规划期已改（#5 翻进行中+调整记录）；实施期不再动（终态归 /review-spec） | S1 提交 |
| docs/context/github-p3-public-g.report.md | 新建 | S7 |

硬边界：本阶段零代码改动——src/、tests/、frontend-minimal/、scripts/、launcher/、
conf.yaml、characters/ 一律不动；任何步骤发现「须改代码才能继续」→ 停下升级，不自行扩面。

行数预检（spec-writing.md §5）：current-work.md 114→约 111 行（移除遗留 3 行，状态行
原地替换）；roadmap.md 95→约 99 行（调整记录 +1 条约 3 行、#5 要点改写同量级）；均远
低于 200 上限。README 不动（规划期 grep 实证全文件仅 `git clone <本仓库地址>`，无任何
分支指引）。

## 2. 函数签名/关键变量

N/A（零代码阶段）。关键量=sha 对照表与 HTTP 状态码：

- `BASE_HEAD=eb8311776994d1981b29743a199f180b5b9334ab`（规划基线，v1-release 冻结终值）
- `REMOTE_MAIN_OLD=acf9ad187da6949151f76508f1ac389720808761`（=tag v1.0.0 解引用点）
- `REMOTE_V1R_OLD=10004635d3de5d92998e07ae2534c4ec0b1b768e`
- 期望 HTTP 序列：私有基线 404 → 切公开后 200 / 200 / 200（tag 页且含 v1.0.0）

## 3. 核心步骤

> 下文 `GIT` 占位=按 S0.4 选定的 git 调用口径（直连=`git`，代理=`git -c
> http.proxy=http://127.0.0.1:7890`）；`CURL` 占位=同口径的 curl（代理时加
> `-x http://127.0.0.1:7890`）。选定后在 report 记录所用口径。

### S0 前置对账（工具可完成）

```bash
git status --short      # 期望恰三项：?? docs/context/github-p3-public-g.spec.md
                        #            M docs/context/current-work.md
                        #            M docs/context/roadmap.md
git config user.name    # 期望 yancheng1018
git config user.email   # 期望 55277749+yancheng1018@users.noreply.github.com
git rev-parse HEAD      # 期望 BASE_HEAD
git branch -vv          # 期望仅 * v1-release（本地无 main——S1 依赖此前提）
```

- 身份不符 → 停下报告（AGENTS.md 硬性契约：须用户先设，不由本阶段改配置）。
- HEAD ≠ BASE_HEAD 或工作树出现规格外改动 → 停下（基线漂移，回强模型核对）。

S0.4 网络口径探定（先例 repo-maintenance.md:87，github-p3-public-c 实踩）：

```bash
git ls-remote origin refs/heads/v1-release    # 直连试一次（容忍约 25s 超时）
```

- 成功 → GIT=直连（后续仍可能间歇，单条失败即按失败处置切代理）。
- 失败 → 代理口径：`netstat -ano | grep LISTEN | grep ":7890 "` 确认 7890 监听
  （规划期实证 PID 21700），再 `curl -s -o /dev/null -w "%{http_code}" -x
  http://127.0.0.1:7890 https://github.com --max-time 15` 期望 200。
- 7890 不在 → 依次探 1080/10808/10809/8888/2080（同款 netstat+curl 探测）；全败 →
  停下（等用户开代理）。
- 代理只作一次性参数，禁止改全局 git/curl 配置。curl 匿名性不受代理影响（无凭证，
  代理出口访问 GitHub 仍是未认证请求，适用于公开态验证）。

### S1 切 main + 提交规划产物（工具可完成）

```bash
git checkout -b main    # 从当前 HEAD(=BASE_HEAD) 建 main；绝不带 origin/main 作起点
                        # （远程 main 停旧在 acf9ad1，作起点会丢 18 个提交）
```

- 报「main 已存在」→ 停下报告（规划期实证本地无 main，存在=环境变动）。
- 未提交的规划产物随切换保留（同一 commit 建分支不动工作树）。
- 编辑 docs/context/current-work.md 状态行：`（规划完成，待弱模型实施）` →
  `（实施中）`（替换不续写）。

```bash
git add docs/context/github-p3-public-g.spec.md docs/context/current-work.md docs/context/roadmap.md
git diff --cached --stat   # 期望恰 3 文件；无 models/、live2d-models/ 混入
                           # （repo-maintenance.md:74 施工习惯）
git commit -m "docs(context): github-p3-public-g 规划入库——spec+roadmap #5 进行中+远程停旧遗留吸收（分支终态C/push已授权）"
```

### S2 push 双支（工具可完成；授权=文首裁决①）

```bash
# 2.1 远程现状复核（防规划后远程被动过）
GIT ls-remote origin refs/heads/main refs/heads/v1-release
# 期望：REMOTE_MAIN_OLD refs/heads/main；REMOTE_V1R_OLD refs/heads/v1-release
# 不符 → 停下报告（远程被外部改动，须重新对账；禁止 --force）

# 2.2 fast-forward 断言（两支各自，缺一不可）
git merge-base --is-ancestor acf9ad187da6949151f76508f1ac389720808761 HEAD && echo main-ff-ok
git merge-base --is-ancestor 10004635d3de5d92998e07ae2534c4ec0b1b768e HEAD && echo v1r-ff-ok
# 任一非 ok → 停下（分叉，禁止强推）

# 2.3 push（v1-release 冻结终值=BASE_HEAD；main 前进到 S1 新提交）
GIT push origin v1-release
GIT push -u origin main

# 2.4 复核
GIT ls-remote origin refs/heads/main refs/heads/v1-release
git rev-parse HEAD
# 期望：refs/heads/v1-release == BASE_HEAD；refs/heads/main == rev-parse HEAD
```

- push 网络失败：同一根因重试合计 ≤3 次（直连↔代理切换算同根因内调整）；3 败 →
  停下报告（用户级纪律第 3 条）。

### S3 本地分支终态确认（工具可完成）

```bash
git branch -vv      # 期望：* main 与 origin/main 同步（0 ahead/behind）；
                    #       v1-release 本地=BASE_HEAD（冻结，本阶段不再动）
git status --short  # 期望干净
```

- v1-release 本地分支保留（封存=不动；删除属破坏性动作，日后由用户另行决定）。
- 本阶段后续提交（S7）一律落 main。

### S4 切 public 前置基线 + 人工项（基线=工具可完成；切 public=人工项）

```bash
CURL -s -o /dev/null -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar
```

- 期望 404（匿名访问私有仓库）→ 输出存 report 作私有态证据。
- 已 200 → 用户已提前切公开：跳过人工项直接 S5（report 注明）。
- 5xx/超时 → 按 S0.4 网络口径处置后重试 ≤3 次，仍败停下。
- 人工项见 §7-1；用户告知完成后继续 S5。

### S5 公开态三项 curl 验证（工具可完成）

```bash
CURL -s -o /dev/null -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar
# 期望 200
CURL -s -o /dev/null -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar/releases
# 期望 200
CURL -s -o "$TMPDIR/tag_page.html" -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar/releases/tag/v1.0.0
# 期望 200
grep -c "v1.0.0" "$TMPDIR/tag_page.html"
# 期望 ≥1（TMPDIR 不存在则先 export TMPDIR=/tmp）
```

- 非 200/404（如 429 限流）：等 30s 重试，该条合计 ≤3 次；仍异常 → 停下报告。
- 404：切公开未生效（回问用户 §7-1 第 ③ 步）或 tag 页缺失（升级）；二者都停下，不猜。

### S6 全量回归（工具可完成）

见 §6 命令块原样执行。零代码阶段任何红=阻断（无代码可修，必为环境或意外改动）→
只按 §6 要求汇报，停下。

### S7 report + 收尾簿记（工具可完成）

- 新建 docs/context/github-p3-public-g.report.md，必含：①sha 对照全过程（S2.1/S2.4
  输出与期望值并排）；②push 输出摘录与所用网络口径；③S4 基线 404 与人工项完成时刻；
  ④S5 三项状态码+grep 计数；⑤S6 输出末行与退出码；⑥S3 分支终态快照（branch -vv +
  ls-remote 终值）；⑦判断类决策记录（代理启用、重试次数、跳过人工项与否）。

```bash
git add docs/context/github-p3-public-g.report.md
git commit -m "docs(context): github-p3-public-g 实施簿记——report 入库+push双支/分支终态C/公开态curl证据"
GIT push origin main
```

- 状态行保持「实施中」（翻「审查通过待人工验收」归 /review-spec）；收尾待办块不写
  （/review-spec 专属）。

## 4. 测试用例列表

零代码阶段：不新建、不修改任何测试文件（处置口径同先例 github-p3-public-d）。本阶段
验证面为一次性实施断言，内嵌于 §3 各步：

| # | 用例名 | 输入 | 预期输出 | 断言点 | 载体（文件/步骤） |
|---|--------|------|----------|--------|------------------|
| V1 | 双支 fast-forward 前置 | merge-base --is-ancestor ×2 | main-ff-ok、v1r-ff-ok 均打印 | 防非快进/强推 | S2.2（无测试文件） |
| V2 | push 后 v1-release 远程值 | ls-remote refs/heads/v1-release | ==BASE_HEAD | 冻结终值落地 | S2.4（无测试文件） |
| V3 | push 后 main 远程值 | ls-remote refs/heads/main | ==本地 main HEAD | 推平落地 | S2.4（无测试文件） |
| V4 | 私有基线 | 匿名 curl 首页 | 404 | 私有态在案 | S4（无测试文件） |
| V5 | 公开首页 | 匿名 curl 首页 | 200 | 公开生效 | S5（无测试文件） |
| V6 | 公开 releases | 匿名 curl /releases | 200 | 发布页可访 | S5（无测试文件） |
| V7 | tag 页含版本号 | 匿名 curl /releases/tag/v1.0.0 + grep | 200 且计数 ≥1 | tag 页公开可访 | S5（无测试文件） |
| V8 | 全量回归维持绿 | 全量 pytest | 211 passed（基线=2026-10-09 github-p3-public-f 收尾实跑） | 无意外改动 | S6（沿用全量命令，不新建文件） |

长期回归保障=现有全量测试维持绿（V8），无新增长期用例（零代码阶段，无「新守卫」对象）。

## 5. 步骤分类汇总

- 工具可完成：S0（含 S0.4 探测）、S1、S2、S3、S4 基线 curl、S5、S6、S7——命令与
  期望值均已在 §3 给全。
- 需要判断（弱模型停下报告，不自行决策）：S0.4 网络口径选择结论；S2.1 远程 sha 不符；
  S2.2 非快进；S4 基线 200 的「已提前切公开」判定；S5 非 200/404 重试后仍异常；S6
  任何红；git 身份不符；本地已存在 main；工作树出现规格外改动。

## 6. 运行测试（弱模型原样执行，不要修改）

```bash
cd /c/Coding/Application/Local-LLM-Voice-Avatar
uv run --extra test python -m pytest -q 2>&1 | tail -n 80
echo "pytest_exit=${PIPESTATUS[0]}"
```

退出码非 0 或输出末行不含 `211 passed`：只汇报失败用例名、断言差异、最后 20 行
traceback，然后停下（本阶段零代码，禁止以任何方式修实现或测试凑绿——用户级纪律第 9 条）。

## 7. 人工验收清单（仅 1 项；其余全部已自动化）

### 7-1 切 public（GitHub 账号操作）

- AI 为何做不了：仓库可见性变更需 GitHub 登录会话与账号权限，AI 无凭证（一句话）。
- 已备好的现场：S4 基线 curl 404 证据已取（私有态在案）；操作页
  https://github.com/yancheng1018/Local-LLM-Voice-Avatar/settings
- 编号步骤（一步一动作一观察点）：
  1. 打开上述 Settings 页 → 观察：进入 Repository 设置页；
  2. 滚动至页面底部 Danger Zone → 观察：可见 Change repository visibility 条目；
  3. 点击 Change visibility → Change to public → 观察：弹出确认框；
  4. 按提示输入仓库名确认 → 观察：页面刷新、可见性标识变为 Public；
  5. 回对话告知「已切公开」→ 观察：AI 随即执行 S5 三项 curl。
- 通过/失败判定：S5 首页匿名 curl 得 200=通过；仍 404=未生效，回看第 3/4 步。
- 预计耗时：约 2 分钟。

## 8. 非目标与边界

- 版本收口：本阶段实施+验收后 v1.0.1 目标集 8 条全部终态，`uv version --bump` 是否
  执行归 /review-spec 收尾裁决（roadmap 头部判据），不在本规格。
- 不动 README（无分支指引，实证见 §1）；不删 v1-release 本地/远程分支（封存≠删除）；
- 不做发版自动化（backlog #5）；遗留 [github-p3-public-f]「README Roadmap 补演示
  GIF 一行（待拍板）」不并入本阶段。
