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
  const coreRaw = { parameters: { ids: paramIds }, parts: { ids: partIds } };
  const coreModel = {
    getModel: () => coreRaw,
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
  assert.ok(!('model' in f.coreModel), '假核心不得带 .model 属性（防回归）');
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
