# docs/assets · l2d.su 逆向产物素材区

> 本目录用于存放 **不可由代码重新生成的知识资产**（逆向产物、采集快照、证据文件）。
> 与 `docs/context/` 的分工：`context/` 放结论与规则，本目录放可复核的原始证据。

## 当前状态：逆向产物已丢失（git_stage2 记录）

stage1 已物理删除 `Temp/`，本阶段（git_stage2）追溯失败，**无法归档**。以下为完整记录。

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

`docs/context/spec-l2dsu-engine.md`（149 行，§1~§8）已固化**结论**：`touch.json` schema 语义、
`actionTrigger` / `actionTriggerActive` 语义、`listenerData` 语义、热区判定算法、动作链状态机。
缺失的是这些结论赖以复核的**原始产物**，故上述结论目前**无法再验证**。

### 遗留的悬空引用（待后续订正）

以下已入库文档仍引用已丢失的 `Temp/` 路径，后续按这些文档施工会扑空：

| 文档 | 引用内容 |
|------|---------|
| `docs/context/research_plan_live2d.md:37,68` | SQ1 依赖 `Temp/stage2_ctx.txt`、`Temp/modelRuntime-BDk3g7Pb.js` |
| `docs/context/research_live2d_stage1.md:145,156,256` | 依赖 `Temp/su_touch_rules_skin9.json`、`Temp/su_modelRuntime_deob.js` |
| `docs/context/spec-l2dsu-engine.md:4,5` | 引用 `Temp/stage2_tests.ps1`、`Temp/stage2_ctx.txt` |
| `docs/context/live2d.md` | 1 处 `Temp/` 引用 |

> 订正动作留给下一阶段（本阶段规格书限定删除范围，不擅自改历史文档）。
> 若日后需重建，须重新采集站点 JS 并重新逆向；注意站点可能已更新，
> 新结果应与 `spec-l2dsu-engine.md` 的既有结论交叉比对。
