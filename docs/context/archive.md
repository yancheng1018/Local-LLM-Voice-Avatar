# 历史归档（已完成记录）

> 压缩格式：日期 + 做了什么 + 留下的契约/文件。过程性叙述不复述，事实以代码与 git log 为准。

## 2026-09-29 research存量提炼 distill 系列（b1~b3 全验收）
- b1 删 6 份大纲脚手架+5 成品溯源行改写；b2 触摸/热区及清理类 3 删+spec-l2dsu v1/v2 合并+repo-maintenance 订正；b3 动作链条域结论提炼入 minimal-frontend-live2d.md（已裁不修红线+站点未取证残留）+4 处置行+口径从句；域内 research/manual 文件全保留作证据链

## 2026-09-18 Live2D 动作链条 research2_v2 + research3（type12 裁决 + tap 抬起命中回退）
- 依 temp_spec_live2d动作链条-research2.md（v1）+ _v2.md + _research3.md 实施（原文已删）。
  v1→v2 验收失败根因：方案A 假设「idle 循环由 motion3.json Meta.Loop 数据标志驱动」——库
  解析 Loop 但无消费者（cubism4.es.js _isLoop 默认 false），须 playIdleOnce 后显式
  enableIdleLoop（setIsLoop(true)），且仅 idle 路径防循环外溢；v2「自愈分层」前提又被
  research3 F3/F8 证伪（drag4/5 亦 mode-1 每帧钉死，无自愈层），分层表述废止订正
- 落地：type12 全局动作裁决（值源=ParamDriver 内部值、半开区间 lo<v<=hi、优先 ATA 名单）；
  默认热区伪规则过闸（只受约束不产生约束）；idle 循环方案A′；touch.json 清库 2 例
  （shengluyisi_4/chaijun_4 rules=[]，守护 test_l2d_touch_data.py CLEARED）；tap 抬起
  命中回退（emitInteraction 增 pressedZone，修复 drag3 卡中值/type12 门死锁/drag4-5
  热区不出现三连锁——根因 pointerup 重命中失配→poke 丢失，值→几何自反馈所致）
- 新增回归：test_l2d_type12_gate / test_l2d_release_fallback / test_l2d_core_value_readout；
  全量 170 全绿 + npm build 通过
- 契约候选终判（五问①均模块级降级）：R2-a/b/c/d 定案为模块约定入
  minimal-frontend-live2d.md；R2-e 分层半句维持废止、「mode-1 不归零」并入 R2-a 域；
  research3 候选（抬起回退语义）驳回——测试逐字锚定自守
- 验收（2026-09-18 用户宣告通过）：guanghui_9 点 drag3 收敛 10/type12 门/drag4-5 可拖/
  复位回基线 + §7-4 回归四步全过
- 过程文档清理：temp_spec/impl_report ×6 删除；research_live2d动作链条-research2/3.md
  与 research_plan ×2 留存（取证链，模块文档引用）

## 2026-09-18 Live2D 动作链条修正 阶段B（live2d动作链条修正2 + v2 修复轮）
- 依 temp_spec_live2d动作链条修正2.md（v1）+ _v2.md 实施：TouchChain 链步状态机
  （action_list (si+1)%len 循环推进/ATA active_list 覆盖/形态A 目标 idle 查表/steps
  持久化）；新建 `l2d_params_relations.ts` 关系预设纯函数层（type104=idleIndex 匹配
  每帧写 target??start??0；type103=relation_value[链步]，v2 修正蛇形字段错配——v1
  规格伪代码写驼峰 relationValue 致生产不生效+夹具同名全绿假象）；ParamDriver
  syncChainState+复位队列（revertIdleIndex 1|'1' / revertActionIndex=1 步差）+预设
  覆写+载体规则 carrier；l2d.ts/main.ts 接线 chainStepIndex
- 测试：新增 test_l2d_touch_chain_stepping.py / test_l2d_param_relations.py（13 用例，
  夹具与真实数据同形）；stage2 两处语义随迁；param_hook/clamp_chain esbuild --bundle
  修复。全量 152 全绿
- 契约沉淀（均降级模块文档）：B2-B4 语义入 spec-l2d-touch-engine.md §5/§7（含蛇形
  字段数据事实）；B5（esbuild 必 --bundle）与「夹具字段名与真实数据同形」入
  minimal-frontend-foundation.md；l2d_params.ts 行数上限 220→390 订正
- 验收（2026-09-18 用户宣告通过）：feiteliedadi_3 F2 维持语义、aerbien_3 TouchDrag17
  死区激活、wuqi_3/xinnong_6 回归、guandao_3 恒表[0]（清缓存后确认——hash 资产更新
  依赖 index.html 不被缓存，验收前清缓存）
- 转 research（[live2d动作链条-research2]，见 current-work.md）：guanghui_9 touchhead
  门控/结束后无热区卡死、idle 不循环静置冻结、shengluyisi_4/5 moc3 无 TouchDrag 绘画件
- temp_spec/impl_report（v1+v2）已删除；research_live2d动作链条修正.md 等研究报告留存

## 2026-09-16 遗留清理第一批（leftover-triage_stage1，A 类机械项）
- 按 research_leftover-triage.md §5.1/§5.3 清 4 条：新增 `fix_live2d_idle_groups.py`
  （幂等补 model3.json 的大小写精确 Idle 别名组，只在需新增时写回并留 .bak；实测修 37 模型，
  mao_pro/shizuku 已合规未动）+ 补 pytest 入 pyproject `test` 组 + 删 `characters/en_nuke_debate.yaml`
  （模型名无效且无引用）+ 新建 `tests/test_live2d_model_data.py`（在用模型必须含非空精确 Idle 组）
- 留下：模型入库脚本链 = `scan_live2d_models.py` → `fix_live2d_idle_groups.py` → `fit_live2d_scale.py`
  （轻量版工作流；launcher 内嵌检测仍为遗留）；规格编写规范新增 3 条（∩ 口径写明具体名单 /
  幂等判据只锚可确定项 / 脚本行数预检留输出余量），见 spec-writing.md §6-8
- 原 temp_spec_leftover-triage*.md 与 impl_report_leftover-triage_stage1.md 已删除；
  研究报告 research_leftover-triage.md 后于 distill-b2 删除（A/C 类已执行、D 类裁决已被后续阶段吸收）

## 2026-09-10 综合会话（GUI v2.0~v2.4 与遗留修复）
- GUI 启动器迭代至 v2.4：模型页、角色编辑器、贴图预览、voices/ 声音模型体系、Live2D 导入（自动登记 model_dict.json）、启动后自动开浏览器；另做 streaming_mode 注解等遗留修复
- 留下：`启动器.bat`（须保持 GBK 编码、不加 chcp）；conf.yaml `ref_audio_path` 指向 `voices/<声音名>/ref.wav`；某 Cubism 2.1 模型因前端不支持而弃用并移出 model_dict.json，其余 41 条 url 核对有效

## 2026-09-10 Live2D 动作表现优化
- 为 xinnong_6 / mao_pro 补 Idle / Talk 动作组与 tapMotions（默认角色从完全静止变为有待机/说话/点击反应）；修正 mao_pro emotionMap 三处错误映射（fear/sadness 原指开心、anger 原指闭眼）并扩至 50 键；重写 live2d_expression_prompt.txt（每句最多一个关键词且放句首）
- 留下：`<think>` 内句子不提取表情、显示文本剔除 [关键词]（transformers.py）；`scan_live2d_models.py` + `live2d_scan_report.md`；非显而易见结论：41 个模型中 37 个 Idle/Talk 组大小写不匹配，mao_pro 是唯一有 HitAreas 的模型，xinnong_6 无表情文件（情绪关键词对它天然无效）

## 2026-09-11 尺寸自适应与关键词显示
- 新增 `fit_live2d_scale.py`：按 moc3 CanvasInfo（u32@0x44）重算全部 41 个模型 kScale，游戏系模型（逻辑画布高 > 5）追加 ×1.5 目测倍率；emotionMap 为空时跳过表情提示词（防 LLM 编造关键词），显示文本正则兜底剔除剩余方括号 token（与 TTS 侧 ignore_brackets 对齐）
- 留下：moc3 顶点自动求包围盒因 keyform 间接索引不可行（勿重试）；mao_pro kScale 保持 0.5（标定自洽）；TTS 重启后首句 65s 属 GPT-SoVITS 冷启动非回归，首音频延迟高也与 `faster_first_response=false` 有关——复现时可加启动预热并改 true（用户暂不改）

## 2026-09-13 上下文文件重构
- 将 ZCODE_CONTEXT.md（约 990 行）拆分为 AGENTS.md（77 行）+ docs/context/ 下 7 个模块文件，实现按需加载
- 根文件保留概述、端口、高频命令、硬性契约速查、索引表、维护规则
- 索引表按任务场景指向模块文件；新增 minimal-frontend.md 收录极简前端设计
- 原文件已删除，备份保留为 ZCODE_CONTEXT.md.bak
## 2026-09-14 合并 Live2D 触摸引擎规格书
- 将 temp_spec_stage1~6 合并为 docs/context/spec-l2d-touch-engine.md
- 固化偏离站点项 D1~D3、明确不做清单、遗留 C4/C6
- 删除已合并的 temp_spec_stage1~6

## 2026-09-14 仓库整理与上游切割（git_stage1~3）
- 三阶段：文件归位与索引整理 → 与上游切割 → 收尾清理（lint/悬空引用/残留）
- 合并 temp_spec_git_stage1~3 与 impl_report_git_stage1~3 为 docs/context/spec-git-reorganize.md，原文删除
- 留下：无 remote、`push.default = nothing`、ruff 归零；`config_templates/` 确认为运行时依赖；
  `frontend/` 忽略但保磁盘（`server.py:172` 无守卫，删前须补）；`Temp/` 逆向产物确认不可找回（见 docs/assets/README.md）

## 2026-09-15 拆分 minimal-frontend.md
- 259 行超 200 上限（/split-module），按域拆为 4 分册 + 总入口索引：minimal-frontend-foundation.md（阶段一工程/协议 + 阶段三历史/口型，81 行）、minimal-frontend-live2d.md（阶段四手势/目光/心跳 + stage2 参数引擎 + stage3 复位，110 行）、minimal-frontend-spine.md（阶段二，47 行）、minimal-frontend-model-switch.md（stage4，20 行），总入口 29 行；原内容逐字保留
- 留下：AGENTS.md 索引表 1 行扩为 5 行；distill_draft_minimal-frontend.md 受阻候选 #3/#6/#7/#8/#10/#14/#15 解锁待入档（落点 model-switch/foundation/live2d）；research_plan_live2d.md:47、spec-l2d-touch-engine.md:21 的 minimal-frontend.md 行号指针已漂移（未改，遗留候选）；遗留节「mao_pro 表情验收未完成」与阶段四「验收完成」条目存在新旧矛盾，保留原文待清理
