# 研究：hotzone-arch 复审（批3）

> 阶段：hotzone-arch 复审（批3）。日期 2026-09-27。只读研究：不改代码/规格/current-work。
> （研究大纲 research_plan_hotzone-arch复审.md 已随 distill-b1 删除，本文自足。）取证基座：docs/assets/ 本地站点资产
> （su_modelRuntime-BDk3g7Pb.js 201,926B 完整引擎源码 + su_modelRuntime_strings.json 642 条
> 解码串表 + _ships_cache/ 33 船数据 + su_ships-CN.json 896 船索引）。
> ⚠️ 联网复核：l2d.su apex 已无 DNS A 记录（DoH 返回 NOERROR+SOA，2026-09-27），
> www↔apex 301 死循环，**站点当前不可达**；本轮取证全部依赖本地资产，未受影响。

## 1. 问题定义

对 current-work.md:31-44 [hotzone-arch] ①–④ 四组待裁决子项逐项核实现状与证据等级，
能定案的定案，不能定案的列明缺口与取证入口，产出 spec-l2d-touch-engine.md 回写候选与处置建议。

## 2. 逐项现状核实总表

| # | 子项 | 现状结论 | 证据等级 |
|---|------|---------|---------|
| 1 | ①OE_TYPES 含 7 vs dispatch 拒 6/7 | **描述过期**：现值与站点 Oe 完全一致，无 7 | A |
| 2 | ①type 9/10/11 未实现清单 | 语义已全部解码（§3），可入档；本地影响面≈0 | A |
| 3 | ①empty 占比差异 | 原观察随 round1 文档丢失；现只存两语料各自占比 | C（证据链断） |
| 4 | ②guanghui 点名 5 区 | 候选解释维持；原始观察仍待用户补充 | C |
| 5 | ②tips 新 schema 消费与否 | **翻案定案**：有消费点=提示图标显隐，不参与交互门槛 | A |
| 6 | ③叠加层方案 A/B/C+退化区门槛 | A/B/C 原文失传不可重建；退化区门槛建议关闭 | C / A(门槛) |
| 7 | ③forEach vs 择一 | 事实定案维持；本地是否改=规格变更待裁决 | A(事实) |
| 8 | ③TouchBody 链自毁/feiteliedadi 可玩性 | 维持（原文失传）；需实机复核 | C |
| 9 | ③stepDrag 起点锚定未扩面 | **升级**：站点一律交互起点锚定（源码级）；本地 stepDrag 重锚 startValue；影响 10 条/5 模型 | A- |
| 10 | ④D4 offset=0 | 站点 \|\|1 直证维持+闸门旁证；统一方向待用户实测读数 | A |
| 11 | ④D5 offsetCircle 普查 | **可关闭**：69 语料 3147 规则 0 样本 | B |
| 12 | ④D6 棘轮三函数 | stableLive2DDragValue 已有全文；本轮补两函数调用点；定案仍需实机 | A-/C |
| 13 | ④D7 triggerConditionMet 常量表 | **翻案定案**：常量表与函数体都在本地 chunk，全文解码 | A |
| 14 | ④§2.2 触发时序 D 级推断 | **升级 A**：triggerLive2DTouchArea 全文佐证本地顺序，唯白名单拒时冷却语义有差 | A |

## 3. ①组：type 分发表与数据面

**常量表解码**（su_modelRuntime-BDk3g7Pb.js:2625-2627 区域，串表辅助）：
`O=1,Se=2,k=3,A=4,Ce=5,j=6,M=8,N=9,we=10,P=11,Te=12,Ee=13,F=14,I=15,De=16`；
**Oe={O,Se,k,A,j,M,N,P,F,I}={1,2,3,4,6,8,9,11,14,15}**（与 l2d.ts:31 OE_TYPES 逐一相同）；
**L（click-action 型）={Se,j,N,P,I}={2,6,9,11,15}**；ye=7 不在两者（遗留「OE_TYPES 含 7」过期，
git 首提交 aaed762 即现值）。r4 记名 live2DRuleTriggerConditionMet 实为 **live2DRuleConditionMatches**（串 549）。

**live2DRuleConditionMatches 全文**（@107288）+ 触发路径复核（@151481）：
- type9（N）「参数逼近」：`|paramTarget − num| ≤ 0.05`（num 标量）。
- type11（P）「参数区间」：`num=[lo,hi)` 且 `lo ≤ paramTarget < hi`（num 数组）。
- type15（I）「近零」：`|paramTarget| ≤ 0.01` 且 `live2DGameIsPlayerTurn()`（游戏回合概念，本地无对应物）。
- 其余 type 一律 true。paramTarget = live2DOfficialParameterTargetValue(at.parameter‖rule.parameter)。

**数据面**（本地 36 份 touch.json / 站点缓存 33 船 1792 规则）：
- type9：本地 **0** 条；站点 12 条（全在 site_30510）→ 本地入档即可，无行为影响。
- type11：本地 **17** 条/3 模型（lafeier_2、meikelunbao_2、dafeng_7）；站点 19 条。样本 num 在但
  parameter 缺失 → 站点拒（target=undefined）；本地 ∈Oe 注册为「可点无效果」区。
  净行为差异≈叠加层 G 态显示。⚠️ dafeng_7 TouchDrag6 同名 5 段 num（[0,0.35]…[0.75,1]）
  无 parameter，疑数据侧应挂参数未挂（站点如何绑定未取证，见 §9）。
- type10（we）：本地 7 + 站点 13 = 20 条，∉Oe → 双方死区一致。样本 parameter 存动作名
  （'idle'/'touch_idleN'）；we 的消费分支本轮未定位，语义未知。
- type15：双方 0 条（语义解码备档）。
- **附带新发现**（均本地 0~1 条，纯入档）：type8(M)=delta 拖动（pointermove 分支
  fixLive2DParameterTargetValue(target+Δ/delta)）；type14(F)=active===1 时区间内自动触发；
  type12 num 监听含一次性触发路径（参数逼近 max(0.01,|num|·0.1) 即触发，@0x2ba 函数）；
  `actionTrigger.const_fit` 按 idle 预设参数（updateLive2DIdleRelationRule）；动画触发规则
  （trigger_name/trigger_rate/parameter_range，updateLive2DAnimationRule）。
- empty 占比：本地 709/1355（52.3%，typed 696/1237）；站点缓存 818/1792（45.6%）。
  原观察的 round1 文档已失，无原口径可复核；两语料同源无「差异」可测 → 建议降级为纯数据事实。
- ATA.idle 数字漂移：r4 记 453/874（2026-09-16）→ 现普查 697/1237（56.4%，33 模型），
  因 0d61551（2026-09-17）重下 9 模型数据；语义已按 r4 §4.3 落地（l2d.ts:328-329），无新问题。

## 4. ②组：guanghui 与 tips

1. **guanghui 点名 5 区**：候选解释维持（research_live2d动作链条-research2.md:104-109）——
   type12 名单中本地可感知的恰是 touch_head/body/special 三默认区 + TouchIdle 自身名单重复点名。
   本地复核：guanghui_9 type12=1 条（num [0.01,10]，无 drawAbleName/无 action）；empty-parameter
   TouchIdle 规则 39 条。type12 门控已实现（research2）。**原始观察（哪 5 区/何种表现）仍待用户补充**。
2. **tips 新 schema 消费与否 → 定案（修正 r2 结论）**：消费点 =
   `officialLive2DHitAreaHintVisible`（@tips 锚点，串 928/951/1003）——**提示图标的显隐**：
   - 前置：区须过交互门槛（live2DRulePointerEnabled / 默认区 allowed）；
   - 动作播放中：图标显示 ⟺ tips.animWhiteList 存在 drawable 匹配项且 white_list 含当前动作名；
   - idle：图标显示 ⟺ tips.idleBlackList **无**（drawable 匹配 ∧ idle 列表含当前 idleIndex）条目。
   - **不参与区交互门槛**（live2DRulePointerEnabled 不读 tips）。
   r2「全站 JS 0 命中死数据」修正为「仅消费于提示图标显隐层」。本地无图标层 → 不消费（no-op）
   仍正确，但 spec §10 表述需修正（§7 delta-3）。
   数据面：本地 **17/36** 份带 tips（六键全：id/tipsOffset/tipsScale/tipsIcon/idleBlackList/animWhiteList）；
   站点缓存 21 皮肤。guanghui_9：idleBlackList=[{drawable:[],idle:[0]}]（空 drawable 是否通配未解码）。
3. **新发现 parameterRange 是站点活数据**：站点写参数时钳幅
   （@164636：`currentSpec.live2dTouch.parameterRange[param]` 覆盖默认 min/max；mode1=set 钳幅、
   2=add、3=multiply）。本地 14/36 份有此键，本地引擎未消费、spec 未记载 → 见 §7 delta-4。
   ignoreDrag（34/36）与 dragRate（12/36）在串表 0 命中 → 死数据结论维持。

## 5. ③组：交互取舍项

1. **叠加层方案 A/B/C + 退化区门槛**：r3 文档失传，仓库内 rg 无残留（archive.md:7「方案A」是
   idle 循环旧案、l2dsu抓取模型说明.md:96「方案A」是抓取脚本，均同名不同事）。可重建的唯一碎片：
   r4 §6.3——r3 建议 5「给 ok 区加最小边长门槛」被站点源码证伪（hasUsableDrawableBounds 仅要求
   isFinite+w,h>0，无门槛）→ **退化区门槛建议关闭（站点口径无此物）**；A/B/C 内容需用户补充。
   本地现状：全区绘制/可用实色/OTG 描边+原因/T 降级仍可交互（l2d_touch_debug.ts:11,139,146）。
2. **forEach vs 择一**：站点事实旁证加强——命中=interactive 过滤→渲染序排序→取顶→**同 id 组
   filter 后逐区 triggerLive2DTouchArea**（@132194/@117978）。本地择一（l2d.ts:392-394）改逐区分发
   = 规格变更，待用户裁决（改则需独立规格+实测表重跑）。
3. **TouchBody 链自毁 / feiteliedadi 可玩性**：r3 §2.3 F-3 原文失传，r4 §4.5 维持「链入口出视口
   推 3 步自毁」；本地链实现 main.ts:172-200。feiteliedadi_3 的 TouchDrag4/5/6 已因 ATA.idle 修正
   恢复（l2d.ts:328-329）；9 个退化区属几何事实（r4 §4.5）。→ 需实机复核，维持挂起。
4. **stepDrag 起点锚定未扩面 → 升级为源码级分歧**：站点一切线性拖动值 =
   `live2DLinearDragValue(rule, startValues.get(rule.id) ?? rule.startValue ?? 0, unityDragDelta)`
   （@148118 等）——**交互起点锚定**；本地 stepSlide 有 holdBase（l2d_params.ts:328）而
   stepDrag 每次从 `r.startValue + |hypot|` 重锚（l2d_params.ts:343），且无轴选择/无保号。
   影响面：本地路由进 stepDrag 的带 offset type1/6/7 规则 = **10 条/5 模型**
   （feiteliekaer_4×4、bunao_3×3、aersasi_2、feiteliedadi_3、mojiaduoer_4）。见 §7 delta-5。

## 6. ④组：站点语义取证

1. **D4 offset=0**：站点 `||1` 直证维持（r4 §3.3，A）；新增旁证——前置闸门
   `ruleHasLive2DSlide = ruleHasLive2DLinearOffset(rule) || rule.offsetCircle?.pos`（@138564），
   0 轴规则仅当另一轴≠0 才进择轴。用户实测矛盾维持 r4 §8-1 两候选（视觉无变化/测错区），
   需用户在奇尔沙治 199041 垂直拖 TouchIdle3/10 并读参数面板（r4 §9-C 可复现）。本地保留
   0 轴排除（l2d_params.ts:317-319 注释即本结论）；r4 §7.2.3 方向=恢复 ||1+补闸门（规格变更）。
2. **D5 → 可关闭**：offsetCircle 字面在本地 36 份 + 站点缓存 33 船（3147 规则）**0 命中**；
   全量索引 su_ships-CN.json（896 船）无内联规则，离线不可扩面。引擎支持 pos
   （live2DDragParameterValue circle 分支 + 转盘 `start??0`）但数据侧零使用 → 边界样本不存在于
   可获得语料，记「0 样本」事实入档即可。
3. **D6 棘轮三函数**：stableLive2DDragValue 全文已有（r4 §3.4，A）；本轮补调用点——
   snapLive2DTouchParameter 在拖拽结束 forEach snap→save→revert 链（@135835）、
   live2DDragStartedAtTarget 用于参数条件路径（@147889）。三函数机制定案仍需实机数值对照
   （r4 §8-2：wuqi 399042 拖 TouchDrag7 连续读数）。维持挂起。
4. **D7 → 定案**：见 §3（r4 §8-5「常量表在未下载 chunk」被推翻——就在 runtime.js 头部；
   顺带提示 r4 其他「chunk 缺失」结论也宜复核，如 §8-3 的 repeatsCurrentIdle 其实已有全文）。
5. **§2.2 触发时序 → 升级 A 级**：triggerLive2DTouchArea 全文（@151481）权威顺序：
   80ms 防抖 → 冷却查 → ConditionMatches（type15 加 GameMove）→ repeatsCurrentIdle
   （activeData = active_list[si] ?? 整体）→ N/P 复核 → **写冷却**（limitTime 秒→ms）→
   type1/4 target≈num 时清 target → **白名单** officialLive2DActionAllowed（此刻 ATA 未应用
   ——「白名单用触发前 enable」获得源码直证）→ 拒则 return true（**冷却已吃**）→ 参数写入
   （circle：|cur−target|<0.05 时翻回 startValue；target_focus===1 时 smooth=0）→
   链步进 (si+1)%len（revertActionIndex===1 时复位参数）→ save 持久化 → 播放
   （idle 组名走 playLive2DIdleMotion 特殊路径）。
   与本地 spec §5 对照：核心顺序一致（白名单先行、成功后应用/持久化），**唯白名单拒时
   站点已写冷却、本地 dispatch 失败不 save**（blockedEnable 区冷却语义差异，影响面小，
   delta-6）；spec §11「D 级推断若被推翻须修正」可解除。

## 7. 证据沉淀与 spec 回写建议（delta 候选，落地须走 /replan + 人工批准）

1. delta-1（§11/§5）：D7 定案——type9/11/15 条件语义与 Oe/L 常量表入档；「需下载 chunk」
   结论撤销；§10「明确不做」补 type9/11/15（数据面小，双方 0~17 条且净行为差异≈叠加层显示）。
2. delta-2（§11）：D5 关闭——「offsetCircle 数据面 0 样本（69 语料/3147 规则）」入档。
3. delta-3（§10）：tips 表述修正——「死数据」→「仅消费于站点提示图标显隐层（H 层），不参与
   交互门槛；本地无图标层故 no-op 维持」。
4. delta-4（新条目）：parameterRange 为站点活数据（写参钳幅），本地未消费——列未实现清单
   （遗留候选，实现另立项）。
5. delta-5（§9 偏离项）：stepDrag 分歧入档——站点交互起点锚定+轴选+保号 vs 本地 startValue
   重锚+幅值累积（10 条/5 模型）；统一=规格变更待裁决。
6. delta-6（§5 注）：触发时序升级 A 级；补记「站点白名单拒时冷却已写」差异。
7. delta-7（§11）：①组清单入档——OE_TYPES 核对一致（关闭「含 7」）、type8/14/12 触发/
   const_fit/动画触发等站点机制补记、empty 占比降级为数据事实、ATA.idle 数目更新为 697/1237。
8. 契约候选（不强立）：「live2d-models 目录被 .gitignore 覆盖，rg 普查数据须用 python glob
   或 rg -uu」——本轮实测 rg 静默漏检 tips（建议入 spec-writing.md 检查项）。

## 8. 逐项处置建议与优先顺序

- **立即入档批**（不改行为；一次 spec 回写完成）：总表 #1/2/3/5/11/13/14 对应 delta-1/2/3/6/7。
- **待用户裁决**（规格变更，各自需独立规格）：#7 forEach→逐区分发；#9/D4 统一方向
  （r4 建议 ||1+闸门+stepDrag 线性化可并案——同属拖动语义对齐）；#13 type11/9 条件门槛是否实现。
- **需人工/实机**（清单化，r4 §9-C 命令可直接用）：#4 guanghui 5 区原始观察；#10 D4 奇尔沙治
  读数；#12 D6 拖 TouchDrag7 读数；#8 TouchBody 自毁复核；#6 方案 A/B/C 内容补充。
- **维持挂起**：#12 三函数机制定案（依赖上一行实机数据）。
- 建议顺序：先做「立即入档批」→ 用户裁决拖动语义并案（delta-5+D4）→ 人工取证集中一次实机。

## 9. 疑点与需人工协助清单

1. dafeng_7 TouchDrag6 五段 type11 num 无 parameter——站点如何绑定参数未取证（数据侧疑点）。
2. type10（we=10）消费分支未定位：∉Oe/∉L 已证，语义未知（20 条死区数据）。
3. tips.idleBlackList 空 drawable 数组是否通配（Ve 匹配器语义未解码）——仅影响图标层，本地无影响。
4. 站点 DNS 故障（apex 无 A 记录+301 死循环）：后续需在线取证（如新 chunk、全量船规则）前
   先验证站点恢复；r4 附录 C 命令需改用可用域名。
5. r4「定义在未下载 chunk」类结论（§8-3/§8-5）已部分被本地 chunk 推翻——凡引用 r4 该类表述处
   需逐条复核（本轮已复核 triggerConditionMet 与 repeatsCurrentIdle 两处）。
6. 需人工补充/实测四项见 §8（guanghui 5 区、D4 读数、D6 读数、TouchBody 复核、A/B/C 内容）。

## 10. 人工取证操作清单（步骤化）

> **2026-09-27 更新**：A 组两项已由 AI 代跑完毕（§11.1/§11.2），B 组两项已降级为
> 本地决策备忘（§11.3/§11.4，站点 DNS 故障无法实测且决策不依赖实测），仅 C-1 仍待用户拍板。

> 分三组：A=本地可立即做（2 项）、B=需站点恢复后做（2 项）、C=用户回忆/拍板（1 项）。
> 通用记录格式：每步一行「操作 → 观察（数值/组名/状态）」；读数一律记数字，不记观感
> （r4 教训：人工观感是取证链最弱一环）。实测前通读 spec-l2d-touch-engine.md §12（区位置
> 随姿态漂移，动作前即时重扫；内嵌浏览器需 `visibility.set(true)`）。

### A-1 TouchBody 链自毁复核（本地，~10 分钟）→ ③组 #8

1. 启动前端加载 feiteliedadi_3（或任一有 touch_idleN 组的模型），打开调试叠加层。
2. 记录初始 idleIndex（叠加层左上角读数）。
3. 连续单击身体区，每次记录：点击序号 / 播放的组名 / idleIndex 变化 / 是否有反应。
4. 连点到链走完一轮：观察是否转播 touch_body/touch_*（冷却生效）。
5. 闲置 10 秒后再连点，确认链重置（main.ts:175 CHAIN_RESET_MS）。
6. **关键观察**：TouchBody 区或其链入口是否在第 N 步后移出视口/不可点（「推 3 步自毁」）；
   若复现，记录 N 与画面表现（区内坐标估计）。
- 判定：复现 → 维持挂起待修；不复现 → ③组 #8 可关闭。

### A-2 guanghui 5 区本地复现（本地，~15 分钟，配合回忆）→ ②组 #4

1. 先凭记忆写下：当年点的 5 个区（区名或身体部位）、期待的行为、实际表现。
2. 加载 guanghui_9 + 叠加层，定位对应区，抄下叠加层状态（ok / G / blockedEnable 标注）。
3. 逐区单击，记录：区名 / 状态 / 是否播动作 / 播了什么 / idleIndex 变化。
4. 对照 research_live2d动作链条-research2.md §5-Q1 候选解释（type12 名单 + TouchIdle 名单
   重复点名）核对吻合度。
- 判定：5 区全部落在候选解释内 → ②组 #4 关闭；有例外区 → 列区名另立小研究。

### B-1 D4 offset=0 读数（需站点恢复）→ ④组 #10

1. 前置：验证 l2d.su 可访问（本轮 2026-09-27 实测站点 DNS 故障，恢复后再做）。
2. 打开站点奇尔沙治 199041 皮肤页，F12 打开参数面板（或控制台读参数值）。
3. 定位 TouchIdle3/10 对应拖动区（r3 §5.4.4：ox=+150, oy=0）。
4. 区内做**纯竖直**上拖/下拖各 3 次，拖动中每约 15px 抄一次参数数值。
- 判定：数值全程无变化 → 「站点 0 轴不参与」观感成立，本地 D4′（0 轴排除）可永久化；
  数值有变化 → 站点 ||1 生效且差异不可见，按 r4 §7.2.3 统一为 ||1+前置闸门（规格变更）。

### B-2 D6 touch_drag7 数值对照（需站点恢复）→ ④组 #12

1. 站点 wuqi 399042，定位 TouchDrag7（startValue=180，rangeAbs=0）。
2. 上拖/下拖各 3 次，每约 15px 抄一次数值（必须数字，非「方向对不对」）。
3. 用 r4 §9-C ⑦ 脚本生成三机制预测轨迹：棘轮（stableLive2DDragValue 只许远离起点）/
   快照吸附（snapLive2DTouchParameter）/ 起点条件（live2DDragStartedAtTarget）。
4. 逐点对照，唯一吻合者即为 D-g 定案。
- 记录：位移-数值对表（两方向 × 3 次）。

### C-1 叠加层方案 A/B/C 补充（拍板项，无取证）→ ③组 #6

r3 §7.1 原文失传，二选一：
1. 凭记忆写出三方案大意（每个一句话即可），供重建选项表；
2. 或放弃考古，直接在现叠加层（全区绘制/可用实色/OTG 描边+原因/T 降级仍可交互）上重新
   拍板显示策略。注意 r4 §6.3：退化区「最小边长门槛」是站点口径外自创，若要恢复须标注为
   本地增强、非对齐项。
- 产出：一句话裁决（维持现状 / 换方案），由 /replan 落地。

## 11. AI 代跑实测与决策备忘（2026-09-27，浏览器自动化 + 本地模拟）

> 方法：后端 12393 `/m` 页 + `window.__vtuber.renderer` 句柄 + `cua` 真实点击 +
> `hitZoneAt` 每次点击前重扫命中点 + `playAction` 运行时钩子记录（只读插桩，未改代码）。
> 全程未改任何源码/测试/规格。

### 11.1 A-1 feiteliedadi_3 TouchBody 链（实测完成）

- 复位后首扫：TouchBody 区 12 网格点可命中（中心≈(632,392)）；touch_idle1~9 组齐全。
- **点击 1-7：touch_idle1→7 按序播出，命中点稳定，无几何自毁**。
- 点击 8/9/10 及闲置 11 秒后：全部静默无动作。
- **根因①（入口白名单锁）**：第 7 步规则 TouchDrag9（id 49902209）的 ATA.enable=
  [touch_idle, touch_idle8, touch_idle9] **不含 touch_body** → main.ts:168 入口闸
  （R2-b 本地设计：伪规则过动作闸）静默返回。已排除其他层：touch_idle8/9 的
  type12（null=不门控）/ATA（enable=[] 放行）/available（组存在）三层闸全绿。
- **根因②（入口几何退化，链后出现）**：链后姿态全画布扫描 TouchBody/Head/Special **零命中**；
  TouchBody 绘画件包围盒 = **7×6px @ 模型坐标 (3330, 20545)**（约 25 屏外）；执行复位
  （resetTouchChain+resetAll+playIdleOnce）后**不恢复**——链前可点、链后不可点，对照实测。
  机制候选=存在不被 resetAll/playIdleOnce 覆盖的参数残留（research2 §5-Q2 家族），待另证。
- **解锁路径存在**：白名单内 TouchDrag10@(840,220) / TouchDrag11@(270,260) 直点即播
  touch_idle8（实测）；但入口（TouchBody）已死，用户视角=「点几下身体就不动了」。
- **结论**：r3 F-3「链入口出视口（推 3 步自毁）」复现为**复合机制**（白名单锁 + 几何退化 +
  复位不可逆），证据 C→A；main.ts:176 的 60s 静默冷却未参与本轮（入口先被锁），但其同样
  压制闲置 10s 重置。是否收敛实现行为=规格变更，待用户裁决。
- 顺带发现（文档-实现漂移）：spec §5 写「冷却期播 touch_body/touch_*」，实际 main.ts:176
  冷却期静默 return——spec 文本待订正（delta 候选）。

### 11.2 A-2 guanghui_9 全区普查（实测完成，不依赖用户回忆）

- 注册 63 区；门槛矩阵：53 区可交互，**10 区被防重复拦**（TouchIdle30~37/41，ataIdle=0）。
- **物理可达（idle0 姿态、全画布 10px 扫描）仅 7 区**：TouchBody（240 扫描点）/ TouchDrag1 /
  TouchDrag2 / TouchDrag3 / TouchDrag15 / TouchHead / TouchSpecial；其余 56 区不可达
  （透明标记/退化投影/被高层遮挡——与 r4 §6 时代结论一致）。
- 行为：TouchBody→touch_idle1（链第 1 步正常）；TouchSpecial→touch_special ✓；
  TouchDrag1/2/3/15 tap 无动作（纯参数型/无 action，符合 r2_v3「可点无效果」语义）；
  **TouchHead 在链步进 1 步后被白名单静默拒**——与 11.1 根因① 同族（ATA.enable 不含 touch_head）。
- **②-1「guanghui 点名 5 区」处置建议**：原始观察已不可回忆；本轮普查显示现行版本无
  数据性异常区（唯一异常=白名单锁族，属实现议题）。建议以本矩阵替代原始观察关闭该悬置项。

### 11.3 B-1 → D4 决策备忘（0 轴规则影响面 + 双语义数值模拟）

- 数据事实：全库**单轴为 0 的线性规则 81 条 / 24 模型**——且全部 81 条带 offset 线性规则
  都是单轴 0（无双轴规则）。
- 模拟（r4 §9-C 同款，4 方向 × 81 条 = 324 组合）：**差异 115，全部为交叉方向**；一致 209。
  站点 `||1` 语义下交叉方向一律满程扫动（例：aerbien_3 TouchDrag1（ox=0,oy=-40）纯水平拖
  ±120px → 站点=10（满程），本地 0 排除=0）。
- **决策项（二选一，替代原 B-1 站点实测）**：
  - A 站点逐字对齐（||1+前置闸门）：81 条规则交叉方向拖动变为满程扫动，观感「参数乱跑」；
  - B 保留 0 轴排除（现状 D4′）：放弃逐字对齐，维持偏离项。
  建议 B（观感优先，先例=r2 收回 D1/D3「实测为净伤害的对齐不采纳」），**由用户一次裁决**。
  原「站点当年为何无误触发」考古项降级为可选（等站点恢复，r4 §9-C 命令备好）。

### 11.4 B-2 → D6 决策备忘（棘轮三函数）

- 棘轮作用域（stableLive2DDragValue：type1/4 且无 offsetCircle.pos）：全库 type1/4 仅
  **6 条 / 3 模型**（aersasi_2 TouchIdle1、feiteliedadi_3 TouchDrag12、feiteliekaer_4 ×4），
  其中带 offset 的参数驱动型仅 **2 条** → 实现棘轮的最大影响面 = 2 条规则。
- D2/D3（门控+符号序）已落地并有运行时对拍（test_l2d_clamp_chain_runtime.py），drag6/7
  主症状已消；棘轮属站点 parity 增强，且 stepDrag 起点锚定扩面（研究 §5-#9，10 条/5 模型）
  影响面更大、应优先。
- **建议**：不实现，入 spec §10 未做清单（注明机制/作用域/影响面）；原站点读数项降级为
  可选考古。**由用户一次裁决**。
