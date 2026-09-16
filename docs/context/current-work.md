## 当前阶段

### 阶段状态
> **live2d动作链条修正**：阶段 0+A（ParamDriver 挂点迁 afterMotionUpdate / 关库 idle
> 自动播放 / 9 模型 touch.json 重下）已完成并验收通过（2026-09-17），收尾完成
> （契约降级入档、过程文档清理、逆向资产归档）。当前无既定下一阶段，等待新需求；
> 阶段 B/C 延后候选见待处理遗留。

### 收尾待办
> 无

### 待处理遗留

- [live2d动作链条] 阶段 B（参数权威层/type104/revertIdleIndex/revertActionIndex——
  G2「动作后热区恢复」与 F2「drag3 后不复位维持」的完整语义）与阶段 C（type12 裁决/
  形态A 查表/冷却先记/链循环）延后未立项。前置：B 须先更新 spec-l2d-touch-engine.md
  §10 并经人工批准（研究 §8-1 站点面板↔模型双路径未取证）；S3/F1 已裁不修（站点同款
  非缺陷，研究 §6.4）。依据：research_live2d动作链条修正.md §7/§8
- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [repo-format] 全仓 25 文件未 ruff format（leftover-triage_stage2 规划实测：
  `ruff format --check .` 报 26 文件，stage2 已清 launcher 1 个，余 25）：15 个
  frontend-minimal/tests/*.py（与 [test-sweep] 盘点耦合，建议其裁决文件去留后再
  批量格式化，避免白做/混 diff）、3 个根脚本（fit/fix/scan_live2d*）、6 个 src/
  后端文件 + tests/test_live2d_model_data.py；处置待用户裁决（建议独立排版工程
  一次清完）
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [hotzone-arch] 热区触摸逆向待裁决项（leftover-triage_stage2 合并自 round1 §7 /
  r2 §9 / r2_v3 / r2_v4 四条，依据 research_leftover-triage.md §5.4；锚点：
  spec-l2d-touch-engine.md；待后续重新研究逐项裁决）：① type 9/10/11 未实现清单
  入档、OE_TYPES 含 7 vs dispatch 拒 6/7、empty 占比差异（游戏数据生成侧）；
  ② guanghui 点名 5 区来源未复现、type12/tips 新 schema（idleBlackList/
  animWhiteList）消费与否；③ 叠加层显示策略（r3 §7.1 方案 A/B/C + 退化区门槛）、
  forEach vs 择一（站点已证 forEach，改属规格变更）、TouchBody 链自毁与
  feiteliedadi 可玩性、stepDrag 起点锚定未扩面；④ D4 offset=0 语义（站点源码 ||1
  直证 vs 用户实测无误触发，待站点数值取证统一，本地保留 0 轴排除）、D5 slide
  闸门边界（offsetCircle 样本未普查）、D6 棘轮三函数/D7 triggerConditionMet 常量表
  （需下载 chunk 反查）、§2.2 触发时序为 D 级推断（若站点取证推翻须修正 resolve
  顺序）。已裁决定案存档：forEach=站点逐区分发、C6=数据事实非实现顺序（r3 裁决，
  原文档已失，以此为准）；findChainRule 匹配面一项已吸收进 r2 规格 §2.3
- [test-sweep] tests/ 既有资产盘点：10 个带 stage/debug 痕迹的已跟踪测试文件
  （test_l2d_hotzone_stage2~7、test_stage6_bugfix、test_debug_panel*、
  debug_panel_runtime.test.mjs、test_touch_debug_overlay）待强模型专项按五问框架
  集中裁决（转正改名/合并/删除）；机制落地后新任务不再积累。r2 系列两份已于
  r2_v4 收尾转正（test_l2d_touch_redlines / test_l2d_touch_param_semantics）
- [live2d] 新模型入库完整性检测：将 scan_live2d_models.py →
  fix_live2d_idle_groups.py → fit_live2d_scale.py 脚本链内嵌进启动器导入流程
  （自动检测 + 一键修复 + 报告展示）；轻量版工作流（导入后手动跑脚本链）随
  leftover-triage_stage1 建立，launcher 集成暂缓待立项（2026-09-16 用户裁决）

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
