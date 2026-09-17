# 研究：清理待处理遗留（顺序裁决）

> 取证日期 2026-09-18。对象：`docs/context/current-work.md:14-64`「待处理遗留」10 条（下称 L1~L10，按原文顺序编号）。
> 边界：本研究只核实现状、分类、理耦合、排顺序；不清理清单、不改代码、不跑格式化、不做 git 操作。
> 用户裁决倾向（2026-09-18）：**尽量减少挂起条数，尽可能清掉遗留**——顺序建议按此偏置。
> 方法先例：research_leftover-triage.md（2026-09-16 分诊，A/B/C/D 分类框架）。

## 1. 问题定义

对 current-work.md 待处理遗留 10 条逐条核实现状与触发条件，识别已被后续工作吸收/口径漂移的条目，梳理依赖耦合，产出一个最大化清零挂起条数的分批执行顺序建议（供用户裁决），不直接执行。

## 2. 现状与逐条盘点

清单权威来源：`current-work.md:14-64`，共 10 条。核实结果总表（分类沿用 leftover-triage 框架：A=机械可处理 / B=应尽快 / C=可关闭 / D=待裁决或立项）：

| 编号 | 条目 | 现状核实 | 分类 | 量级 |
|---|---|---|---|---|
| L1 | l2d.ts 1081 行拆分 | `wc -l` = 1081 ✓；例外已入档（minimal-frontend-live2d.md:138-140），无 LIMIT 守护 | 触发条件挂起+重构工程 | L |
| L2 | downhit 窗口断言漂移风险 | test_l2d_release_fallback.py:30-39，窗口=锚点后 30 行 ✓ | A（可提前加固） | S |
| L3 | 阶段 B 尾巴 + 阶段 C | 延后项原文在 research_live2d动作链条修正.md §6.3/§8；前置取证完成一半 | 路线图（非清理对象） | L |
| L4 | spec-writing 检查项候选 | spec-writing.md 现 §1-8，候选 3 条未入档 ✓ | A（需确认措辞） | S |
| L5 | emotionMap 为空 | **口径漂移**：实测 39/40 空，mao_pro 已有 50 键（live2d_scan_report.md:246） | 按需内容生产 | M |
| L6 | repo-format 未格式化 | **口径漂移**：实测 26 文件（非 25），多出 docs/assets/su_survey_touch_json.py | A（机械，分两步） | S |
| L7 | stage6 load() 无回滚 | l2d.ts:694 `async load`，:700-705 先 destroy 置 null，无 try/catch ✓ 结构未变 | 待立项（与 L1 同文件） | M |
| L8 | hotzone-arch 逆向待裁决 | 锚点 spec-l2d-touch-engine.md §11:154-166 留痕完整（C4/D5/D6/D7/§2.2） | 待研究专项 | L |
| L9 | test-sweep 盘点裁决 | **口径漂移**：git 实测 11 个文件（非 10），另有 __tsout__ 编译产物 2 个联动 | 裁决专项+机械执行 | M |
| L10 | launcher 入库集成 | 轻量脚本链已在（archive.md:47-56），集成 2026-09-16 用户裁决暂缓待立项 | 待立项（功能开发） | M~L |

### 关键发现（分条，附证据）

1. **三条口径已漂移，执行前必须订正**：
   - L5：`rg -c "emotionMap: 0 个键" live2d_scan_report.md` = **39**（非 40）；mao_pro 为唯一非空（50 键，2026-09-10 会话建立）。leftover-triage §N02「40/40 全空、无参照样本」已过时——**mao_pro 就是现成参照样本**（情绪关键词→表情 index 映射语义有先例可抄）。
   - L6：`uv run ruff format --check .` = **26 文件**（非 25）：15 个 frontend-minimal/tests/*.py + 3 根脚本（fit/fix/scan_live2d*）+ 6 个 src/ + tests/test_live2d_model_data.py + **docs/assets/su_survey_touch_json.py（旧盘点遗漏项）**。
   - L9：`git ls-files frontend-minimal/tests/` 实测 stage/debug 候选 **11 个**：stage2~7（6）+ test_stage6_bugfix + test_debug_panel + test_debug_panel_runtime + debug_panel_runtime.test.mjs + test_touch_debug_overlay；另有跟踪的编译产物 `__tsout__/l2d_debug_panel.js` 与 `_types.js` 2 个，去留随调试栏裁决联动。current-work 原文「10 个」与其自身枚举不符。
2. **L2 可主动加固且不属放宽断言**：脆弱点在 `test_l2d_release_fallback.py:34` `lines[idx:idx+31]`——emitInteraction 调用若因后续扩码退到 30 行外即误报。修复=把窗口扩大为整个 pointerup handler 块；`test:36-38` 的 call 切片以 `this.emitInteraction(` 起、首个 `);` 止，**自约束不受扩窗影响**，`this.downHitZone not in call` 断言严格度不变。属「修复测试自身缺陷使语义匹配原意」，非「放宽断言把失败改通过」；但按纪律仍列为待批准测试改动。
3. **L3 大半子项在「明确不做」清单里**：冷却先记、dynamicFlag 可见性、tips 显隐等均为 spec-l2d-touch-engine.md §10:146-152 明确不做项。做阶段 C=翻案规格变更，须逐项用户裁决+站点取证（§8-1 双路径：research_live2d动作链条-research2.md:45 已定案一半「type12 与面板读同一条目标表」，motion 曲线写入与目标表交互仍未取证）。**结论：L3 是功能路线图不是清理对象**，混在遗留清单里是挂起条数虚高的主因之一。
4. **L1/L7/C-1 同文件三合一**：l2d.ts:694 load() 无回滚（L7）、l2d.ts:1007-1009 canvasinfo 死代码兜底（minimal-frontend-live2d.md:125-126 早已列为清理候选但从未进清单）都应在 L1 拆分立项时一并规格化，leftover-triage §5.4 亦有合并建议。
5. **L1 拆分的隐性成本**：多个测试按文件路径读 l2d.ts 源文做静态断言（如 test_l2d_release_fallback.py:22 `read("src/renderer/l2d.ts")`、行数预算测试），拆分会打散全部锚点——立项时须按 spec-writing.md §1 先做断言盘点。
6. **L8 与 L3-C 取证同源**：L8 子项④（D6/D7 常量表需下载 chunk）与 L3 阶段 C 的 type9/11/15 取证是同一批站点 chunk——**一次复审研究可同时喂饱两条**。
7. **L6 与 L9 强耦合**：L6 的 15 个 tests 文件中 9 个与 L9 候选重叠（stage3~7×5、stage6_bugfix、touch_debug_overlay、debug_panel×2），先格式化可能白做；另 6 个为已转正测试（core_value_readout/reset/touch_chain/param_semantics/redlines/type12_gate）。非耦合 11 文件（3 根脚本+6 src+test_live2d_model_data+su_survey_touch_json）可立即独立排版提交。
8. **回归基线**：全量 170 测试全绿（archive.md:16-17），任何批次执行后以此为回归锚。

## 3. 触发条件核查

| 条目 | 声明触发条件 | 当前状态 |
|---|---|---|
| L1 | 下次对 l2d.ts 加新功能前 | 未触发（当前无既定新功能阶段） |
| L2 | 首次误报时 | 未触发（误报未发生）；可提前主动加固 |
| L3-B尾巴 | F2 验收不足时另立 | 未触发 |
| L3-C | §8-1 取证完成 | 未完成（已答一半） |
| L5 | 按需 | 未触发 |
| L7 | 另立项 | 待用户立项裁决 |
| L8 | 后续重新研究逐项裁决 | 无前置，可随时立项 |
| L10 | 2026-09-16 用户裁决暂缓 | 显式挂起中 |

无触发条件、纯待办：L4、L6、L9。

## 4. 依赖与耦合分析

- **L6 ↔ L9**（强）：9 文件重叠，必须先裁 L9 再批量格式化，否则白做/混 diff。
- **L1 ↔ L7 ↔ C-1**（强）：同文件（l2d.ts）→ 合并为一个「l2d.ts 重构」立项。
- **L8 → L3-C**（单向供证）：同一批站点 chunk 取证，L8 复研产出直接服务阶段 C。
- **L5 ↔ L10 ↔ C-3**（域耦合）：同属「模型入库」域（emotionMap 补充、launcher 集成、扫描报告过期重扫）。
- L2、L4 相互独立，无前置。

## 5. 可选方案对比

- **方案甲（最小动作）**：只做 L2+L6 非耦合 11 文件+L4，其余维持。清单 10→7 条。优点：几乎无裁决成本；缺点：L9/L8 两条最大混沌源仍在，挂起数降幅有限。
- **方案乙（推荐，最大化清零）**：四批推进+清单重组（见 §6），终点=清单收敛到 2~3 条真实挂起。优点：每批独立可验收、批间无死锁；缺点：需 3~4 次裁决/确认介入。
- **方案丙（激进）**：乙+L1 立即开工。不推荐：L1 触发条件未到、量级 L、会打散全部静态断言锚点（发现 5），当前无新功能需求，提前开工性价比最低。

## 6. 结论与建议：分批解决顺序（推荐方案乙）

| 批次 | 内容 | 关闭条目 | 清单变化 |
|---|---|---|---|
| 批1（机械清理，无裁决依赖） | ① L2 测试加固（窗口扩为整个 handler 块，待批准的测试改动）；② L6 非耦合 11 文件独立排版 commit；③ L4 三条补入 spec-writing.md（措辞经用户确认）；④ 顺带订正 current-work 三处口径（L5=39/40、L9=11 个、L6=26 文件） | L2、L4、L6 一半 | 10→8 |
| 批2（裁决+执行） | L9 五问框架集中裁决 11 文件+2 编译产物（转正/合并/删除）→ 执行 → L6 余下 15 个 tests 文件批量格式化（同一排版 commit 或紧随其后） | L9、L6 收尾 | 8→6 |
| 批3（研究专项） | 「hotzone-arch 复审」一次研究：下载站点 chunk，D4~D7/§2.2 时序/①②③子项逐项取证裁决，定案当场沉淀进 spec-l2d-touch-engine.md（leftover-triage §5.5 流程建议），顺带产出阶段 C 可复用取证 | L8（或收敛为少量已定案入档） | 6→5 |
| 批4（重构立项，可选提前或维持触发） | 「l2d.ts 重构」一个立项：拆分+load 回滚语义+canvasinfo 死代码，前置=spec-writing §1 断言盘点；维持触发条件则等下次加功能时启动 | L1、L7 | 5→3 |
| 清单重组（随批1 或单独做） | L3 移出「待处理遗留」改挂「路线图/功能演进」（B 尾巴触发条件不变、阶段 C 等 L8 取证+D2 裁决）；L5 并入 L10 的「模型入库」域表述 | L3、L5 出清单 | 终点 2~3 条 |

**终点状态**：待处理遗留只剩——L10（launcher 集成，显式挂起的立项候选）、L3（路线图指针）、L5（并入入库域的按需项）。达成「尽量少挂起」目标。

**排序依据**：先无裁决机械项（摩擦最小、立即减条）→ 裁决类（解锁 L6 尾巴）→ 研究类（L8 是最大混沌源且喂 L3）→ 重构类（触发未到，排最后）。

**每批需用户介入点**：批1 = L2 测试改动批准 + L4 措辞确认 + 排版 commit 确认；批2 = 裁决结果确认；批3 = 研究产出裁决；批4 = 立项批准。

## 7. 清单外候选与边界说明

**本次研究新发现的清单外候选**（仅记录，未处理）：
- C-1：l2d.ts:1007-1009 canvasinfo 死代码兜底（模块文档已列候选，从未进清单）→ 并入批4。
- C-2：spec-l2d-touch-engine.md:164-165 待办「live2d.md stage1 实测修正合并回 spec-l2dsu-engine.md / live2d.md」→ 文档合并小任务，可入批1 或独立。
- C-3：live2d_scan_report.md 过期（2026-09-10 生成，emotionMap/模型数口径已漂移）→ 重扫挂 L10 入库链。
- C-4：spec-l2d-touch-engine.md:166「l2d.ts 1030 行」行数过时（现 1081）→ 批4 立项时订正。

**边界**：
- 本研究未修改任何文件；执行需按批次另立实施（批1 起步即需用户批准三点，见 §6）。
- L2 测试改动属边界案例（修复测试自身缺陷、非放宽断言），已按纪律单列待批。
- 口径修正（39/40、11 个、26 文件）以本次实测为准；不一致时 live2d_scan_report.md 以重扫结果为准。
- 无新增硬性契约候选（纯排序研究）；批3 复审若产出定案，按「契约候选→确认→入档」流程走。
