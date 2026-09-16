## 当前阶段

### 阶段状态
> **live2d-hotzone-touch-r2（含 stage7）**：全部完成并验收通过（2026-09-16）。历程：
> v1/v2 → v3 两轮人工验收失败，r4 站点源码直证（research_live2d-hotzone-touch-r4.md，
> 已保留归档）推翻 v3 两处定案后产出 v4 定案：ATA.idle 防重复方向 / clampChain 三步链
> 门控 / resolve 触发时序 / 调试栏指针捕获。定案已并入 spec-l2d-touch-engine.md，
> 规格编写教训入档 spec-writing.md。**当前无既定下一阶段，等待新需求**；热区/触摸
> 遗留（D4~D7、显示策略等）见「待处理遗留」。前序：阶段一~六已验收提交（4bccd87）；
> test-lifecycle 已完成并验收通过（2026-09-16）。

### 收尾待办
> 无

### 待处理遗留

- [live2d] 37 个模型 Idle 组大小写不匹配（实际为 `idle`，空闲动作不播放）：
  跑 scan_live2d_models.py 生成根目录 live2d_scan_report.md 查看，用哪个补哪个（加 Idle 别名组）
- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [环境] pytest 未入 pyproject [project.optional-dependencies]：加 test 组后
  frontend-minimal 测试可 venv 直跑（现需 uv run --with pytest）；仓库杂务，与前端无关
- [stage5] launcher ruff format 全文件重排单独立项：stage5 曾尝试对
  launcher/OpenLLMVTuber_GUI.py 跑 format，产生 +332/-181 纯排版 diff
  （该文件历史样式从未 format 过），已回退保持最小功能 diff；
  触发时机：作为独立的排版工程提交，不混入功能阶段
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [stage6] characters/en_nuke_debate.yaml 的 `live2d_model_name: "shizuku-local"`
  本就与登记名不符；stage6 删除 shizuku 后目录也不存在（删前删后该角色都无模型），
  不影响启动。建议删除该示例角色或改指向有效模型，待裁决
- [stage6] 既有失败基线：`test_live2d_model_switch.py::test_resolver_runtime_allowlist`
  报 `ModuleNotFoundError: No module named 'prompts'`（测试导入路径问题，非代码回归）；
  已用 stash 基线比对确认与 stage6 改动无关，勿当回归处理
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

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
