/** 仿 l2d.su 左侧调试栏：显示/动作/参数/部件。仅 Live2D；model 由面板自行 cast。
 *  已知行为：被 ParamDriver/眨眼/呼吸/物理/口型每帧回写的参数会覆盖滑条（调试工具预期）。 */
import type { DebugCoreModel, DebugCoreSource, DebugPanelModel, Row } from './l2d_debug_panel_types';

export type { DebugCoreModel, DebugPanelModel } from './l2d_debug_panel_types';

const BEHAVIORS = ['eyeBlink', 'breath', 'physics'] as const;
const LABELS: Record<string, string> = { eyeBlink: '眨眼', breath: '呼吸', physics: '物理' };

export class DebugPanel {
  private el: HTMLElement | null = null;
  private raf: number | null = null;
  private rows: Row[] = [];
  private active = new Set<string>();
  private behaviorSaved: Record<string, unknown> = {};

  constructor(private container: HTMLElement, private getModel: () => unknown) {
    this.el = document.createElement('div');
    this.el.id = 'debug-panel';
    this.container.appendChild(this.el);
    this.buildSections();
    const loop = () => {
      this.raf = requestAnimationFrame(loop);
      this.refresh();
    };
    this.raf = requestAnimationFrame(loop);
  }

  /** 模型加载/切换后重建分区内容（未开启时 el 为 null，直接 return） */
  onModelChanged(): void {
    this.rows = [];
    this.active.clear();
    this.behaviorSaved = {};
    this.buildSections();
  }

  private buildSections(): void {
    const el = this.el;
    if (!el) return;
    const model = this.getModel() as DebugPanelModel | null;
    el.replaceChildren();
    if (!model) return void el.appendChild(this.text('（无模型）'));
    this.buildDisplay(el, model);
    this.buildMotions(el, model);
    const core = model.internalModel?.coreModel;
    this.buildList(el, '参数', core, 'parameters', true);
    this.buildList(el, '部件', core, 'parts', false);
  }

  private buildDisplay(root: HTMLElement, model: DebugPanelModel): void {
    root.appendChild(this.heading('显示'));
    const visible = this.checkbox(!!model.visible, (on) => (model.visible = on));
    root.appendChild(this.line('可见', visible));
    this.makeRow(root, '不透明度', 0, 1, () => model.alpha, (v) => (model.alpha = v), 'alpha');
    const im = model.internalModel as Record<string, unknown>;
    for (const key of BEHAVIORS) {
      if (im[key] == null) continue; // 字段缺失或已为 null 时不渲染该行
      this.behaviorSaved[key] = im[key];
      const box = this.checkbox(true, (on) => {
        im[key] = on ? this.behaviorSaved[key] : null;
      });
      root.appendChild(this.line(LABELS[key] ?? key, box));
    }
  }

  private buildMotions(root: HTMLElement, model: DebugPanelModel): void {
    root.appendChild(this.heading('动作'));
    const cfg = model.internalModel?.settings as Record<string, unknown> | undefined;
    const keys = Object.keys((cfg?.motions ?? cfg?.motionGroups ?? {}) as Record<string, unknown>);
    if (keys.length === 0) return void root.appendChild(this.text('（无动作组）'));
    for (const g of keys) {
      const btn = document.createElement('button');
      btn.textContent = '▶';
      btn.addEventListener('click', () => void model.motion(g, undefined, 3));
      root.appendChild(this.line(g, btn));
    }
  }

  /** 参数区/部件区共用：ids 逐条建滑条（asParam=true 参数区读 min/max，否则部件区固定 0~1） */
  private buildList(
    root: HTMLElement,
    title: string,
    core: DebugCoreModel | null | undefined,
    field: 'parameters' | 'parts',
    asParam: boolean,
  ): void {
    root.appendChild(this.heading(title));
    if (!core) return void root.appendChild(this.text('（未暴露 coreModel）'));
    const ids = this.ids(core, field);
    if (ids.length === 0) return void root.appendChild(this.text('（未暴露 ID 列表）'));
    const n = Math.min(ids.length, asParam ? core.getParameterCount() : core.getPartCount());
    for (let i = 0; i < n; i++) {
      const id = ids[i];
      const read = () => (asParam ? core.getParameterValueById(id) : core.getPartOpacityById(id));
      this.makeRow(
        root,
        id,
        asParam ? core.getParameterMinimumValue(i) : 0,
        asParam ? core.getParameterMaximumValue(i) : 1,
        read,
        (v) => (asParam ? core.setParameterValueById(id, v) : core.setPartOpacityById(id, v)),
        `${field}:${id}`,
      );
    }
  }

  /** 原始 core 结构取 ID 列表（核心 Live2DCubismCore.Model 结构：parameters.ids / parts.ids，
   *  dist 内库自身消费 this._model.parts.ids 同源；经框架 getModel() 公开访问器取） */
  private ids(core: DebugCoreModel, field: 'parameters' | 'parts'): string[] {
    const raw = (core as unknown as DebugCoreSource).getModel?.()[field]?.ids;
    return Array.isArray(raw) ? raw : [];
  }

  /** 行工厂：label + range + 数值 span，统一注册进 rows 供 RAF 回写 */
  private makeRow(
    parent: HTMLElement,
    label: string,
    min: number,
    max: number,
    get: () => number,
    set: (v: number) => void,
    key: string,
  ): void {
    const row = document.createElement('div');
    row.className = 'row';
    const input = document.createElement('input');
    input.type = 'range';
    input.min = String(min);
    input.max = String(max);
    input.step = '0.01';
    input.value = String(get());
    input.addEventListener('pointerdown', () => this.active.add(key));
    for (const ev of ['pointerup', 'pointercancel', 'blur']) {
      input.addEventListener(ev, () => this.active.delete(key)); // 拖动结束恢复回写
    }
    const val = document.createElement('span');
    val.className = 'val';
    val.textContent = get().toFixed(2);
    input.addEventListener('input', () => {
      set(Number(input.value));
      val.textContent = get().toFixed(2);
    });
    this.rows.push({ key, input, val, get });
    row.append(this.label(label), input, val);
    parent.appendChild(row);
  }

  private refresh(): void {
    if (!this.el) return;
    for (const r of this.rows) {
      if (this.active.has(r.key)) continue; // 拖动中的滑条不被回写覆盖
      r.input.value = String(r.get());
      r.val.textContent = r.get().toFixed(2);
    }
  }

  private heading(text: string): HTMLElement {
    const h = document.createElement('h3');
    h.textContent = text;
    return h;
  }

  private text(t: string): HTMLElement {
    const p = document.createElement('div');
    p.textContent = t;
    return p;
  }

  private label(text: string): HTMLLabelElement {
    const lab = document.createElement('label');
    lab.textContent = text;
    lab.title = text;
    return lab;
  }

  private checkbox(checked: boolean, onChange: (checked: boolean) => void): HTMLInputElement {
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = checked;
    box.addEventListener('change', () => onChange(box.checked));
    return box;
  }

  private line(label: string, control: HTMLElement): HTMLElement {
    const row = document.createElement('div');
    row.className = 'row';
    row.append(this.label(label), control);
    return row;
  }

  destroy(): void {
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
    this.el?.remove();
    this.el = null;
    this.rows = [];
    this.active.clear();
    this.behaviorSaved = {};
  }
}
