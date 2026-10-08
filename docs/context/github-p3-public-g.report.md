# github-p3-public-g 实施交接报告

> 依据规格：github-p3-public-g.spec.v2.md（施工唯一权威版）。实施日期 2026-10-09。
> 网络口径：S0.4 直连探定成功；S5 首轮直连 000（间歇阻断复发）按规格切代理
> 127.0.0.1:7890 一次成——全程未改全局 git/curl 配置。

## 1. 状态

完成（S0→S7 全步骤落地；S6 经一轮自纠后 211 绿；人工项切 public 已由用户完成）。

## 2. 实际改动的文件清单

- docs/context/spec-demo-gif.md：1 行改写（:47 三私有声音名脱敏，S0.5 提交 64e9cad）
- docs/context/github-p3-public-g.spec.v2.md：+7/-6（S0.5 段私有名指代化自纠，提交 69fa2e1）
- docs/context/github-p3-public-g.spec.md / .spec.v2.md / current-work.md / roadmap.md：
  规划产物入库（S1 提交 293b595，4 文件 +542/-6，状态行已翻实施中）
- docs/context/github-p3-public-g.report.md：新建（本文件，S7）

## 3. 测试资产变化

无（零新增/修改/删除；V0 守卫单测与 V8 全量均沿用现有文件）。

## 4. 与规格书的一致性

- 照做：S0/S0.4/S0.5/S1/S2/S3/S4/S5/S6/S7 全部按规格命令与期望值执行，断言全过。
- 偏离 1（S6 首轮红自纠）：spec.v2 自身 S0.5 段含该私有声音名字面量 3 处，随 S1
  入库触发守卫红——规格硬边界未预见「规格文本自身受守卫约束」，按 S0.5 同类口径
  脱敏自纠（指代化），守卫单测 4 passed 后全量复跑 211 绿。
- 偏离 2（S5 网络口径）：规格预期直连，实际直连间歇阻断（000），按规格内建 S0.4
  处置切代理后全绿——属规格授权路径内处置，非超范围。

## 5. 遇到的问题

- S6 首轮 1 failed/210 passed：根因=拷打期把守卫红的名字字面量写进 spec.v2 依据段，
  f 阶段同类教训（守卫扫描全被跟踪文件）在规格文本上重演；修复=3 处指代化。
- S5 首轮三项 000：github.com 直连间歇阻断（repo-maintenance.md:87 已知模式），
  非可见性问题；代理重试即绿，未耗尽 30s×3 窗口。

## 6. 改进建议

- 规格模板补注候选（列遗留，勿入本阶段）：规格文本引用守卫名单字面量必触发隐私
  守卫——凡涉及守卫类修复的规格，依据段一律用「该私有名」指代，字面量只出现在
  会话记录不入库文件。
- 行数预检数字宜在写入前 wc 实测（v2 已按实测口径修正，但 v1 曾凭记忆写 114→111，
  实际 112→110，与复审发现一致）。

## 7. 待确认疑点

- spec.v2 初版（含私有名字面量）已随 293b595 推入公开仓库历史：守卫只保 tip 干净
  （规格 §8 引 B6 现状口径：不重写历史），字面量将留存于公开 git 历史——按既定
  裁决无需动作，特此报备知情。
- 其余无。

## 8. 契约候选

无（隐私守卫已机械覆盖全被跟踪文件含 docs，本次是既有契约的执行而非新契约；
「规格文本不写守卫名单字面量」属写作纪律，建议走遗留模板补注通道）。

## 9. 自动化验证证据

- S0.5：`git grep -n "<名单唯一私有名>" -- . ':!tests'` 修复前唯一命中 spec-demo-gif.md:47；
  修复后 rc=1 零命中；守卫单测 `pytest tests/test_repo_privacy_guard.py -q` →
  4 passed（修复前 1 failed/3 passed）。
- S2.1 前置复核：ls-remote main=acf9ad1、v1-release=1000463（与规格期望一致）；
  ff 断言 main-ff-ok+v1r-ff-ok。
- S2.3/2.4：push `1000463..64e9cad v1-release`、`acf9ad1..293b595 main`（均
  fast-forward 无强推）；复核 ls-remote main=293b595=本地、v1-release=64e9cad=FIX_HEAD。
- S4：匿名 curl 首页=404（私有态证据，直连）。
- S5（代理口径）：home=200、releases=200、tag_page=200、`grep -c v1.0.0`=19。
- S6 终局（全量，规格 §6 命令块原样）：
  ```
  ..................[100%]
  211 passed in 49.47s
  pytest_exit=0
  ```
- S3 终态：`* main 293b595 [origin/main]`（同步）、`v1-release 64e9cad
  [origin/v1-release]`（冻结）、工作树干净。
- S7 收尾推送后终值见 git log（REDACT=69fa2e1、report 提交见尾）。

## 关键 sha 对照

| 量 | 值 |
|----|----|
| BASE_HEAD（开工基线） | eb8311776994d1981b29743a199f180b5b9334ab |
| FIX_HEAD（S0.5 后，v1-release 冻结终值） | 64e9cad9ce51fc291f0dca9ff8d7e9835d9882cd |
| S1 规划入库 | 293b595bab636ad4b849f93bf17d673958c14eff |
| S7 spec.v2 自纠 | 69fa2e1d12969373633493155e546fc508ae6084 |
| 远程旧值（push 前） | main=acf9ad1、v1-release=1000463 |
