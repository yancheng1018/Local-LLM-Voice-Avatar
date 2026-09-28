## 当前阶段

### 阶段状态
> **github-p0-privacy：上传github前准备·P0隐私批——私人资产出索引+B档文档脱敏+filter-repo 历史抹除与 mailmap 改写（审查通过，待人工验收）[1/6]**

### 阶段路线图 · 上传github前准备
> 把仓库整理为可公开发布的 GitHub 仓库（已定名 Local-LLM-Voice-Avatar，分发名 local-llm-voice-avatar）；共 6 阶段；建立于 2026-09-29
> 阶段划分依据 research_上传github前准备.md §7 分批表；事实基准 temp_spec_github_publish.md

| # | 阶段 | 目标一句话 | 状态 | 备注（依赖/前置） |
|---|------|-----------|------|------------------|
| 1 | github-p0-privacy | 私人资产出索引+文档B档脱敏+filter-repo 抹历史与 mailmap 改写 | 审查通过待验收 | mailmap 已定 noreply（55277749+yancheng1018）；规格 temp_spec_github-p0-privacy.md |
| 2 | github-p0-decouple | GUI:573 占位文案通用化+收录 start_v4_dpo.bat/.py（注明 v2pro-20260604）+私有声音名 grep 守卫测试落位 | 未开始 | 依赖批1；是否连带收录停止脚本待用户定（研究 §8-②） |
| 3 | github-p0-characters | ja_test 本地改名 shinano.yaml+忽略项换名+新建大众化默认测试角色入库 | 未开始 | 依赖批1；新角色人设内容需用户过目 |
| 4 | github-p1-facade | 改名四联动+版本 1.0.0+README 主写（Live2D 授权声明/多引擎亮点/快速层 pyttsx3） | 未开始 | edge_tts→pyttsx3 方案默认采纳（研究 §3 建议，§8-① 待最终确认） |
| 5 | github-p1-robust | frontend/ mount 守卫+新克隆冒烟（零 GPT-SoVITS 路径加验转必做） | 未开始 | 依赖批4（按 README 冒烟） |
| 6 | github-p2-release | 建仓（先私有）→显式 refspec push→tag v1.0.0+Release→收尾 | 未开始 | push 需用户明确确认；需 GitHub 用户名 |

### 收尾待办

> 收尾执行清单已备：finalize_exec_github-p0-privacy.md（10 条），人工验收通过后运行 /finalize github-p0-privacy

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

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
