## 当前阶段

### 阶段状态
> **live2d-hotzone-touch-r2**：收回 D1/D3 透明剔除 + G/T 状态序修正 + 链步进 action
> 优先（依据 research_live2d-hotzone-touch-r2.md：根因 C1/C2/C3，数据层 A/B 已排除）
> （规划完成，待弱模型实施；规格书 temp_spec_live2d-hotzone-touch-r2.md）。
> 前序：阶段一~六已验收提交（4bccd87）；stage7 审查通过但**人工验收未通过**（核心问题
> 未解决，round1 根因被 r2 推翻），不标记完成，收尾挂起见下方「收尾待办」。
> **test-lifecycle**：已完成并验收通过（2026-09-16）。纯文档任务：4 个用户级命令文件
> 接入测试资产处置/五问终判机制 + [test-sweep] 遗留登记；机制线无既定下一阶段，
> 主线仍为 r2。

### 收尾待办
> 最终人工验收通过后，先经 /finalize 重核再执行；回退期间原样保留、不得执行。
- [stage7] git 统一提交：add 清单 = frontend-minimal 的 l2d.ts / l2d_touch_debug.ts /
  l2d_touch_debug_helpers.ts / tests/test_l2d_hotzone_stage7.py + docs/context 的
  repo-maintenance.md（MSYS 伪 0 施工习惯一条，混入 stage7 改动；current-work.md
  已随 test-lifecycle 收尾提交，移出清单）；
  commit 草稿：`feat(frontend-minimal): stage7 热区叠加层可读性与可交互性提示`
  （拆 helpers 纯函数模块 247→220 行；候选 A 'empty' 不作前缀 / B 非交互标签降透明度 /
  C 无命中点击 1.2s 轻提示；新增 8 用例，回归 41 用例通过）
- [stage7] 规格书处置：temp_spec_stage7.md / impl_report_stage7.md 暂缓——r2 已推翻
  round1 部分结论且 r2 阶段将修订 stage7 的 T 区呈现语义，待 r2 验收后一并裁决
  （压缩并入 minimal-frontend-live2d.md 或删除）；round1/r2 四份 research 文件与
  l2dsu抓取模型说明.md（round1 报告已被 r2 §8 部分推翻，原文未改）的归档去向
  （并入 spec-l2d-touch-engine / 交 /distill-research）同批裁决
- [stage7] 契约候选：l2d_touch_debug.ts 220 行例外入档（拟 minimal-frontend-live2d.md，
  参照 l2d_params.ts 先例）；r2 规格已按净减设计，若 r2 实现后 ≤200 本条自然失效
- [stage7] 实机验收 §6 未执行：人工复核已否定（核心问题未解决，根因转 r2 处理），
  由 r2 验收口径取代；stage7 不标记完成

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
- [hotzone-touch] round1 §7 遗留候选收敛（r2 研究已吸收/更新部分）：仍待裁决 =
  type 9/10/11 未实现清单入档、OE_TYPES 含 7 vs dispatch 拒 6/7、empty 占比差异
  （游戏数据生成侧）；C6 口径已经 r2 §8-6 二次修正（G=idleIndex 门槛锁可点性、
  C6=enable 白名单锁播放，两者并存）；findChainRule 匹配面一项已吸收进 r2 规格 §2.3
- [hotzone-touch-r2] r2 §9 疑点待取证（需强模型重建站点混淆上下文）：forEach vs
  择一裁决、C6 resolve 时序（先播后建白名单？）、站点 idleIndex=4 残留推进路径、
  guanghui 点名 5 区来源未复现；type12/tips 新 schema（idleBlackList/animWhiteList）
  消费与否待裁决
- [test-sweep] tests/ 既有资产盘点：12 个带 stage/debug/r2 痕迹的已跟踪测试文件
  （test_l2d_hotzone_stage2~7、_r2、test_stage6_bugfix、test_debug_panel*、
  debug_panel_runtime.test.mjs、test_touch_debug_overlay）待强模型专项按五问框架
  集中裁决（转正改名/合并/删除）；机制落地后新任务不再积累

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
