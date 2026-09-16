# l2d.su 模型抓取说明 · 碧蓝航线 Live2D 数据源完整指南

> 2026-09-16 由 r2 系列研究过程 + 当日补抓实测提炼（过程文档已清理，本文自足）。
> 所有 URL / 响应矩阵 / 数据结构均经当日实测验证；站点改版后需复核（数据带 `generatedAt`/`version` 字段可判新旧）。
> 本项目用法：`touch.json`（= 数据里的 `live2dTouch`）由 frontend-minimal 规则引擎消费，
> 规格见 spec-l2d-touch-engine.md；其余文件为通用 Live2D 渲染资产。

## 0. 文件完整性现状（先纠正一个误判）

数据审计结论：**本地模型文件是忠实的，不是「不完整」**——wuqi_3/guanghui_9 的 touch.json 与站点当前
数据逐字段比对：guanghui_9 语义全同，wuqi_3 仅 1 token 差异（TouchIdle4.enable 内 touch_drag9↔
touch_drag11，系站点侧数据更新，非本地缺料）。「顶层键比记载少」是站点对不同 ship 本来就发得不一样（§3-2）。

真实缺件是 **DisplayInfo（cdi3.json）×27 个模型 + liekexingdunII_2 的 motions/touch_idle19.motion3.json**——
原爬取项目没抓 cdi3。已于 2026-09-16 全部补齐（28/28 成功，200+JSON 校验通过）。

## 1. 完整的模型包含哪些文件

每个 Live2D 皮肤一个目录，目录名 = 数据里的 `model.key`（charKey，如 `wuqi_3`）：

| 文件 | 作用 | 引用方 |
|------|------|--------|
| `<key>.model3.json` | 模型清单（引用根） | 渲染器入口 |
| `<key>.moc3` | 模型本体 | model3.json `FileReferences.Moc` |
| `<key>.physics3.json` | 物理演算 | `FileReferences.Physics` |
| `<key>.cdi3.json` | 显示信息（参数/部件中文名，编辑器用；**渲染不用但属完整集，最易漏**） | `FileReferences.DisplayInfo` |
| `textures/texture_NN.webp` | 贴图（webp 多张） | `FileReferences.Textures[]` |
| `motions/<组名>.motion3.json` | 动作（每组通常 1 文件；组含 idle/touch_idleN/touch_dragN/UI 音效动作等） | `FileReferences.Motions` |
| `touch.json` | **= 舰船数据 JSON 里 `ship.skins[].model.live2dTouch` 原样落盘**（触摸规则引擎数据） | 本项目自约定 |
| `info.json`（可选） | 抓取元数据 `{id(skinId), name(中文名), prefab(=key)}` | 本项目自约定 |
| `<key>.pose3.json`（如有） | 部分模型有 | `FileReferences.Pose`（引用了就必须抓） |

下载后必须跑「引用存在性扫描」（§4 校验）：model3.json 里引用到的每个相对路径都要存在——
本轮 28 个缺件全靠它发现。

## 2. 从哪里、如何爬取

### 2.1 端点清单（2026-09-16 实测响应矩阵）

| 端点 | curl 直连（无代理） | 说明 |
|------|---------------------|------|
| `https://l2d.su/data/ships-CN.json` | **200 application/json（2.8MB）** | 全舰索引：896 艘，含 shipGroupId/defaultSkinId/名称/rarity/icon 路径；无模型路径 |
| `https://l2d.su/data/ships/CN/<shipGroupId>.json` | **200 application/json（150~400KB）** | 舰船级数据：`ship.skins[]` 每皮肤含 `{id, name, model:{type:'live2d'\|'spine', key, path, live2dTouch}}`；**一个文件拿全该舰所有 Live2D 皮肤** |
| `https://static.l2d.su/azurlane/live2d/<key>/<file>` | 200 | 模型静态文件；根 = `https://static.l2d.su/azurlane/` + 数据里 `model.path`（如 `live2d/wuqi_3/wuqi_3.model3.json`） |
| `https://l2d.su/data/ships/CN/<skinGroupId>.json`（如 399042） | ⚠️ 200 但返回 **SPA HTML** | **皮肤级路径是死路**：与 SPA 路由 `/cn/skins/<id>/` 撞车，服务端回退 index.html——历史上「数据接口失效」误判即由此而来 |
| `https://l2d.su/cn/`、`/cn/skins/<skinId>/` | HTML（SPA） | 网页入口，仅浏览器调试用 |

- locale：`/data/ships/{CN|EN|JP|KR|TW}/...` 五套；数据带 `generatedAt`、`version`（如 9.7.381）、`sourceRoot`（上游 `vendor/azurlane_lua`）。
- 关键 ID 辨析（最大的坑）：**shipGroupId**（舰船，如吾妻=39904）≠ **skinId/skinGroupId**（皮肤，wuqi_3=399042）。
  数据接口用**舰船 id**，静态路径用**皮肤的 charKey**。touch.json 规则 id = skinGroupId×100+序号（39904201…，可自校验）。

### 2.2 三步流程（纯脚本可完成）

```bash
# ① 索引：筛出目标舰船（或全量）
curl -s --noproxy '*' -A 'Mozilla/5.0' -o ships-CN.json https://l2d.su/data/ships-CN.json
# ② 舰船数据：按索引里的 shipGroupId
curl -s --noproxy '*' -A 'Mozilla/5.0' -o ship-39904.json https://l2d.su/data/ships/CN/39904.json
# ③ 静态文件：对每个 model.type=='live2d' 的皮肤，base = https://static.l2d.su/azurlane/
#    下载 model.path（model3.json）后解析其 FileReferences，逐个下载 Moc/Physics/DisplayInfo/
#    Textures/Motions（相对 model3.json 所在目录）；live2dTouch 另存为 touch.json
```

### 2.3 兜底：浏览器法（当 curl 被站点策略挡时）

用 Playwright/无头浏览器开 `https://l2d.su/cn/skins/<skinId>/`：
- 网络 interception 捕获 `/data/ships/...` 与静态响应；或
- 页面内 `fetch(url)` 后取文本；或
- **内存提取（最后手段）**：模型加载后遍历 React fiber 找 `pendingProps.activeModel.model.live2dTouch`
  直接序列化（本轮 r2 研究即用此法；ship 级数据同在 fiber 可达处）。localStorage 键
  `l2d-touch:<skinId>:<charKey>` 是引擎状态，与抓取无关。

## 3. 注意事项与踩过的坑

1. **shipId/skinId 混淆**（见 §2.1）：皮肤级路径返回 HTML 不是反爬、不是接口失效，是路径错了。
2. **live2dTouch 顶层键 per-ship 差异**：实测 wuqi_3=4 键（无 tips/dragRate）、guanghui_9=5 键（有 tips 无
   dragRate）、spec-l2dsu-engine §1 记载的 6 键是 207037 系皮肤——不要假设固定键集，解析按需取。
3. **tips 子键比旧记载多**：guanghui_9 实测有 `tipsOffset/tipsScale/tipsIcon/idleBlackList/animWhiteList`
   （后三者为 spec-l2dsu-engine §1 未记载的新发现）。
4. **不认识的规则类型也要原样保留**：实测存在 type12（参数 num 监听，两模型各 1 条带大 ignore 表）、
   9/10/11 等；本地引擎未实现 ≠ 数据不需要，重抓后 diff 会因丢弃而误报。
5. **动作组跳号是数据事实**：wuqi_3 无 idle8 组、guanghui_9 无 touch_idle11/idle11 组且规则集同样缺号
   （自洽）；但 model3.json 引用了而文件缺失是真缺件（liekexingdunII_2 的 touch_idle19 即此类）。
6. **组名小写**：空闲组是 `idle`/`idle1`…（非 `Idle`）——本项目「37 模型 Idle 组大小写不匹配」遗留的根源。
7. **规则集必须匹配皮肤**：历史上曾把 guanghui_7（207037 系）的规则配到 guanghui_9 模型（stage1 §8/§9.1
   已核销修正）；抓取时以 `ship.skins[].id` 与规则 id 前缀双重核对。
8. **编码**：全部 JSON 为 UTF-8，原样保存；Windows 控制台打印中文会乱码是显示问题，别转码。
9. **代理**：本机默认直连可通（curl 加 `--noproxy '*'` 或清 *_PROXY 环境变量）；如需走代理先请示。
10. **命名与目录卫生**：目录名必须用 `model.key`（本项目 model_dict/emotionMap 按名关联）；不要把
    desktop.ini/Thumbs.db/`.bak` 打进模型目录。
11. **多皮肤舰船**：一份舰船 JSON 含全部皮肤（含 Spine/无模型皮肤），按 `model.type=='live2d'` 过滤。
12. **节制抓取**：按需单模型最小文件集，不批量全站爬；每模型记录 `generatedAt`/`version` 便于增量。

## 4. 稳定抓取方案与校验

**推荐方案 A（当前全部端点 curl 可通，纯脚本）**：§2.2 三步 + 落盘 `info.json`（含抓取日期与
generatedAt）。无浏览器依赖，可 cron 化增量（先抓索引 diff `newSkins`/`skinUpdateHistory`，只抓变化舰）。

**兜底方案 B**：站点将来若对 data 接口加 Cloudflare 校验（对 curl 回 HTML），切 Playwright 无头浏览器
拦截响应（§2.3）；静态源 static.l2d.su 本轮无任何拦截，预期长期可直连。

**落盘后校验清单（三道）**：
1. 引用存在性扫描：model3.json 的 Moc/Physics/Pose/DisplayInfo/Textures/Motions/Expressions 逐个
   `os.path.exists`（本轮 28 缺件即此法发现；零容忍）。
2. touch.json 忠实性：与舰船 JSON 内嵌 live2dTouch 做 JSON 级 diff（不是字符串 diff——顶层键序无关）。
3. 动作组三方比对：model3.json 组清单 = motions/ 文件 = touch.json 引用动作名，三者互查缺漏并区分
   「数据事实跳号」与「真缺文件」。

## 5. 与既有文档的关系

- spec-l2dsu-engine.md §1「数据源 `/data/ships/CN/<shipGroupId>.json`」的 id 语义应订正为**舰船级**；
  其 6 顶层键描述限定 207037 系皮肤（§3-2）。research_live2d_stage1.md §6 的「接口失效」结论已被
  stage1b §9.1 推翻（本轮再证）。订正动作待裁决后由 /distill-research 类命令执行，本文不直接改旧文档。
- 本文件未录入 AGENTS.md 索引表（改索引需确认）；建议登记为「l2d.su 数据源抓取」场景条目。
