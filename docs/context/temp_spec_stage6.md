# 规格书 · stage6：链推进修复（ATA 按 drawAbleName 应用）+ 真实渲染序 + 实测协议 v2

> 供弱模型执行。stage5 实测（stage1d §11）已证：像素拖拽（T7~T9）、circle 翻转（T10）、默认区
> 动作（T6）、idle 单次化（T1）全部 PASS。剩余两个阻塞根因本规格处理：
> ①链推进断裂——TouchIdleN 规则 `parameter='empty'`，链步进按 parameter 找规则永远落空，
> ATA 永不应用 → idleIndex 恒 0 → ATA.idle=N 门槛区（光辉 TouchIdle17/idle:17、吾妻
> TouchIdle1/idle:11）永久锁死（「互动无法进行下一步」）；②命中择序从未真实生效——
> pixi-live2d-display 0.5.0-beta 的 coreModel 无 getDrawableVisibility/getDrawableRenderOrder
> （stage1d 补充 1），兜底恒 0/true，渲染序排序退化成包围盒面积平局，小区常驻遮蔽大区。
> 红线：不改 AGENTS.md、backend、官方 `frontend/`；不改 `l2d_touch.ts` 既有导出签名；命令一律 PowerShell。
> 测试集：guanghui_9 + wuqi_3 + xinnong_6。本轮无需爬站点（修复点全部可本地闭环）。

## 0. 数据事实（主模型已核验，勿重推导）

- 光辉 62 条规则中 **51 条 parameter 为空**；TouchIdle1~30 形如
  `{drawAbleName:'TouchIdleN', parameter:'empty', action touch_idleN, ATA.idle=N}`（gate）；
  TouchIdle31~42 部分 `parameter=Paramtouch_idle38`（模型参数）且 ATA.idle=0。
- 吾妻 TouchIdle1：`{parameter:'empty', action touch_drag12, ATA:{enable:[touch_idle1…], idle:11}}`
  （stage1d T11 已录）。吾妻全部 TouchIdleN parameter='empty'。
- 真实渲染序在原生属性 `coreModel.drawables.renderOrders`（Int32Array，下标=drawableIndex）；
  `getDrawableVisibility` 同样缺失，暂维持 `?? true`（透明度剔除已按 stage4 移除，不回退）。

## 1. 文件清单

| 操作 | 路径 | 内容 |
|------|------|------|
| 修改 | `frontend-minimal/src/main.ts` | 链步进的规则查找走 `findChainRule`（三字段匹配） |
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | 新增 findChainRule；hitZoneAt 渲染序接原生 renderOrders；仪表盘加 idleIndex 读数 |
| 修改 | `frontend-minimal/src/renderer/l2d_touch_debug.ts` | 标签/读数面板显示 `idleIndex=N`（ TouchChain 只读注入已有 chainIdleIndex） |
| 新建 | `frontend-minimal/tests/test_l2d_hotzone_stage6.py` | pytest 断言（§4） |
| 修订 | `frontend-minimal/tests/test_l2d_hotzone_stage5.py` | 冲突断言（如有）改写并报告 |
| 不改 | `l2d_params.ts`、`l2d_touch.ts`、三模型 touch.json | stage5 已实测通过，保持 |

## 2. 实现规格

### 2.1 链步进规则查找（修链断裂，l2d.ts + main.ts）

- l2d.ts 新增（renderer 公开方法，main.ts 现有 `findRuleByParameter` 的超集替换）：

```ts
/** 链步进找规则：parameter === 组名 | drawAbleName === 驼峰化组名 | action 含组名 */
findChainRule(groupName: string): TouchRule | null {
  const cap = groupName.replace(/^touch_/, 'Touch');   // 'touch_idle17' → 'TouchIdle17'
  return (
    this.touchRules?.find(
      (r) =>
        r.parameter === groupName ||
        (r.drawAbleName ?? '').toLowerCase() === cap.toLowerCase() ||
        actionNamesOf(r).includes(groupName),
    ) ?? null
  );
}
```

- `touchRules`：loadTouchRules 时把整份 rules 数组挂在 renderer 上（现可能只有 touchAreas；
  空参数规则 stage5 起已注册为区，但查找需要**全部**规则含未注册为区的——直接存原始数组）。
- main.ts 链步进（TouchBody 分支）：`findRuleByParameter(gname)` → `findChainRule(gname)`；
  其余不变（resolve 应用 ATA → idleIndex=ata.idle → 门槛区逐步解锁 → playAction）。
- 语义确认：TouchIdle_k 触发 → `applyActive` 置 idleIndex=ata.idle（TouchChain 已有，零改动）；
  TouchIdle31~42（idle:0）行为保持；enable 白名单可能拦截自身 action（吾妻 touch_drag12 vs
  enable[touch_idle*]）——按数据行事，拦截时仪表盘标注 `blocked:enable` 并记录 enable 全文
  进 stage1e（数据疑点，不改代码绕过）。

### 2.2 真实渲染序（修命中择序，l2d.ts）

- `touchCore()` 返回类型追加原生数组访问：
  `drawables?: { renderOrders?: Int32Array; dynamicFlags?: Int32Array }`（取
  `coreModel.drawables`，防御式可选链）。
- `hitZoneAt` 的 renderOrder 取值链改为：
  `core?.getDrawableRenderOrder?.(i) ?? core?.drawables?.renderOrders?.[i] ?? 0`。
- visibility 保持 `?? true`（注释注明：native 无该方法、透明度剔除已移除、dynamicFlags 位义
  未逐字核实故不启用）。
- 排序逻辑不变（渲染序降序 → 包围盒面积平局）。

### 2.3 仪表盘 idleIndex 读数（可验证性）

- 叠加层固定位置（如左上角一行）显示 `idleIndex=N`（数据源 chainIdleIndex 注入），随链步进
  实时刷新；`blocked:enable` 状态按 §2.1 标注。

## 3. 明确不做

不为 ATA 门槛做自动解锁/跳门槛；不启用 dynamicFlags 可见性（位义未核实）；不改姿态机制
（stage4 单次 idle 冻结保持）；不爬站点（本轮修复点全部本地闭环，站点侧同类门槛行为已有
stage1b/1d 记录佐证）。

## 4. 测试用例（新建 `test_l2d_hotzone_stage6.py`；stage5 冲突断言改写并报告）

| # | 用例名 | 输入 | 预期 | 断言点 |
|---|--------|------|------|--------|
| 1 | test_chain_rule_lookup | l2d.ts + main.ts | 命中 | `findChainRule`；`replace(/^touch_/, 'Touch')`（或等价驼峰化）；main.ts 调用它 |
| 2 | test_touch_rules_kept | l2d.ts | 命中 | 原始 rules 数组挂 renderer（`touchRules` 或等价字段） |
| 3 | test_real_render_order | l2d.ts | 命中 | `drawables?.renderOrders`（或 `renderOrders[`）读取链 |
| 4 | test_idle_readout | l2d_touch_debug.ts | 命中 | `idleIndex` 读数渲染 |
| 5 | test_regression_core | 各源文件 | 命中 | 像素增量（clientX/prevY）、转盘 atan2、poke 翻转停留、`Meta.Loop` 单次化、空参数区注册、xinnong shipSkinId==307085、TouchChain 签名、构建字面量 |
| 6 | test_build_and_bundle | `npm --prefix frontend-minimal run build` | exit 0 | 构建通过 |

## 5. 实测协议 v2（**强制**；结果写入 research_live2d_stage1.md「stage1e」，逐行填实测值/证据）

准备同 stage5（构建 + 本地服务 + 仪表盘模式）。

| # | 模型 | 操作 | 期望 | 判定 |
|---|------|------|------|------|
| C1 | 光辉 | 仪表盘观察 idleIndex 初值 | 0 | 读数正确 |
| C2 | 光辉 | 单击身体区 5 次 | 每次：播 touch_idle{1..5} 动作、idleIndex 依次 1→5 | 逐步递增 |
| C3 | 光辉 | 继续单击至 idleIndex=17 | TouchIdle17 区状态 G→ok（仪表盘/叠加层可见） | 门槛解锁 |
| C4 | 光辉 | 单击 TouchIdle17 区 | 播 touch_idle17 动作 | resolved=true |
| C5 | 吾妻 | 单击身体区 1 次 | idleIndex → **11**（TouchIdle1 ATA.idle=11） | 读数跳变 |
| C6 | 吾妻 | 单击 TouchIdle1 区 | touch_drag12 播放；若被自身 enable 白名单拦截 → 记录 enable 全文并标 `blocked:enable` | 播放或数据疑点留证 |
| C7 | 信浓 | 单击身体区 3 次 | touch_idle1→3 逐步、idleIndex 递增（链组齐全） | 递增 |
| C8 | 全部 | 重跑 stage5 §5 的 T1/T6/T7/T8/T9/T10 | 全 PASS（回归） | 不回退 |
| C9 | 光辉 | 重叠区点击（如头部默认区与任一 ok 规则区交叠处） | 命中渲染序更高者（renderOrders 非全 0 的证据：日志打印两个候选的实际 renderOrder 值） | 择序生效 |

弱模型逐行填实测值/PASS-FAIL/证据，全 PASS 前不得声称完成；FAIL 行附控制台日志。

## 6. 步骤分类

**工具可完成**：rg 定位（`rg -n "findRuleByParameter|renderOrders|chainIdleIndex" frontend-minimal/src`）；
`npm --prefix frontend-minimal run build`；pytest 全部文件；§5 协议自动化。
**需要判断**：renderOrders 数组在 0.5.0-beta 的实际存在性与下标语义（打印验证）；C6 白名单拦截
的数据疑点记录方式；仪表盘 idleIndex 的展示位置。

## 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_l2d_hotzone_stage6.py frontend-minimal/tests/test_l2d_hotzone_stage5.py frontend-minimal/tests/test_l2d_touch_chain.py frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
