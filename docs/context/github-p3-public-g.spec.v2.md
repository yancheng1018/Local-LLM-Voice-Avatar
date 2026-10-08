# github-p3-public-g · 切 public + S9 公开态三项 curl 验证（规格书 v2）

> roadmap v1.0.1 #5（阶段路线图 7/8）。零代码改动主体+一处文档脱敏（S0.5）的实施型阶段。
> 门禁裁决（2026-10-09 用户，/plan-feature 期）：
> ① push 授权=规划问答即授权，弱模型按本规格执行全部 push；
> ② 分支终态=C 回归 main 单主线——push v1-release+main 双支、本地切回 main 今后在
> main 工作、v1-release 冻结封存（B 切默认/A 双推维持两案均弃）。
> 拷打裁决（2026-10-09 用户，/grill-spec 期，共 3 项）：
> ③ GitHub Release 对象确认建过（p2-release 档案在案），S9 第三项判据维持原样；
> ④ S5 三项 curl 加 30s×3 重试窗口（切公开生效可能秒级延迟）；
> ⑤ 全量基线红（隐私守卫：spec-demo-gif.md:47 私有声音名，f 收尾入库晚于最后一次
> 211 绿实跑）并入本阶段前置 S0.5 修复，不另立阶段（涉事私有声音名在规格内一律以
> 「该私有声音名」指代——规格文本自身同受隐私守卫约束，不入字面量）。
> 取证（2026-10-09 工作流「github-p3-public-g 拷打取证」，18 项核对 17 符合）：
> origin/main=acf9ad1、origin/v1-release=1000463、tag v1.0.0 解引用=acf9ad1（经代理
> ls-remote 实证）；本地 HEAD=eb83117、仅 v1-release 分支、身份 yancheng1018 ✓；
> 7890 代理监听+匿名探 github.com 200 ✓；全量 pytest 实跑 1 failed/210 passed
> exit=1（唯一偏差，处置=⑤ S0.5）；复审员 5 条发现全部吸收进本版（S6 判定措辞、
> TMPDIR→/tmp、404 处置分 curl 归因与引用统一、行数预检实测口径、基线数）。
> 规划期网络实证：直连 github.com 约 21s 超时间歇阻断，127.0.0.1:7890 代理可通。

## 1. 修改/新建文件

| 文件 | 动作 | 时机 |
|------|------|------|
| docs/context/github-p3-public-g.spec.v2.md | 拷打期已新建（本文件，施工唯一权威版） | S1 提交 |
| docs/context/github-p3-public-g.spec.md | v1 存档，随规划产物一并入库（先例：github-p3-public-h 实施 spec v1/v2/v3 全量入库） | S1 提交 |
| docs/context/current-work.md | 规划期已改（状态行/遗留吸收）；S1 再改状态行→实施中 | S1 提交 |
| docs/context/roadmap.md | 规划期已改（#5 翻进行中+调整记录）；实施期不再动（终态归 /review-spec） | S1 提交 |
| docs/context/spec-demo-gif.md | S0.5 脱敏：第 47 行去除三个私有声音名（仅此一行内容改写，不减行） | S0.5 提交 |
| docs/context/github-p3-public-g.report.md | 新建 | S7 |

硬边界：除 spec-demo-gif.md 一行脱敏外零改动——src/、tests/、frontend-minimal/、
scripts/、launcher/、conf.yaml、characters/ 一律不动；尤其不修改守卫测试本身、
不放宽任何断言（用户级纪律 9）。任何步骤发现「须改代码/测试才能继续」→ 停下升级。

行数预检（spec-writing.md §5，实测口径）：current-work.md 工作树 110 行（S1 状态行
原地替换不加行，上限 200 余量充足）；roadmap.md 98 行（实施期不再改）；spec-demo-gif.md
仅一行改写不减行。spec.v2 与 report 属阶段产物（容忍口径，不入 200 上限账）。README
不动（实证全文件仅 `git clone <本仓库地址>`，无任何分支指引）。

## 2. 函数签名/关键变量

N/A（无代码签名）。关键量=sha 对照表、HTTP 状态码与守卫计数：

- `BASE_HEAD=eb8311776994d1981b29743a199f180b5b9334ab`（阶段开工基线，S0 复核）
- `FIX_HEAD`（S0.5 修复提交 sha，实施期 `git rev-parse HEAD` 记录；v1-release 冻结终值）
- `REMOTE_MAIN_OLD=acf9ad187da6949151f76508f1ac389720808761`（=tag v1.0.0 解引用点）
- `REMOTE_V1R_OLD=10004635d3de5d92998e07ae2534c4ec0b1b768e`
- 期望 HTTP 序列：私有基线 404 → 切公开后 200 / 200 / 200（tag 页且含 v1.0.0）
- 守卫单测期望：tests/test_repo_privacy_guard.py 全文件 4 passed（拷打期实跑 1 failed/3 passed）

## 3. 核心步骤

> 下文 `GIT` 占位=按 S0.4 选定的 git 调用口径（直连=`git`，代理=`git -c
> http.proxy=http://127.0.0.1:7890`）；`CURL` 占位=同口径 curl（代理时加
> `-x http://127.0.0.1:7890`）。选定后在 report 记录所用口径。

### S0 前置对账（工具可完成）

```bash
git status --short      # 期望恰四项：
                        #   ?? docs/context/github-p3-public-g.spec.md
                        #   ?? docs/context/github-p3-public-g.spec.v2.md
                        #    M docs/context/current-work.md
                        #    M docs/context/roadmap.md
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
  （拷打期实证仍在监听），再 `curl -s -o /dev/null -w "%{http_code}" -x
  http://127.0.0.1:7890 https://github.com --max-time 15` 期望 200。
- 7890 不在 → 依次探 1080/10808/10809/8888/2080（同款 netstat+curl 探测）；全败 →
  停下（等用户开代理）。
- 代理只作一次性参数，禁止改全局 git/curl 配置。curl 匿名性不受代理影响（无凭证，
  代理出口访问 GitHub 仍是未认证请求，适用于公开态验证）。

### S0.5 隐私守卫红修复（工具可完成；拷打裁决⑤）

依据（供审查）：失败实证=tests/test_repo_privacy_guard.py:98 断言（拷打期全量实跑
1 failed/210 passed）；`git grep` 全仓（除 tests）该私有声音名唯一命中 spec-demo-gif.md:47，
该行入库于 f 收尾提交、晚于 f 阶段最后一次 211 绿实跑。修复必须落在 v1-release
（切 main 之前）：v1-release 冻结分支的 tip 公开后必须干净，两分支共享本修复提交。
历史提交中的残留与 B6 已接受现状同类（2026-10-07 用户裁决，不重写历史）。

```bash
git grep -n "<私有声音名>" -- . ':!tests'
# 期望唯一命中：docs/context/spec-demo-gif.md:47；出现任何其他命中 → 停下报告（本步骤仅覆盖实证面）
```

1. 编辑 docs/context/spec-demo-gif.md 第 47 行：删除该行「voices/ 三卡在位（…）」
   括号内三个私有声音名与分隔顿号（改后该行括号内仅余「激活链=」起头的原文），
   行内其余原文一字不动，不改文件其他行。
2. 复跑守卫单测：

```bash
uv run --extra test python -m pytest tests/test_repo_privacy_guard.py -q
# 期望：4 passed（拷打期 1 failed/3 passed 转绿）；仍红 → 停下报告，不扩大脱敏面
```

3. 提交并记录冻结终值：

```bash
git add docs/context/spec-demo-gif.md
git diff --cached --stat    # 期望恰 1 文件 1 行改动
git commit -m "fix(docs): 隐私守卫红修复——spec-demo-gif.md 私有声音名脱敏（github-p3-public-g S0.5）"
git rev-parse HEAD          # 记为 FIX_HEAD（写入 report；S2/S3 断言用）
```

### S1 切 main + 提交规划产物（工具可完成）

```bash
git checkout -b main    # 从当前 HEAD（=FIX_HEAD）建 main；绝不带 origin/main 作起点
                        # （远程 main 停旧在 acf9ad1，作起点会丢 18 个提交）
```

- 报「main 已存在」→ 停下报告（规划期实证本地无 main，存在=环境变动）。
- 未提交的规划产物随切换保留（同一 commit 建分支不动工作树）。
- 编辑 docs/context/current-work.md 状态行：将括号内状态措辞（含 v2 注记）整体替换
  为「（实施中）」（替换不续写）。

```bash
git add docs/context/github-p3-public-g.spec.md docs/context/github-p3-public-g.spec.v2.md docs/context/current-work.md docs/context/roadmap.md
git diff --cached --stat   # 期望恰 4 文件；无 models/、live2d-models/ 混入
                           # （repo-maintenance.md:74 施工习惯）
git commit -m "docs(context): github-p3-public-g 规划入库——spec v1/v2+roadmap #5 进行中+远程停旧遗留吸收（分支终态C/push已授权/S0.5隐私前置）"
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

# 2.3 push（v1-release 冻结终值=FIX_HEAD；main 前进到 S1 新提交）
GIT push origin v1-release
GIT push -u origin main

# 2.4 复核
GIT ls-remote origin refs/heads/main refs/heads/v1-release
git rev-parse HEAD
# 期望：refs/heads/v1-release == FIX_HEAD；refs/heads/main == rev-parse HEAD
```

- push 网络失败：同一根因重试合计 ≤3 次（直连↔代理切换算同根因内调整）；3 败 →
  停下报告（用户级纪律第 3 条）。

### S3 本地分支终态确认（工具可完成）

```bash
git branch -vv      # 期望：* main 与 origin/main 同步（0 ahead/behind）；
                    #       v1-release 本地=FIX_HEAD（冻结，本阶段不再动）
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

### S5 公开态三项 curl 验证（工具可完成；重试窗口=拷打裁决④）

```bash
CURL -s -o /dev/null -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar
# 期望 200
CURL -s -o /dev/null -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar/releases
# 期望 200
CURL -s -o /tmp/tag_page.html -w "%{http_code}\n" https://github.com/yancheng1018/Local-LLM-Voice-Avatar/releases/tag/v1.0.0
# 期望 200（Git Bash /tmp 映射用户临时目录，直接用，不依赖 TMPDIR 变量）
grep -c "v1.0.0" /tmp/tag_page.html
# 期望 ≥1；仅当第三条状态码为 200 时才执行与判定本行（404 页不参与 grep 判定）
```

404/异常处置（每条 curl 独立计数：等 30 秒重试，单条合计 ≤3 次）：

- 首页或 /releases 404：归因只有切公开未生效/生效延迟——重试窗口内等；3 次后仍
  404 → 停下回问用户 §7-1 步骤③/④是否实际完成。
- tag 页 404 且前两条已 200：Release 页问题（用户已确认建过 Release，裁决③）——
  同窗口重试；3 次后仍 404 → 停下升级（S9 判据不动，不猜原因）。
- 5xx/超时/其他码（如 429）：同窗口重试；3 次后停下报告。

### S6 全量回归（工具可完成）

见 §6 命令块原样执行。判定口径（211 的来源：拷打期全量实跑 210 passed+1 failed，
S0.5 修复后总用例数不变、红转绿=211；S0.5 单测 4 passed 与本步全量双保险）：
任何红=阻断（本阶段无代码改动面，红必为环境或意外改动）→ 只按 §6 要求汇报，停下。

### S7 report + 收尾簿记（工具可完成）

- 新建 docs/context/github-p3-public-g.report.md，必含：①FIX_HEAD 与 S0.5 证据
  （git grep 前后输出、守卫单测 4 passed 输出、提交 sha）；②sha 对照全过程（S2.1/
  S2.4 输出与期望值并排）；③push 输出摘录与所用网络口径（注明确认出口=代理出口
  还是直连）；④S4 基线 404 与人工项完成时刻；⑤S5 三项状态码+grep 计数+重试发生
  情况；⑥S6 输出摘要行与退出码；⑦S3 分支终态快照（branch -vv + ls-remote 终值）；
  ⑧判断类决策记录（代理启用、重试次数、跳过人工项与否）。

```bash
git add docs/context/github-p3-public-g.report.md
git commit -m "docs(context): github-p3-public-g 实施簿记——report 入库+S0.5隐私修复/push双支/分支终态C/公开态curl证据"
GIT push origin main
```

- 状态行保持「实施中」（翻「审查通过待人工验收」归 /review-spec）；收尾待办块不写
  （/review-spec 专属）。

## 4. 测试用例列表

除沿用现有测试外不新建、不修改任何测试文件（处置口径同先例 github-p3-public-d；
S0.5 是文档脱敏使现有守卫复绿，不是改测试）。本阶段验证面为一次性实施断言，
内嵌于 §3 各步：

| # | 用例名 | 输入 | 预期输出 | 断言点 | 载体（文件/步骤） |
|---|--------|------|----------|--------|------------------|
| V0 | 隐私守卫复绿 | 单跑 tests/test_repo_privacy_guard.py -q | 4 passed | 私有名零命中断言 rc==1 转绿 | S0.5（沿用现有文件） |
| V1 | 双支 fast-forward 前置 | merge-base --is-ancestor ×2 | main-ff-ok、v1r-ff-ok 均打印 | 防非快进/强推 | S2.2（无测试文件） |
| V2 | push 后 v1-release 远程值 | ls-remote refs/heads/v1-release | ==FIX_HEAD | 冻结终值落地且 tip 干净 | S2.4（无测试文件） |
| V3 | push 后 main 远程值 | ls-remote refs/heads/main | ==本地 main HEAD | 推平落地 | S2.4（无测试文件） |
| V4 | 私有基线 | 匿名 curl 首页 | 404 | 私有态在案 | S4（无测试文件） |
| V5 | 公开首页 | 匿名 curl 首页 | 200（重试窗口后） | 公开生效 | S5（无测试文件） |
| V6 | 公开 releases | 匿名 curl /releases | 200（重试窗口后） | 发布页可访 | S5（无测试文件） |
| V7 | tag 页含版本号 | 匿名 curl /releases/tag/v1.0.0 + grep | 200 且计数 ≥1 | Release 页公开可访 | S5（无测试文件） |
| V8 | 全量回归维持绿 | 全量 pytest | 211 passed 且退出码 0 | 无意外改动+基线红已修 | S6（沿用全量命令，不新建文件） |

长期回归保障=现有全量测试维持绿（V8，含守卫复绿），无新增长期用例。

## 5. 步骤分类汇总

- 工具可完成：S0（含 S0.4 探测）、S0.5、S1、S2、S3、S4 基线 curl、S5、S6、S7——
  命令与期望值均已在 §3 给全。
- 需要判断（弱模型停下报告，不自行决策）：S0.4 网络口径选择结论；S0.5 git grep
  出现规格外命中或守卫单测仍红；S2.1 远程 sha 不符；S2.2 非快进；S4 基线 200 的
  「已提前切公开」判定；S5 重试窗口耗尽后的分归因停报；S6 任何红；git 身份不符；
  本地已存在 main；工作树出现规格外改动。

## 6. 运行测试（弱模型原样执行，不要修改）

```bash
cd /c/Coding/Application/Local-LLM-Voice-Avatar
uv run --extra test python -m pytest -q 2>&1 | tail -n 80
echo "pytest_exit=${PIPESTATUS[0]}"
```

判定：`pytest_exit` 非 0，或 tail 输出中的 pytest 摘要行（`N passed` 统计行）不含
`211 passed` → 只汇报失败用例名、断言差异、最后 20 行 traceback，然后停下（本阶段
无代码改动面，禁止以任何方式修实现或测试凑绿——用户级纪律第 9 条）。

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
- 通过/失败判定：S5 首页匿名 curl（含重试窗口）得 200=通过；窗口耗尽仍 404=未生效，
  回看第 3/4 步。
- 预计耗时：约 2 分钟。

## 8. 非目标与边界

- 版本收口：本阶段实施+验收后 v1.0.1 目标集 8 条全部终态，`uv version --bump` 是否
  执行归 /review-spec 收尾裁决（roadmap 头部判据），不在本规格。
- 不动 README（无分支指引，实证见 §1）；不删 v1-release 本地/远程分支（封存≠删除）；
- 不做发版自动化（backlog #5）；遗留 [github-p3-public-f]「README Roadmap 补演示
  GIF 一行（待拍板）」不并入本阶段。
- 历史提交中的私有名残留维持 B6 现状口径（2026-10-07 用户裁决接受，不重写历史）；
  本阶段只保证分支 tip 干净（S0.5）。
