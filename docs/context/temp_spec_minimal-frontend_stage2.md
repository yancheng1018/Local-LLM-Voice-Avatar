# 规格书 · minimal-frontend stage2：调试栏验收失败修正 + 测试体系升级

> 2026-09-14。stage1（temp_spec_minimal-frontend_stage1.md）人工验收失败后的**修正规格**。
> 执行者按本文件逐步实现；有冲突停下来汇报。stage1 规格书保持原样不回写。
> 旧系列 temp_spec_stage1~5.md（热区/参数引擎）与本文件无关，不要读写。

## 0. 验收失败根因（已核实，勿再排查接线）

**现象**：点「🧪 调试栏」后面板参数区/部件区永远显示「（未暴露 ID 列表）」，
得不到 l2d.su 式的参数/部件滑条（若当时连面板都没有，是页面缓存/访问姿势问题，见 §7）。

**根因**：`l2d_debug_panel.ts` 的 `ids()` 读 `core.model.parameterIds` / `core.model.partIds`
——这个路径**不存在**。核心模型（`Live2DCubismCore.Model`）的真实结构是
`parameters.ids` / `parts.ids`。这是 stage1 规格书 §2 的断言错误（未经运行时验证），
弱模型忠实照抄导致。三条证据：

1. **本仓库 dist 产物中库自身代码**（`dist/assets/index-*.js`，即生产实际执行的代码）：
   `getPartId(t){return this._model.parts.ids[t]}`、
   `const e=this._model.parts.ids`、`const e=this._model.parameters.ids`、
   `this._model.parameters.minimumValues` —— 库读核心模型全部走 `.parameters.ids`/`.parts.ids`。
2. **官方 typings**（`node_modules/pixi-live2d-display/types/index.d.ts`）：核心 `class Model`
   只声明 `parameters: Parameters; parts: Parts; drawables: Drawables; canvasinfo: CanvasInfo;`。
3. **框架 CubismModel 的 `_parameterIds`/`_partIds` 是 private 字段**（typings 同文件），
   不存在同名公开属性——任何 `parameterIds` 直读都返回 undefined。

**`coreModel.model` 公开访问器确实存在**（stage1 规格这点没错）：
`l2d.ts:882` 的 `coreModel?.model?.canvasinfo?.PixelsPerUnit` 生产验证过（kScale 布局正常）。

**接线链已逐处核实无误（本次不要再动）**：index.html 按钮、ui.ts 监听+回调字段、
main.ts 开关状态+load 后重申、types.ts 可选方法、l2d.ts 的 import/字段/setDebugPanel/
load 内 onModelChanged/dispose 清理、style.css 样式块——全部存在且正确；dist 已重建。
弱模型实施时的合理偏离（types 拆分到 `l2d_debug_panel_types.ts`）**予以保留**。

## 1. 修正范围（硬性契约）

| 文件 | 动作 |
|------|------|
| `frontend-minimal/src/renderer/l2d_debug_panel.ts` | **修改**：仅 `ids()` 与 `buildList` 两处（§2） |
| `frontend-minimal/tests/debug_panel_runtime.test.mjs` | **新建**：运行时行为测试（附录 A 原文照抄） |
| `frontend-minimal/tests/test_debug_panel_runtime.py` | **新建**：pytest 编排（附录 B 原文照抄） |
| `frontend-minimal/tests/test_debug_panel.py` | **重写**：按 §4 升级断言 |

**禁改**：l2d.ts / ui.ts / main.ts / types.ts / index.html / style.css /
l2d_debug_panel_types.ts / ws.ts / audio.ts / history.ts / 后端一切文件；不新增 npm 依赖。
行数上限：`l2d_debug_panel.ts` ≤ 200 行（既有测试强制，修正后行数应基本不变）。

## 2. 代码修正（唯一改动点，l2d_debug_panel.ts）

`buildSections` 里两处调用，字段名换成核心结构的子对象名：

```ts
// 修改前
this.buildList(el, '参数', core, 'parameterIds', true);
this.buildList(el, '部件', core, 'partIds', false);

// 修改后
this.buildList(el, '参数', core, 'parameters', true);
this.buildList(el, '部件', core, 'parts', false);
```

`buildList` 的 `field` 参数类型与 `ids()` 同步改：

```ts
// buildList 签名（field 类型改）
field: 'parameters' | 'parts',

// 修改前（错误路径）
private ids(core: DebugCoreModel, field: 'parameterIds' | 'partIds'): string[] {
  const raw = (core as unknown as { model?: Record<string, string[]> }).model?.[field];
  return Array.isArray(raw) ? raw : [];
}

// 修改后（核心 Live2DCubismCore.Model 结构：parameters.ids / parts.ids，
//  dist 内库自身消费 this._model.parts.ids 同源；经框架 coreModel.model 公开访问器取）
private ids(core: DebugCoreModel, field: 'parameters' | 'parts'): string[] {
  const raw = (core as unknown as { model?: Record<string, { ids?: string[] }> }).model?.[field]?.ids;
  return Array.isArray(raw) ? raw : [];
}
```

行 key `${field}:${id}` 自动跟随新字段名，无需额外改。其余逻辑（min/max、滑条、
RAF 回写、行为开关快照）stage1 实现已正确，不要动。

## 3. 测试体系升级设计（为什么）

stage1 测试全是**子串断言**——「代码里存在这个字符串」≠「路径正确」≠「逻辑可用」，
所以 9 个用例全绿但功能是坏的。本次分三层，各自抓一类失败：

| 层 | 抓什么 | 形式 |
|----|--------|------|
| L1 静态接线（升级） | 接线链断裂、旧路径残留、CSS 没进构建 | pytest 精确正则（§4） |
| L2 运行时行为（新增，核心） | 路径/逻辑错误——用**真面板代码 + 假模型**跑，本次根因必红 | node:test + mini-DOM（附录 A） |
| L3 构建产物 | 构建后产物缺 CSS / 缺正确路径串 | pytest 查 dist（§4） |

L2 原理：把 `l2d_debug_panel.ts` 用 tsc 编译成 JS，在 Node 内置 test runner 里
配一个**按 §2 证据构造的假核心模型**（`model.parameters.ids` / `model.parts.ids`）
和 ~90 行 mini-DOM 垫片直接驱动 DebugPanel 类。零新依赖、完全离线。
**假模型的结构就是「真实核心结构」的镜像——面板代码再读错路径，行数断言立刻红。**

## 4. 重写 `tests/test_debug_panel.py`（pytest，静态层）

骨架沿用现文件（ROOT/FM/read()，UTF-8）。用例表：

| # | 用例 | 断言 |
|---|------|------|
| 1 | test_button_in_status_bar | index.html 含 `id="debug-panel-btn"`、`调试栏：关`（保留 stage1） |
| 2 | test_ui_wiring | ui.ts 正则 `debug-panel-btn'\) as HTMLButtonElement` 与 `onToggleDebugPanel\?\.\(debugPanelBtn` |
| 3 | test_main_handler_block | main.ts 正则 `ui\.onToggleDebugPanel = \(on\) => \{[^}]*renderer\.setDebugPanel\?\.\(on\)`；且含 `renderer\.setDebugPanel\?\.\(debugPanelOn\)`（load 后重申） |
| 4 | test_l2d_method | l2d.ts 正则 `new DebugPanel\(this\.container, \(\) => this\.model\)`；含 `this\.debugPanel\?\.onModelChanged\(\)` |
| 5 | test_renderer_interface_optional | types.ts 正则 `setDebugPanel\?\(enabled: boolean\): void`（保留） |
| 6 | test_id_path_fixed | 面板文件含 `'parameters'`、`'parts'`、正则 `model\?\.\[field\]\?\.ids`；**不含** `parameterIds`、`partIds`（旧路径根除） |
| 7 | test_library_cross_check | `node_modules/pixi-live2d-display/types/index.d.ts` 含 `parameters: Parameters;`、`parts: Parts;`、`private _parameterIds;`（库结构证据；库升级后此测试红=提示重新核对路径） |
| 8 | test_css_source_and_dist | style.css 含 `#debug-panel`；构建后 `dist/assets/*.css` 合并文本含 `#debug-panel`（stage1 漏查 CSS 产物） |
| 9 | test_module_line_limit | 面板文件 ≤200 行（保留） |
| 10 | test_types_module_split | 保留弱模型已加的用例原样 |
| 11 | test_build_and_bundle | 保留 stage1 的构建用例（失败时写 stderr 末 2000 字），追加：dist JS 合并文本含 `.parts.ids` 与 `.parameters.ids` |

注意 #6 的「不含」断言：`parameterIds` 在面板文件中必须 0 次出现
（`assert 'parameterIds' not in panel`），防止旧路径回潮。

## 5. 运行测试（弱模型原样执行，不要修改）

先构建再跑全部三个测试文件：

```
npm --prefix frontend-minimal run build
pytest frontend-minimal/tests/test_debug_panel.py frontend-minimal/tests/test_debug_panel_runtime.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

EXIT 非 0 时只汇报：失败用例名、断言差异、最后 20 行输出。
单独跑运行时层（调试用）：`node --test frontend-minimal/tests/debug_panel_runtime.test.mjs`

## 6. 人工验收清单（测试全绿后，按序执行）

1. **Ctrl+F5 强刷** `http://localhost:12393/m/`（必须带尾斜杠；HTML 有 no-cache 但保险起见）。
2. 控制台自检：`__vtuber.renderer.model.internalModel.coreModel.model.parameters.ids.length`
   应输出 > 0（此命令同时是「路径是否正确」的一锤定音诊断）。
3. 点「🧪 调试栏：关」→ 左侧面板出现，**参数区是大量滑条**（不再是「（未暴露 ID 列表）」）。
4. 拖 `ParamAngleX` 类参数 → 头实时转动；部件区某行滑到 0 → 对应部位消失。
5. 眨眼取消勾选 → 眨眼停止；动作区点 ▶ → 播放该组动作。
6. 切角色（mao_pro ↔ 碧蓝航线系）→ 面板列表换成新模型；切 Spine 角色 → 面板消失；
   切回 L2D → 面板按开关状态恢复。
7. 已知预期行为（不算失败）：被物理/呼吸/眨眼/口型驱动的参数，滑条会被每帧回写冲走。

## 附录 A · `frontend-minimal/tests/debug_panel_runtime.test.mjs`（原文照抄）

```js
// 运行时行为测试：真 DebugPanel 代码（tsc 编译到 tests/__tsout__/）+ 假核心模型 + mini-DOM。
// 零依赖，node --test 直接跑。假模型结构 = 核心 Live2DCubismCore.Model 的镜像
// （model.parameters.ids / model.parts.ids，见 stage2 规格书 §0 证据）。
import test from 'node:test';
import assert from 'node:assert/strict';
import { DebugPanel } from './__tsout__/l2d_debug_panel.js';

// ---- mini-DOM：只实现 DebugPanel 用到的 API 面 ----
class El {
  constructor(tag) { this.tagName = tag; this.children = []; this.parentNode = null;
    this.listeners = {}; this._text = ''; this.attrs = {}; }
  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); }
  set id(v) { this.attrs.id = v; } get id() { return this.attrs.id; }
  set className(v) { this.attrs.className = v; } get className() { return this.attrs.className; }
  set title(v) { this.attrs.title = v; } get title() { return this.attrs.title; }
  set type(v) { this.attrs.type = v; } get type() { return this.attrs.type; }
  set min(v) { this.attrs.min = String(v); } get min() { return this.attrs.min; }
  set max(v) { this.attrs.max = String(v); } get max() { return this.attrs.max; }
  set step(v) { this.attrs.step = String(v); } get step() { return this.attrs.step; }
  set value(v) { this._value = String(v); } get value() { return this._value ?? ''; }
  set checked(v) { this._checked = Boolean(v); } get checked() { return Boolean(this._checked); }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c);
    c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { for (const c of cs) this.appendChild(c); }
  replaceChildren() { for (const c of this.children) c.parentNode = null; this.children = []; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  removeChild(c) { const i = this.children.indexOf(c);
    if (i !== -1) this.children.splice(i, 1); c.parentNode = null; }
  addEventListener(ev, fn) { (this.listeners[ev] ??= []).push(fn); }
  dispatch(ev) { for (const fn of (this.listeners[ev] ?? []).slice()) fn({ type: ev }); }
}
let rafSeq = 0; const rafQ = [];
globalThis.document = { createElement: (t) => new El(t) };
globalThis.requestAnimationFrame = (fn) => (rafQ.push(fn), ++rafSeq);
globalThis.cancelAnimationFrame = () => {};
function tick() { const q = rafQ.splice(0, rafQ.length); for (const fn of q) fn(); }

// ---- 假模型：结构镜像真实核心（参数/部件 id 走 .parameters.ids / .parts.ids）----
function makeFake(paramIds = ['ParamA', 'ParamB', 'ParamC'], partIds = ['Part1', 'Part2'],
                  groups = { Idle: [{}], Talk: [{}] }) {
  const calls = { setParam: [], setPart: [], motions: [] };
  const paramValues = Object.fromEntries(paramIds.map((id, i) => [id, i === 1 ? -3 : 0.5]));
  const partOpacity = Object.fromEntries(partIds.map((id) => [id, 1]));
  const coreModel = {
    model: { parameters: { ids: paramIds }, parts: { ids: partIds } },
    getParameterCount: () => paramIds.length,
    getParameterValueById: (id) => paramValues[id] ?? 0,
    setParameterValueById: (id, v) => { paramValues[id] = v; calls.setParam.push([id, v]); },
    getParameterMinimumValue: (i) => (i === 1 ? -30 : -1),
    getParameterMaximumValue: (i) => (i === 1 ? 30 : 1),
    getPartCount: () => partIds.length,
    getPartOpacityById: (id) => partOpacity[id] ?? 1,
    setPartOpacityById: (id, v) => { partOpacity[id] = v; calls.setPart.push([id, v]); },
  };
  const fakeModel = {
    visible: true, alpha: 1,
    motion: (g, i, p) => (calls.motions.push([g, i, p]), Promise.resolve(true)),
    internalModel: {
      coreModel, settings: { motions: groups },
      eyeBlink: { tag: 'eyeBlink' }, breath: { tag: 'breath' }, physics: { tag: 'physics' },
    },
  };
  return { calls, coreModel, fakeModel, paramValues };
}

// ---- 查找辅助 ----
function walk(el, pred, out = []) {
  if (pred(el)) out.push(el);
  for (const c of el.children) walk(c, pred, out);
  return out;
}
const sliderOf = (panel, label) => {
  const lab = walk(panel, (e) => e.tagName === 'label' && e.textContent === label)[0];
  return lab ? walk(lab.parentNode, (e) => e.tagName === 'input' && e.type === 'range')[0] : undefined;
};
const checkboxOf = (panel, label) => {
  const lab = walk(panel, (e) => e.tagName === 'label' && e.textContent === label)[0];
  return lab ? walk(lab.parentNode, (e) => e.tagName === 'input' && e.type === 'checkbox')[0] : undefined;
};
const panelEl = (container) => walk(container, (e) => e.attrs.id === 'debug-panel')[0];

// ---- 用例 ----
test('四区标题齐全', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  for (const t of ['显示', '动作', '参数', '部件'])
    assert.ok(walk(panelEl(c), (e) => e.tagName === 'h3' && e.textContent === t).length === 1, t);
});
test('参数/部件滑条按核心结构生成（路径错误的回归用例）', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  for (const id of ['ParamA', 'ParamB', 'ParamC', 'Part1', 'Part2'])
    assert.ok(sliderOf(panelEl(c), id), `缺滑条 ${id}`);
});
test('参数滑条 min/max 取自核心值域', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const s = sliderOf(panelEl(c), 'ParamB');
  assert.equal(s.min, '-30'); assert.equal(s.max, '30');
});
test('拖动参数滑条写入核心', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const s = sliderOf(panelEl(c), 'ParamB');
  s.value = '5'; s.dispatch('input');
  assert.deepEqual(f.calls.setParam.at(-1), ['ParamB', 5]);
  assert.equal(f.paramValues.ParamB, 5);
});
test('部件滑条写入不透明度', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const s = sliderOf(panelEl(c), 'Part1');
  s.value = '0'; s.dispatch('input');
  assert.deepEqual(f.calls.setPart.at(-1), ['Part1', 0]);
});
test('行为开关：置 null / 还原快照', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const origin = f.fakeModel.internalModel.eyeBlink;
  const box = checkboxOf(panelEl(c), '眨眼');
  box.checked = false; box.dispatch('change');
  assert.equal(f.fakeModel.internalModel.eyeBlink, null);
  box.checked = true; box.dispatch('change');
  assert.equal(f.fakeModel.internalModel.eyeBlink, origin);
});
test('动作按钮以 FORCE 优先级播放', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const btn = walk(panelEl(c), (e) => e.tagName === 'button')[0];
  btn.dispatch('click');
  assert.deepEqual(f.calls.motions[0], ['Idle', undefined, 3]);
});
test('RAF 回写跳过拖动中的行，松手恢复', () => {
  const f = makeFake(); const c = new El('div');
  new DebugPanel(c, () => f.fakeModel);
  const s = sliderOf(panelEl(c), 'ParamA');
  s.dispatch('pointerdown');
  f.paramValues.ParamA = 0.9;
  tick();
  assert.equal(s.value, '0.5'); // 拖动中不回写
  s.dispatch('pointerup');
  tick();
  assert.equal(s.value, '0.9'); // 松手后回写
});
test('onModelChanged 按新模型重建', () => {
  const c = new El('div');
  const f1 = makeFake(); const f2 = makeFake(['P1', 'P2', 'P3', 'P4'], ['Q1']);
  let cur = f1.fakeModel;
  const p = new DebugPanel(c, () => cur);
  cur = f2.fakeModel; p.onModelChanged();
  assert.ok(sliderOf(panelEl(c), 'P4'));
  assert.ok(!sliderOf(panelEl(c), 'ParamA'));
  assert.ok(sliderOf(panelEl(c), 'Q1'));
});
test('destroy 移除面板且后续 tick 不抛', () => {
  const f = makeFake(); const c = new El('div');
  const p = new DebugPanel(c, () => f.fakeModel);
  p.destroy();
  assert.equal(c.children.length, 0);
  assert.doesNotThrow(() => tick());
});
test('无模型时显示占位', () => {
  const c = new El('div');
  new DebugPanel(c, () => null);
  assert.ok(walk(panelEl(c), (e) => e.textContent === '（无模型）').length === 1);
});
```

说明：静态 import 会先于本文件顶层执行——DebugPanel 模块顶层不碰 `document`
（只在构造函数里用），故全局垫片在用例执行前就位即可，顺序安全。

## 附录 B · `frontend-minimal/tests/test_debug_panel_runtime.py`（原文照抄）

```python
# -*- coding: utf-8 -*-
"""运行时行为测试编排：tsc 编译面板模块到 tests/__tsout__ → node --test 执行附录 A 用例。
输出目录放在 frontend-minimal 包内（package.json type=module），编译产物才是 ESM。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
OUT = FM / "tests" / "__tsout__"


def run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True)


def test_runtime_behavior():
    compile_cmd = (
        f'node "{FM / "node_modules/typescript/bin/tsc"}" '
        f'"{FM / "src/renderer/l2d_debug_panel.ts"}" '
        f'--outDir "{OUT}" --rootDir "{FM / "src/renderer"}" '
        f"--module es2020 --target es2020 --skipLibCheck"
    )
    r = run(compile_cmd)
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "")[-1500:])
        sys.stderr.write((r.stderr or "")[-1500:])
    assert r.returncode == 0, "tsc 编译失败"

    js = OUT / "l2d_debug_panel.js"
    assert js.exists(), f"编译产物缺失：{js}"

    r2 = run(f'node --test "{FM / "tests/debug_panel_runtime.test.mjs"}"')
    if r2.returncode != 0:
        sys.stderr.write((r2.stdout or "")[-3000:])
        sys.stderr.write((r2.stderr or "")[-3000:])
    assert r2.returncode == 0, "node --test 运行时用例失败"
```

注意：`tests/__tsout__/` 是编译产物目录，验收后可留可删（不在 vite 引用图内，不影响构建）；
若人工验收或后续阶段要清掉，直接删目录即可。

## 附录 C · stage1 规格书勘误记录（只读备查，不回写）

| stage1 原文 | 错误 | 更正 |
|-------------|------|------|
| §2 `coreModel.model.parameterIds / partIds` | 路径不存在（本次根因） | `coreModel.model.parameters.ids / parts.ids`（§0 证据） |
| §3.1 注释「未开启时 el 为 null」 | 与实现不符（构造即建 el） | 以弱模型实现为准 |
| §6 曾出现误建 .py 的示例命令 | 笔误 | 已在 stage1 当场修正 |
| types 内联在面板文件 | 实施行数超限 | 弱模型拆 `l2d_debug_panel_types.ts`，保留并已有测试 |
