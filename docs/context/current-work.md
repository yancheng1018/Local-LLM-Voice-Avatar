## 当前阶段

### 阶段状态
> **leftover-triage_stage1** 已完成并验收通过（2026-09-16）。遗留清理第一批（A 类）：
> Idle 别名组修复脚本 + pytest test 组 + 删 en_nuke_debate.yaml + Idle 契约回归测试。
> **当前无既定下一阶段，等待新需求**；清理进度见「待处理遗留」（A 类已清，
> N02/N04/N08 与 D 类待裁决，依据 research_leftover-triage.md）。

### 收尾待办
> 无

### 待处理遗留

- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [stage5] launcher ruff format 全文件重排单独立项：stage5 曾尝试对
  launcher/OpenLLMVTuber_GUI.py 跑 format，产生 +332/-181 纯排版 diff
  （该文件历史样式从未 format 过），已回退保持最小功能 diff；
  触发时机：作为独立的排版工程提交，不混入功能阶段
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [stage7] l2d_touch_debug.ts 已达 220 行硬上限：叠加层再加功能必须先拆分
  （r2 规格已内置净减拆分，r2 实现后复核行数）
- [hotzone-touch] round1 §7 遗留候选收敛（r3 已裁决：forEach=站点逐区分发、C6=数据事实
  非实现顺序）：仍待裁决 = type 9/10/11 未实现清单入档、OE_TYPES 含 7 vs dispatch 拒 6/7、
  empty 占比差异（游戏数据生成侧）；findChainRule 匹配面一项已吸收进 r2 规格 §2.3
- [hotzone-touch-r2] r2 §9 疑点：forEach/C6 已由 r3 裁决（见上条）；guanghui 点名 5 区
  来源未复现、type12/tips 新 schema（idleBlackList/animWhiteList）消费与否仍待裁决
- [r2_v3] v3 规格遗留的用户裁决项（r2_v4 重核）：叠加层显示策略（r3 §7.1 方案 A/B/C
  + 退化区门槛）、forEach vs 择一（站点已证 forEach，改属规格变更）、TouchBody 链自毁
  与 feiteliedadi 可玩性、stepDrag 起点锚定未扩面；D-g 已并入 D6（见 [r2_v4] 条）
- [r2_v4] v4 §6 明确不做（待后续裁决/取证）：D4 offset=0 语义（站点源码 ||1 直证 vs
  用户实测无误触发，疑点 1 未决，待站点数值取证后统一，本地保留 0 轴排除）、D5 slide
  闸门边界（offsetCircle 样本未普查）、D6 棘轮三函数/D7 triggerConditionMet 常量表
  （r4 §5.2 优先级 4，需下载 chunk 反查）、§2.2 触发时序为 D 级推断（若站点取证推翻
  须修正 resolve 顺序）
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
