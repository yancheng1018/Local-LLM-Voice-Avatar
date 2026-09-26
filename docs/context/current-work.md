## 当前阶段

### 阶段状态
> **清理待处理遗留-批2 已完成并验收通过（2026-09-27）**。test-sweep 五问裁决：7 文件
> 转正改名、11 个重复/墓碑函数删除、__tsout__ 停跟踪+全仓排版清零（[test-sweep]/
> [repo-format] 关账）；提交 f1831cb/708f241，全量 162 测试绿，ruff format --check
> 全仓 0 files。批3（hotzone-arch 复审研究）/批4（l2d.ts 重构立项）待各自立项；
> 当前无既定下一阶段，等待新需求。

### 收尾待办
> 无（清理待处理遗留-批2 收尾已执行完毕：temp_spec/impl_report 删除+pytest 调用
> 契约入档 AGENTS.md+终态写入——2026-09-27）。

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
  S3/F1 已裁不修（站点同款非缺陷，研究 §6.4）。依据：research_live2d动作链条修正.md §7/§8
- [live2d] 39 个模型 emotionMap 为空（mao_pro 已有 50 键可作参照样本；情绪关键词
  不触发表情）：同样按需补（口径订正 2026-09-18，research_清理待处理遗留.md 发现 2）
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [hotzone-arch] 热区触摸逆向待裁决项（leftover-triage_stage2 合并自 round1 §7 /
  r2 §9 / r2_v3 / r2_v4 四条，依据 research_leftover-triage.md §5.4；锚点：
  spec-l2d-touch-engine.md；待后续重新研究逐项裁决）：① type 9/10/11 未实现清单
  入档、OE_TYPES 含 7 vs dispatch 拒 6/7、empty 占比差异（游戏数据生成侧）；
  ② guanghui 点名 5 区来源未复现（research2 §5-Q1 候选解释：type12 名单+TouchIdle
  名单重复点名，原始观察待用户补充）、tips 新 schema（idleBlackList/animWhiteList）
  消费与否（type12 已实现于 live2d动作链条-research2 阶段）；③ 叠加层显示策略（r3 §7.1 方案 A/B/C + 退化区门槛）、
  forEach vs 择一（站点已证 forEach，改属规格变更）、TouchBody 链自毁与
  feiteliedadi 可玩性、stepDrag 起点锚定未扩面；④ D4 offset=0 语义（站点源码 ||1
  直证 vs 用户实测无误触发，待站点数值取证统一，本地保留 0 轴排除）、D5 slide
  闸门边界（offsetCircle 样本未普查）、D6 棘轮三函数/D7 triggerConditionMet 常量表
  （需下载 chunk 反查）、§2.2 触发时序为 D 级推断（若站点取证推翻须修正 resolve
  顺序）。已裁决定案存档：forEach=站点逐区分发、C6=数据事实非实现顺序（r3 裁决，
  原文档已失，以此为准）；findChainRule 匹配面一项已吸收进 r2 规格 §2.3
- [live2d] 新模型入库完整性检测：将 scan_live2d_models.py →
  fix_live2d_idle_groups.py → fit_live2d_scale.py 脚本链内嵌进启动器导入流程
  （自动检测 + 一键修复 + 报告展示）；轻量版工作流（导入后手动跑脚本链）随
  leftover-triage_stage1 建立，launcher 集成暂缓待立项（2026-09-16 用户裁决）
- [repo-hygiene] 两处轻量清理（2026-09-18 批2 规划发现，可并入任意后续批）：
  ① .gitignore `!live2d-models/shizuku/` 白名单行与「仅入库 mao_pro / shizuku」注释
  过期（shizuku 已删，白名单成死配置）；② test_l2d_touch_redlines /
  test_l2d_touch_param_semantics 的 docstring 指向已删除的 r2 temp_spec 文档
  （应改指 spec-l2d-touch-engine.md 对应章节）

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
