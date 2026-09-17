## 当前阶段

### 阶段状态
> **live2d动作链条修正2（含 v2 修复轮）已完成并验收通过（2026-09-18 用户宣告）**。
> 范围：阶段 B——type104 idle 预设 + revertIdleIndex/revertActionIndex 复位 + 形态A 查表
> 修正 + action_list 链步（循环步进/active_list 覆盖/type103 链步语义）+ spec §10 边界修订；
> v2 修正 type103 蛇形 relation_value 字段错配。全量 152 全绿；验收通过项：feiteliedadi_3
> F2、aerbien_3 死区激活、wuqi_3/xinnong_6 回归、guandao_3 恒表[0]（清缓存后确认）。
> 未过项转 research（见待处理遗留 [live2d动作链条-research2]）。归档：archive.md 2026-09-18 条目。

### 收尾待办
> 无（live2d动作链条修正2 收尾已执行完毕：git 提交、契约/文档订正入模块文档、
> temp_spec/impl_report 过程文档清理——2026-09-18，详见 archive.md）

### 待处理遗留

- [live2d动作链条-research2] 聚焦研究立项候选（live2d动作链条修正2 验收分诊沉淀，
  2026-09-18；细节见 archive.md 2026-09-18 条目）：①站点 touchhead 场景语义——动作
  播放期参数规则门控（嫌疑=type12 num 监听：guanghui_9 23703161 监听
  touch_drag3∈[0.01,10]+大 ignore 名单+limitTime 0.1）、动作结束后的 idle/热区恢复
  （本地实测：结束后无热区+模型卡死+drag3 滞留 2.61）；②idle 生命周期——本地 idle
  不循环（playIdleOnce，stage1b §0.4；pixi 官方 idle 随机已禁用）致清缓存静置数秒后
  动态停止（aerbien_3 实测，视线跟随仍正常）vs 站点行为对照与循环化裁决；③
  shengluyisi_4/5 热区定位——moc3 零 TouchDrag 绘画件（仅 TouchBody/Head/Special），
  touch.json 的 TouchDrag14 等规则不可达，站点如何为无对应绘画件的规则定热区/模型
  版本差异；④验收仪表补强——调试叠加层补 core 写入值列（与 ParamDriver 内部值区分，
  本阶段两次验收栽在仪表上；已有控制台句柄 window.__vtuber 可临时读 core）
- [live2d动作链条] 阶段 B 已完成并验收（2026-09-18，归档见 archive.md）；剩余延后项：
  阶段 B 尾巴——type2+target 非 circle 点按写参（v2 §3.1 ⑧，811 条 type2 爆炸半径大，
  F2 验收不足时另立）；阶段 C——type12 裁决、type9/11/15 条件门槛、冷却先记（被拒也吃
  冷却）、dynamicFlag 可见性、tips 显隐、type5/10/13、参数权威层全量化（前置：研究
  §8-1 站点面板↔模型双路径未取证）；链循环 vs D2 取舍待权威层阶段一并裁决。
  S3/F1 已裁不修（站点同款非缺陷，研究 §6.4）。依据：research_live2d动作链条修正.md §7/§8
- [spec-writing] 检查项补充候选（live2d动作链条修正2 impl_report §6）：既有运行时测试的
  esbuild 编译方式（bundle 与否）入断言盘点；规格代码块行数逐块累加替代估算；测试叙事
  与实现先自演（首同步守卫/次帧可见时序/save 触发方）
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
