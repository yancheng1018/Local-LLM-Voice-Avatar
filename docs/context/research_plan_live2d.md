# 研究大纲 · l2d.su 互动热区分区重新研究（stage1）

> 2026-09-13 主模型规划，供弱模型执行 /research-doc 使用。**只读研究**，不改任何代码。
> 前情：`spec-l2dsu-engine.md`（stage2 逆向）已证实 touch.json 字段语义；本次聚焦其中
> 仍标「推断/待证」的**空间分区与命中判定**，并解释现实现为何在 guanghui_9 上退化成
> 「上下二分」。测试例：guanghui_9（用户指定，唯一）。

## 1. 研究问题定义（一句话）

l2d.su 对 guanghui_9 的互动热区在模型表面上如何**分区并判定命中**（尤其 28 个
Touch* 绘画件是实体区域还是画布外虚拟标记、命中链路用什么几何判据），frontend-minimal
需据此把「y<30% 判头 / 其余判身 + 包围盒」的粗暴方案替换成什么。

## 2. 需要回答的子问题

- **SQ1 命中链路**：l2d.su 指针事件→命中 drawable 的完整链路是什么？Pixi
  EventBoundary/hitTest 走到哪一层、按 containsPoint（逐像素/alpha）还是 getBounds
  （包围盒）；`Ve(drawables, rule)` 的匹配顺序与小写归一细节
  （spec-l2dsu-engine.md §5.1 现为「stage1 证据 + 推断」，需升级为证实）。
- **SQ2 热区几何实测**：guanghui_9 的 28 个 drawAbleName 绘画件（TouchDragN/TouchIdleN…）
  运行时 getDrawableBounds 的真实几何是什么？多少在画布内（实体热区）、多少画布外/零尺寸
  （虚拟标记）？l2d.ts 的画布内过滤（l2d.ts:184-191）因此丢了几条规则、控制台
  `[Touch] N/31 生效` 的 N 是多少——这是否就是用户看到「上下二分」的直接原因。
- **SQ3 虚拟标记的触发语义**：对画布外虚拟标记，l2d.su 如何不靠空间命中触发
  （点击次数/拖动方向/链状态？§2 的 type 2/1/6/7 与 num/time 如何与空间维度组合）；
  touch.json `ids`（20703701…）与 drawable/part 的对应关系。
- **SQ4 mode2 位置反应分区**：3 条无 drawAbleName 的 Param3 规则（reactPosX/Y × 指针
  位置）的坐标系（模型局部 or 屏幕）与作用范围（全模型 or 某区域），与 SQ1 命中链路的关系。
- **SQ5 tips 锚定旁证**：touch.json `tips`（28 个 Touch* drawable 的 offset/scale）
  由站点哪段代码消费、锚点如何换算——这是站点「知道」每个热区屏幕位置的旁证，可反推
  分区实现；四份运行时 JS 中 grep 为 0 命中，需在完整站点资源里找消费方。

## 3. 各子问题的资料与代码位置

| 子问题 | 本地资料/代码 | 需抓取/实测（本次已获许可） |
|--------|--------------|------------------------------|
| SQ1 | `Temp/modelRuntime-BDk3g7Pb.js`（Ve、hitTest）；`Temp/stage2_ctx.txt`（已提取符号上下文，先查此文件避免重复逆向）；spec-l2dsu-engine.md §5 | 站点在线 JS 与 Temp 快照 diff（站点更新则以新为准） |
| SQ2 | `live2d-models/guanghui_9/{touch.json, guanghui_9.model3.json, guanghui_9.moc3}`；`frontend-minimal/src/renderer/l2d.ts:104-231`（emitInteraction/loadTouchRules/pointInDrawable）；`frontend-minimal/src/renderer/l2d_touch_debug.ts`（可视化叠加层，本地实测工具）；`frontend-minimal/src/main.ts:122-201`（兜底分支） | l2d.su 页面控制台注入 getDrawableBounds 逐件实测；或本地 frontend-minimal + TouchDebug 覆盖层读 `[Touch] N/31` 日志 |
| SQ3 | `Temp/modelRuntime-BDk3g7Pb.js`（type 分发/num/time/circle）；spec-l2dsu-engine.md §2/§3/§6；`live2d-models/guanghui_9/motions/`（touch_* 动作与 rule.parameter 对照）；`frontend-minimal/src/renderer/l2d_touch.ts`（现 TouchChain，对照差距） | 站点实测：逐热区点击/拖动观察触发行为 |
| SQ4 | touch.json 的 3 条 Param3 规则原文；`Temp/modelRuntime-BDk3g7Pb.js`（mode===2 过滤与 reactPosX/Y 求和消费点）；spec-l2dsu-engine.md §1/§5.3 | 站点实测：指针在模型各部位移动时的参数变化 |
| SQ5 | touch.json 顶层 `tips` 键 | 站点 HTML + 全部 JS chunk（Temp 四文件之外可能有 app 层代码）；数据源 `https://l2d.su/data/ships/CN/<shipGroupId>.json`（guanghui_9 的 id 由 touch.json 反推，疑似 207037；URL 记录见 minimal-frontend.md:91） |

> 注：上表所列 `Temp/` 路径的产物已丢失（stage1 删除、从未入库，见 `docs/assets/README.md`）。
> 按本表施工前须重新采集站点资源，或改用 spec-l2dsu-engine.md 的既有结论。

> 抓取方法自选（Invoke-WebRequest/curl、浏览器 DevTools、WebFetch 均可），命令示例用
> PowerShell 语法（与 temp_spec 系列一致）；产物统一存 `docs/assets/`（命名 `su_*`；早期 Temp/ 产物已丢失），
> URL 与命令清单记入研究文档附录以便复现。

## 4. 输出文档结构（/research-doc 产物的章节标题）

1. 结论速览：l2d.su 热区分区机制要点 + 现实现差距 + 可落地改动清单（一页）
2. 指针命中链路实证（SQ1；混淆代码证据 + 置信度标注）
3. guanghui_9 热区几何实测（SQ2；31 规则 × 实测几何分类表：实体/虚拟/被过滤）
4. 虚拟标记热区的触发语义（SQ3；空间 × 次数/方向/链 的组合模型）
5. mode2 位置反应分区（SQ4；坐标系与作用范围）
6. tips 气泡锚定与热区定位旁证（SQ5）
7. 现实现差距与「上下二分」替换路径（对照 spec-l2dsu-engine.md §7/§8 增量更新；
   给 frontend-minimal 的升级建议，不改代码）
8. 附录：抓取/实测命令与 URL 清单（可复现）

## 5. 已知约束和边界

- **只读研究**：不改 frontend-minimal/、后端、AGENTS.md、model_dict.json；不改 l2d.su 站点。
- **爬取许可（本次新解禁）**：允许访问 l2d.su 及其静态资源域抓取页面/JS/模型数据；
  此外禁止泛搜索或抓其他站点。上次 stage2 规格书的禁网约束对本任务**无效**。
- **测试例唯一**：guanghui_9。其余 41 个模型的 touch.json 差异不在本次范围
  （涉及通用性只作标注，不展开）。
- **几何实测优先运行时 API**（getDrawableBounds / Pixi hitTest），不解析 moc3 顶点
  （live2d.md 已记录该路线因 keyform 间接索引放弃；Node+WASM 属新工程，不在本次）。
- **混淆 JS 逆向基线**：以 spec-l2dsu-engine.md §5 的既有结论为准（原 `stage2_ctx.txt` 已丢失），新增提取沿用
  stage2 的符号上下文方法；字段语义结论必须附置信度（证实/推断）。
- **与既有文档的关系**：产出为新研究文档，不直接改写 spec-l2dsu-engine.md；
  与其 §5/§7 冲突处须显式列出矛盾点，合并由主模型决定。
- **前端硬边界**（live2d.md 硬性契约）：官方 frontend/ 是无源码构建产物不可改；
  仅支持 Cubism 3/4；升级建议必须落在 frontend-minimal/ 能力范围内。
- 无法证实的点标注「未决」并说明卡点，不得臆测填空。
