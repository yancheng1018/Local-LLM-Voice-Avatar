# 极简前端 · Live2D 渲染与互动（手势 / 目光跟随 / 触摸引擎 / 一键复位）

> 拆分自 minimal-frontend.md（2026-09-15）。总入口与遗留 → minimal-frontend.md；兄弟分册：基础管线（工程/协议/历史/口型）→
> minimal-frontend-foundation.md、Spine → minimal-frontend-spine.md、模型切换 → minimal-frontend-model-switch.md、
> 调试工具 → minimal-frontend-live2d-debug.md。
> 与 docs/context/live2d.md 的分工：那边=模型资源与后端侧契约（如 stage4 契约 8/9）；本文件=极简前端渲染器侧行为

**阶段四已完成**（2026-09-12，手势互动 + 目光跟随 + 心跳保活）：

- **互动区域判定来源（重要）**：头/身区域是**前端自己估计的**（模型显示
  包围盒顶部 30% 为头，其余为身）——碧蓝航线模型**没有** Live2D HitAreas，
  游戏和 l2d.su 的区域判定都在各自代码里，不存在于模型文件中。
  唯 mao_pro 有真实 HitAreas（但其热区绘画件位置与视觉位置不重合，
  命中区在胸口一带）；tapMotions 热区表只对它的非空热区名生效
- **真实互动区域数据已接入（2026-09-12 第二轮）**：l2d.su 的互动配置在
  `https://l2d.su/data/ships/CN/<shipGroupId>.json` 的
  `ship.skins[].model.live2dTouch`（rules 含 drawAbleName 热区绘画件名、
  parameter 动作组、actionTrigger、dragDirect 等；索引在
  /data/ships-CN.json，按 prefab 匹配）。已批量下载 36 个模型写入
  `live2d-models/<name>/touch.json`（缺 bulaimodun_5、yichui_2——
  非 L2D+ 皮肤；mao_pro/shizuku 非碧蓝航线源）。
  ⚠️ 大部分 TouchIdle/TouchDrag 绘画件是**画布外虚拟标记**（y -12000~
  -56000），不做区域定位，游戏按点击次数/方向触发——前端已过滤画布外
  规则，这些模型退化到递进链/头身启发式（行为与 l2d.su 等价）；
  部分模型（吾妻 wuqi_3）的规则绘画件在画布内，点中即播对应动作。
  touch.json 加载失败/缺失不影响功能（启发式兜底）
- ⚠️ **递进链动作组必须交互时实时取**：处理器赋值发生在新模型 load 完成
  前，赋值时 getMotionGroups() 返回上一个模型的组（切吾妻→Mao 后链里
  还是吾妻的 touch_idle，导致 Mao 点身播不出动作）
- **完整手势互动（仅 L2D）**：canvas 层手势状态机区分三种手势——
  单击 / 拖动（位移>40px 即触发一次）/ 长按（按住≥800ms）。选组链：
  单击头→`touch_head`→touch_special→touch_*；单击身→**touch_idle 递进链**
  （复刻碧蓝航线连续触摸：把 touch_idleN 组按编号排序，连点依次推进，
  闲置 10s 重置回开头，走完一轮冷却 60s，冷却期播 touch_body/touch_*；
  缺某些编号的模型自动跳过）；拖动→`touch_drag*`；tapMotions 热区表
  仅对有真实非空热区命中的模型生效；全部 FORCE 优先级。
  递进链逻辑参考 l2d.su 查看器（其 JS 解析动作组名为 type+number 并按
  编号排序推进，互动数据来自游戏 Lua 衍生的 /data/ships/CN/<shipid>.json，
  该文件只有台词/语音映射，不含区域数据；区域判定站点也是前端自己做的）。
  实测：光辉 tap@head→touch_head、tap@body→touch_idle1→3→6→7→8→9
  （跳号因模型缺编号）、drag→touch_drag10、longpress→touch_special；
  信浓（tapMotions 合并）、mao_pro（空串组）均正常
  - 碧蓝航线模型没有 Live2D HitAreas（游戏用屏幕区域判定），头身区域是
    前端按包围盒估计的；互动语音/台词不在模型资源里，无法还原
- **目光跟随**：`autoHitTest:false, autoFocus:true`（0.5.0-beta 中
  autoInteract 已废弃，且其 hit 事件只在命中时才发会挡死兜底，故
  hitTest 由 canvas 手势层自己做）
- ⚠️ **pixi v7 必须设 `stage.eventMode='static'` + `stage.hitArea=app.screen`**，
  否则模型上的指针事件时有时无（pixi-live2d-display 只把 model 设为
  interactive，stage 不可命中时事件派发不稳定）
- **心跳保活**（ws.ts 内部）：30s 发 `heartbeat`，90s 没收到任何服务端
  消息则主动断开走 2s 重连。注意 WSClient 内部 `this.ws` 是原生 WebSocket，
  页面侧包 `__vtuber.ws.send` 拦不到心跳，要在 `WebSocket.prototype.send`
  上埋点（实测 65s 两跳）
- **mao_pro 表情肉眼验收完成**：真实对话 LLM 输出情绪 → expressions[0]
  应用（exprLog: 1→7）；肉眼确认表情 1=眯眼笑、7=瞪眼怒，差异清晰

**stage2 参数驱动引擎（2026-09-13，热区/动作链升级）**：

- `src/renderer/l2d_params.ts`：l2d.su 同款规则驱动参数引擎（mode1 circle/drag 状态机 +
  mode2 指针反应 + type103 查表 + localStorage 持久化）。契约与测试口径已并入
  `spec-l2d-touch-engine.md`（原 temp_spec_stage2.md），逆向结论见 `spec-l2dsu-engine.md`
- ⚠️ **行数上限例外：该文件 390 行封顶（2026-09-18 阶段B 关系预设层后实测 390；
  stage2 时为 215/220 封顶）**。
  理由：4 轮压缩（242→215）已删尽全部可删排版，剩余超标全是逆向语义契约注释，
  删了丢可读性；拆分方案已否决——纯函数与状态机共享 ParamRule 域模型，
  且 test_params_module_exists 按文件路径断言四个 export function 位置（测试语义不得改）。
  若 stage3 后续给引擎加 listenerData 等新职责导致明显超限，再按职责拆分（数学纯函数 vs 状态机）
  （阶段B 已拆出关系预设纯函数 l2d_params_relations.ts，86 行）

**stage3 一键复位（2026-09-14，Live2D 模型复位）**：

- `index.html` 顶栏「↺ 复位模型」→ `ui.onResetModel` → `L2DRenderer.resetToInitialMotion()`。
  复位序列：停全部 motion → 清 `touchPlay` 播放门控 → `resetExpression()` →
  `TouchChain.reset()` → `playIdleOnce()`。文案固定 `模型已复位` /
  `当前模型不支持复位`
- ⚠️ **复位是纯本地视觉操作：禁止触碰对话生命周期**。具体地，`ui.onResetModel` 内
  **不得发送会取消 / 重置 / 并发化当前对话轮次的 WebSocket 指令**，尤其不得发
  `interrupt-signal`——服务端收到它会取消角色正在生成的回复，用户点「复位模型」却丢失
  回复且无任何报错，这是最容易顺手照抄 `onSend`/`onInterrupt` 模式踩到的坑。
  复位只打断前端音频队列、清本地 `turnActive`/busy，**本地轮次状态因此与后端脱钩**：
  后端仍会推完 `backend-synth-complete` 与后续 `audio` 帧（`audioQueue.interrupt()`
  自增 generation，旧播放循环自行退出，不串台），但下一轮 `onSend` 时
  `turnActive`/`audioQueue.busy` 均为 false，**不会补发 `interrupt-signal`**，
  服务端上一轮与新一轮可能并存。这是有意设计（视觉复位不碰对话），非缺陷。
  注意 `test_main_resets_chain_and_audio_only` 目前断言该回调块内**完全不含** `ws.send`，
  比"不发 `interrupt-signal`"更严：若将来确需发送与对话生命周期无关的消息
  （遥测、只读状态同步等），必须先证明它不改变服务端轮次状态，
  并相应收窄该测试中"禁止全部 `ws.send`"的断言，而非绕过它
- **`resetToInitialMotion?()` 当前是 L2D 专属能力，不是跨渲染器契约**。本阶段只由
  `L2DRenderer` 实现，且**不打算**为 Spine 补一个假复位：现有两个 cutscene Spine 模型
  只有环境循环动画（loop/loop_2/cut_A/B），没有与"回到模型初始动作"等价的语义，
  硬套待机动画会让用户以为复位生效而实际语义不同。因此接口刻意声明为可选
  （`CharacterRenderer.resetToInitialMotion?()`），`SpineRenderer` 不实现，
  `main.ts` 走「当前模型不支持复位」分支——**能力缺失必须如实上报，不得伪装成功**。
  这不是永久禁令：若将来拿到带表情动画的 Spine 模型、能定义其"初始状态"，
  允许 Spine 实现复位，但须同时补验收口径与该渲染器的测试；
  另注意 `resetExpression(): void` 是 Spine **也实现**的非可选方法（打断 / 新对话 /
  chain-end 都调它），故 Spine 的"打断走表情复位、复位按钮走不支持"是有意的不对称
- ⚠️ **`resetTouchChain` 可空，且注入是「每模型一次」而非一次性**：L2DRenderer 不持有
  TouchChain 实例（实例在 main.ts 的 `set-model-and-conf` 处理器里按模型闭包创建，
  键 `l2d-touch:<角色名>`），链归零必须经注入的只写回调 `resetTouchChain: (() => void) | null`。
  三处推论：
  1. **可空即未就绪**：模型未加载、当前是 Spine 模型时该字段为 `null`，复位必须在链缺席时
     仍完成表情与初始 idle——故 `this.resetTouchChain?.()` 包 try/catch，且
     `resetExpression()` 放在它之前（注入回调由 main.ts 提供，抛错不能连带吞掉表情与 idle）
  2. **每次换模型都重新注入**：renderer 实例会被 `ensureRenderer()` 销毁重建，
     旧实例的回调指向上一个模型的 TouchChain；依赖「重新赋值」而非「注入一次永久有效」
  3. **`playIdleOnce()` 依链状态选组**：`chainIdleIndex()` 为 0 才播初始 `idle` 组，
     否则播 `idleN`——链归零失败时复位会退化为播当前递进组的 idle（可接受降级，不报错）
- 复位调用的是模块级 `renderer`，而注入发生在 `activeRenderer` 上：二者恒为同一实例
  （`ensureRenderer()` 只改 `renderer` 自身并原样 return，无第二处赋值）。
  后续若引入多 renderer 实例缓存（预加载）必须重新审视这条隐性依赖

**stage7 热区调试叠加层 + r2 系列修正（2026-09-16，已验收）**：

- 叠加层与调试滑条条目（含 l2d_touch_debug.ts 行数例外）已拆至 minimal-frontend-live2d-debug.md（R30，2026-09-30）
- ⚠️ **行数上限例外：`l2d.ts` 1081 行**（仓内最大源文件、核心渲染器；research3 收尾
  裁决 2026-09-18：拆分属重构工程另立项，登记例外不设 LIMIT 守护，下次对其加新功能
  前先决策拆分）
- r2 系列（v1~v4）四轮修正定案已并入 spec-l2d-touch-engine.md（透明剔除收回/G 前移/
  findChainRule action 优先/无 action 放行/ATA.idle 防重复方向/clampChain 三步链/resolve
  触发时序/0 轴排除保留/起点锚定/resetAll）；站点取证与 D4~D7 遗留见
  research_live2d-hotzone-touch-r4.md（已保留归档）

**动作链条修正阶段 0+A（2026-09-17，已验收）**：

- ⚠️ **硬性约定：ParamDriver 挂点必须是 `afterMotionUpdate`**（l2d.ts 常量
  `PARAM_DRIVE_EVENT`）。库 cubism4.es.js InternalModel.update 帧内次序：动作曲线写
  参数 → `afterMotionUpdate` → saveParameters 快照 → 眨眼/物理/姿势 →
  `beforeModelUpdate` → model.update → loadParameters **用快照覆盖**——挂
  beforeModelUpdate 的写入帧末被还原，touch 参数恒 0。口型 attachLipSync 保持
  beforeModelUpdate 不迁移（无动作曲线竞争）。守护：`tests/test_l2d_param_hook.py`
  （静态锚点 + 200 帧运行时对拍写入值收敛）
- ⚠️ **硬性约定：库的 idle 自动播放必须关闭**——`Live2DModel.from` 传非空哨兵
  `idleMotionGroup:'__no_auto_idle__'`（库仅在 truthy 时覆盖 groups.idle，空串无效；
  不存在的组名使 startRandomMotion 安全返回 false）。idle 只能由本地 `playIdleOnce()`
  按 idleIndex 驱动，否则 Idle 组多的模型（xinnong_6 15 条）静置自发乱跳。附带效果：
  motionPreload:'IDLE' 不再预载任何组，动作首次播放懒加载（可接受）。守护：
  `tests/test_l2d_idle_autoplay.py`
- 数据面：9/36 模型 touch.json 曾为站点**前一编号皮肤**数据（系统性错配），已重下修复
  （数据源校验规则见 docs/assets/README.md）；根因详情 research_live2d动作链条修正.md。
  阶段 B 已完成验收（2026-09-18）；type12 裁决已随 research2 落地（见下节）；阶段 C
  其余项见状态入口遗留

**live2d动作链条-research2 实施（2026-09-18，已完成验收）**：

- **type12 全局动作裁决**（模块约定 R2-a，2026-09-18 验收定案）：判定值源 = ParamDriver 内部值（本地参数
  权威层，不得读 core 实时值），半开区间 `lo<v<=hi`；扩展判定**优先于** ATA 全局名单
  （返回布尔即短路，v2 spec §3.2）。入口：`l2d_touch.ts type12Decision()` +
  `TouchChain.paramGate`（main.ts 注入渲染器实现）；l2d.ts 命中门槛与叠加层
  blockedEnable 走 `actionAllowedWithParamGate` 组合闸
- **默认热区伪规则过闸**（模块约定 R2-b，2026-09-18 验收定案）：touchhead/touchbody/touchspecial 与 gname
  直播兜底过同一动作闸；**只受约束、不产生约束**——不推进链状态/冷却（站点默认区
  仅过闸语义，v2 spec §2.5）
- **idle 循环化方案A′**（模块约定 R2-c，2026-09-18 验收定案；初版方案A 已被人工验收证伪）：本地库
  解析 Meta.Loop 但不接线（pixi-live2d-display cubism4.es.js :3283→:3822 存
  _motionData.loop 无消费者，播放判定只读 _isLoop 默认 false）——「尊重数据标志」须
  playIdleOnce 播放成功后显式 `enableIdleLoop`（setIsLoop(true)）落实，**仅 idle 路径**
  （全库动作数据 Loop=true 而站点动作单次，循环不得外溢）；库自动播放哨兵
  `'__no_auto_idle__'` 保留（禁随机跳，非禁循环）。自愈分层表述废止（research3 F3/F8 证伪）：drag4/5 为 slide 型 mode-1 注册参数，同样被
  ParamDriver 每帧钉死；idle 曲线 touch_drag3/4/5 首末值均 0 且被钉死层覆盖，无自愈层；
  drag4/5 热区可见性由 touch_drag3 值驱动美术层（opacity=值/10，值=10 才入画布）——值卡中值
  则三连锁（卡值/type12 门死锁/热区不出现），详见 research_live2d动作链条-research3.md。
- v2 修正说明（2026-09-18）：上行原方案A 表述「循环由 motion3.json Meta.Loop=true 数据
  标志驱动」为验收失败根因（库解析 Loop 但无消费者，须显式 enableIdleLoop；证据与
  修订原 temp_spec_v2 §0，过程文档已清理，摘要见 archive.md 2026-09-18 research2 条目；
  研究文档 research2 §3.3 机制归因同步作废，以本条为准）
- **叠加层 core 写入值列**：`TouchZoneState.coreValue`（core.getParameterValueById，
  旧 core 无此 API 自动降级单显）；标签 |内-核|>0.05 双显 `内→核`；持续 60 帧
  idleText 追加 ⚠写入失效（写入失效=动作曲线残留/层间混淆定位仪，research2 §5-Q5）
- **touch.json 清库**（模块约定 R2-d，2026-09-18 验收定案）：全库对照站点快照（su_ships-CN.json +
  _ships_cache），确认「站点无规则而本地有」2 例——shengluyisi_4（54 条 = _5 错配）
  与 chaijun_4（17 条），已清空 rules=[]（文件保留，默认三区靠代码合成仍可用）；
  shi_3 同型嫌疑排除（71==71 与站点同源）。守护：test_l2d_touch_data.py CLEARED

**research3 修正（2026-09-18，已完成验收）**：
- F1 根因：pointerup 重命中失配 → poke 丢失 → 值冻在按下点角度派生中值（4.76/7.73 类）；
  值→几何自反馈（F2：值 0→10 时 TouchDrag3 模型坐标 x 1675→−14418）使抬起命中必然失配。
- 修复：emitInteraction 增 pressedZone 回退参数（抬起命中失败→用按下区；drag 不回退），
  tap/longpress 的 poke 与动作分发均落在按下区。
- F5 死锁链（修复后解除入口）：值卡 (0.01,10] → type12 门关 → touchbody 链不推进 →
  idleIndex 恒 0 → revertOnIdle 不触发。修复后首次点击即收敛到 10，drag4/5 入画布可拖，
  复位路径恢复可达。

**动作链条域结论提炼（distill-b3，2026-09-29；来源 research_live2d动作链条修正/-research2/-research3 与 manual_live2d动作链条验证.md，均保留作证据链，处置行见各文件文首）**：
- ⚠️ **已裁不修红线（站点同款非缺陷，勿再立项修复）**：S3 touch_head/touch_body 播放后 touch_drag10 0→4（站点实测同样变 4，动作曲线末值属数据设定）；F1 feiteliedadi_3 TouchDrag6 初始不可互动（站点初始同样无此热区）；另不得为提高可点率放宽 opacity/门槛判定（r2 已证 D1 净伤害）。依据：修正.md §5.2/§5.6/§6.4（T3/T5 实测）
- ⚠️ **站点侧未取证残留（未来立项前置，勿当已验证事实引用）**：面板↔模型双路径后半——motion 曲线写入与目标表交互（修正.md §8-1，research2 §3.1 定案一半）；`ruleHasLive2DSlide`/`playLive2DIdleMotion` 函数体（research2 §8-5）；站点 dial 写入时机与值→几何自反馈对照（research3 Q3）
