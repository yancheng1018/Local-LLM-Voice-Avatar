# github-p3-public-e · .gitattributes 根治新克隆 CRLF 测试红（roadmap v1.0.1 #7）

> 来源：roadmap v1.0.1 #7（2026-10-08 用户立项；病灶实测发现于 p3-public-d S3.5）。
> 剩余三序裁决（2026-10-08）：#7 → #6 → #5，本阶段先行；顺序依据见 roadmap 调整记录。
> 规划实跑基线（spec-writing §3）：主仓全量 200 passed in 51.11s（2026-10-08 规划会话实测）。

## 0. 背景与机制（规划已取证，执行层不需重查）

- 断言面：`tests/test_publish_facade.py:157` `test_live2d_core_vendored`，断言
  `static/libs/live2dcubismcore.min.js` 存在、`len(data)==206492`、
  sha1==`6b35977308b3219a4dd0bbcfb72026d54fc5d852`、前 600 字节含 `b"Live2D"`。
- 病灶机制：`.gitattributes` 现为单行 `static/libs/* linguist-vendored`（实测 31 字节、
  无尾换行），未钉 `-text`；入库 blob=206492（LF、8 行）。autocrlf=true 环境（本机
  系统级 gitconfig `C:/Program Files/Git/etc/gitconfig` 实测 true）新克隆检出时 LF→CRLF
  转换全文 8 处换行 → 206500，字节与 sha1 双断言红。主仓工作树自入库起未重检出
  （LF 206492）故恒绿——根修后两侧检出均应为 LF 原样字节。
- 复验环境：`C:/Coding/Application/LLMVA-clean-clone-test`（v1-release、树干净、
  落后主仓 4 个纯 docs 提交、`.venv` 在位），其工作树该文件当前 206500——红态在位，
  可先取证红、再复验绿。
- 根修口径（roadmap 裁决）：属性层修复，现有字节/sha1 断言**原样保留**作回归守卫，
  不碰任何测试代码。

## 1. 修改/新建文件清单

| 文件 | 动作 | 行数预检（spec-writing §5） |
|------|------|------------------------------|
| `.gitattributes` | 修改：单行改写并补尾换行 | 1→1 行（根文件上限 100，余量足） |
| `docs/context/github-p3-public-e.report.md` | 新建：实施交接报告 | 阶段产物，容忍口径不计 |
| `docs/context/github-p3-public-e.spec.md` | 已由规划写入，执行层不改动 | 同上 |

不碰 `tests/`、不碰 `static/libs/` 文件本体、不 push、不动 remote。

## 2. 改动详情（唯一代码面改动）

`.gitattributes` 全文由（现文件无尾换行）：

```
static/libs/* linguist-vendored
```

改为（两属性同行、补行尾换行）：

```
static/libs/* linguist-vendored -text
```

要点：必须补行尾换行（od -c 实测现文件 31 字节止于 `d`，无 `\n`）；`-text` 关闭该
路径 eol 双向转换与文本 diff 归一化，检出=原样字节（LF 206492）。不拆两行、不调整
属性顺序、不加其他路径。

## 3. 断言盘点（spec-writing §1）

- 规划会话 rg 实测：`tests/` 内引用 `live2dcubismcore` 仅
  `tests/test_publish_facade.py:157` 一处；`rg "gitattributes|linguist" tests/`
  零命中——本改动测试断言面恰为 §0 一处，处置=原样保留不改动。
- 仓库其余 `live2dcubismcore` 引用（`frontend-minimal/index.html` script 标签、
  `docs/context/gui-launcher.md`、`LICENSE`/`LICENSE-Live2D.md`）均非字节断言引用，
  不受影响。
- 无迁移类改动，§1 的迁移断言盘点条款不适用；§2 bundle 断言条款不适用（非构建产物
  改动，且该测试锚字节/哈希非注释）。

## 4. 测试用例列表（全部沿用现有文件，零新增/零修改/零删除）

| 用例名 | 输入 | 预期输出 | 断言点 | 目标测试文件 |
|--------|------|---------|--------|--------------|
| test_live2d_core_vendored（主仓） | 修复后主仓跑单节点 | 1 passed | len==206492 + sha1 + 版权头 | 沿用 `tests/test_publish_facade.py` |
| 同上（主仓全量回归） | 修复后主仓全量 | 200 passed | 全量恰为基线数（本阶段零测试/产品代码改动） | 沿用同文件 |
| 同上（克隆·红态取证） | 拉取修复提交**前**，克隆内跑单节点 | 1 failed：`len(data)==206500` | 断言差异信息含 206500 | 沿用同文件 |
| 同上（克隆·绿态复验） | 拉取修复提交并重检出后跑单节点 | 1 passed | 同主仓 | 沿用同文件 |

## 5. 实施步骤

### S1「工具可完成」：改写 .gitattributes（按 §2 全文落盘）

验证（三条全过才进 S2）：

```bash
git check-attr text eol linguist-vendored -- static/libs/live2dcubismcore.min.js
# 期望三行，其中 text 行为： text: unset
git status --short        # 期望仅 " M .gitattributes" 一条
git diff                  # 期望恰为该行行尾追加 " -text" 与换行
```

### S2「工具可完成」：主仓验证

按 §7 命令块原样执行：单节点 → 1 passed；全量 → 200 passed。

### S3「工具可完成」：提交修复（先核对 git 身份）

- `git config user.name` == `yancheng1018` 且 `git config user.email` ==
  `55277749+yancheng1018@users.noreply.github.com`（不符即停下汇报，勿改任何 git 配置）。
- `git add .gitattributes` → `git diff --cached --stat` 确认恰 1 文件 +1/-1 行。
- 提交信息（单行）：
  `fix(repo): .gitattributes 钉 static/libs -text 根治新克隆 CRLF 字节断言红（github-p3-public-e）`

### S4「工具可完成」：克隆复验（红态取证 → 拉取 → 重检出 → 绿态）

```bash
CL="C:/Coding/Application/LLMVA-clean-clone-test"
MAIN="C:/Coding/Application/Local-LLM-Voice-Avatar"
```

1. 前置自检：`git -C "$CL" status --short` 为空；
   `wc -c < "$CL/static/libs/live2dcubismcore.min.js"` == `206500`（红态在位；非此值
   停下汇报，勿继续）。
2. 红态取证（预期失败，不触发停机规则，输出留作 report 证据）：
   `uv --directory "$CL" sync --extra test` 后运行
   `uv --directory "$CL" run --extra test python -m pytest -q "tests/test_publish_facade.py::test_live2d_core_vendored" 2>&1 | tail -5`
   → 期望 `1 failed`，断言差异含 206500。
3. 拉取：`git -C "$CL" pull "$MAIN" v1-release`（本地路径直拉，不走 origin——修复
   未推送；期望输出含 `Fast-forward`）。拉入的均为 docs/属性提交，`uv.lock` 不变，
   无需联网。
4. 重检出：`rm "$CL/static/libs/live2dcubismcore.min.js" && git -C "$CL" checkout -- static/libs/live2dcubismcore.min.js`
5. 断言：`wc -c` == `206492`；`git -C "$CL" status --short` 为空（属性生效后无幻影
   modified）。
6. 绿态复验：重跑第 2 步同命令 → `1 passed`。

任一断言不过 → 停下汇报（保留克隆目录原状），不试错超过 3 次（用户级协议）。

### S5「需要判断」：写实施交接报告 `docs/context/github-p3-public-e.report.md`

必含：S1 三条验证输出、S2 全量 200 证据（末行）、S4 红/绿对照输出（各含命令与关键
行）、提交 sha×2、未做事项（不 push、不删克隆目录、可选子项未含）、疑点（如有）。

### S6「工具可完成」：簿记提交

```bash
git add docs/context/github-p3-public-e.spec.md docs/context/github-p3-public-e.report.md
git commit -m "docs(context): github-p3-public-e 实施簿记——spec+report 入库（克隆复验红→绿）"
```

不 push（push 属阶段 g（roadmap #5）前置门禁，须用户确认）。

## 6. 范围外与收尾处置注记

- 可选子项 `*.bat text eol=crlf`（roadmap #7 待拍板项；全仓仅 `启动器.bat` 一个 .bat）：
  默认不含；用户拍板并入则出 spec.v2，不自行加行。
- 克隆目录 `LLMVA-clean-clone-test` 删除：触发=本阶段复验通过且用户验收后，列入
  /review-spec 收尾清单执行，不属实施步骤（遗留吸收自 [github-p3-public-d]）。
- 不改 AGENTS.md 契约行（「须先钉 .gitattributes 或改行尾归一化比较」仍为通用规则，
  本阶段正是其落地实例）。

## 7. 人工验收清单

无。全部验证点均已自动化（S2/S4）；无主观观感项、无外部账号操作（切 public 属阶段 g）。

### 运行测试（弱模型原样执行，不要修改）

```bash
set -o pipefail
uv run --extra test python -m pytest -q "tests/test_publish_facade.py::test_live2d_core_vendored" 2>&1 | tail -5
uv run --extra test python -m pytest -q 2>&1 | tail -80
```

预期：第 1 条 `1 passed`；第 2 条末行 `200 passed`。
如果退出码不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
