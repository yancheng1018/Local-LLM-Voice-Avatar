# docs/context 维护手册

## 一、文件体系总览

| 文件 | 职责 | 行数上限 | 加载时机 |
|------|------|---------|---------|
| AGENTS.md | 导航 + 防崩红线 | 100 行 | 始终加载 |
| config-system.md | 配置层级与角色系统语义 | 200 行 | 改配置/角色/人设/语言 |
| live2d.md | Live2D 显示/表情/动作约定 | 200 行 | 改模型/表情/动作/尺寸 |
| gui-launcher.md | GUI 启动器功能与实现 | 200 行 | 改 launcher/声音模型/编辑器 |
| ollama-backend.md | 后端定制与数据流 | 200 行 | 改后端/Ollama/streaming |
| minimal-frontend.md | 极简自研前端设计 | 200 行 | 开发极简前端 |
| current-work.md | 进行中工作摘要 | 30 行 | 每次续接工作 |
| archive.md | 历史归档（压缩格式） | 无硬限 | 查历史决策时 |

核心原则：一个文件只拥有一个关注点，规则不重复。同一条规则出现在两个地方，等于没有规则。

## 二、维护分工

| 内容 | 谁写 | 什么时候 |
|------|------|---------|
| 新结论、新契约、踩坑记录 | Agent | 每次会话结束时，由你指示 |
| 当前进展、待处理 | Agent | 每次会话结束时 |
| 模块边界调整 | 你 | 发现归属不对时 |
| 索引表改名/增删 | 你 | 新建或删除模块文件时 |
| 删除过时内容 | 你 | 定期扫一眼时 |
| 行数超标后的拆分/压缩 | AI + 你 | 超标触发时 |

关键提醒：Agent 不会自动更新文档。这是特性，不是限制。如果 Agent 在每次代码任务后静默更新文档，而那次任务有 bug，文档就会把错误行为记录为“预期行为”，下一个会话会把错误当成规则。你是检查点——先确认代码正确，再指示 Agent 更新文档。

## 三、日常流程（每次会话）

### 会话开始时

读 AGENTS.md，本次任务：<任务描述>。
只加载 docs/context/<对应模块>.md。

AGENTS.md 中的索引表会告诉 Agent 该读哪个文件。你不需要指定具体文件名，索引表负责路由。

### 会话结束时

追加一句：

把本次改动记入 docs/context/<对应模块>.md：
- 改了什么
- 留下的契约/结论
- 踩了什么坑
不要动 AGENTS.md。

必须明确指定写入哪个文件。不指定的话，Agent 可能默认往 AGENTS.md 塞，根文件会慢慢膨胀。

### 如果本次是“完成一个阶段”

再追加一句：

把本次会话的已完成记录以压缩格式追加到 docs/context/archive.md。

归档格式（每段 2-3 行）：

## YYYY-MM-DD 标题
- 做了什么
- 留下的契约/文件

## 四、周期性检查

### 检查脚本（每周或每阶段跑一次）

```powershell
Write-Host "===== 行数检查 =====" -ForegroundColor Cyan
Get-ChildItem AGENTS.md, docs/context/*.md | ForEach-Object {
    $n = (Get-Content $_.FullName -Encoding UTF8).Count
    $limit = if ($_.Name -eq "AGENTS.md") { 100 } else { 200 }
    $flag = if ($n -gt $limit) { "超标" } else { "OK" }
    "{0,-40} {1,4} 行  {2}" -f $_.Name, $n, $flag
}

Write-Host "`n===== 索引表一致性 =====" -ForegroundColor Cyan
$mentioned = Select-String -Path AGENTS.md -Pattern 'docs/context/[^\s|\)\]]+\.md' -AllMatches |
    ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
$actual = Get-ChildItem docs/context/*.md | ForEach-Object { "docs/context/" + $_.Name } | Sort-Object -Unique

Write-Host "索引表提到但不存在："
$mentioned | Where-Object { $_ -notin $actual }
Write-Host "存在但索引表未提："
$actual | Where-Object { $_ -notin $mentioned }
