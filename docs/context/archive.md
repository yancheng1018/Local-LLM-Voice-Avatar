# 历史归档（已完成记录）

> 压缩格式：日期 + 做了什么 + 留下的契约/文件。过程性叙述不复述，事实以代码与 git log 为准。

## 2026-09-29 research存量提炼 distill 系列（b1~b3 全验收）
- b1 删 6 份大纲脚手架+5 成品溯源行改写；b2 触摸/热区及清理类 3 删+spec-l2dsu v1/v2 合并+repo-maintenance 订正；b3 动作链条域结论提炼入 minimal-frontend-live2d.md（已裁不修红线+站点未取证残留）+4 处置行+口径从句；域内 research/manual 文件全保留作证据链
- github-p0-privacy 批（同日）：42 项私人资产出索引保磁盘；voices 声音卡+launcher_config.json+舰船缓存 34 项 filter-repo 抹历史；mailmap 全量改 `yancheng1018 <55277749+yancheng1018@users.noreply.github.com>`（上游署名 1 条保留）；B 档私有名脱敏 7 文件；索引守卫 tests/test_repo_privacy_guard.py 入库。仓库外备份：../pre-scrub-backup.bundle、../pre-namescrub-backup.bundle
- github-p0-decouple 批（同日）：GUI:573 占位文案通用化；收录 GPT-SoVITS v2pro-20250604 自建启动脚本至 external/gpt_sovits/（bat/py+README，仅 lint 修正无逻辑改动）；私有声音名 grep 守卫落位（本地名单 tests/private_names.local.txt，缺失 skip）；本任务线开发文档（research 2 份+finalize_exec）出库保护落地；全量 166 passed

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

> 上传github前准备路线图（2026-09-29~09-30，11 阶段全部验收）：p0-隐私出库+历史抹除+mailmap → p0-占位通用化+GSV脚本收录 → p0-默认测试角色 → p1-改名四联动+v1.0.0+README → p1-旧前端退役+新克隆冒烟 → p2-precheck-a 上传物与文档 → b 后端清理+Live2D Core → c 结构归置 → d GSV适配器+external退役 → e AGENTS治理 → p2-release 建仓私有+push v1-release:main+tag v1.0.0+Release（暂缓公开走 A 线）

## 2026-10-01 存量收尾清单归档销毁（workflow-audit 批次3）

> 机制补账：收尾清单（finalize_exec_*，新命名 {{stage}}.close.md）执行完毕后压缩归档并自删
> （research_工作流复审.md 裁决）；本批为存量 13 份一次性清理，彼时命令尚无销毁流程。
> 各阶段业务结论已由上方对应日期节与 git log 承载，此处只登记清单执行终态：

- distill-b1/b2/b3（09-29）：12 文件入账 commit 64e4e3f；24 文件入账 commit 77a5c5d；
  current-work 终态写入（research存量提炼线收口）
- github-p0-characters / p0-decouple / p0-privacy / p1-facade_v2（09-29）：产物删除；
  空名单防御+定向守卫 2 passed；审查状态同步 commit 3c85a3b；测试 docstring 去规格引用
- github-p2-precheck-a / b（09-30）：repo-maintenance 施工习惯补记；precheck-c（09-30）：
  三跑终成（首跑条目矛盾经修订、二跑 .zcodeignore 文件集差异、三跑 7 条全过
  commit b588ae5 + cb6d2e1）；precheck-d（09-30）：7 条全过 commit ff07e99 + 36a4322；
  precheck-e（09-30）：AGENTS 治理主提交 2f9e8a4
- github-p2-release（09-30）：7 条全过（条目 7 首跑停止、补裁后成功 commit a706a3a）；
  路线图压缩行已入本文件

## 2026-10-01 工作流体系优化（workflow-audit，对话式执行+review-spec 审查收尾）

- 用户级（~/.zcode/）：AGENTS.md 增「命令公共约定」（模块定位/文档目录/查阅规则/停止条件/
  阶段文件字典与生命周期出口）与「状态入口结构规范」两节（38→75 行）；第 5 条例外改 B 案
  口径、第 10 条阶段产物新命名。命令 9→8：删 plan-tests（职责并 plan-feature）；删
  split-module（B 案，步骤下沉 repo-maintenance「模块文档拆分」节）；新增 plan-roadmap
  （方向层：探讨五要素/入册逐条点头/调整留痕/版本收口提醒）；plan-feature 加 roadmap 出身闸
  +对账 8 条归并 4 组；review-spec 加 roadmap 回写/版本号裁决（uv version --bump，版本目标集
  清空才 bump）/清单自删尾条目/组级大纲处置；plan-research+research-doc 组研究编组（组级
  大纲兼进度表，末位完成者删）；implement-spec/replan 补 stage 推导（.vN 去后缀）；参数全线
  去 module/task-description（AI 按项目索引自定位，≤3 文档）
- 阶段文件新命名：{{stage}}.spec（.vN 修订版）/.fix（覆盖式单份）/.report/.close +
  research.{{topic}}(.outline)；存量旧名不迁移，处置按旧名定位
- 项目侧：roadmap.md 建册（backlog 8 条=README 2+遗留待立项 6，均「构想」，升格走
  /plan-roadmap）；AGENTS.md 索引+绑定节；repo-maintenance 下沉拆分步骤+阶段文件口径+
  doc-record 引用订正；spec-writing 适用范围行换新命名（审查补漏）；13 份存量 finalize_exec
  压缩归档后删除（见上方同日节）
- 决策记录：split-module B 案（用户裁决 2026-10-01）；规格书=本阶段 research_工作流复审.md
  v2，机制本体已全量落于命令与两级 AGENTS.md，原文随本阶段删除
