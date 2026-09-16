# 站点引擎逆向记录 · l2d.su modelRuntime（源码级直证，2026-09-17）

> 本文件是 **l2d.su 前端引擎（modelRuntime chunk）的源码级逆向记录**，供后续开发/维护复用。
> 与 `spec-l2dsu-engine.md`（stage2 逆向，部分结论为推断/含混淆名）的关系：**本文为源码级直证版本，
> 冲突处以本文为准**；stage2 的 T12 失败说明与 §5 的 `Ve()` 判定等仍有效。
>
> 取证手段：下载 `https://l2d.su/assets/modelRuntime-BDk3g7Pb.js`（201,926 字节，2026-09-17 取），
> 用其自带解码器还原全部混淆字符串（`_0x25d3` = base64 表 + decodeURIComponent），
> 逐函数反混淆后阅读。**产物已归档**（见 §8），可复核、可重放。

## 1. 混淆与解码方法（可复现）

站点 JS 的字符串经两层混淆：

1. `function _0x1cdf(){const _0x50e0a3=[...]}` —— 字符串表（base64 变体，14286 字符）
2. `function _0x25d3(i)` —— 取表项 → 自建 base64 解码（表 `abc...XYZ0-9+/=`）→ `decodeURIComponent`
3. 启动时 IIFE `(function(t,e){...}(_0x1cdf,0xe81e9))` 对表做**旋转**（按校验和调整 shift 次数）

解码复现（Node，已验证 642 条字符串）：

```js
const src = require('fs').readFileSync('su_modelRuntime-BDk3g7Pb.js','utf8');
const tStart = src.indexOf("function _0x1cdf(){const _0x50e0a3=['");
const tEnd = src.indexOf("return _0x1cdf();}", tStart) + "return _0x1cdf();}".length;
const dStart = src.indexOf("function _0x25d3(_0x51d62b,_0x1beea2){");
const dEnd = src.indexOf("_0x25d3c7;}", dStart) + "_0x25d3c7;}".length;
const rStart = src.indexOf("(function(_0x4096de,_0x5598ee){const _0xf5c163=_0x25d3,");
const rEnd = src.indexOf("}(_0x1cdf,0xe81e9));", rStart) + "}(_0x1cdf,0xe81e9));".length;
const dec = new Function(src.slice(tStart,tEnd)+src.slice(dStart,dEnd)+src.slice(rStart,rEnd)+"; return _0x25d3;")();
```

**关键混淆常量已解码**（后续章节直接引用其语义名）：

| 混淆名 | 值 | 语义 |
|--------|----|------|
| `O`/`Se`/`k`/`A`/`Ce`/`j`/`M`/`N`/`we`/`P`/`Te`/`Ee`/`F`/`I`/`De` | 1/2/3/4/5/6/8/9/10/11/12/13/14/15/16 | actionTrigger.type 常量 |
| `Oe` | Set{1,2,3,4,6,8,9,11,14,15} | **可交互 type 集**（= 我们 `OE_TYPES`，注意**不含 5/7/10/12/13/16**） |
| `L` | Set{2,6,9,11,15} | **pointerdown 即触发集**（见 §4.2） |
| `E`/`D`/`ge`/`_e` | 1/2/3/5 | listener 事件：动作结束/点下/链状态变化/拖动 |
| `be`/`xe` | 1/2 | listenerData.change 的方向语义：+增量 / 直接置值 |

**字符串键位对照**（`0x` 为解码入参）：`0x186`=parameters、`0x1b9`=startValue、`0x1f1`=rules、
`0x1f2`=relation_value、`0x225`=live2DRuleConditionMatches、`0x232`=limitTime、`0x23b`=change_focus、
`0x27c`=num、`0x28c`=idleIndex、`0x29b`=live2dTouch、`0x2ee`=idle、`0x335`=revert、
`0x349`=live2DIdleMotionName、`0x366`=actionTriggerActive、`0x376`=relations、`0x385`=action_list、
`0x393`=live2DActiveDataRepeatsCurrentIdle、`0x39b`=actionIndices、`0x3c9`=type、`0x3cc`=resetLive2DTouchRuleParameters、
`0x3e2`=enable、`0x3ea`=motionGroupExists。

## 2. 热区可交互判据（完整链路，源码直证）

### 2.1 `live2DRulePointerEnabled`（§核心，混淆键 `0x225`）

```js
['live2DRulePointerEnabled'](rule){
  const type = rule['actionTrigger']?.['type'];
  if (typeof type != 'number') return this['ruleHasLive2DSlide'](rule);   // 无 type → slide 型
  const {activeData} = this['live2DRuleCurrentActionData'](rule);
  return Oe.has(type)
      && this['live2DRuleConditionMatches'](rule)
      && !this['live2DActiveDataRepeatsCurrentIdle'](activeData)
      && this['live2DRuleHasAllowedAction'](rule);
}
```

**四项与现实现的差异**（重要）：

1. **`live2DRuleConditionMatches`（type 条件门槛）**——现实现**完全没有**：
   ```js
   ['live2DRuleConditionMatches'](rule){
     const at=rule.actionTrigger, type=at?.type, p=at?.parameter||rule.parameter;
     const val = p ? this['live2DOfficialParameterTargetValue'](p) : undefined;
     const num = this['live2DActionTriggerNum'](rule);
     return type===9  ? (typeof num=='number' && typeof val=='number' && Math.abs(val-num)<=0.05)
          : type===11 ? (Array.isArray(num) && typeof val=='number' && num[0]<=val && val<num[1])
          : type===15 ? (typeof val=='number' && Math.abs(val)<=0.01 && this['live2DGameIsPlayerTurn']())
          : true;   // 其余 type 恒真
   }
   ```
   → **type9/11/15 是「参数条件门槛」**：区域是否可点取决于参数当前值（type9=接近 num；type11=落在 num 区间；type15=游戏回合）。
   全库普查：type9 **12 条**、type11 **12 条**、type12 **13 条**、type10 **6 条**、type1 **4 条**、type3/4 各 2 条、type6 4 条、type7 7 条、type8 1 条。

2. **`activeData` 取自链步**——不是整条 rule 的 ATA：
   ```js
   ['live2DRuleCurrentActionData'](rule){
     const at=rule.actionTrigger, list=at?.action_list||[];
     const idx = list.length>0 ? Math.min(list.length-1, Math.max(0, this['live2dOfficialActionListIndices'].get(rule.id)||0)) : -1;
     const step = idx>=0 ? list[idx] : undefined;
     const activeData = (step && Array.isArray(rule.actionTriggerActive?.active_list) && rule.actionTriggerActive.active_list[idx]) || rule.actionTriggerActive;
     return {names: Z(at?.action ?? step?.action), activeData};
   }
   ```
   → **`action_list` 步进索引会覆盖 ATA**（我们 `l2d_touch.ts` 只透传 action，不消费 `active_list`）。

3. **`live2DRuleHasAllowedAction`**：`names.length===0 || names.some(n=>officialLive2DActionAllowed(n))`
   ——与我们 r2_v3「无 action 放行」一致（**无 action 时长度 0 → true**）。

4. **`live2DActiveDataRepeatsCurrentIdle`**：`ata.idle === live2dOfficialIdleIndex` 即跳过（**我们已实现，r4 §4.3 结论成立**）。

### 2.2 `ruleHasLive2DSlide`（无 type 规则的门槛）

无 `actionTrigger.type` 的规则走 slide 分支（本站 slide 判定），源码里未直接取到函数体（`_0x2bc` 等间接名），
但调用点证明其语义：`if(!rule||!this['ruleHasLive2DSlide'](rule)) return;`（拖动路径）——
即 **无 type 规则只有 slide 型才可交互**。

### 2.3 可见性判定 `isLive2DDrawableVisible`（源码直证）

```js
['isLive2DDrawableVisible'](i){
  const core=this['getCoreModel']();
  try{
    if(core?.['getDrawableDynamicFlagIsVisible']?.(i)===false) return false;   // ① 动态标志（我们未启用）
    const op=core?.['getDrawableOpacity']?.(i);
    return !(typeof op=='number' && op<=0.01);                                 // ② 透明度阈值（我们已实现）
  }catch{ return true; }
}
```

→ **站点确实同时用 `getDrawableDynamicFlagIsVisible`**（我们 spec §4 记为「位义未核实故不启用」，现可确认站点在用）。
这正是「热区显隐」与「滑块半显」症状的关键机制候选（见研究报告）。

### 2.4 命中择一 `hitAreaAt`（源码直证）

```js
['hitAreaAt'](x,y,?){ 
  const hits=this['hitAreasAt'](x,y,?)['filter'](h=>officialLive2DHitAreaInteractive(h)&&visibleLive2DHitAreaDrawIndex(h,pos)>=0)
            ['sort']((a,b)=>live2DHitAreaRenderOrder(b)-live2DHitAreaRenderOrder(a));
  const top=hits[0]; if(!top) return;
  const group=hits.filter(h=>h['id']===top['id']);
  return group.find(h=>h.rule&&this['ruleHasLive2DSlide'](h.rule)) || group.find(h=>h.action||h.motionGroup) || ...
}
```
→ 与 spec §4 的 class1(class2(class3)) 择序**一致**（slide 型优先 → 有动作 → 其余），渲染序降序。

### 2.5 热区**提示**显隐 `officialLive2DHitAreaHintVisible`（源码直证，新增认知）

```js
['officialLive2DHitAreaHintVisible'](area){
  if((area.rule && !this['live2DRulePointerEnabled'](area.rule)) ||
     (!area.rule && !this['officialLive2DActionAllowed'](area.action||area.motionGroup))) return false;
  if(!area.official) return !this['live2dOfficialIsPlaying'];
  const tips=this['currentSpec']?.['live2dTouch']?.['tips'];
  return this['live2dOfficialIsPlaying']
    ? !!tips?.['animWhiteList']?.['some'](e=>Ve(e.drawable,area) && Q(e.white_list, this['live2dOfficialActionName']))
    : !tips?.['idleBlackList']?.['some'](e=>Ve(e.drawable,area) && (e.idle||[]).includes(this['live2dOfficialIdleIndex']));
}
```
→ **热区「提示图标」的显隐规则**：动作播放中按 `tips.animWhiteList[].white_list` 决定显示；
空闲时按 `tips.idleBlackList[].idle`（当前 idleIndex 在列即隐藏）。**这是站点「热区显隐」的正式机制**，
我们**未实现**（我们的 `touchZoneStates` 只做可交互/几何判定，不消费 tips 的 animWhiteList/idleBlackList）。

## 3. 动作链状态机（源码直证，关键修正）

### 3.1 `triggerLive2DTouchArea`（完整触发链，本站核心）

```js
['triggerLive2DTouchArea'](area){
  const now=Date.now(), key=area.ruleId? area.name+':'+area.ruleId : area.name;
  if(this['lastLive2DTouchTrigger']?.key===key && now-this['lastLive2DTouchTrigger'].time<0x50) return false; // 80ms 去重
  this['lastLive2DTouchTrigger']={key,time:now};
  if(!(area.official && area.rule)) { /* 非规则区：走 motionGroup 分支 */ }
  if((this['live2dOfficialRuleCooldowns'].get(rule.id)||0) > now) return false;              // ① 冷却
  const at=rule.actionTrigger||{};
  if(!this['live2DRuleConditionMatches'](rule) || (at.type===I && !this['applyLive2DGameMove'](rule))) return false; // ② 条件门槛
  const list=Array.isArray(at.action_list)? at.action_list : [];
  const cur=this['live2dOfficialActionListIndices'].get(rule.id)||0;
  const si=list.length>0 ? Math.min(list.length-1, Math.max(0,cur)) : -1;
  const step=si>=0? list[si]:undefined;
  const act=Be(at.action)||Be(step?.action);
  const ata=(step && Array.isArray(rule.actionTriggerActive?.active_list) && rule.actionTriggerActive.active_list[si]) || rule.actionTriggerActive;
  if(this['live2DActiveDataRepeatsCurrentIdle'](ata)) return false;                          // ③ ATA.idle 防重复
  const p=at.parameter||rule.parameter, val=p?this['live2DOfficialParameterTargetValue'](p):undefined;
  const num=this['live2DActionTriggerNum'](rule);
  if((at.type===N && typeof num=='number' && (typeof val!='number'||Math.abs(val-num)>0.05)) ||
     (at.type===P && Array.isArray(num) && (typeof val!='number'||val<num[0]||num[1]<=val))) return false;  // ④ type9/11 值条件
  this['live2dOfficialRuleCooldowns'].set(rule.id, now+Math.max(0,Number(rule.limitTime||0))*1000);          // ⑤ 记冷却（先记！）
  let target=typeof step?.target=='number'? step.target : at.target;
  const pname=this['live2DParameterExists'](at.parameter||rule.parameter)? (at.parameter||rule.parameter):undefined;
  let numv=num;
  if((at.type===O||at.type===A) && pname===rule.parameter && typeof target=='number' && typeof numv=='number'
     && !this['live2DTriggerValueNear'](target,numv)) target=undefined;                                    // ⑥ circle 近值判定
  if(!this['officialLive2DActionAllowed'](act) || (act && this['live2dOfficialIsPlaying'] && focus!==1)) return true; // ⑦ 白名单/播放门控
  if(pname && typeof target=='number'){
    const curVal=this['live2DOfficialParameterTargetValue'](pname);
    if(at.circle && typeof curVal=='number' && Math.abs(curVal-target)<0.05) target=rule.startValue??0;      // ⑧ circle 翻转
    this['setOfficialLive2DParameterTarget'](target_focus===1? {...rule,smooth:0}:rule, pname, target);
  }
  const idleAfter=this['applyLive2DActiveData'](ata, rule.id);                                             // ⑨ 应用 ATA
  if(list.length>0){                                                                                       // ⑩ 链步进
    const next=(si+1)%list.length;
    this['live2dOfficialActionListIndices'].set(rule.id, next);
    if(rule.revertActionIndex===1 && next!==si) this['resetLive2DTouchRuleParameters'](rule);
  }
  this['saveLive2DOfficialTouchState'](rule);
  this['activeLive2DTouch']={area:area.name, action:act, ruleId:rule.id, params:...};
  if(act && this['motionGroupExists'](act)){ /* 播动作；若 act 是 idle/idleN → playLive2DIdleMotion(idleAfter) */ }
  return true;
}
```

**与现实现的差异（高价值）**：

| # | 站点行为 | 现实现 | 影响 |
|---|---------|-------|------|
| ① | 冷却检查在**最前**（早于条件与白名单） | `resolve()` 冷却最先（一致） | — |
| ② | **条件门槛**（type9/11/15 参数条件） | **无** | type11 区间型热区（lafeier_2 等）恒可点或恒不可点 |
| ③ | ATA.idle 防重复 | 已有 | — |
| ⑤ | 冷却**先记**再判白名单（`return true` 也记） | `resolve()` 仅在 dispatch 成功后记 | 站点「被白名单拦也吃冷却」 |
| ⑥⑧ | **circle 参数翻转**：目标≈当前值时翻回 startValue | `ParamDriver.poke` 有等价翻转（一致） | — |
| ⑦ | 播放中门控：`act && isPlaying && focus!==1` → **返回 true（吞掉本次，不推进链）** | `main.ts` 播放门控直接 return（一致） | — |
| ⑨ | **ATA 应用返回 `idleAfter`**，动作播完后 `playLive2DIdleMotion(idleAfter)` | 我们播完后 `playIdleOnce()` 按 `chainIdleIndex()` 取组（等价） | — |
| ⑩ | 链步进 `(si+1)%len` **循环**（非终止） | 我们 body 链走完冷却 60s | 站点链是**循环推进**，不终止 |
| ⑪ | `revertActionIndex===1 && next!==si` → 复位参数 | **未实现**（spec §11 遗留） | guanghui TouchDrag3 有此字段 |
| ⑫ | `active_list[si]` 覆盖 ATA | **未实现**（仅透传 action） | 有 active_list 的模型链行为偏差 |

### 3.2 `applyLive2DActiveData`（ATA 应用，源码直证）

```js
['applyLive2DActiveData'](ata, ruleId){
  if(!ata) return;
  const prev=this['live2dOfficialIdleIndex'];
  const idle=Ue(ata['idle'], prev, !!ata['repeat_flag']);        // 数字直接用；数组随机（排除 prev，除非 repeat_flag）
  if(Array.isArray(ata['enable'])) this['live2dOfficialEnableActions']=ata['enable'];
  else if(Array.isArray(ata['idle_enable']) && typeof idle=='number'){
    const e=ata['idle_enable'].find(x=>x[0]===idle); if(e) this['live2dOfficialEnableActions']=e[1]||[];
  }
  if(Array.isArray(ata['ignore'])) this['live2dOfficialIgnoreActions']=ata['ignore'];
  else if(Array.isArray(ata['idle_ignore']) && typeof idle=='number'){
    const e=ata['idle_ignore'].find(x=>x[0]===idle); if(e) this['live2dOfficialIgnoreActions']=e[1]||[];
  }
  if(typeof idle=='number'){
    this['live2dOfficialIdleIndex']=idle;
    this['activeLive2DTouch']={...this['activeLive2DTouch'], ruleId};
    if(idle!==prev){ this['resetLive2DRulesForIdle'](idle); this['notifyLive2DOfficialListener'](3, idle); }  // 链状态变化事件
  }
  this['updateLive2DHitAreaFrame'](); this['emitDetails']();
  return idle;
}
```

**关键修正（vs 我们 `l2d_touch.ts` applyActive）**：

1. **形态A 查表用「新 idle 值」而非「当前 idleIndex」**：站点先 `Ue(ata.idle,…)` 得到**目标 idle**，
   再用它查 `idle_enable/idle_ignore`。我们 `l2d_touch.ts:143-146` 用的是 `this.idleIndex`（**应用前**的值）——
   **当 ATA 同时带 `idle` 与 `idle_enable` 时会查错行**（形态A 目前数据少，但语义错）。
2. **形态B 的 `enable`/`ignore` 是「数组即赋值」，空数组 = 空名单（长度 0 → 站点 `officialLive2DActionAllowed` 中 `length>0` 才启用 → 空数组等效无限制）**：
   ```js
   ['officialLive2DActionAllowed'](name){
     if(!name) return true;
     const ext=this['live2DExtendActionDecision'](name);
     if(typeof ext=='boolean') return ext;
     return !( (this['live2dOfficialEnableActions'].length>0 && !Q(this['live2dOfficialEnableActions'],name))
             || Q(this['live2dOfficialIgnoreActions'],name) );
   }
   ```
   → 与现实现一致（r4 定案成立），**但注意 `live2DExtendActionDecision`（type12 扩展判定）优先**：
   ```js
   ['live2DExtendActionDecision'](actionName){
     for(const rule of rules){
       const at=rule.actionTrigger;
       if(at?.type!==12 || !at.parameter || !Array.isArray(at.num)) continue;
       const [lo,hi]=at.num;
       const v=this['live2DOfficialParameterTargetValue'](at.parameter);
       if(typeof v=='number' && lo<v && v<=hi){
         if(Q(rule.actionTriggerActive?.ignore, actionName)) return false;   // 区间命中 → ignore 拒
         if(Q(rule.actionTriggerActive?.enable, actionName)) return true;    // 区间命中 → enable 放行
       }
     }
   }
   ```
   → **type12 = 参数区间内的全局动作裁决器**（半开区间 `lo<v<=hi`）。这正是 guanghui 的 `touch_drag3 ∈ (0.01,10]` 规则：
   **drag3 参数 >0.01 时，`touch_special`/`touch_body`/`touch_head`/`main_*` 等被 ignore 全禁**（§2.1 的 type12 规则 ignore 列表 15 项）。
   我们**未实现**，是 guanghui 现象 1/2 与 shi_3 现象 2 的重要机制候选。

3. **`resetLive2DRulesForIdle(idle)`**：idle 变化时，对所有 `revertIdleIndex===1 || ==='1' || (数组含该 idle)` 的规则
   执行 `resetLive2DTouchRuleParameters(rule)` = `parameter → startValue` + `relationParameter[].name → start`。
   **我们未实现**（guanghui TouchDrag3 的 `revertIdleIndex:"1"` 即此机制：进入 idle1 时 drag3 参数复位）。

### 3.3 链步进与 pointerdown 触发集（源码直证）

- **pointerdown 即触发**：`beginLive2DTouchInteraction` 中
  `if(!rule?.actionTrigger?.down || !L.has(type)) return; this.triggerLive2DTouchArea(area) && triggeredRuleIds.add(rule.id)`
  → **只有带 `actionTrigger.down` 且 type∈{2,6,9,11,15} 的规则在按下瞬间触发**。
  `L = Set{2,6,9,11,15}`；`down` 是规则字段（全库明文 0 命中，属游戏数据保留字段）。
- **拖动/长按路径**（`updateLive2DPressedRules`）：type 1/4 → `maybeTriggerLive2DDragAction`；type 3 → 计时后触发
  （`time` 字段 ×1000ms，`triggerStartTimes` 记录按下时刻）；type 8 → `maybeTriggerLive2DDragAction`。
- **释放路径**（`endLive2DTouchInteraction`）：对 `ruleHasLive2DSlide(rule) || type===M(8)` 的命中区
  `maybeTriggerLive2DDragAction` + `snapLive2DTouchParameter`。
- **动作列表循环**：`(si+1)%list.length` —— **无终止步**，链永远循环推进（我们 body 链的「走完冷却 60s」是本地偏离项 D2）。

### 3.4 `updateLive2DOfficialRuleStates`（每帧总调度，源码直证）

```js
['updateLive2DOfficialRuleStates'](){
  if(!currentLive2d || !currentSpec?.live2dTouch?.rules) return;
  const now=performance.now();
  const dt=Math.min(0.1, Math.max(0, now-this['live2dOfficialLastUpdateAt'])/1000);
  this['live2dOfficialLastUpdateAt']=now;
  this['updateLive2DPressedRules'](Date.now(), dt);
  rules.forEach(rule=>{
    const t=rule.actionTrigger?.type;
    t===5  ? this['updateLive2DIdleRelationRule'](rule)
   :t===10 ? this['updateLive2DAnimationRule'](rule)
   :t===13 ? this['updateLive2DParameterMoveRule'](rule)
   :t===16 && this['updateLive2DGameResultRule'](rule);
    this['updateLive2DReactRule'](rule);
    this['updateLive2DGyroRule'](rule);
    this['updateLive2DRelationParameters'](rule);
  });
  /* 游戏结束判定 … */
  if(!this['live2dOfficialIsPlaying']) this['flushLive2DPendingParameterTargets']();
}
```

**逐类型帧处理（全部为现实现缺失项）**：

| type | 处理函数 | 语义（源码） |
|------|---------|-------------|
| 5 | `updateLive2DIdleRelationRule` | `at.const_fit.find(e=>e.idle===idleIndex)?.target` → **按 idleIndex 设参数目标**（idle 关联常量拟合） |
| 10 | `updateLive2DAnimationRule` | 动作进度到 `trigger_rate` 后触发对应热区（`trigger_name`/`trigger_index` 指定目标动作） |
| 13 | `updateLive2DParameterMoveRule` | 参数缓动移动 |
| 16 | `updateLive2DGameResultRule` | 游戏结果 |
| — | `updateLive2DReactRule` | `reactPosX/Y × 指针归一化` → 参数目标（我们已实现 mode2，但站点**统一走参数目标系统**） |
| — | `updateLive2DGyroRule` | 陀螺仪 → 参数（我们不做） |
| — | `updateLive2DRelationParameters` | 见 §5 |

## 4. 参数系统（源码直证，重大机制差异）

### 4.1 参数目标 + Tween（`setOfficialLive2DParameterTarget` / `updateLive2DOfficialParameterTweens`）

```js
['setOfficialLive2DParameterTarget'](rule, name, value){
  if(!this['live2DParameterExists'](name) || !Number.isFinite(value)) return;
  const tween=this['live2dOfficialParameterTweens'].get(name), prevTarget=this['live2dOfficialParameterTargets'].get(name);
  if(typeof prevTarget=='number' && Math.abs(prevTarget-value)<=0.0001) return;
  const from=tween?.value ?? prevTarget ?? this['getParameterValue'](name) ?? rule.startValue ?? 0;
  const smoothMs=Math.max(0, Number(rule.smooth||0));
  this['live2dOfficialParameterTargets'].set(name, value);
  this['live2dOfficialParameterModes'].set(name, rule.mode||1);
  this['live2dOfficialParameterTweens'].set(name, {value:from, target:value, velocity:0, lastTime:performance.now(), smoothMs});
  if(smoothMs<=0) this['setLive2DParameterFrameValue'](name, value, rule.mode);
}

['updateLive2DOfficialParameterTweens'](){   // 每帧（挂在 beforeModelUpdate）
  if(targets.size===0 && tweens.size===0) return;
  const now=performance.now();
  this['live2dOfficialParameterTargets'].forEach((target,name)=>{
    const tw=this['live2dOfficialParameterTweens'].get(name); let out=target;
    if(tw){
      const dt=Math.max(0, now-tw.lastTime); tw.lastTime=now;
      if(Math.abs(tw.value-tw.target)<0.01 || tw.smoothMs<=0){ out=tw.target; this['live2dOfficialParameterTweens'].delete(name); }
      else { const s=this['smoothDamp'](tw.value, tw.target, tw.velocity, tw.smoothMs/1000, dt/1000);
             tw.value=s.value; tw.velocity=s.velocity; out=tw.value; }
    }
    this['setLive2DParameterFrameValue'](name, out, this['live2dOfficialParameterModes'].get(name));
  });
  this['live2dOfficialParameterTweens'].forEach((_,name)=>{ if(!this['live2dOfficialParameterTargets'].has(name)) this['live2dOfficialParameterTweens'].delete(name); });
}
```

**核心机制（现实现的最大结构性差异）**：

- 站点所有参数写入都经**参数目标表**（`live2dOfficialParameterTargets`），并由 `updateLive2DOfficialParameterTweens`
  **每帧强制回写**（`setLive2DParameterFrameValue`）。因此**动作曲线对同一参数的驱动会被参数目标持续覆盖**——
  这就是「动作播放期间参数不漂移」的机制。
- 现实现 `ParamDriver` 是**独立参数写入器**（`writeParam` 每帧写），**没有「目标覆盖动作曲线」的统一层**，
  且 `update()` 只对注册过的 ParamRule 生效。因此当动作曲线（motion3.json 的 Parameter 曲线）与我们的参数规则
  操作**同一参数**时，会出现相互覆盖 → **「滑块半显」「参数被动作改写」** 类症状。
- `setLive2DParameterFrameValue` 内部含 `parameterRange` 钳制（§5.3 已证：`currentSpec.live2dTouch.parameterRange`
  优先，其次 core 的 min/max）。

### 4.2 `fixLive2DParameterTargetValue`（钳制链，站点唯一入口）

```js
['fixLive2DParameterTargetValue'](value, rule){
  if(!Number.isFinite(value)) return 0;
  if((value<0 && rule.dragDirect===1) || (value>0 && rule.dragDirect===2)) value=0;   // ① 方向门控
  if(rule.rangeAbs===1) value=Math.abs(value);                                        // ② 取绝对值
  if(Array.isArray(rule.range)) value=Math.min(rule.range[1], Math.max(rule.range[0], value));  // ③ 钳幅
  return value;
}
```
→ 与现实现 `clampChain` **完全一致**（r4 §3.1c 定案成立）。

### 4.3 拖动数值链（`live2DLinearDragValue` / `live2DUnityDragDelta` / `live2DDragParameterValue`）

- `live2DUnityDragDelta(interaction, x1,y1, axis)`：**像素位移**（x 轴：`currentX-x`；y 轴：`y-currentY`，上正）
- `live2DLinearDragValue(rule, base, delta, axis)`：`base + delta / (rule['offset'+axis] || 1)`
  （**除式 + `||1` 兜底**；r4 定案：站点无「0 轴排除」，观感另有成因）
- `live2DDragParameterValue`：取轴 → `fixLive2DParameterTargetValue` → `setOfficialLive2DParameterTarget`
- `maybeTriggerLive2DDragAction`：拖动中触发 type1/4/8 的 action（带 `num`/`time`）

### 4.4 type104（relationParameter 的 idle 预设，feiteliedadi 用）

`updateLive2DRelationParameters`（源码直读，节选）：
```js
rel.type===0x68(104) && rel.idle===this['live2dOfficialIdleIndex'] ? out = rel.target ?? rel.start ?? rule.startValue ?? 0
```
→ **type104 = 「当前 idleIndex 等于 rel.idle 时，把 rel.name 参数设为 target」**。
另有 `type===0x65(101)`（拖动线性驱动）、`0x66(102)`（y 轴）、`0x67(103)`（按 actionListIndices 查 `relation_value`）。

**关键修正**：我们 `l2d_params.ts` 把 `RELATION_LOOKUP_TYPE=103` 实现为「value/rangeMax 线性映射到 relation_value 下标」，
但站点 type103 的取值是 **`relation_value[actionListIndices.get(rule.id) || 0]`**（**链步索引直接取表**，不是数值线性映射）。
→ **现实现 type103 语义与站点不符**（全库 type103 出现次数：见 §7 普查）。

## 5. 数据源与皮肤匹配（重要数据事实）

- 站点数据实际路径：`https://l2d.su/data/ships/CN/<shipGroupId>.json`（**shipGroupId 不是 skinId**；
  按 `skins[].prefab` 匹配模型名；旧文档记的 `ships/<skinId>` 已失效）。
- **规则数据在 `skins[].model.live2dTouch`**（非顶层）。
- ⚠️ 该端点有防盗链：请求需带 `User-Agent` + `Referer: https://l2d.su/`，否则 403。
- 同一 `prefab` 可能在多个皮肤条目出现（如 `antu_2` 同时有 live2d 与 spine 条目），
  **必须筛「有 live2dTouch.rules 且 dynamicType=live2d」的那条**。
- **皮肤错配实例（全库普查，2026-09-17，36 模型）**：25 个与站点逐字节一致，**9 个错配**
  （本地数据 = 同名皮肤的**前一编号**皮肤，详见 `research_live2d动作链条修正.md` §5.1）：
  `shi_3`（shi_2 数据）、`feiteliedadi_4`（feiteliedadi_3）、`feiteliekaer_4`（feiteliekaer_3）、
  `dafeng_7`（dafeng_3）、`guandao_3`（guandao_2）、`mojiaduoer_4`（mojiaduoer_2）、
  `ougen_8`（ougen_6）、`tiancheng_cv_3`（tiancheng_cv_2）、`wuzang_4`（wuzang_3）；
  另 2 例站点无对应规则（`chaijun_4`、`shengluyisi_4`，本地为旧数据）。

## 6. 现实现对照表（差距总览）

| 机制 | 站点 | 现实现 | 证据 |
|------|------|-------|------|
| 热区可交互四判据 | type∈Oe + 条件 + ATA.idle + 白名单 | 缺「条件」（type9/11/15） | §2.1 |
| `getDrawableDynamicFlagIsVisible` | 用 | 未启用 | §2.3 |
| 热区提示显隐 | `tips.animWhiteList`/`idleBlackList` | 未实现 | §2.5 |
| type12 全局裁决 | `live2DExtendActionDecision` | 未实现 | §3.2 |
| `revertIdleIndex` 参数复位 | 有 | 未实现 | §3.2 |
| `revertActionIndex` 参数复位 | 有 | 未实现 | §3.1 |
| `active_list` 步覆盖 ATA | 有 | 未实现 | §2.1/§3.1 |
| 链步进循环 | `(si+1)%len` | 终止+冷却（本地偏离 D2） | §3.3 |
| 冷却先记 | 是 | 成功后才记 | §3.1 |
| 参数目标 Tween 覆盖动作曲线 | 有（核心） | 无（独立写入器） | §4.1 |
| type103 语义 | `relation_value[链步索引]` | 数值线性映射（**错**） | §4.4 |
| type5 idle 常量拟合 | 有 | 未实现 | §3.4 |
| type10 动作进度触发 | 有 | 未实现 | §3.4 |
| type13 参数缓动 | 有 | 未实现 | §3.4 |
| 陀螺仪 | 有 | 不做 | §3.4 |
| `clampChain` 三步链 | 同 | 同（一致） | §4.2 |
| 拖动除式 `||1` | 有 | 0 轴排除（本地偏离 D4′） | §4.3 |

## 7. 全库字段普查（36 模型 touch.json，可脚本复现）

```
actionTrigger.type 分布: {1:4, 2:811, 3:2, 4:2, 6:4, 7:7, 8:1, 9:12, 10:6, 11:12, 12:13, None:132}
relationParameter 出现: 30 条规则（其中 type104 = feiteliedadi 系列 36 项；type103 = 若干）
listenerData 出现: 10 条规则（type1/2/3）
trigger_name 出现: 6 条（type10 用）
```

## 8. 归档产物（docs/assets/）

| 文件 | 内容 |
|------|------|
| `su_modelRuntime-BDk3g7Pb.js` | 站点引擎 JS 原始快照（201,926 字节，2026-09-17） |
| `su_modelRuntime_strings.json` | 解码后的字符串表（642 条，键=入参十六进制） |
| `su_ships-CN.json` | 站点全量索引（prefab→shipGroupId、皮肤清单） |
| `_ships_cache/site_20703.json` | 站点光辉 shipGroup 全量数据（含 guanghui_7/guanghui_9 皮肤规则） |
| `_ships_cache/site_20516.json` | 站点狮 shipGroup 全量数据（含 shi/shi_2/shi_3 皮肤规则） |
| `_ships_cache/site_30708.json` | 站点信浓 shipGroup 全量数据（含 xinnong_6） |
| `_ships_cache/site_49902.json` | 站点腓特烈大帝 shipGroup 全量数据（含 feiteliedadi_3/4） |
| `su_survey_touch_json.py` | touch.json 皮肤匹配普查脚本（复现 §5 的 9/36 错配结论） |

> 复核方式：按 §1 的 Node 片段重建解码器，对任意 `_0x26917f(0xNNN)` 查 `strings.json` 同键即得明文；
> 数据侧复核用 `python docs/assets/su_survey_touch_json.py <repo_root> --fetch`。

## 9. 宿主库层：pixi-live2d-display 的两个致命细节（本地栈特有）

### 9.1 idle 自动播放（X1 症状根因）

本地 `frontend-minimal` 用 pixi-live2d-display 0.5.0-beta 渲染，**该库自带 idle 自动播放**：

```js
// dist/cubism4.es.js
__publicField(this, "groups", { idle: "Idle" });          // 默认 idle 组名 = "Idle"（大写）
// MotionManager.update(): 动作播完后
if (this.state.shouldRequestIdleMotion()) { this.startRandomMotion(this.groups.idle, MotionPriority.IDLE); }
// shouldRequestIdleMotion() => currentGroup===undefined && reservedIdleGroup===undefined
```

**推论（重要）**：

1. 库会在**任何动作结束且无后续动作**时，从 `Idle` 组**随机**播一条（`IDLE` 优先级）。
   本地 `playIdleOnce()` 播的是小写 `idle` 组（站点语义），**与库的 `Idle` 组是两条独立路径**。
2. 若模型 `Idle` 组含多条动作（**xinnong_6：15 条 `idle.motion3.json`…`idle16.motion3.json`**），
   库会随机播其中一条 —— 用户「未点击自动进 idle10」即此机制（T8 实测：静置 3 分钟 14 次自动动作、
   `idleIndex` 恒 0）。guanghui_9/shi_3/feiteliedadi_3 的 `Idle` 组各仅 1 条，故无此现象。
3. `MotionPriority.IDLE` 与本地 `model.motion(group, idx, 2)`（NORMAL）**优先级不同**：
   本地触摸动作用 `3`(FORCE)、idle 用 `2`(NORMAL)，库的 idle 自动播放用 `IDLE`(1)。
4. 站点引擎的对应机制是**自己的** `playLive2DIdleMotion(idleIndex)`（§3.2/§3.4），
   与库的 `Idle` 组自动播放**无关**——站点把库当纯渲染层用。

### 9.2 ⚠️ `beforeModelUpdate` 挂点的参数写入会被同帧还原（G1/G2/G3/F2 共同根因）

**库源码**（`dist/cubism4.es.js:10289-10311`，逐字）：

```js
update(dt, now) {
  this.emit("beforeMotionUpdate");
  const motionUpdated = this.motionManager.update(this.coreModel, now);  // ① 动作曲线写参数
  this.emit("afterMotionUpdate");
  model.saveParameters();                        // ② 快照当前参数值
  ...expression / eyeBlink / focus / physics / pose...
  this.emit("beforeModelUpdate");                // ③ 本地 ParamDriver 在此写入
  model.update();
  model.loadParameters();                        // ④ 用 ② 的快照覆盖 → ③ 的写入被丢弃
}
```

**结论**：在 `beforeModelUpdate` 写入的参数**不会影响本帧渲染**（被 `loadParameters()` 还原）。
必须改在 **`afterMotionUpdate`**（②之前）写入才能存活。

**实测证据（2026-09-17 本地浏览器复现）**：

| 挂点 | 写入 3 后模型读数 |
|------|-----------------|
| `beforeModelUpdate` | **0**（被还原） |
| `afterMotionUpdate` | **7**（生效） |

**影响面**：本地 `l2d.ts:903-932 attachParamDriver()`（`ParamDriver` 全部参数写入）与
`l2d.ts:871-890 attachLipSync()`（口型，同挂点）都受此影响。口型未暴露是因多数模型 LipSync 参数无动作曲线。

**与站点对照**：站点引擎**不在**这个挂点上写参数（它有自己的 `applyLive2DParameterFrame` 帧循环，
且 T3 实测站点「面板值变化但模型不变」说明站点也有脱钩现象）——两边实现不同，**不可照搬挂点**。

## 10. 未取到的部分（如实标注）

- `ruleHasLive2DSlide` 函数体（仅从调用点推定语义）
- `Be()`/`Z()`/`He()` 等小工具函数体（语义从调用点推定：动作名归一化/匹配）
- `updateLive2DParameterMoveRule`(type13)、`updateLive2DGameResultRule`(type16) 完整函数体
- `snapLive2DTouchParameter` / `stableLive2DDragValue` / `live2DDragStartedAtTarget`（r4 遗留 D6/D7 的棘轮三函数）
  —— 本次未展开，取证入口同 §1。
