# docs/assets · l2d.su 逆向产物素材区

> 本目录用于存放 **不可由代码重新生成的知识资产**（逆向产物、采集快照、证据文件）。
> 与 `docs/context/` 的分工：`context/` 放结论与规则，本目录放可复核的原始证据。

## 当前状态（2026-09-17 更新）

**stage2 丢失的产物已重建一部分**：本轮（动作链条修正研究）重新采集了站点引擎 JS 并完成反混淆，
新增归档如下；stage2 丢失清单仍见下方「历史记录」。

### 现行归档清单

| 产物 | 用途 | 复核方式 |
|------|------|---------|
| `su_modelRuntime-BDk3g7Pb.js` | 站点引擎 JS 原始快照（201,926 字节，2026-09-17） | 直接读；混淆字符串按下方脚本还原 |
| `su_modelRuntime_strings.json` | 解码后的字符串表（642 条，键=解码入参十六进制） | `su_survey_touch_json.py` 同目录脚本；或按 spec-l2dsu-engine §1 的 Node 片段重建解码器 |
| `su_ships-CN.json` | 站点全量索引（prefab→shipGroupId、皮肤清单），2.8MB；**已出库（本地保留磁盘，不入库，2026-09-29）** | 直接读；survey 脚本的索引源 |
| `_ships_cache/site_<group>.json` | 33 组站点数据快照（研究期 4 症状组 + 普查/修复全量缓存，6.6MB）；**已出库（本地保留磁盘，不入库，2026-09-29）** | 直接读；含各皮肤完整 `live2dTouch`；可用脚本 `--fetch` 重新采集 |
| `su_survey_touch_json.py` | **touch.json 皮肤匹配普查脚本**（发现 9/36 错配） | `python docs/assets/su_survey_touch_json.py <repo_root> [--fetch]` |

**touch.json 数据源规则（动作链条修正候选 A1 降级，2026-09-17）**：本地
`live2d-models/<name>/touch.json` 必须来自站点**同名 prefab 精确匹配**且 rules 非空的
live2d 皮肤（dynamicType=='live2d'，过滤后空再降级）。重下脚本 `fix_live2d_touch_data.py`
（仓库根）内置校验，任一不符即 `[ABORT]` 拒写：prefab 索引漂移 / 候选皮肤 ≠1 /
规则数与普查表不符 / shipSkinId 与所选皮肤号不符。回归：
`frontend-minimal/tests/test_l2d_touch_data.py`（9 模型规则数 + 单一皮肤号）。

**结论文档**：`docs/context/spec-l2dsu-engine.md`（站点引擎源码级逆向，与本文档同批产出）、
`docs/context/research_live2d动作链条修正.md`（四模型症状归因与数据普查结果）。

> 重新采集注意：站点数据端点 `https://l2d.su/data/ships/CN/<shipGroupId>.json` 有防盗链，
> 请求必须带 `User-Agent` + `Referer: https://l2d.su/`，否则 403。

---

## 历史记录：stage2 逆向产物丢失（git_stage2 记录）

stage1 已物理删除 `Temp/`，该阶段（git_stage2）追溯失败，**无法归档**。以下为完整记录。

### 丢失清单

| 产物 | 用途 |
|------|------|
| `su_touch_rules_skin9.json` | 站点 62 条热区规则集（按 guanghui_9 对齐的关键依据） |
| `su_touch_geometry.json` | 热区几何数据 |
| `su_ships-CN.json` | 站点中文文案快照 |
| `su_site_model3.json` | 站点 model3 结构快照 |
| `su_decoded_strings.json` | 反混淆字符串表 |
| `su_sparseRuntime*.js` | 站点运行时 JS 快照 |
| `su_modelRuntime_deob.js` | 反混淆运行时 JS |
| `xinnong_*.json` | 心农模型相关 JSON |
| `Temp/stage2_ctx.txt` | 已提取的符号上下文全文（避免重复逆向用） |
| `Temp/stage2_tests.ps1` | 逆向验证测试脚本（T1~T20） |

### 不可找回的依据

- `.gitignore:33` 含 `Temp/` —— 该目录**从未进入索引**，git 无法恢复。
- `git log --all --diff-filter=D --name-only -- 'Temp/*'` → 空。
- `git log --all --oneline -- 'Temp/*'` → 空（无任何提交触碰过该路径）。
- 全历史路径扫描 `su_*` / `xinnong_*` / `deob` / `sparseRuntime` → 无匹配。

### 已保留的部分（结论层完好，证据层缺失）

`docs/context/spec-l2dsu-engine.md`（stage2 版 149 行 §1~§8；v1/v2 已于 distill-b2 合并为源码
直证版，见上方「现行归档清单」）当时已固化**结论**：`touch.json` schema 语义、`actionTrigger` /
`actionTriggerActive` 语义、`listenerData` 语义、热区判定算法、动作链状态机。
缺失的是这些结论赖以复核的**原始产物**（2026-09-17 已部分重建，见上）。

### 遗留的悬空引用（待后续订正）

以下已入库文档仍引用已丢失的 `Temp/` 路径，后续按这些文档施工会扑空：

| 文档 | 引用内容 |
|------|---------|
| `docs/context/research_plan_live2d.md:37,68` | SQ1 依赖 `Temp/stage2_ctx.txt`、`Temp/modelRuntime-BDk3g7Pb.js`（该大纲已随 distill-b1 脚手架清理删除，本行仅历史记录） |
| `docs/context/research_live2d_stage1.md:145,156,256` | 依赖 `Temp/su_touch_rules_skin9.json`、`Temp/su_modelRuntime_deob.js` |
| `docs/context/spec-l2dsu-engine.md` §12 | 引用 `Temp/stage2_tests.ps1`、`Temp/stage2_ctx.txt`（v1 头注随 distill-b2 合并迁入） |
| `docs/context/live2d.md` | 1 处 `Temp/` 引用 |

> 订正动作留给下一阶段（本阶段规格书限定删除范围，不擅自改历史文档）。
> 若日后需重建，须重新采集站点 JS 并重新逆向；注意站点可能已更新，
> 新结果应与 `spec-l2dsu-engine.md` 的既有结论交叉比对。
