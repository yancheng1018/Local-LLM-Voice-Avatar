# 行数检查
Write-Host "===== 行数检查 =====" -ForegroundColor Cyan
Get-ChildItem AGENTS.md, docs/context/*.md | ForEach-Object {
    $n = (Get-Content $_.FullName -Encoding UTF8).Count
    $limit = if ($_.Name -eq "AGENTS.md") { 100 } else { 200 }
    $flag = if ($n -gt $limit) { "⚠️ 超标" } else { "✓" }
    "{0,-40} {1,4} 行  {2}" -f $_.Name, $n, $flag
}

# 索引表一致性
Write-Host "`n===== 索引表一致性 =====" -ForegroundColor Cyan
$mentioned = Select-String -Path AGENTS.md -Pattern 'docs/context/[^\s|\)\]]+\.md' -AllMatches |
    ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
$actual = Get-ChildItem docs/context/*.md | ForEach-Object { "docs/context/" + $_.Name } | Sort-Object -Unique

Write-Host "索引表提到但不存在："
$mentioned | Where-Object { $_ -notin $actual }
Write-Host "存在但索引表未提："
$actual | Where-Object { $_ -notin $mentioned }