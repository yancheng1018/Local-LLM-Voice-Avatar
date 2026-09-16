# 研究：待处理遗留清理（leftover-triage）

> 阶段：leftover-triage。取证日期 2026-09-16。对象：current-work.md「待处理遗留」
> 现存 13 条（N01~N13）+ 本轮规划新暴露 1 条（N14）。
> 边界：本报告只取证分类，不清理清单、不改代码。所有命令在仓库根 Git Bash 执行。

## 1. 问题定义

`docs/context/current-work.md:15-54` 累积 13 条待处理遗留，跨 live2d 资源 / 环境 /
源码结构 / 站点逆向四类，条目间年龄差达数周且多条已被后续阶段事实性解决，
需一次集中取证以决定哪些可立即处理、哪些应优先、哪些可关闭。

## 2. 现状

- 遗留清单：`docs/context/current-work.md:15-54`（13 条，无优先级标记、无状态标记）
- 数据面：`live2d-models/`（40 个模型目录）、`model_dict.json`、`characters/*.yaml`（11 个）
- 代码面：`frontend-minimal/src/renderer/`（9 个 .ts）、`frontend-minimal/tests/`（17 个）
- 环境面：`pyproject.toml:42-48`、`launcher/OpenLLMVTuber_GUI.py`
- 逆向面：`docs/context/spec-l2d-touch-engine.md`、`research_live2d-hotzone-touch-r4.md`

## 3. 关键发现

### N01 [live2d] 37 个模型 Idle 组大小写不匹配
- 原文锚点：current-work.md:17-18
- 证据：`uv run python scan_live2d_models.py` → 报告 40 个模型；
  `rg -c "Idle 组: ⚠️ 大小写不匹配" live2d_scan_report.md` = **37**（与历史一致）；
  `rg -c "Idle 组: ✅"` = 2（mao_pro、xinnong_6）
- **关键：影响面远小于 37。** 实测在用角色引用（`rg -n "live2d_model" characters/*.yaml`）：
  azuma→wuqi_3 ⚠️、Illustrious→guanghui_9 ⚠️、Friedrich→feiteliedadi_3 ⚠️、
  mao_pro→mao_pro ✅、ja_test→xinnong_6 ✅、spine_test→Spine 模型（不适用）、
  en_nuke_debate→shizuku-local（见 N06）；conf.yaml:31 默认角色 azuma.yaml → 命中 ⚠️。
  即「当前真正会被看到的坏模型 = 3 个（含默认角色）」
- 现状判定：仍成立，但规模应从「37 个模型」改写为「37/40 模型；在用 3 个」
- - 分类：A 简单可处理——修法是往 model3.json 加 `Idle` 别名组，机械、按需补 3 个即可
- 备注：是否要全量补 37 个属取舍，建议只补在用 3 个

### N02 [live2d] 40 个模型 emotionMap 为空
- 原文锚点：current-work.md:19-20
- 证据：`rg -c "emotionMap" live2d_scan_report.md` = 40；逐条格式为
  `- emotionMap: 0 个键（空，情绪关键词不会触发表情）`（报告 15、26、37 行等）
- 现状判定：仍成立，40/40 全空（无一个模型可作参照样本）
- - 分类：D 待裁决——补 40 个模型的情绪映射属内容生产而非清扫，且需先定映射语义
  （情绪关键词表 ↔ 表情文件名），无规格无先例，不是「简单清理」
- 备注：N01 是补别名（结构修正），N02 是造内容（语义映射），两者不应混为一谈

### N03 [环境] pytest 未入 optional-dependencies
- 原文锚点：current-work.md:20-21
- 证据：`sed -n '42,48p' pyproject.toml` → 仅 `bilibili = [...]` 一组，无 test 组
- 现状判定：仍成立
- - 分类：A 简单可处理——加 `test = ["pytest~=8.0"]` 一行；改动面小、无行为风险
- 备注：本报告全部 pytest 取证均被迫用 `uv run --with pytest`（见 §6 实际命令），
  说明该遗留确有日常摩擦成本

### N04 [stage5] launcher ruff format 全文件重排
- 原文锚点：current-work.md:22-25
- 证据：`uv run ruff format --check launcher/OpenLLMVTuber_GUI.py` →
  `Would reformat: launcher\OpenLLMVTuber_GUI.py`，`1 file would be reformatted`，**exit=1**；
  `git log --oneline -2 -- launcher/OpenLLMVTuber_GUI.py` → 最新为 4bccd87（stage6），
  该提交未做排版重排
- 现状判定：仍成立（文件确实未格式化，且无后续提交处理过）
- - 分类：B 应尽快处理——这是**唯一会持续恶化**的遗留：只跑 `ruff check . && ruff format .`
  （AGENTS.md 高频命令）就会把该文件混进任何无关提交里。迟早要付，越晚 diff 越大
- 备注：处理即「独立排版提交」，需单独一次 commit，不混功能改动

### N05 [stage6] l2d.ts load() 先销毁后加载、失败不恢复
- 原文锚点：current-work.md:26-28
- 证据：`frontend-minimal/src/renderer/l2d.ts:656` `async load(modelInfo)` →
  `l2d.ts:662-665` 先 `detachLipSync()/detachParamDriver()/this.model?.destroy();
  this.model = null`，随后 `l2d.ts:677` `await Live2DModel.from(...)`；
  从 656 到 690 无 try/catch、无旧模型快照、无回滚分支
- 现状判定：仍成立，结构未变
- - 分类：D 待裁决——是否收敛为统一「重建回滚」模式（原文即写明「另立项」），
  属架构取舍非清扫
- 备注：与 `ensureRenderer` 同属「先销毁无回滚」家族，应合并为一次立项

### N06 [stage6] en_nuke_debate.yaml 指向无效模型
- 原文锚点：current-work.md:29-31
- 证据：`rg -n "live2d_model" characters/en_nuke_debate.yaml` →
  `4: live2d_model_name: "shizuku-local"`；`ls live2d-models/ | rg -i shizuku` → 无输出（目录不存在）；
  `rg -n "en_nuke" conf.yaml config_templates/ src/ characters/README.md` → 无引用命中
- 现状判定：仍成立，且**该角色未被任何配置引用**（非默认角色、不在模板、不被代码点名）
- - 分类：A 简单可处理——删除该示例角色文件，或改指 `mao_pro`（在用且 Idle 正常）
- 备注：删除比改指向更干净；删除后需确认 config_alts_dir 扫描（conf.yaml:12）不会报错

### N07 [stage6] 失败基线 test_resolver_runtime_allowlist
- 原文锚点：current-work.md:32-34
- 证据：`uv run --with pytest python -m pytest frontend-minimal/tests/test_live2d_model_switch.py::test_resolver_runtime_allowlist -q`
  → `1 passed in 2.08s`，**pytest-exit=0**；
  全量 `... -m pytest frontend-minimal/tests/ -q` → `129 passed in 51.96s`，exit=0
- 根因：测试自带导入路径处理，`test_live2d_model_switch.py:72` 等三处
  `sys.path.insert(0, str(ROOT / "src"))`（行 72/283/301），
  故 `No module named 'prompts'` 不复现
- 现状判定：**已变化——基线失败已不存在**，`prompts` 导入问题已被测试自身的 sys.path
  注入解决（该处理在 5a66cf6 或更早已存在，非本阶段引入）
- - 分类：C 已过时/已解决——原条目描述的现象实测不可复现，全量 129 用例 0 失败
- 备注：该条属「历史噪声」，继续挂在清单里会误导后续把绿色当红色。

### N08 [stage7] l2d_touch_debug.ts 220 行硬上限
- 原文锚点：current-work.md:35-36
- 证据：`wc -l` → `l2d_touch_debug.ts` **203**、`l2d_touch_debug_helpers.ts` 106、
  `l2d_debug_panel.ts` **200**
- 现状判定：**部分变化**——r2 的净减拆分已落地（220→203），但**仍未达标**（上限 200，超 3 行）；
  且姊妹文件 `l2d_debug_panel.ts` 恰为 200，零余量
- - 分类：B 应尽快处理——超限已存在，是 spec-writing.md §5 明确点名的返工诱因
  （r2_v4 教训：超限留给执行层临场压缩，引入未审内容）
- 备注：超 3 行，属可一次清掉的小额欠账；同时应连 `l2d_debug_panel.ts` 零余量一并
  在规格里预检

### N09 [hotzone-touch] round1 §7 余项
- 原文锚点：current-work.md:37-39
- 证据：`rg -n "OE_TYPES|type 9|type12" docs/context/*.md` → 命中仅
  `research_live2d_stage1.md:162`（描述现状数据）、`spec-l2dsu-engine.md:39`（relationParameter）、
  `spec-l2d-touch-engine.md:132`（列为未实现）、`l2dsu抓取模型说明.md:80`（保留原则）；
  **r3 文档已不在仓库**（`ls docs/context/ | rg -i r3` 无命中），原文提到的「r3 已裁决」
  在仓库内无文档可查
- 现状判定：仍成立且**证据链已断**——裁决所依据的 r3 文档不在了，
  仅 current-work.md 自述「r3 已裁决」，无法复核
- - 分类：D 待裁决——type 9/10/11 未实现清单入档、OE_TYPES 含 7 vs dispatch 拒 6/7、
  empty 占比差异（游戏数据生成侧）三项均需强模型裁决
- 备注：建议把 r3 的裁决结论沉淀进 spec-l2d-touch-engine.md 后再关闭，避免二次失忆

### N10 [hotzone-touch-r2] r2 §9 疑点
- 原文锚点：current-work.md:40-41
- 证据：同上 `rg` 未命中 guanghui 点名 5 区来源、idleBlackList/animWhiteList 的消费决策；
  `l2dsu抓取模型说明.md:80` 只说「type12 原样保留」，未定消费语义
- 现状判定：仍成立
- - 分类：D 待裁决——guanghui 点名 5 区来源未复现（需重新抓包/取证）、
  type12/tips 新 schema 消费与否属实现取舍

### N11 [r2_v3] v3 用户裁决项
- 原文锚点：current-work.md:42-44
- 证据：`rg -n "显示策略|方案 A|退化区" docs/context/*.md` → 仅 current-work.md 自身命中；
  `l2dsu抓取模型说明.md:96` 的「方案 A」是抓取脚本方案，同名不同事；
  `spec-l2d-touch-engine.md:52` 已实现「择一优先级（class1>class2）」，
  但 v3 遗留的「forEach vs 择一」是**规格变更**议题（原文已注明「站点已证 forEach」）
- 现状判定：部分议题另有进展（择一优先级已实现），但显示策略/退化区门槛、
  TouchBody 链自毁、stepDrag 起点锚定三项仍无定案
- - 分类：D 待裁决——含「叠加层显示策略（方案 A/B/C）」这类需要用户拍板的 UI 取舍

### N12 [r2_v4] v4 §6 明确不做
- 原文锚点：current-work.md:45-49
- 证据：`spec-l2d-touch-engine.md:141` D5（slide 闸门边界，offsetCircle 样本未普查）、
  `:142-143` D6/D7（touch_drag7 棘轮三函数、triggerConditionMet 常量表未实现）、
  `:100-101` D4′（offset=0 轴排除为本地保留项）
- 现状判定：仍成立，且**已正确入档于引擎规格文档**（非仅挂在 current-work）
- - 分类：D 待裁决——原文即「待站点数值取证后统一」，需下载 chunk 反查，属强模型+取证工作
- 备注：本条与 N09~N11 性质相同（逆向未决），但**唯一一条已在模块文档留痕的**，
  可优先保留；其余应先沉淀再谈关闭

### N13 [test-sweep] tests/ 既有资产盘点
- 原文锚点：current-work.md:50-54
- 证据：`wc -l frontend-minimal/tests/*` → 17 个测试文件（.py 16 + .mjs 1），共 1914 行；
  带 stage 痕迹的已跟踪文件：test_l2d_hotzone_stage2~7（6 个）、test_stage6_bugfix、
  test_debug_panel、test_debug_panel_runtime、debug_panel_runtime.test.mjs、
  test_touch_debug_overlay —— **确认与原文清单一致**；
  r2 系列两份已转正（test_l2d_touch_redlines 82 行、test_l2d_touch_param_semantics 73 行）
- 现状判定：仍成立，清单准确
- - 分类：D 待裁决——转正/合并/删除属强模型按五问框架的裁决工作，非机械清扫
- 备注：本项是清单里**唯一有明确方法论（五问框架）但待执行的**，适合单独立项排期

### N14 [结构] 模块行数上限余量普遍归零（本轮新增）
- 来源：本报告起草时实测（`wc -l frontend-minimal/src/renderer/*.ts`）
- 证据：`l2d.ts` **1030**、`l2d_params.ts` **346**、`l2d_touch_debug.ts` **203**（超限）、
  `l2d_debug_panel.ts` **200**（恰满）、`spine.ts` 243 —— 对照 AGENTS.md「单模块 ≤ 200 行」，
  除少数外**全部超标**，与 spec-writing.md §5 的规定直接冲突
- 现状判定：存量事实；说明「≤200」实际是按某个子文件集执行的（l2d.ts 1030 行长期存在未被处理）
- - 分类：D 待裁决——需先明确「模块」粒度的判定口径（是文件？还是逻辑单元？），
  口径不定则 N08 的「203 超限」同样没有稳定基准

## 4. 分类汇总

| 编号 | 标签 | 分类 | 依据 | 建议处置 |
|---|---|---|---|---|
| N01 | live2d Idle 37 | A | 37/40 实测确认；在用仅 3 个 | 立项（只补在用 3 个） |
| N02 | emotionMap 40 空 | D | 40/40 全空，属内容生产 | 保持挂起，先定映射语义 |
| N03 | pytest 未入 deps | A | pyproject:42-48 仅 bilibili | 立项（一行改动） |
| N04 | launcher format | B | ruff --check exit=1，未处理 | **优先立项**（持续恶化） |
| N05 | load() 无回滚 | D | l2d.ts:656-690 无 try/catch | 保持挂起，与 ensureRenderer 合并立项 |
| N06 | en_nuke 无效模型 | A | 目录不存在且无任何引用 | 立项（删除文件） |
| N07 | 失败基线 | C | 实测 1 passed + 全量 129 passed | **可关闭**（从清单移除） |
| N08 | 调试叠加层超限 | B | 203 > 200，拆分已做一半 | **优先立项** |
| N09 | round1 §7 余项 | D | r3 文档已不在仓库，无法复核 | 先沉淀再关 |
| N10 | r2 §9 疑点 | D | 未复现/未裁决 | 保持挂起（需取证） |
| N11 | v3 裁决项 | D | 显示策略需用户拍板 | 保持挂起 |
| N12 | v4 §6 不做项 | D | 已在引擎规格留痕 | 保持挂起（证据最完整） |
| N13 | tests 资产盘点 | D | 17 文件清单已确认 | 单独立项（五问框架） |
| N14 | 行数口径 | D | 多文件超 200，口径待定 | 保持挂起（需先定口径） |

统计：A 3 条（N01/N03/N06）、B 2 条（N04/N08）、C 1 条（N07）、D 8 条。

## 5. 结论与建议

1. **立即可做（A，无裁决依赖）**：N03（pytest 入 deps，一行）、N06（删 en_nuke_debate.yaml）、
   N01（只补在用 3 个模型的 Idle 别名组）。三条互不耦合，可作一个「杂务清理」小阶段。
2. **应尽快（B）**：N04 与 N08 都属「拖下去成本上升」型——N04 会让每次 `ruff format .`
   污染无关提交，N08 超限会诱发执行层临场压缩（spec-writing.md §5 的返工诱因）。
   建议排在 A 之前或同批处理。
3. **可关闭（C）**：N07 实测已解决，全量 129 用例 0 失败，继续挂账会把绿色当红色，
   建议直接移出清单（清理动作待用户裁决后执行）。
4. **保持挂起（D，8 条）**：其中 N09/N10/N11/N12 同属「站点逆向未决」族，
   建议**合并为一条**「热区逆向待裁决项」以降低清单噪声；N12 因已在引擎规格留痕，
   可作为该族的主锚点。
5. **流程性建议**：N09 暴露的真问题不是「未裁决」，而是**裁决证据随过程文档删除而丢失**
   （r3 已不在仓库）。建议裁决结论必须当场沉淀进 spec-l2d-touch-engine.md，
   current-work.md 只留指针，不留「某文档已裁决」这类无锚点自述。

## 6. 疑点

- N01 的「补 37 个还是补 3 个」是范围取舍，本报告按「只补在用」建议，需用户确认
- N14 的「模块 ≤200 行」口径未定，直接影响 N08 的判定基准；本报告按「文件粒度」记录，
  若口径实为逻辑单元，则 N08 需重新分类
- N09 原文称「r3 已裁决」，但 r3 文档已不在 `docs/context/`，
  其裁决内容是否已并入 spec-l2d-touch-engine.md 无法判断（`rg` 未命中 forEach 相关定案段）
