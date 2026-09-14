# 规格书 · minimal-frontend 界面优化 stage1：仿 l2d.su 左侧调试栏

> 2026-09-14。执行者按本文件逐步实现，不要偏离接口名与插入点；有冲突停下来汇报。
> 本系列阶段划分（假设）：stage1=调试栏（本文件）、stage2=前端切换 Live2D 模型、
> stage3=一角色多模型映射、stage4=一键复位。旧系列 temp_spec_stage1~5.md 是热区/参数引擎，
> **不要读写、不要覆盖**。

## 0. 范围与硬性契约

- stage1 只做：状态栏新增「🧪 调试栏」按钮，开启后画布左侧出现仿 l2d.su 的调试面板，
  分四区——**显示**（可见性/不透明度/眨眼/呼吸/物理开关）、**动作**（按组播放）、
  **参数**（全参数滑条实时读写）、**部件**（部件不透明度滑条）。
- **仅 Live2D**。SpineRenderer 不实现（types.ts 中方法为可选，调用处全部 `?.`）。
- 纯前端 DOM 改动：**不碰** ws.ts / audio.ts / history.ts / 后端 / WS 协议；
  **不碰** l2d.ts 里既有触摸链、ParamDriver、口型同步逻辑。
- 新模块 `l2d_debug_panel.ts` **≤200 行**（AGENTS.md 硬规则，有测试强制）。
- 已知并接受的行为：被 ParamDriver / 眨眼 / 呼吸 / 物理 / 口型每帧回写的参数，
  调试滑条会被覆盖——调试工具预期行为，不做协调逻辑。
- 改完必须 `npm run build` 才在 `/m` 生效（构建含 tsc 类型检查，类型不过=失败）。

## 1. 文件清单（修改 6 + 新建 3）

| 文件 | 动作 | 内容 |
|------|------|------|
| `frontend-minimal/src/renderer/l2d_debug_panel.ts` | 新建 | DebugPanel 全部逻辑（≤200 行；199 行） |
| `frontend-minimal/src/renderer/l2d_debug_panel_types.ts` | 新建 | 迁出 `DebugCoreModel` / `DebugPanelModel` / `Row` 纯类型（33 行），面板 `import type` 引入 |
| `frontend-minimal/tests/test_debug_panel.py` | 新建 | 静态断言测试（仿 test_touch_debug_overlay.py） |
| `frontend-minimal/index.html` | 修改 | status-bar 加 1 个按钮 |
| `frontend-minimal/src/ui.ts` | 修改 | +1 回调字段、+1 监听、+1 setter |
| `frontend-minimal/src/main.ts` | 修改 | +1 状态变量、+1 回调接线、+1 处模型切换重申 |
| `frontend-minimal/src/renderer/types.ts` | 修改 | +1 可选方法签名 |
| `frontend-minimal/src/renderer/l2d.ts` | 修改 | +1 字段、+1 import、+1 方法、load/dispose 各 +1 行 |
| `frontend-minimal/src/style.css` | 修改 | 末尾追加 `#debug-panel` 样式块；`#debug-panel-btn` 追加进既有按钮选择器列表 |

> 拆分说明（2026-09-14 执行决定）：原计划单文件实现，实测 266 行，3 次压缩后仍 227 行 >
> 200 上限。超标部分非排版冗余（约 45 行是 §3.1 强制要求的两个导出接口），故按职责拆分：
> 纯类型迁出到 `l2d_debug_panel_types.ts`。公共导出名保持不变——面板文件用
> `export type { ... } from './l2d_debug_panel_types'` 再导出，外部（l2d.ts / 测试）导入路径与语义不变。
> `Row` 不再从面板导出（原为文件内私有 interface，未导出过，无影响）。


## 2. 已核实的 API 面（照此写，勿自创）

`internalModel.coreModel`（pixi-live2d-display 0.5.0-beta 框架 CubismModel，**类型已核实**）：

```
getParameterCount(): number
getParameterMinimumValue(i: number): number
getParameterMaximumValue(i: number): number
getParameterValueById(id: string): number
setParameterValueById(id: string, value: number): void
getPartCount(): number
getPartOpacityById(id: string): number
setPartOpacityById(id: string, opacity: number): void
```

- ⚠️ **没有** `getParameterIds()` / `getPartIds()`（`getParameterIds` 属于 EyeBlink 接口，勿用）。
- 参数/部件 ID 枚举走**原始 core 结构**（本仓库已有先例 `l2d.ts:882` 的 `coreModel.model.canvasinfo`）：
  `coreModel.model.parameterIds: string[]`、`coreModel.model.partIds: string[]`。
  防御式取用：取不到就显示「（未暴露 ID 列表）」占位，不抛错。
- 播动作：`model.motion(group, undefined, 3)`（priority 3=FORCE，先例 `l2d.ts:907`）。
- 动作组枚举：`model.internalModel.settings.motions` 的键（先例 `l2d.ts:780-789`，兼容
  `motionGroups` 别名键）。
- 行为开关字段：`internalModel.eyeBlink` / `breath` / `physics`（防御式访问，字段不存在
  或为 null 时该行不渲染或置灰；关闭=置 null，恢复=还原快照值）。
- 模型可见性/透明度：`model.visible`（bool）、`model.alpha`（0~1，pixi DisplayObject）。

## 3. 新建 `src/renderer/l2d_debug_panel.ts`

### 3.1 导出签名

> 类型定义在 `src/renderer/l2d_debug_panel_types.ts`（拆分见 §1 说明）；
> 面板文件 `import type` 引入并 `export type { ... } from` 再导出，
> 故下列导入路径写法对调用方依然成立：`import type { DebugCoreModel } from './l2d_debug_panel'`。

```ts
/** coreModel 的结构化子集（§2 的 8 个方法） */
export interface DebugCoreModel { /* §2 的 8 个方法签名 */ }

/** Live2DModel 的结构化子集；main/l2d 传入的 this.model 由面板自行 cast */
export interface DebugPanelModel {
  visible: boolean;
  alpha: number;
  motion(group: string, index?: number, priority?: number): Promise<boolean>;
  internalModel: {
    coreModel?: DebugCoreModel | null;
    settings?: { motions?: Record<string, unknown[]> } & Record<string, unknown>;
  } & Record<string, unknown>;
}

export class DebugPanel {
  constructor(container: HTMLElement, getModel: () => unknown);
  /** 模型加载/切换后重建分区内容（未开启时 el 为 null，直接 return） */
  onModelChanged(): void;
  /** 取消 RAF、移除 DOM、清空 rows/active/snapshot */
  destroy(): void;
}
```

### 3.2 核心逻辑（分步）

1. **构造**：立即创建根元素 `<div id="debug-panel">`（append 到 container），调
   `buildSections()`，启动 `requestAnimationFrame` 刷新循环（循环句柄存 `this.raf`，
   循环内 `this.el` 为 null 时 return；`destroy()` 里 cancel）。
2. **buildSections()**（`onModelChanged()` 与构造都调它）：`const model = this.getModel() as
   DebugPanelModel | null;` 根元素 `replaceChildren()` 后重建四区。model 为 null 时只放一行
   占位文本「（无模型）」。
   - **显示区**：标题「显示」；① 可见 checkbox ←→ `model.visible`（change 事件赋值）；
     ② 不透明度滑条 0~1 step 0.01 ←→ `model.alpha`；③ 行为开关（眨眼/呼吸/物理）：
     build 时快照 `this.behaviorSaved[key] = im[key]`（仅当 `!= null`），每项一行 checkbox，
     勾选=还原快照值，取消=置 `null`；快照里不存在的 key 不渲染该行。
   - **动作区**：标题「动作」；组列表 = `model.internalModel.settings?.motions ??
     (settings as any)?.motionGroups` 的键；每组一行「组名 + ▶ 按钮」，点击
     `void model.motion(group, undefined, 3)`；无组显示「（无动作组）」。
   - **参数区**：标题「参数」；`core = model.internalModel?.coreModel`；无 core 显示占位；
     有则 `ids = (core as any).model?.parameterIds ?? []`，
     `n = Math.min(ids.length, core.getParameterCount())`，逐 i 建行：label=`ids[i]`，
     滑条 min=`core.getParameterMinimumValue(i)`、max=`getParameterMaximumValue(i)`、
     step 0.01；`input` 事件 → `core.setParameterValueById(ids[i], Number(v))`；ids 为空
     显示「（未暴露 ID 列表）」。
   - **部件区**：标题「部件」；同参数区，`ids = (core as any).model?.partIds ?? []`，
     滑条固定 0~1 step 0.01，读 `getPartOpacityById`，写 `setPartOpacityById`。
3. **行工厂（省行数的关键，参数/部件/透明度共用）**：
   `makeRow(parent, label, min, max, get: () => number, set: (v: number) => void, key: string)`
   → 行内 `<label>`（超长省略）+ `<input type=range>` + `<span class=val>`；
   注册进 `this.rows.push({ key, input, val, get })`；input 上 `pointerdown` →
   `this.active.add(key)`，`pointerup`/`pointercancel`/`blur` → `delete`；`input` 事件里
   `set(Number(input.value))` 并立即刷新该行 val 文本。
4. **RAF 刷新**：每帧遍历 `this.rows`，跳过 `this.active.has(key)` 的行，
   `v = get()` → `input.value = String(v)`、`val.textContent = v.toFixed(2)`。
   （用户拖动中的滑条不被回写覆盖。）
5. `destroy()`：cancel RAF、`this.el.remove()`、`this.el = null`、清 `rows/active/behaviorSaved`。

## 4. 修改点（插入锚点用当前行号定位，行号允许漂移、以内容搜索为准）

### 4.1 `src/renderer/l2d.ts`
- 顶部 import 区：`import { DebugPanel } from './l2d_debug_panel';`
- 字段 `private touchDebugOverlay: TouchDebugOverlay | null = null;`（≈93 行）之后加：
  `private debugPanel: DebugPanel | null = null;`
- `setTouchDebug` 方法（≈378 行）之后加：

```ts
/** 仿 l2d.su 左侧调试栏（显示/动作/参数/部件）。仅 L2D。 */
setDebugPanel(enabled: boolean): void {
  if (!enabled) {
    this.debugPanel?.destroy();
    this.debugPanel = null;
    return;
  }
  if (!this.debugPanel) this.debugPanel = new DebugPanel(this.container, () => this.model);
}
```

- `load()` 内 `this.touchDebugOverlay?.onModelChanged();`（≈619 行）下一行加：
  `this.debugPanel?.onModelChanged();`
- `dispose()` 内 `this.touchDebugOverlay?.destroy();`（≈925 行）之前加：
  `this.debugPanel?.destroy(); this.debugPanel = null;`

### 4.2 `src/renderer/types.ts`
`setTouchDebug?` 之后加：`/** 仿 l2d.su 左侧调试栏开关（仅 L2D 实现） */`
`setDebugPanel?(enabled: boolean): void;`

### 4.3 `index.html`
`touch-debug-btn`（≈18 行）之后加：
`<button id="debug-panel-btn" title="仿 l2d.su 左侧调试栏：模型显示/动作/参数/部件实时调试。仅 Live2D 模型有效">🧪 调试栏：关</button>`

### 4.4 `src/ui.ts`
- `onToggleTouchDebug` 字段（≈17 行）后加：
  `onToggleDebugPanel: ((enabled: boolean) => void) | null = null;`
- 构造函数 `touchDebugBtn` 监听（≈41-42 行）后加：
  `const debugPanelBtn = document.getElementById('debug-panel-btn') as HTMLButtonElement;`
  `debugPanelBtn.addEventListener('click', () => this.onToggleDebugPanel?.(debugPanelBtn.textContent!.includes('关')));`
- `setTouchDebugEnabled` 方法（≈53-56 行）后加：
  `/** 调试栏开关状态（按钮文案 开/关） */`
  `setDebugPanelEnabled(enabled: boolean): void { const btn = document.getElementById('debug-panel-btn') as HTMLButtonElement; btn.textContent = enabled ? '🧪 调试栏：开' : '🧪 调试栏：关'; }`

### 4.5 `src/main.ts`
- `let touchDebugOn = false;`（≈24 行）后加：
  `let debugPanelOn = false; // 调试栏开关状态（换 L2D 模型后需重申）`
- `renderer.setTouchDebug?.(touchDebugOn);`（≈253 行）后加：
  `renderer.setDebugPanel?.(debugPanelOn);`
- `ui.onToggleTouchDebug = ...` 块（≈350-354 行）后仿写：

```ts
ui.onToggleDebugPanel = (on) => {
  debugPanelOn = on;
  ui.setDebugPanelEnabled(on);
  renderer.setDebugPanel?.(on);
};
```

### 4.6 `src/style.css`（末尾追加，数值允许目测微调 top/width）

⚠️ **必须同时把 `#debug-panel-btn` 追加进既有的两条按钮选择器列表**——否则新按钮
不继承状态栏胶囊样式，会显示成裸 HTML 按钮：

```css
#new-chat-btn,
#touch-debug-btn,
#debug-panel-btn,          /* ← 新增 */
#history-toggle-btn { ... }

#new-chat-btn:hover,
#touch-debug-btn:hover,
#debug-panel-btn:hover,    /* ← 新增 */
#history-toggle-btn:hover { ... }
```

追加块：

```css
/* 仿 l2d.su 左侧调试栏（仅 Live2D） */
#debug-panel {
  position: absolute; left: 8px; top: 56px; width: 240px;
  max-height: calc(100% - 140px); overflow-y: auto; z-index: 20;
  background: rgba(20, 22, 30, 0.78); color: #dfe3ea;
  border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px;
  padding: 8px; font-size: 12px; pointer-events: auto;
}
#debug-panel h3 { margin: 6px 0 4px; font-size: 12px; color: #9fc3ff; }
#debug-panel .row { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
#debug-panel .row label { flex: 0 0 108px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#debug-panel .row input[type='range'] { flex: 1 1 auto; min-width: 0; }
#debug-panel .val { flex: 0 0 40px; text-align: right; font-variant-numeric: tabular-nums; opacity: 0.8; }
```

## 5. 测试用例（新建 `frontend-minimal/tests/test_debug_panel.py`，全部静态断言）

文件骨架仿 `frontend-minimal/tests/test_touch_debug_overlay.py`（同款 `ROOT`/`FM`/`read()`，
UTF-8 读取）。用例清单：

| # | 用例名 | 输入（读哪个文件） | 预期 | 断言点 |
|---|--------|-------------------|------|--------|
| 1 | test_button_in_status_bar | index.html | True | 含 `id="debug-panel-btn"` 且含 `调试栏：关` |
| 2 | test_ui_wiring | src/ui.ts | True | 含 `onToggleDebugPanel`、`setDebugPanelEnabled`、`debug-panel-btn` |
| 3 | test_renderer_interface_optional | src/renderer/types.ts | True | 正则 `setDebugPanel\?\(enabled: boolean\): void` |
| 4 | test_l2d_and_panel_module | l2d.ts + l2d_debug_panel.ts | True | l2d.ts 含 `DebugPanel`、`setDebugPanel\(enabled: boolean\): void`、`debugPanel?.onModelChanged()`；面板文件含 `export class DebugPanel`、`getParameterCount`、`setParameterValueById`、`setPartOpacityById`、`requestAnimationFrame` |
| 5 | test_main_state_reapply | src/main.ts | True | 含 `ui.onToggleDebugPanel`、`setDebugPanel?.(`、`debugPanelOn` |
| 6 | test_css_selector | src/style.css | True | 含 `#debug-panel-btn`、`#debug-panel` |
| 7 | test_module_line_limit | src/renderer/l2d_debug_panel.ts | True | 行数 ≤ 200（`(read(...)).count("\n") <= 200`） |
| 8 | test_build_and_bundle | 子进程构建 + dist 产物 | returncode 0 | `npm --prefix frontend-minimal run build` 成功；dist/index.html 含 `debug-panel-btn`；dist/assets/*.js 合并文本含 `调试栏：开` |

注意：#8 完全照抄 test_touch_debug_overlay.py 的 test_build_and_bundle（含失败时把
stdout/stderr 末 2000 字写 stderr 的处理），只改断言内容。

## 6. 步骤分类

**工具可完成**（给出命令，PowerShell，仓库根执行）：

```powershell
# 定位插入锚点（确认行号是否漂移）
rg -n "touchDebugOverlay\?\.onModelChanged|setTouchDebug\?\(touchDebugOn\)|let touchDebugOn" frontend-minimal/src
```

两个新文件（`l2d_debug_panel.ts`、`test_debug_panel.py`）按 §3/§5 直接写出，无脚手架命令。

实现完成后（顺序固定，仓库根执行）：

```powershell
cd frontend-minimal; ./node_modules/.bin/tsc --noEmit -p .   # 类型检查（build 也含，单独跑便于定位）
cd ..; npm --prefix frontend-minimal run build                # 构建产物到 dist（/m 生效前提）
(Get-Content frontend-minimal/src/renderer/l2d_debug_panel.ts).Count   # 应 ≤ 200
```

⚠️ **不要用 `npx tsc`**：本机 npx 会拉到 npm 上的同名垃圾包 `tsc@2.0.4`，
输出「This is not the tsc command you are looking for」且退出码仍为 0，
会掩盖真实类型错误。务必走 `<package>/node_modules/.bin/tsc`。

**需要判断**（弱模型写代码，不给命令）：
- §3.2 全部（四区 DOM 构建、行工厂、RAF 刷新、快照语义）——按伪代码逐条落实
- l2d.ts / ui.ts / main.ts 的五处插入（§4，内容已给出，只需放对位置）
- 测试文件按 §5 表格逐条落成 `assert`

**禁止**：改 AGENTS.md、docs/context 其他文件、l2d_params.ts、l2d_touch*.ts、ws/audio/history；
新增 npm 依赖；把调试栏接到 WS/后端。

## 7. 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_debug_panel.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。

## 8. 手动验收清单（测试全绿后）

1. `npm --prefix frontend-minimal run build` 后访问 `http://localhost:12393/m/`（服务已起时）。
2. 点「🧪 调试栏：关」→ 左侧出现面板；再点消失。
3. 显示区：取消勾选可见 → 模型隐藏；拖不透明度 → 实时变化；关/开眨眼可见眼睛停止/恢复。
4. 动作区：点任一组的 ▶ → 模型播放该组动作（FORCE，盖过待机）。
5. 参数区：拖一个未被自动行为驱动的参数（如 ParamAngleX）→ 模型实时转头；松手后数值不被回写漂移。
6. 部件区：某部件滑到 0 → 对应部位消失。
7. 切角色（如 mao_pro.yaml ↔ 任一碧蓝航线角色）→ 面板列表自动换成新模型的参数/部件/动作组。
8. 切到 Spine 角色 → 面板自动消失（SpineRenderer 无此方法）；切回 L2D → 状态仍为开则面板回来。
