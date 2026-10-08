# 项目级 Roadmap

> 单一事实源：方向、优先级、版本目标集。条目状态：构想 / 已立项 / 进行中(关联 stage) /
> 已完成(日期) / 已取消(原因)。README Roadmap 是本文件的对外粗粒度投影。
> 与「待处理遗留」单向通道：遗留正式立项后升格入册并从遗留移除（升格走 /plan-roadmap）。

## 版本目标集

版本收口判据：目标集内条目全部终态 → 对应阶段 /review-spec 收尾时裁决 `uv version --bump`（是否 tag 由用户定）。

### v1.0.1 · github-p3-public（转 public 收口，目标 2026-10-08）

> 来源：2026-10-07 转公开只读审查（B1-B6/基线 1-6 逐项核实，证据见当日会话记录）。
> 依赖：#3/#4 原被网络阻塞——2026-10-08 实测 github.com 间歇可通（同命令 ls-remote 一败一成），#3 已开工；#2 已定稿 A 口径（仅出库+归档清单主动声明，不做 rewrite），与 #3 无顺序耦合。

| # | 条目 | 状态 | 方向结论要点 | 来源 |
|---|------|------|-------------|------|
| 1 | 公开克隆修复批：test_live2d_model_data 加公开克隆 skip + model_dict.json 精简为 mao_pro + 调试残留清理（vad/silero.py:205 print、l2d.ts:718 / fit_live2d_scale.py:5 注释私有模型名） | 已完成（2026-10-07） | 克隆模拟实测 in_use=['mao_pro']，known 断言缺 5 私有模型必红；model_dict 42 条含 41 舰船死条目；skip 参照 test_characters_manifest.py:84 现成模式；修完跑全量 195；2026-10-07 补盘克隆红面另含 test_l2d_touch_data 全文件/test_l2d_circle_dial.test_xinnong_data 无守卫直读本机数据，并入本阶段 S10 一并 skip 化（规划复盘发现，非审查遗漏外的扩项） | 审查 B1/B3/B6 |
| 2 | l2d.su JS 快照出库：git rm docs/assets/su_modelRuntime-BDk3g7Pb.js + su_modelRuntime_strings.json + ignore 条目 + docs/assets/README.md 归档清单注明出库原因与重抓路径 | 已完成（2026-10-08） | 全库唯一「别人的表达」类内容（站点引擎 JS 原样快照 202KB+衍生解码表；引擎复刻代码与逆向结论文档系原创表达，保留）；历史清理已裁决不做 rewrite（2026-10-07 用户拍板 A 口径：原告现实性≈0、JS 可按抓取说明随时重采、保 10-08 时间线；以归档清单主动声明替代，残余风险中和），与 #3 无顺序耦合 | 审查 B2 |
| 3 | 发布完整性：提交 p3-public-a/b 存量产出与簿记 + push v1-release + 确认 v1.0.0 tag 在远程 | 已完成（2026-10-08） | origin 无 v1-release 跟踪引用、本地领先 origin/main 4 提交（+7189b4f）；待提交面 9 文件（p3-b 实施 6+簿记 3，archive.md:142 登记归并本条）；v1.0.0 tag 规划时 ls-remote 实证已在远程且与本地一致（2d8780c/acf9ad1），S6 转纯校验；push 须用户确认 | 审查 B4/基线1 |
| 4 | 干净目录实测 15 分钟快速开始（全新克隆 uv sync→npm build→模板 conf→对话） | 已完成（2026-10-08） | docs 无历史实测记录；git archive 模拟已暴露 #1 必红，修完 #1/#2 后一次通过；依赖网络（拉包）；功能一次通过；「约15分钟」弱网直连不成立（pull 24.5min+ASR 999MB 瓶颈）；衍生 #7 微修复批 | 审查 基线4 |
| 5 | 切 public + S9 公开态验证（GitHub Settings 切 Public，三项 curl：首页 200 / releases 200 / releases/tag/v1.0.0 页含 v1.0.0） | 已立项 | 账号操作无法自动化（人工项）；切公开后即跑。切公开前置门禁（2026-10-08 疑点裁决）：push v1-release（本地领先 2 纯 docs 提交 a91e2c8/cf03a58，fast-forward）+ main 停旧处置（推平或切默认分支，届时二选一） | 遗留 [github-p2-release] S9 升格 |
| 6 | README 增补「相对上游的改动总览」10 项浓缩表 | 已完成（2026-10-09） | 现 README 无该节（仅核心特性 6 条+Roadmap 3 条）；素材在 docs/context 各册浓缩即可。触摸引擎三层方案（2026-10-07 用户拍板）：表内占 2 行（触摸规则引擎/手势+参数驱动）+ 核心特性现有 bullet 补半句适配口径（Azur Lane 类 touch.json 模型解锁全部特性、mao_pro 走启发式兜底）+ 不独立成节，主角位留给 #9 演示 GIF | 审查 基线3 |
| 7 | 微修复批：.gitattributes 加 `static/libs/* -text` 根治新克隆 CRLF 测试红（test_live2d_core_vendored 字节断言 206492 vs 检出 206500）；可选子项 `*.bat text eol=crlf` 待拍板 | 已完成（2026-10-08） | #1 修复盲区补丁：git archive 模拟不走 smudge 测不出、主仓库工作树 LF 恒绿掩盖；根修=属性层，现有字节断言原样保留作回归守卫（不碰测试代码）；复验用现成 LLMVA-clean-clone-test pull 后重检出 | 实测 p3-public-d S3.5 发现，2026-10-08 用户立项 |
| 8 | 新模型登记缺口修复批：fengyun_4/rangbaer_5 补录 model_dict.local.json + live2d_model None 解引用守卫 3 处 | 已完成（2026-10-08） | 两症状同根因=两新模型未登记本机 active 表 .local（42 条含 wuqi_3 故吾妻正常，实证 2026-10-08）；「无法启动」实为服务已起、WS 连接链 websocket_handler.py:197 无守卫解引用 None.model_info 砖死全部连接（traceback=logs/debug_2026-10-08.log 05:03）；修复=①补录两模型+Idle 别名组+kScale 回填（rangbaer_5 无角色卡不影响下拉显示，下拉源=登记表）②守卫 3 处（websocket_handler.py:197、service_context.py:712/:350）兑现 proceed-without-Live2D 容错（:682 规划期核实由切换成功路径保证非 None，免守卫）；GUI 编辑器下拉「表∪目录名」陷阱（OpenLLMVTuber_GUI.py:1718-1728）不并入、列遗留；演示口径=舰船模型仅 README 展示不分发资源（用户拍板 2026-10-08）；两 plan 首核已闭环（rangbaer_5 不在表实证、live2d_model_names=[] 为原始字段日志非缺陷） | 故障报告 2026-10-08 + 取证型子代理闭环（traceback 在案） |

## Backlog（未分版本）

| # | 条目 | 状态 | 方向结论要点 | 来源 |
|---|------|------|-------------|------|
| 1 | TouchBody 链几何退化+复位不可逆修复（跨模型普遍问题） | 构想 | 复审判定建议优先立项：用户感知强、非单模型问题；白名单锁已修，几何层待立项。依据 research_hotzone-arch复审.md §11 | 遗留 [hotzone-arch]① |
| 2 | l2d.ts 1081 行拆分重构 | 构想 | 核心渲染器含手势/热区/调试挂点，拆分需独立规格；触发=下次对该文件加新功能前 | 遗留 [live2d] |
| 3 | 统一「重建回滚」模式（load/ensureRenderer 先销毁无回滚） | 构想 | 症状驱动；收敛失败恢复旧模型的能力 | 遗留 [stage6] |
| 4 | 新模型入库完整性检测 launcher 集成 | 构想 | 脚本链内嵌导入流程（自动检测+一键修复+报告）；轻量版工作流已建立，集成暂缓（2026-09-16 用户裁决） | 遗留 [live2d] |
| 5 | 发版自动化+打包分发（gh CLI / Actions 自动 Release / portable 包） | 构想 | 待拍板是否立项（2026-09-30 问答提出） | 遗留 [github-p2-release] |
| 6 | Piper TTS 接入（离线低资源语音合成） | 构想 | 离线低资源 TTS 引擎接入，复用现有 TTS 引擎架构 | README Roadmap |
| 7 | 语音合成引擎体系持续演进 | 构想 | 长期方向；具体子项依赖各引擎接入结论（含 #6） | README Roadmap |
| 8 | live2d动作链条 阶段 C（type9/11/15 条件门槛/冷却/dynamicFlag/tips/参数权威层） | 构想 | 前置：站点面板↔模型双路径研究未取证（research2 §3.1 定案一半）；先补研究再规划 | 遗留 [live2d动作链条] |
| 9 | 演示视频/GIF 录制并挂 README（1-2 分钟全链路：ASR→LLM→TTS→Live2D 动效） | 已完成（2026-10-09） | 2026-10-08 用户指示提前并入 f 阶段（原 public 后补挂作废）；同日拍板：舰船出镜风险自担、无声 GIF 入库（docs/assets ≤10MB）、角色 kazagumo（fengyun_4，登记由 stage h 完成）、ASR 不展示改文字输入；commit+push 仍须用户确认 | 遗留 [github-p2-release] D2 升格 + 审查 基线2 |

> 初始登记为「构想」，未从 current-work 待处理遗留移除——正式升格/排序/版本归属由
> /plan-roadmap 逐条确认后执行（升格时才从遗留移除）。

## 调整记录

- 2026-10-01 建册（workflow-audit 阶段）：README Roadmap 2 条 + 遗留中明确待立项 6 条
  入 backlog；机制依据 research_工作流复审.md
- 2026-10-07 建 v1.0.1 版本目标集（github-p3-public 转 public 收口）：转公开只读审查
  6 条入册（#1-#4/#6 审查新发现，#5 遗留 S9 升格）；目标 10-08 转 public
- 2026-10-07 backlog 增 #9 演示视频（遗留 D2 升格 + 审查基线 2，public 后补挂）
- 2026-10-07 遗留 S9/D2 升格入册，current-work 待处理遗留同步移除两条
- 2026-10-07 #2 历史清理口径定稿 A（仅出库+主动声明；rewrite 子方案裁决不做——原告
  现实性≈0、JS 可随时重采、保 10-08 时间线）；#6 并入触摸引擎三层方案（2 行+半句+GIF，
  不独立成节，2026-10-07 用户拍板）
- 2026-10-07 #1 修复批完成（github-p3-public-a 验收通过）；#2-#6 待续（#3/#4 依赖网络恢复）
- 2026-10-08 #2 完成（github-p3-public-b 验收通过）；#3 开工（github-p3-public-c 规划完成）：
  待提交面从「2 簿记」修正为 9 文件全集（p3-b 按规格授权边界不提交，archive 登记）；
  v1.0.0 tag 规划时实证已在远程且与本地一致；网络实测间歇可通
- 2026-10-08 #3 完成（github-p3-public-c 验收通过）：实施 6+簿记 3 两提交入库（4435346+1000463）、v1-release 已推远程、tag v1.0.0 远程一致；#4/#5/#6 待续
- 2026-10-08 #4 开工（github-p3-public-d 规划完成，待弱模型实施）：实测型任务零代码改动；
  克隆须 -b v1-release（main 停旧）；Ollama 模型口径默认忠实 pull qwen2.5:latest（疑点待裁决）
- 2026-10-08 #4 实施完成（github-p3-public-d，待 /review-spec；提交 cf03a58 未推）：功能
  一次通过，「约 15 分钟」弱网直连不成立（瓶颈=pull 24.5min+ASR 999MB，详见 report）。
  疑点四项裁决落档：S3.5 未停追认；#5 门禁补 push v1-release+main 处置；微修复批立项
  （#7）；Enter/isComposing 记遗留+人工现场已备
- 2026-10-08 #4 完成（github-p3-public-d 验收通过）：功能一次通过，弱网不成立详见归档；cf03a58 与本收尾提交均未推，并入 #5 门禁 push
- 2026-10-08 剩余三序裁决 #7→#6→#5，#7 开工（github-p3-public-e 规划完成，待弱模型实施）：
  #7 先行=公开质量门禁（新克隆首跑即红）且复验环境现成；#6 次之=README 是公开首页，
  转 public 前内容齐备；#5 收尾=切 public 不可逆+push 门禁须用户确认，#6/#7 提交并入
  前置 push 一次推齐。#7 可选子项 *.bat text eol=crlf 默认不含、待拍板
- 2026-10-08 #7 完成（github-p3-public-e 验收通过）：.gitattributes 双钉（static/libs -text + *.bat crlf）根治新克隆 CRLF 红，主仓/克隆双侧绿（0693c2d）
- 2026-10-08 #6 开工（github-p3-public-f 规划完成，待弱模型实施）：吸收遗留弱网注记+
  克隆测试口径两条（已移除）；触摸引擎表内 2 行+bullet 半句口径维持 2026-10-07 拍板；
  基线实跑 200 passed
- 2026-10-08 #6 暂停，新增 #8 新模型登记缺口修复批（已立项）并裁决排序 #8→#6→#5
  （替代原 #7→#6→#5 序）：kazagumo「无法启动」与下拉缺模型同根因实证（两新模型未登记
  .local 表+WS 连接链无守卫解引用，取证型子代理闭环）；#6 README 演示素材依赖模型可用
  故让位；GUI 编辑器下拉陷阱列遗留不入子项
- 2026-10-08 #8 开工（github-p3-public-h 规划完成，待弱模型实施）：守卫点核实收敛为
  3 处（:197/:712/:350；:682 由切换成功路径保证非 None 免守卫）；前端契约实证 main.ts
  对 model_info 空值现成降级；两 plan 首核闭环（rangbaer_5 不在表实证、
  live2d_model_names=[] 为原始字段日志非缺陷）；规格预检排雷两处=fit 全量跑会打红
  mao_pro 双份一致断言（只回填两条）、补录后 fengyun_4 进 in_use 必须 Idle 别名组
- 2026-10-08 #9 并入 #6（用户指示，原 public 后补挂作废）：拍板=舰船出镜风险自担、
  无声 GIF 入库 ≤10MB（docs/assets）、角色 kazagumo（fengyun_4）、ASR 不展示改文字
  输入；commit+push 仍须用户确认。附实证：用户手修 fengyun_4 后主仓 1 failed/206
  passed（动作组名回退小写 idle 触 h 域 Idle 组契约红）——f 实施前置 R-1，修复归属
  待用户裁决
- 2026-10-08 R-1 裁决执行（用户授权顺手修复）：fix_live2d_idle_groups.py 重跑
  fixed=2（fengyun_4+rangbaer_5 同批回退一并修复），全量 207 passed 复绿；同批追加
  拍板：切换镜头目标=rangbaer_5（无 allowlist 键回退全局名单已核实）、新增调试栏+
  热区叠加层展示镜头（入 f spec §3 R2）
- 2026-10-09 #6/#9 完成（github-p3-public-f 验收通过）：README 改动总览 10 项表+弱网/测试口径注记+演示 GIF（64.5s/9.67MB 无声循环）挂载，全量 211 passed，spec.v2 升格 spec-demo-gif.md；#5 待续（切 public 前置门禁=push v1-release+main 停旧二选一，须用户确认）
- 2026-10-08 #8 完成（github-p3-public-h 验收通过）：未登记模型补录+None 守卫 4 处落地（守卫点较规划 +1=switch 成功尾部日志 :399），全量 207 passed；#6/#5 待续（排序 #6→#5）
