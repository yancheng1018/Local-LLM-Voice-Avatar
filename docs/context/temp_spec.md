# 临时规格书：极简前端「触摸热区可视化」开关

> 执行者：弱模型。本文件自足，不需要再读 docs/context 其他文档（所有契约已内联）。
> 全部命令为 PowerShell 语法，在仓库根目录 `C:\Coding\Application\v1.2.1_Open-LLM-VTuber-v1.2.1-zh` 执行。
> 红线：不改 AGENTS.md；不改 `frontend/`（官方前端）与任何后端代码；不升级/改动依赖版本。
> 任务完成后本文件可删除。

## 0. 需求与范围

在 frontend-minimal（自研极简前端）显示 Live2D 模型时，状态栏新增开关按钮。开启后在模型上叠加**半透明彩色方框**标出触摸互动区域，框上带**文字标签（对应动作组）**；区域随模型动作实时移动（每帧重算）。关闭后框全部消失，不影响手势互动。

区域数据来源（全部已存在于代码中，本任务只做「显示」，不改判定逻辑）：

| 区域类型 | 数据源 | 现有代码位置 |
|---|---|---|
| touch.json 规则热区 | `L2DRenderer.touchAreas`（`loadTouchRules()` 已过滤画布外虚拟标记） | `frontend-minimal/src/renderer/l2d.ts` |
| model3.json HitAreas | `internalModel.settings.hitAreas`（仅 mao_pro 等少数模型有） | 同上 |
| 头/身启发式区域 | `model.getBounds()` 顶部 30% 为头、其余为身（屏幕坐标，无需换算） | `l2d.ts` 的 `emitInteraction()` |

已知事实（不是 bug，不要「修」）：
- 大部分碧蓝航线模型的 TouchIdle/TouchDrag 绘画件是画布外虚拟标记，已被 `loadTouchRules()` 过滤——这些模型开开关后**只有头/身两个框**，正常。
- mao_pro 的 HitArea 框与视觉位置不重合（在胸口一带），正常。
- Spine 渲染器没有手势/热区，开关对其无操作。

技术栈：pixi.js 7.4.3 + pixi-live2d-display 0.5.0-beta + Vite + TypeScript（无框架）。构建 = `tsc --noEmit && vite build`，**改完必须构建**才在 `/m` 生效。

## 1. 文件清单

| 操作 | 路径 | 内容 |
|---|---|---|
| 新建 | `frontend-minimal/src/renderer/l2d_touch_debug.ts` | 叠加层模块 `TouchDebugOverlay`（核心逻辑都在这，≤200 行） |
| 新建 | `frontend-minimal/tests/test_touch_debug_overlay.py` | pytest 静态+构建验证 |
| 修改 | `frontend-minimal/index.html` | 状态栏加 1 个按钮（约第 17 行后） |
| 修改 | `frontend-minimal/src/style.css` | 2 处选择器加 `#touch-debug-btn` |
| 修改 | `frontend-minimal/src/renderer/types.ts` | `CharacterRenderer` 加可选方法 |
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | 薄接线（约 +15 行） |
| 修改 | `frontend-minimal/src/ui.ts` | 回调 + 文案方法 |
| 修改 | `frontend-minimal/src/main.ts` | 开关状态 + 换模型后重申 |

## 2. 函数签名与关键变量（均为最终定名，照用）

### 2.1 新文件 `l2d_touch_debug.ts`

```ts
import { Container, Graphics, Point, Text } from 'pixi.js';
import type { Matrix, Ticker } from 'pixi.js';

/** 模型侧最小接口（L2DRenderer 用 as unknown as 转入，与 l2d.ts 现有风格一致） */
export interface TouchDebugModel {
  worldTransform: Matrix;
  getBounds(): { x: number; y: number; width: number; height: number };
  toModelPosition(position: Point, result?: Point, skipUpdate?: boolean): Point;
  internalModel: {
    settings?: { hitAreas?: { Id?: string; Name?: string }[] };
    coreModel?: {
      getDrawableIndex(id: string): number;
      getDrawableVisibility?(i: number): boolean;
    };
    getDrawableBounds?(i: number): { x: number; y: number; width: number; height: number };
    localTransform?: Matrix; // 是否存在见查阅任务 T1
  };
}

export class TouchDebugOverlay {
  constructor(
    private readonly ticker: Ticker,
    private readonly getStage: () => Container,
    private readonly getModel: () => TouchDebugModel | null,
    private readonly getTouchAreas: () => { drawIndex: number; group: string; name: string }[] | null,
    private readonly getTapMotions: () => Record<string, Record<string, number>> | undefined,
  ) {}
  setEnabled(enabled: boolean): void;   // 开/关：建层挂 ticker / 摘 ticker 毁层
  onModelChanged(): void;               // 换模型后：层重新置顶 + 重建 HitArea 映射
  destroy(): void;                      // 摘 ticker + 销毁层（L2DRenderer.dispose 调用）
  // 私有（命名固定）：tick / loadHitAreas / collectRegions / modelPointToScreen /
  //                   modelRectToScreen / ensureLayer / syncLabels / selfCheck
}
```

私有字段命名：`enabled`、`layer: Container | null`、`rects: Graphics | null`、`labels: Text[]`、`hitAreas: { name: string; drawIndex: number }[]`、`warned: boolean`（自检只警告一次）。

### 2.2 `types.ts`（CharacterRenderer 接口内新增）

```ts
/** 触摸热区可视化开关（仅 L2D 实现；Spine 渲染器无此功能，故为可选方法） */
setTouchDebug?(enabled: boolean): void;
```

### 2.3 `l2d.ts`（L2DRenderer 新增成员）

```ts
import { TouchDebugOverlay } from './l2d_touch_debug';
private touchDebugOverlay: TouchDebugOverlay | null = null;
private modelInfo: ModelInfo | null = null;   // load() 时缓存，供 tapMotions 查询

setTouchDebug(enabled: boolean): void {
  // 懒创建：new TouchDebugOverlay(this.app.ticker, () => this.app.stage,
  //   () => this.model as unknown as TouchDebugModel | null（用 as unknown as），
  //   () => this.touchAreas,
  //   () => this.modelInfo?.tapMotions as Record<string, Record<string, number>> | undefined)
  // 然后 overlay.setEnabled(enabled)
}
```

改 3 处现有方法：`load()` 入口存 `this.modelInfo = modelInfo`；`load()` 中 `this.app.stage.addChild(model)` 之后调 `this.touchDebugOverlay?.onModelChanged()`；`dispose()` 里 `app.destroy` 前调 `this.touchDebugOverlay?.destroy()` 并置 null。

### 2.4 `ui.ts`（UI 类新增）

```ts
onToggleTouchDebug: ((enabled: boolean) => void) | null = null;   // 回调字段
setTouchDebugEnabled(enabled: boolean): void;                    // 按钮文案 开/关
```

### 2.5 `main.ts`（新增）

```ts
let touchDebugOn = false;                                        // 声明在 ws.register 之前
ui.onToggleTouchDebug = (on: boolean): void => { … };            // 记状态 + renderer.setTouchDebug?.(on)
// set-model-and-conf 的 .load().then() 里追加：renderer.setTouchDebug?.(touchDebugOn);
```

## 3. 核心逻辑（分步 + 伪代码）

### 前置查阅任务（先做，共 2 项）

**T1 坐标换算方向（关键）**：`getDrawableBounds()` 返回的是**模型空间**矩形，画到屏幕需要正向变换。库只有 `toModelPosition`（屏幕→模型），没有反向 API（已在 types 与 dist 中确认 `fromModelPosition` 不存在）。需确认反向链：

```powershell
Select-String -Path frontend-minimal\node_modules\pixi-live2d-display\dist\cubism4.es.js -Pattern "toModelPosition\(position"
Select-String -Path frontend-minimal\node_modules\pixi-live2d-display\types\index.d.ts -Pattern "localTransform"
```

找到 match 后读上下文约 ±30 行（`Get-Content <文件> | Select-Object -Skip <行号-30> -First 60`）。判定：
- 若 `toModelPosition` 实现形如 `worldTransform.applyInverse` → `internalModel.localTransform.applyInverse`（两级仿射），则反向为 `localTransform.apply` → `worldTransform.apply`，即 `modelPointToScreen` 的实现。
- 若链路不同，按实际源码反向构造。
- typings 缺 `localTransform` 但运行时代码有的话，直接用（接口里已声明为可选字段）。
- **无论采用哪种，必须实现运行时自检** `selfCheck()`：取首个已画框中心 c_model → `modelPointToScreen` 得屏幕点 → `model.toModelPosition(屏幕点)` 回代，距离 > 2px 则 `console.warn('[TouchDebug] 坐标换算疑似错误')`（`warned` 保证只警告一次），且后续帧跳过依赖换算的框（头/身框用 `getBounds()` 屏幕坐标，不依赖换算，保留）。

**T2 HitArea 字段名**：

```powershell
Select-String -Path frontend-minimal\node_modules\pixi-live2d-display\types\index.d.ts -Pattern "HitArea"
```

确认 Cubism4 的 `settings.hitAreas` 元素字段（预计 `Id` + `Name`，types 约 2791 行）。若实际字段名不同，同步改 `TouchDebugModel` 接口与 `loadHitAreas()`。

### S5 伪代码：`TouchDebugOverlay`（新文件主体）

```
ensureLayer():
  layer = new Container(); layer.eventMode = 'none'   // ⚠ 必须 'none'：不拦截指针事件，
  rects = new Graphics(); layer.addChild(rects)       //   否则挡住 canvas 手势与目光跟随
  getStage().addChild(layer)

setEnabled(on):
  if on == enabled: return
  enabled = on
  if on: ensureLayer(); loadHitAreas(); ticker.add(tick)
  else:  ticker.remove(tick); layer?.destroy({children:true}); layer=null; rects=null; labels=[]

onModelChanged():
  if layer: getStage().addChild(layer)   // addChild 已在容器内的对象=移到顶层，盖住新模型
  loadHitAreas()

loadHitAreas():
  hitAreas = []
  m = getModel(); 无 m 则 return
  for h of m.internalModel.settings?.hitAreas ?? []:
    idx = m.internalModel.coreModel.getDrawableIndex(h.Id ?? '')
    if h.Name 非空且 idx >= 0: hitAreas.push({name: h.Name, drawIndex: idx})
  // Name 为空的 HitArea 不画：与 main.ts 交互逻辑「键名非空才算定向热区」一致

tick = ():   // ticker 回调；视觉用途，允许读到上一帧的 worldTransform
  if !enabled 或无 model: return
  regions = collectRegions()
  draw(regions)

collectRegions():   // 返回 [{x,y,w,h,color,label}]，屏幕坐标
  out = []
  // A. touch.json 规则热区（橙色系区分类型）
  for a of getTouchAreas() ?? []:
    if !可见(a.drawIndex): continue          // coreModel.getDrawableVisibility?.(i) ?? true
    b = im.getDrawableBounds(a.drawIndex); 无 b 则 continue
    r = modelRectToScreen(b); 无 r 则 continue
    color = a.name 以 'TouchDrag' 开头 ? 0xf472b6      // 粉=拖动区
          : a.name 以 'TouchSpecial' 开头 ? 0xa78bfa   // 紫=长按区
          : 0xf59e0b                                  // 橙=其余规则（TouchIdle 等）
    out.push(r, color, label = `${a.group}（${a.name}）`)
  // B. model3.json HitAreas（红）
  tm = getTapMotions()
  for h of hitAreas:
    if !可见(h.drawIndex): continue
    b = im.getDrawableBounds(h.drawIndex); 无 b 则 continue
    motionKey = tm?.[h.name] 中第一个权重>0 的键（无则 undefined）
    label = h.name + (motionKey ? ` → ${motionKey}` : '（tapMotions 未配置）')
    out.push(modelRectToScreen(b), 0xf87171, label)
  // C. 头/身启发式（绿/蓝）——仅无 touch 规则时判定才实际生效，有规则时不画（画了会误导）
  if !(getTouchAreas()?.length):
    b = m.getBounds()   // 已是屏幕坐标，直接用
    out.push({x:b.x, y:b.y, w:b.width, h:b.height*0.3}, 0x4ade80, '头 → touch_head/touch_special/touch_*')
    out.push({x:b.x, y:b.y+b.height*0.3, w:b.width, h:b.height*0.7}, 0x60a5fa, '身 → touch_idle 递进链 / touch_body')
  return out

draw(regions):
  rects.clear()
  syncLabels(regions.length)   // Text 复用：不足则 new Text('', 样式).anchor.set(0,0.5) 入 layer；多余则 pop 并 destroy
  for i, r of regions:
    rects.lineStyle(2, r.color, 0.9)
    rects.beginFill(r.color, 0.18); rects.drawRect(r.x, r.y, r.w, r.h); rects.endFill()
    labels[i].text = r.label
    labels[i].position.set(r.x + 6, r.y + 12)

modelRectToScreen(b): 四角各自 modelPointToScreen，取 min/max 得 {x,y,w,h}
modelPointToScreen(x, y): 按 T1 结论反向链（localTransform.apply → worldTransform.apply，
                          Point 结果用 new Point() 承接）；T1 未定时先按此默认实现 + selfCheck 兜底
```

Text 样式（pixi v7 语法，固定）：`{ fontSize: 12, fill: '#ffffff', stroke: '#000000', strokeThickness: 3, fontFamily: "'Segoe UI', 'Microsoft YaHei', sans-serif" }`

### S2 `index.html`（照抄）

锚点 `<select id="char-select" title="切换角色（含 Live2D / Spine 模型）"></select>`（约第 17 行）之后插入一行：

```html
        <button id="touch-debug-btn" title="在模型上叠加显示触摸互动区域与对应动作（框随模型动作实时移动）。仅 Live2D 模型有效">🔍 热区：关</button>
```

### S3 `style.css`（两处选择器各加一行）

- 锚点 `#new-chat-btn,` + `#history-toggle-btn {`（约第 68-69 行）→ 选择器列表加 `#touch-debug-btn,`
- 锚点 `#new-chat-btn:hover,` + `#history-toggle-btn:hover {`（约第 81-82 行）→ 同上加 `#touch-debug-btn:hover,`

### S4 `types.ts`

锚点 `readonly hasTouchRules: boolean;`（约第 30 行）之后插入 2.2 的注释 + 可选方法声明。

### S6 `l2d.ts` 接线（全部锚点）

1. import 区（第 3 行附近）加 `import { TouchDebugOverlay } from './l2d_touch_debug';`
2. 字段区 `private touchAreas…` 声明后（约第 28 行）加 2.3 的两个字段
3. `get hasTouchRules` getter 后（约第 134 行）加 `setTouchDebug`（懒创建 + setEnabled，见 2.3）
4. `load()`：入口三行赋值处加 `this.modelInfo = modelInfo;`；`this.app.stage.addChild(model);`（约第 240 行）后加 `this.touchDebugOverlay?.onModelChanged();`
5. `dispose()`：`this.app.destroy(...)` 前加 `this.touchDebugOverlay?.destroy(); this.touchDebugOverlay = null;`

### S7 `ui.ts` 接线

1. 回调字段区 `onToggleHistory` 行后加 `onToggleTouchDebug` 声明（2.4）
2. 构造函数内 `historyBtn.addEventListener` 块后（约第 39 行）：取 `#touch-debug-btn`，click → `this.onToggleTouchDebug?.(btn.textContent!.includes('关'))`（与历史按钮同语义：当前显示「关」=点击后开启）
3. `setHistoryEnabled` 方法后加 `setTouchDebugEnabled`：`btn.textContent = enabled ? '🔍 热区：开' : '🔍 热区：关';`

### S8 `main.ts` 接线

1. `let renderer: CharacterRenderer = …`（第 22 行）后加 `let touchDebugOn = false;`
2. `ui.onToggleHistory = …`（约第 290 行）后加：
   `ui.onToggleTouchDebug = (on) => { touchDebugOn = on; renderer.setTouchDebug?.(on); };`
3. `set-model-and-conf` 的 `.then(() => ui.setStatus(…))`（约第 202 行）改为：`.then(() => { renderer.setTouchDebug?.(touchDebugOn); ui.setStatus(原文案); })` —— 换模型/换渲染器实例后重申开关状态

## 4. 测试用例列表

### pytest 自动用例（文件 `frontend-minimal/tests/test_touch_debug_overlay.py`，全部为子串/正则断言 + 1 个构建用例；实现时用例名、断言点如下，不得增减语义）

| 用例名 | 输入 | 预期输出 | 断言点 |
|---|---|---|---|
| test_button_in_status_bar | 读 `index.html` | 按钮存在且默认关 | 含 `id="touch-debug-btn"` 与 `热区：关` |
| test_ui_wiring | 读 `src/ui.ts` | 回调+文案方法+监听齐全 | 含 `onToggleTouchDebug`、`setTouchDebugEnabled`、`touch-debug-btn` |
| test_renderer_interface_optional | 读 `src/renderer/types.ts` | 可选方法声明 | 正则 `setTouchDebug\?\(enabled: boolean\): void` |
| test_l2d_and_overlay_module | 读 `src/renderer/l2d.ts`、`l2d_touch_debug.ts` | 实现存在且层不拦截事件 | 两文件含 `TouchDebugOverlay`；l2d.ts 正则 `setTouchDebug\(enabled: boolean\): void`；l2d_touch_debug.ts 含 `'none'` |
| test_main_state_reapply | 读 `src/main.ts` | 状态记忆+换模型重申 | 含 `ui.onToggleTouchDebug`、`setTouchDebug?.(`、`touchDebugOn` |
| test_css_selector | 读 `src/style.css` | 样式覆盖新按钮 | 含 `#touch-debug-btn` |
| test_build_and_bundle | `npm --prefix frontend-minimal run build`（subprocess，shell=True，cwd=仓库根） | 退出码 0（含 tsc --noEmit 类型检查）；产物含特征 | returncode==0；`frontend-minimal/dist/index.html` 含 `touch-debug-btn`；`dist/assets/*.js` 拼接后含 `热区：开` |

写测试的注意：文件用 UTF-8；断言子串与上表逐字一致；构建失败时把 stdout/stderr 末尾打印到 stderr 再 assert，便于定位。

### 人工验收（自动化之外，用户在浏览器做，弱模型只需列出不改代码）

| 场景 | 操作 | 预期 |
|---|---|---|
| mao_pro | 开开关 | 红框（HitAreas，位置在胸口一带属正常）+ 绿/蓝头身框 |
| 吾妻 wuqi_3 | 开开关 | 橙/粉/紫规则框，模型动作时框跟随移动 |
| 无 touch.json 模型（如 shizuku） | 开开关 | 仅绿/蓝头身框，无报错 |
| 开→关 | 关闭 | 框立即消失；单击/拖动/长按手势仍正常 |
| 开着切角色 | L2D↔L2D、L2D↔Spine | 新 L2D 模型自动带框；Spine 无框无报错 |

## 5. 步骤分类

### 工具可完成（PowerShell 原样执行）

```powershell
# S0 安装 pytest（已确认：python 3.14 在 PATH，pytest 未装）
python -m pip install pytest

# S1 建测试目录
New-Item -ItemType Directory -Force frontend-minimal\tests

# S10 各步完成后的锚点核对（每条应都有输出）
Select-String -Path frontend-minimal\index.html,frontend-minimal\src\ui.ts,frontend-minimal\src\main.ts -Pattern "touch-debug-btn"
Select-String -Path frontend-minimal\src\renderer\types.ts,frontend-minimal\src\renderer\l2d.ts,frontend-minimal\src\main.ts -Pattern "setTouchDebug"
Select-String -Path frontend-minimal\src\renderer\l2d_touch_debug.ts -Pattern "TouchDebugOverlay|'none'"
Select-String -Path frontend-minimal\src\style.css -Pattern "#touch-debug-btn"

# S11 构建（含 tsc --noEmit 类型检查；通过才算实现完成）
npm --prefix frontend-minimal run build
```

### 需要判断（弱模型执行）

- **T1/T2 查阅任务**（第 3 节开头）：定位 → 读片段 → 按判定规则定 `modelPointToScreen` 实现与 HitArea 字段名；`selfCheck()` 兜底必做
- **S2~S9 代码写入**：内容/锚点/命名已完全给定（第 2、3 节），按锚点插入；锚点找不到时停下汇报，不要凭记忆改别处
- **S9 写 pytest 文件**：按第 4 节用例表实现
- l2d_touch_debug.ts 控制在 ≤200 行（项目维护规则），超了就压缩注释不拆逻辑

## 6. 运行测试

### 运行测试（弱模型原样执行，不要修改）
```powershell
pytest frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。不要自行改测试文件来「让测试通过」。
