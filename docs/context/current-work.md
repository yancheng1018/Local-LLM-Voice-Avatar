## 当前阶段

### 阶段状态
> **github-p2-release 及所属功能线全部完成并验收通过（2026-09-30）。当前无既定下一阶段，等待新需求**

### 收尾待办

> 无。

### 待处理遗留

- [live2d] l2d.ts 1081 行拆分重构（例外已入档模块文档，research3 收尾裁决 2026-09-18）：
  核心渲染器含手势/热区/调试挂点，拆分需独立规格；触发时机=下次对该文件加新功能前
- [live2d动作链条] 阶段 B 已完成并验收（2026-09-18，归档见 archive.md）；剩余延后项：
  阶段 B 尾巴——type2+target 非 circle 点按写参（v2 §3.1 ⑧，811 条 type2 爆炸半径大，
  F2 验收不足时另立）；阶段 C——type9/11/15 条件门槛、冷却先记（被拒也吃
  冷却）、dynamicFlag 可见性、tips 显隐、type5/10/13、参数权威层全量化（前置：研究
  §8-1 站点面板↔模型双路径未取证——research2 §3.1 已定案一半：type12 与面板读同一条
  目标表，motion 曲线写入与目标表交互仍未取证）；type12 裁决已吸收进
  live2d动作链条-research2 阶段。链循环 vs D2 取舍待权威层阶段一并裁决。
  依据：research_live2d动作链条修正.md §7/§8（S3/F1 已裁不修已提炼入模块文档，distill-b3）
- [live2d] 39 个模型 emotionMap 为空（mao_pro 已有 50 键可作参照样本；情绪关键词
  不触发表情）：同样按需补（口径 2026-09-18 实测：39/40 空，mao_pro 唯一非空）
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [hotzone-arch] 复审裁决落地后剩余（2026-09-27，裁决子项已全部回写 spec-l2d-touch-engine.md
  并随本阶段验收关账；依据 research_hotzone-arch复审.md §11）：
  ① TouchBody 链几何退化+复位不可逆，建议优先立项（跨模型普遍、非单模型问题：feiteliedadi_3
  链第 3 步后、aerbien_3 第 1 步后 TouchBody 全画布不可命中——命中区退化 7×6px @模型坐标
  y≈20545，touch_idleN 末帧姿态出视口；paramDriver.resetAll+playIdleOnce 不恢复；body 链
  实际被截断在 1~3 步、用户感知强。白名单锁已由 hotzone-arch裁决落地阶段修复，几何层待立项）；
  ② stepDrag 起点锚定未扩面（站点=交互起点 startValues 锚定，本地 startValue 重锚+幅值累积，
  10 条/5 模型，待症状驱动再议）；③ TouchChain+main.ts 运行时测试候选（aerbien_3 直调
  onInteraction 链推进演示可固化为运行时回归，补静态断言之不足）
- [live2d] 新模型入库完整性检测：将 scan_live2d_models.py →
  fix_live2d_idle_groups.py → fit_live2d_scale.py 脚本链内嵌进启动器导入流程
  （自动检测 + 一键修复 + 报告展示）；轻量版工作流（导入后手动跑脚本链）随
  leftover-triage_stage1 建立，launcher 集成暂缓待立项（2026-09-16 用户裁决）
- [distill-b2] 收尾两项待拍板：① l2dsu抓取模型说明.md 是否登记 AGENTS.md 索引表（自荐
  「l2d.su 数据源抓取」条目，索引增删属用户）；② 合并版 spec-l2dsu-engine.md 601 行超标按
  归档容忍口径确认（先例 r4=948）——①拍板后自改或指示执行，②默认容忍无需动作
- [github-p2-precheck-e] 规格行数账边界空行口径并入 spec-writing.md（本批投影 83 实得 81：
  节删除后相邻空行合并未计入账）——与 d① 同触发点（下次规格模板维护），届时合并处理
- [github-p2-precheck-d] 收尾三项（2026-09-30 审查登记）：① 规格收尾清扫模板与守卫测试
  字面量自指冲突——裁决口径已定（生产路径零命中为准，tests/ 卫生由 pytest 兜底），
  spec-writing.md 模板注记待下次规格模板维护并入（批 e 范围限 AGENTS.md，另择时机）；
  ② GUI 版本推导裸目录边缘：_gsv_launch_command 对无后缀 GPT_weights 目录权重派生非法
  version 串——现实包裸目录为空不可达，触发=用户向裸目录放权重并选择，症状驱动时加
  派生值校验；③ _await_api 可选加固：感知进程早退免 120s 空轮询误报，非必需随手改时带上
- [github-p2-release] S9 公开态验证补跑：用户在 GitHub Settings 把仓库切 Public 后跑三项
  curl（首页 200 / releases 200 / releases/tag/v1.0.0 页含 v1.0.0 ≥1）；触发时机=切公开后
  即跑（本阶段裁决 A 线暂缓公开，命令已内联无需回查规格）
- [github-p2-release] D2 README 演示图后补（人工子项）：用户录屏/截图后补进 README，随附
  commit+push（届时 push 仍需用户确认）；原由路线图行 11 备注承载，归档前抢救登记
- [github-p2-release] 发版自动化+打包分发候选（用户问答提出 2026-09-30，未立项）：① 装
  gh CLI（winget install GitHub.cli + gh auth login）使 gh release create 可自动化；②
  Actions 打 tag 自动建 Release；③ portable zip/安装包分发工程；待用户拍板是否立项
- [github-p2-release] 规格 S1 门禁「工作树干净」宜注记「允许状态入口未提交改动（规划协议
  产物）」：与 precheck-e/d① 同触发点，下次规格模板维护时并入 spec-writing.md


### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
