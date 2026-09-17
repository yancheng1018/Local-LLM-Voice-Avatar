# 研究大纲 · live2d动作链条-research2

> /plan-research 产物（2026-09-18）。来源：current-work.md 待处理遗留 [live2d动作链条-research2]
> （live2d动作链条修正2 验收分诊沉淀）+ 按用户指示吸收强相关遗留项（见 §5 吸收边界）。
> 前置基线：阶段 0/A/B + v2 修复轮已完成并验收（2026-09-18），全量 152 测试全绿。
> 本文件只规划不实现；执行档位 /research-doc（弱模型），输出文档建议名
> `research_live2d动作链条-research2.md`。

## 1. 研究问题定义

l2d.su 精确引擎在「动作播放期门控（type12）、动作结束后恢复、idle 生命周期、无绘画件热区」
四个场景下的真实语义是什么，本地实现（阶段 0/A/B 后）与它的差距各由什么根因造成，
以及验收仪表需补什么才能让这些差距可观测。

## 2. 需要回答的子问题

### Q1 站点「动作播放期」参数规则门控（type12 num 监听）的语义与生效路径
- 对应遗留①前半；吸收 [live2d动作链条]阶段C-8（type12 裁决）与 [hotzone-arch]②
  （type12 新 schema 消费与否、guanghui 点名 5 区来源未复现）。
- guanghui_9 规则 23703161（actionTrigger `{type:12, num:[0.01,10], parameter:"touch_drag3"}`
  ——本轮已核验数据）在什么时机、读**哪个参数值源**做判定；把 15 个动作加入 ignore 的
  确切效果边界（拒绝触发 or 拒绝播放 or 两者）。
- 关联前研究 §8-1「站点面板↔模型双路径」疑点：type12 读的是目标表
  （live2dOfficialParameterTargets）还是模型实际参数值——这同时是后续阶段C
  参数权威层全量化的前置取证。
- guanghui「点名 5 区」现象是否即 type12 关联行为（hotzone-arch ② 未复现项，一并取证）。

### Q2 站点「动作结束后」的恢复语义与本端卡死根因
- 对应遗留①后半：本地实测 guanghui_9 touchhead 播放结束后「无热区 + 模型卡死 +
  drag3 滞留 2.61」。
- 站点动作结束后的完整恢复链：热区重算（tips 显隐 idleBlackList/animWhiteList——
  research §3.5「热区随状态增减」的正式机制）、idle 回放、受管参数复位
  （revertIdleIndex 复位队列——阶段B已实现，须解释为何本场景不生效或本就不该生效）。
- 结论须区分三种可能：「数据/规则本该如此」vs「本地实现缺口」vs「阶段B复位语义边界
  （spec §10 修订后）」。

### Q3 idle 生命周期对照与循环化裁决依据
- 对应遗留②：本地 playIdleOnce 单发（l2d.ts:700 加载播一次、:766 动作结束回放一次，
  stage1b §0.4 契约；库 idleMotionGroup='__no_auto_idle__' 已禁用，l2d.ts:690）→
  清缓存静置数秒后动态全停（aerbien_3 实测，视线跟随仍正常）。
- 站点 idle 驱动策略取证：循环 / 定时 / 事件驱动 / 条件触发；站点同模型静置行为对照。
- 输出循环化候选方案与副作用评估（对 152 测试、localStorage 链状态、动作结束后回放的
  交互）；只给依据，不裁决。

### Q4 无 TouchDrag 绘画件模型的热区可达性
- 对应遗留③：shengluyisi_4/5（touch.json 各 54 规则、其中 34 条 TouchDrag——本轮已核验）
  moc3 零 TouchDrag 绘画件（仅 TouchBody/Head/Special），TouchDrag14 等规则本地不可达。
- 站点如何为无对应绘画件的规则定热区：同为不可达（数据冗余）、或经 name/id 命中而非
  drawAbleName（spec-l2dsu-engine.md §5 命中三源）、或站点模型版本不同（含绘画件）。
- ⚠️ 已知数据事实：阶段A 普查记录 **shengluyisi_4 站点无规则**（旧数据保留未换，
  前研究 §6.1-3），shengluyisi_5 不在该清单——两者数据来源年代可能不同，须先核数据来源
  再谈行为对照。模型版本差异核查沿用阶段A 契约 A1（prefab 精确匹配 + rules 非空）。

### Q5 验收仪表补强的最小方案
- 对应遗留④：调试叠加层补「core 写入值」列，与 ParamDriver 内部值区分
  （本阶段两次验收栽在仪表；现有 window.__vtuber 控制台句柄可临时读 core）。
- 只出设计方案：数据通路（core.getParameterValueById 帧采样 vs ParamDriver 镜像值）、
  列布局、采样与刷新频率；不实现。

## 3. 子问题 → 资料/代码位置

| 子问题 | 站点侧资料 | 本地代码/数据 | 实测/复现 |
|---|---|---|---|
| Q1 type12 门控 | spec-l2dsu-engine.md §1（26 字段表）；spec-l2dsu-engine-v2.md（live2DExtendActionDecision 完整逆向）；research_live2d动作链条修正.md §3.2/§8-1 | l2d_touch.ts（actionAllowed/dispatch 门链；rg 已确认 type12 零实现）；live2d-models/guanghui_9/touch.json 规则 23703161 | 站点 chunk 下钻（须 User-Agent + Referer https://l2d.su/ 否则 403）；本地复现：touch_drag3>0.01 时点 touchhead 应被拒而未拒 |
| Q2 结束后恢复 | spec-l2dsu-engine.md §3/§6（打断/序列号守卫/复位）；research_live2d动作链条修正.md §3.3/§3.5 | l2d_touch.ts（applyActive + 复位队列，阶段B实现）；l2d.ts（热区重扫/可见性门槛）；l2d_params_relations.ts | guanghui_9 清 localStorage → 点 touchhead → 动作结束后观察叠加层 + window.__vtuber 读 drag3 与热区状态 |
| Q3 idle 生命周期 | spec-l2dsu-engine-v2.md（检索站点 idle 驱动路径：idle/Index/定时器关键词） | l2d.ts:689-700/:766（行号须 rg 复核）；minimal-frontend-live2d.md（stage1b §0.4 契约原文） | aerbien_3 清缓存静置复测（动态停止时刻、idleIndex、视线跟随）；站点同模型静置对照 |
| Q4 无绘画件热区 | spec-l2dsu-engine.md §5（命中三源 name/id/drawAbleName、mode2 不靠区域）；research_live2d动作链条修正.md §5.1（数据错配方法论）；工具 docs/assets/su_survey_touch_json.py --fetch | shengluyisi_4/5 touch.json（34 条 TouchDrag 规则清单）；moc3 绘画件清单（rg 既有扫描脚本/报告 live2d_scan_report.md） | 站点 shengluyisi 页面取证：当前 prefab/皮肤与热区是否含 TouchDrag14；必要时下载站点版模型比对绘画件 |
| Q5 仪表补强 | —（纯本地工程项） | l2d_touch_debug.ts / l2d_touch_debug_helpers.ts / l2d_debug_panel.ts（stage7 叠加层）；window.__vtuber 句柄定义处（rg 锚定）；l2d_params.ts（ParamDriver 值语义） | 复用 Q2 复现流程，验证方案能区分「内部值正常 / 模型读数失效」两类状态 |

> ⚠️ 行号时效：research_live2d动作链条修正.md §4 行号表基于阶段0前代码，已过时——
> 研究中所有行号引用必须重新 rg 锚定（阶段0/A/B 已改 l2d.ts / l2d_params.ts /
> l2d_touch.ts 并新增 l2d_params_relations.ts）。

## 4. 输出文档结构（research_live2d动作链条-research2.md）

1. 结论速览
2. 症状与复现基线（本轮三症状 + 数据事实核验记录）
3. 站点行为基准取证（3.1 type12 门控与参数值源；3.2 动作结束恢复链；3.3 idle 驱动策略；
   3.4 无绘画件热区）
4. 本地实现现状梳理（重新锚定行号；与站点结构差表）
5. 逐问题归因与对照（Q1~Q4 各一节，标注置信度与证据级 A/B/C）
6. 修正方向候选（含契约候选；Q5 仪表方案单列一节）
7. 验收协议（证伪方法）
8. 未决疑点与需人工协助清单

## 5. 已知约束和边界

- **只读研究**：不改源码、不改测试；Q5 也只出方案。实施另行立项。
- **已定案不重开**：F1/S3 站点同款不修（前研究 §6.4）；不放宽 opacity/门槛判定（D1 教训）。
- **基线为阶段 0/A/B 后代码**：参数写入挂点 afterMotionUpdate、type103/104 关系预设、
  action_list 循环链步、revertIdleIndex/revertActionIndex 复位、库 idle 自动播放禁用
  均已落地；引用旧报告结论前先核实现状。
- **站点取证约束**：请求须带 User-Agent + Referer https://l2d.su/（否则 403）；
  Temp/ 逆向产物不可找回（docs/assets/README.md），chunk 反查须重新下载；
  以源码/数据为准，不依赖截图记忆。
- **裁决权保留**：idle 循环化、D2（链循环 vs 60s 冷却）、参数权威层全量化路径——
  研究只给证据与方案候选，交人工裁决。
- **范围吸收边界**：纳入 [live2d动作链条]阶段C 的 type12/tips 前置取证与前研究 §8-1
  双路径、[hotzone-arch]② 的 type12/tips schema 与 guanghui 5 区；阶段C 其余项
  （type9/11/15、type5/10/13、冷却先记、dynamicFlag、D4~D7）与其余遗留
  （spec-writing 候选、repo-format、test-sweep、emotionMap、stage6、launcher 集成）
  不纳入本轮。
- **硬性契约**：动 Live2D 前必读 docs/context/live2d.md；研究报告落 docs/context/；
  新契约只列「契约候选」，经确认后入档。
