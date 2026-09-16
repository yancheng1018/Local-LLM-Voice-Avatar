const BEHAVIORS = ['eyeBlink', 'breath', 'physics'];
const LABELS = { eyeBlink: '眨眼', breath: '呼吸', physics: '物理' };
export class DebugPanel {
    constructor(container, getModel) {
        this.container = container;
        this.getModel = getModel;
        this.el = null;
        this.raf = null;
        this.rows = [];
        this.active = new Set();
        this.behaviorSaved = {};
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
    onModelChanged() {
        this.rows = [];
        this.active.clear();
        this.behaviorSaved = {};
        this.buildSections();
    }
    buildSections() {
        const el = this.el;
        if (!el)
            return;
        const model = this.getModel();
        el.replaceChildren();
        if (!model)
            return void el.appendChild(this.text('（无模型）'));
        this.buildDisplay(el, model);
        this.buildMotions(el, model);
        const core = model.internalModel?.coreModel;
        this.buildList(el, '参数', core, 'parameters', true);
        this.buildList(el, '部件', core, 'parts', false);
    }
    buildDisplay(root, model) {
        root.appendChild(this.heading('显示'));
        const visible = this.checkbox(!!model.visible, (on) => (model.visible = on));
        root.appendChild(this.line('可见', visible));
        this.makeRow(root, '不透明度', 0, 1, () => model.alpha, (v) => (model.alpha = v), 'alpha');
        const im = model.internalModel;
        for (const key of BEHAVIORS) {
            if (im[key] == null)
                continue; // 字段缺失或已为 null 时不渲染该行
            this.behaviorSaved[key] = im[key];
            const box = this.checkbox(true, (on) => {
                im[key] = on ? this.behaviorSaved[key] : null;
            });
            root.appendChild(this.line(LABELS[key] ?? key, box));
        }
    }
    buildMotions(root, model) {
        root.appendChild(this.heading('动作'));
        const cfg = model.internalModel?.settings;
        const keys = Object.keys((cfg?.motions ?? cfg?.motionGroups ?? {}));
        if (keys.length === 0)
            return void root.appendChild(this.text('（无动作组）'));
        for (const g of keys) {
            const btn = document.createElement('button');
            btn.textContent = '▶';
            btn.addEventListener('click', () => void model.motion(g, undefined, 3));
            root.appendChild(this.line(g, btn));
        }
    }
    /** 参数区/部件区共用：ids 逐条建滑条（asParam=true 参数区读 min/max，否则部件区固定 0~1） */
    buildList(root, title, core, field, asParam) {
        root.appendChild(this.heading(title));
        if (!core)
            return void root.appendChild(this.text('（未暴露 coreModel）'));
        const ids = this.ids(core, field);
        if (ids.length === 0)
            return void root.appendChild(this.text('（未暴露 ID 列表）'));
        const n = Math.min(ids.length, asParam ? core.getParameterCount() : core.getPartCount());
        for (let i = 0; i < n; i++) {
            const id = ids[i];
            const read = () => (asParam ? core.getParameterValueById(id) : core.getPartOpacityById(id));
            this.makeRow(root, id, asParam ? core.getParameterMinimumValue(i) : 0, asParam ? core.getParameterMaximumValue(i) : 1, read, (v) => (asParam ? core.setParameterValueById(id, v) : core.setPartOpacityById(id, v)), `${field}:${id}`);
        }
    }
    /** 原始 core 结构取 ID 列表（核心 Live2DCubismCore.Model 结构：parameters.ids / parts.ids，
     *  dist 内库自身消费 this._model.parts.ids 同源；经框架 getModel() 公开访问器取） */
    ids(core, field) {
        const raw = core.getModel?.()[field]?.ids;
        return Array.isArray(raw) ? raw : [];
    }
    /** 行工厂：label + range + 数值 span，统一注册进 rows 供 RAF 回写 */
    makeRow(parent, label, min, max, get, set, key) {
        const row = document.createElement('div');
        row.className = 'row';
        const input = document.createElement('input');
        input.type = 'range';
        input.min = String(min);
        input.max = String(max);
        input.step = '0.01';
        input.value = String(get());
        input.addEventListener('pointerdown', (e) => {
            // r4 §10.2-C：指针捕获——拖出滑条外释放时 pointerup 也必达 input，
            // 防 active 永久滞留导致该行不再回写（面板"不刷新"）；异常时退化为原行为
            try {
                input.setPointerCapture(e.pointerId);
            }
            catch {
                /* 运行时无该 API（如测试 fake 元素）或 pointer 已释放时忽略 */
            }
            this.active.add(key);
        });
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
    refresh() {
        if (!this.el)
            return;
        for (const r of this.rows) {
            if (this.active.has(r.key))
                continue; // 拖动中的滑条不被回写覆盖
            r.input.value = String(r.get());
            r.val.textContent = r.get().toFixed(2);
        }
    }
    heading(text) {
        const h = document.createElement('h3');
        h.textContent = text;
        return h;
    }
    text(t) {
        const p = document.createElement('div');
        p.textContent = t;
        return p;
    }
    label(text) {
        const lab = document.createElement('label');
        lab.textContent = text;
        lab.title = text;
        return lab;
    }
    checkbox(checked, onChange) {
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.checked = checked;
        box.addEventListener('change', () => onChange(box.checked));
        return box;
    }
    line(label, control) {
        const row = document.createElement('div');
        row.className = 'row';
        row.append(this.label(label), control);
        return row;
    }
    destroy() {
        if (this.raf !== null)
            cancelAnimationFrame(this.raf);
        this.raf = null;
        this.el?.remove();
        this.el = null;
        this.rows = [];
        this.active.clear();
        this.behaviorSaved = {};
    }
}
