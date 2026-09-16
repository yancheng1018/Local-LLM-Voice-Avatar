/**
 * Live2D 参数驱动引擎（纯逻辑 + localStorage，无 pixi 依赖，≤220 行，
 * 2026-09-13 放宽：逆向语义契约注释密度高，拆分会破坏单文件布局+测试断言，见 minimal-frontend.md）。
 * l2d.su 参数侧语义：mode1 circle=按住绕区中心的「转盘」（l2d.ts 每帧按 atan2 角度算值经
 * setHoldValue 下传，hold 中平滑趋近、不回落；单击 poke=翻转开关：目标在 circleTarget/startValue
 * 间切换后到位停留，不自动回落）；slide（无 action 且 offset≠0，typed-无 action 同走线性）=拖拽轴灵敏度
 * （0 轴排除为本地保留，r4 疑点1；值=hold 起点值+主轴位移/offset，经 clampChain 三步链
 * dragDirect 门控→rangeAbs→range 钳幅（r4 §3.1c）；增量单位=CSS 像素、y 上正，由调用方换算）；
 * mode1 drag(type1/6/7)=拖动累积值（type103 查表）驱动；mode2=指针归一化 × 增益求和。动作播放归 TouchChain。
 */

/** relationParameter.list[].type === 103：查表驱动（relation_value）标记 */
export const RELATION_LOOKUP_TYPE = 103;
/** localStorage 存储键前缀（构建产物断言依赖，勿改字面量） */
export const PARAM_STORAGE_PREFIX = 'l2d-param:';

export interface ParamRule {
  /** id=rule.id（默认热区负数）；parameter=模型参数名；mode=1 手势驱动 / 2 指针位置反应 */
  id: number; parameter: string; mode: number;
  /** range=[min,max]；rangeAbs=1 取绝对值；dragDirect=0 双向 1 仅正 2 仅负 */
  startValue: number; range: [number, number]; rangeAbs?: number; dragDirect?: number;
  /** smooth/revertSmooth=ms 时间常数；revert=-1 不自动归位；saveParameter≠-1 且 revert=-1 → 持久化 */
  smooth?: number; revertSmooth?: number; revert?: number; saveParameter?: number;
  /** reactPosX/Y=mode2 增益；relationValue=type 103 查表；circleTarget={circle:true,target:N}
   *  slide=slide 型拖拽轴灵敏度（无 actionTrigger 且 offset≠0，offsetX/Y 是灵敏度非位置） */
  reactPosX?: number; reactPosY?: number; relationValue?: number[]; circleTarget?: number;
  slide?: { ox: number; oy: number };
}

/** 防御式结构类型，调用方传 internalModel.coreModel（Cubism 4 core） */
export interface ParamCore {
  setParameterValueById?(id: string, v: number): void;
  getParameterValueById?(id: string): number;
  [key: string]: unknown;
}

/** value=当前平滑值；dragAccum=累积输入；pokeTarget=poke 目标；holdValue=转盘实时值；
 *  inputUntil=输入中窗口；saved/dirty=持久化 */
interface ParamState {
  value: number; dragAccum: number; saved: number; dirty: boolean;
  phase: 'idle' | 'poke'; pokeTarget: number; holdValue?: number; inputUntil: number;
}

const clamp = (v: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, v));
const POINTER_ACTIVE_MS = 300;   // addDrag 后视为输入中的窗口（拖动中每帧刷新）
const POKE_EPSILON = 0.05;       // |v-target| 小于此值视为到位
const DEFAULT_SMOOTH = 180;      // 目测校准（TouchDrag1 实测 180）
const DEFAULT_REVERT_SMOOTH = 500;

/** 拖动累积值修正（r4 §3.1c 站点 fixLive2DParameterTargetValue 三步次序源码直证）：
 *  dragDirect 方向门控 → rangeAbs 取绝对值 → range 钳幅。v3 §2.5 曾删门控（r3 §5.4.2
 *  观感反推），致 rangeAbs=1 的负 offset 规则向上拖翻正（wuqi drag6 两方向同值 30，
 *  r4 §10.4 用户实测+模拟确证）——门控恢复后负增量归零，与站点一致 */
export function clampChain(value: number, r: Pick<ParamRule, 'range' | 'rangeAbs' | 'dragDirect'>): number {
  let v = value;
  if ((v < 0 && r.dragDirect === 1) || (v > 0 && r.dragDirect === 2)) v = 0;
  if (r.rangeAbs === 1) v = Math.abs(v);
  return clamp(v, r.range[0], r.range[1]);
}

/** type 103 查表：value/rangeMax 线性映射到 relation_value 下标后取值 */
export function lookup103(relationValue: number[], value: number, rangeMax: number): number {
  const len = relationValue.length;
  if (!len || !Number.isFinite(value)) return 0;
  const rm = rangeMax > 0 ? rangeMax : 1;
  return relationValue[clamp(Math.round((value / rm) * (len - 1)), 0, len - 1)] ?? 0;
}

/** mode2 目标值：同 parameter 只取最小 id（存在更小 id 的大 id 规则跳过），Σ(reactPosX×nx + reactPosY×ny) */
export function reactSum(rules: ParamRule[], nx: number, ny: number): number {
  const best = new Map<string, ParamRule>();
  for (const r of rules) {
    if (r.mode !== 2) continue;
    const cur = best.get(r.parameter);
    if (!cur || r.id < cur.id) best.set(r.parameter, r);
  }
  let sum = 0;
  for (const r of best.values()) sum += (r.reactPosX ?? 0) * nx + (r.reactPosY ?? 0) * ny;
  return sum;
}

/** 画布矩形归一化 [-1,1]；y 反向（向上为正，l2d.su 同款） */
export function canvasNorm(clientX: number, clientY: number, rect: DOMRect): { x: number; y: number } {
  return {
    x: clamp(((clientX - rect.left) / rect.width) * 2 - 1, -1, 1),
    y: clamp(-((clientY - rect.top) / rect.height) * 2 + 1, -1, 1),
  };
}

export class ParamDriver {
  private rules: ParamRule[] = [];
  private parameterRange: Record<string, [number, number]> = {};
  private scopeName = '';
  private states = new Map<number, ParamState>();
  /** hold 管线（spec stage3 v2 §3.1.2）：按住拖拽的参数规则 id 与模型局部累积位移 */
  private holdId: number | null = null;
  private holdAcc = { x: 0, y: 0 };
  /** hold 起点的当前值（r3 §5.1 站点 interaction.values 语义：拖拽从当前值续算，非 startValue 重锚） */
  private holdBase = 0;

  constructor(private readonly storagePrefix: string) {}

  setRules(rules: ParamRule[], parameterRange: Record<string, [number, number]>, scopeName: string): void {
    this.rules = rules;
    this.parameterRange = parameterRange ?? {};
    this.scopeName = scopeName ?? '';
    this.states = new Map(
      rules.map((r) => [
        r.id,
        {
          value: r.startValue, dragAccum: r.startValue, saved: r.startValue, dirty: false,
          phase: 'idle' as const, pokeTarget: r.startValue, inputUntil: 0,
        },
      ] as [number, ParamState]),
    );
    this.restore();
  }

  /** circle 型单击点戳：目标翻转——当前值已在 circleTarget（<0.05）则翻回 startValue，
   *  否则逼近 circleTarget；到位回落由 stepCircle 处理（快速单击 = 一次逼近+回落）。
   *  清除残留转盘值：tap 优先于上一次 hold 的收敛 */
  poke(id: number): void {
    const r = this.rules.find((x) => x.id === id);
    const st = this.states.get(id);
    if (!r || !st || r.circleTarget === undefined) return;
    st.holdValue = undefined;
    st.pokeTarget = Math.abs(st.value - r.circleTarget) < POKE_EPSILON ? r.startValue : r.circleTarget;
    st.phase = 'poke';
  }

  /** hold 开始（spec stage3 v2 §3.1.2）：仅参数规则响应；circle 进入画圈循环起点 */
  beginHold(id: number): void {
    const r = this.rules.find((x) => x.id === id);
    if (!r) return;
    this.holdId = id;
    this.holdAcc = { x: 0, y: 0 };
    this.holdBase = this.states.get(id)?.dragAccum ?? r.startValue;
    const st = this.states.get(id);
    if (st && r.circleTarget !== undefined) {
      st.phase = 'poke';
      st.pokeTarget = r.circleTarget;
    }
  }

  /** hold 中每帧模型局部位移累积；非 hold 中的 id 静默忽略（非参数规则天然不响应） */
  holdDelta(id: number, dx: number, dy: number): void {
    if (this.holdId !== id) return;
    this.holdAcc.x += dx;
    this.holdAcc.y += dy;
    const st = this.states.get(id);
    if (st) st.inputUntil = Date.now() + POINTER_ACTIVE_MS; // 释放后短暂保持再回落
  }

  /** hold 中下传转盘实时值（spec stage4 §2.2）：l2d.ts 每帧按角度公式算好，这里只存 */
  setHoldValue(id: number, value: number): void {
    if (this.holdId !== id) return;
    const r = this.rules.find((x) => x.id === id);
    const st = this.states.get(id);
    if (!r || !st || r.circleTarget === undefined) return;
    st.holdValue = clampChain(value, r);
  }

  /** hold 结束（spec stage4 §2.2）：revert=-1 值保留——holdValue 留存，释放后继续收敛到
   *  最后的转盘值（stepCircle 收敛后清除）；否则立即回落 startValue */
  endHold(id: number): void {
    if (this.holdId !== id) return;
    this.holdId = null;
    const r = this.rules.find((x) => x.id === id);
    const st = this.states.get(id);
    if (!r || !st) return;
    if (r.circleTarget !== undefined && r.revert !== -1) {
      st.holdValue = undefined;
      st.pokeTarget = r.startValue;
      st.phase = 'poke';
    } else if (r.circleTarget !== undefined) {
      st.phase = 'idle';
    }
  }

  update(dtMs: number, core: ParamCore, pointer: { x: number; y: number }): void {
    const dt = clamp(dtMs, 0, 250);
    const now = Date.now();
    for (const r of this.rules) {
      const st = this.states.get(r.id);
      if (!st || r.mode === 2) continue;
      const holding = this.holdId === r.id;
      if (r.circleTarget !== undefined) this.stepCircle(r, st, dt, holding);
      else if (r.slide) this.stepSlide(r, st, dt, holding);
      else this.stepDrag(r, st, dt, now, holding);
      const out = r.relationValue ? lookup103(r.relationValue, st.value, r.range[1]) : st.value;
      this.writeParam(r, st, core, out);
    }
    // mode2：target = reactSum；同 parameter 取最小 id 者代表写参数
    const mode2 = this.rules.filter((r) => r.mode === 2);
    const done = new Set<string>();
    for (const r of mode2) {
      if (done.has(r.parameter)) continue;
      done.add(r.parameter);
      const rep = mode2.filter((o) => o.parameter === r.parameter).reduce((a, b) => (b.id < a.id ? b : a));
      const st = this.states.get(rep.id);
      if (!st) continue;
      const target = reactSum(mode2, pointer.x, pointer.y);
      st.value += (target - st.value) * this.k(dt, r.smooth);
      this.writeParam(rep, st, core, st.value);
    }
  }

  /** 只读：按参数名取当前内部值（叠加层验收仪表盘用，spec stage5 §2.6）；无此参数返回 undefined */
  getValue(parameter: string): number | undefined {
    const r = this.rules.find((x) => x.parameter === parameter);
    return r ? this.states.get(r.id)?.value : undefined;
  }

  /** 把脏参数值写 localStorage[`${prefix}${scopeName}`]（键=rule.id），pointerup 时由调用方触发 */
  save(): void {
    if (!this.scopeName) return;
    const dirty: Record<string, number> = {};
    for (const r of this.rules) {
      const st = this.states.get(r.id);
      if (st?.dirty) dirty[String(r.id)] = st.saved;
    }
    if (!Object.keys(dirty).length) return;
    try {
      localStorage.setItem(this.storagePrefix + this.scopeName, JSON.stringify(dirty));
    } catch { /* localStorage 不可用时静默跳过 */ }
  }

  /** setRules 后回填持久化参数值 */
  restore(): void {
    if (!this.scopeName) return;
    try {
      const raw = localStorage.getItem(this.storagePrefix + this.scopeName);
      if (!raw) return;
      const map = JSON.parse(raw) as Record<string, number>;
      for (const r of this.rules) {
        const st = this.states.get(r.id);
        const v = map[String(r.id)];
        if (!st || typeof v !== 'number' || !Number.isFinite(v)) continue;
        st.value = clamp(v, r.range[0], r.range[1]);
        st.dragAccum = st.saved = st.value;
      }
    } catch { /* 持久化数据损坏时静默忽略 */ }
  }

  /** 一键复位（r3 §6.3 R-1/R-2/R-5）：全部状态回 startValue 并清 dirty/saved，
   *  删除 localStorage 持久化键，防「复位 → 刷新」残留回填 */
  resetAll(): void {
    for (const r of this.rules) {
      const st = this.states.get(r.id);
      if (!st) continue;
      st.value = st.dragAccum = st.saved = r.startValue;
      st.dirty = false;
      st.holdValue = undefined;
      st.phase = 'idle';
      st.pokeTarget = r.startValue;
      st.inputUntil = 0;
    }
    this.holdId = null;
    this.holdAcc = { x: 0, y: 0 };
    if (this.scopeName) {
      try {
        localStorage.removeItem(this.storagePrefix + this.scopeName);
      } catch { /* localStorage 不可用时静默跳过 */ }
    }
  }

  /** circle 状态机（spec stage5 §2.3 翻转开关）：转盘值存在时平滑趋近——hold 中实时跟角度，
   *  释放后收敛到最后转盘值（revert=-1 值保留语义，收敛后清除）；
   *  poke 路径：逼近 pokeTarget 到位后 **停留**（不自动回落，翻转只在 poke 入口） */
  private stepCircle(r: ParamRule, st: ParamState, dt: number, holding: boolean): void {
    if (st.holdValue !== undefined) {
      st.value += (st.holdValue - st.value) * this.k(dt, r.smooth);
      if (!holding && Math.abs(st.value - st.holdValue) < POKE_EPSILON) {
        st.holdValue = undefined;
        st.dragAccum = st.value;
        st.phase = 'idle';
      }
      return;
    }
    if (holding) return; // hold 中尚无转盘值（未移动）则保持
    if (st.phase !== 'poke') return;
    st.value += (st.pokeTarget - st.value) * this.k(dt, r.smooth);
    if (Math.abs(st.value - st.pokeTarget) < POKE_EPSILON) {
      st.value = st.pokeTarget;
      st.phase = 'idle'; // 到位停留（引擎同款：下次 poke 才翻转）
    }
  }

  /** slide 状态机（spec stage3 v2 §3.1.3 + r4 §3.3/疑点1）：值 = hold 起点值 + 主轴位移/offset
   *  （除式、保号）→ clampChain（dragDirect 门控→rangeAbs→range，r4 §3.1c）→ smooth 趋近；
   *  释放后 revert≠-1 回落 startValue。0 轴排除为本地保留项：站点源码实为 ||1 兜底
   *  （r4 §3.3 推翻 r3 §5.4.5），但用户实测站点纯垂直拖无误触发（疑点 1 未决），
   *  待站点数值取证后统一，勿当站点语义引用 */
  private stepSlide(r: ParamRule, st: ParamState, dt: number, holding: boolean): void {
    if (holding && r.slide) {
      const xv = r.slide.ox !== 0 ? this.holdAcc.x / r.slide.ox : undefined;
      const yv = r.slide.oy !== 0 ? this.holdAcc.y / r.slide.oy : undefined;
      const lin =
        xv === undefined ? yv
        : yv === undefined ? xv
        : Math.abs(xv) >= Math.abs(yv) ? xv : yv;
      st.dragAccum = clampChain(this.holdBase + (lin ?? 0), r);
      st.value += (st.dragAccum - st.value) * this.k(dt, r.smooth);
    } else if (r.revert !== -1) {
      st.value += (r.startValue - st.value) * this.k(dt, r.revertSmooth, DEFAULT_REVERT_SMOOTH);
      if (Math.abs(r.startValue - st.value) < POKE_EPSILON) st.value = st.dragAccum = r.startValue;
    } else if (st.value !== st.dragAccum) {
      // 松手且 revert=-1：继续平滑收敛到拖拽终点（值保留语义）
      st.value += (st.dragAccum - st.value) * this.k(dt, r.smooth);
    }
  }

  /** drag 状态机（type1/6/7）：hold 中按位移幅值累积；输入结束且 revert≠-1 时回落 startValue */
  private stepDrag(r: ParamRule, st: ParamState, dt: number, now: number, holding: boolean): void {
    if (holding) {
      const lin = Math.hypot(this.holdAcc.x, this.holdAcc.y);
      st.dragAccum = clampChain(r.startValue + lin, r);
      st.value += (st.dragAccum - st.value) * this.k(dt, r.smooth);
    } else if (now < st.inputUntil) {
      st.value += (st.dragAccum - st.value) * this.k(dt, r.smooth);
    } else if (r.revert !== -1) {
      st.value += (r.startValue - st.value) * this.k(dt, r.revertSmooth, DEFAULT_REVERT_SMOOTH);
      if (Math.abs(r.startValue - st.value) < POKE_EPSILON) st.value = st.dragAccum = r.startValue;
    } else if (st.value !== st.dragAccum) {
      // 松手且 revert=-1：继续平滑收敛到拖拽终点（值保留语义）
      st.value += (st.dragAccum - st.value) * this.k(dt, r.smooth);
    }
  }

  /** 写参数：模型级 parameterRange 先钳制；revert===-1 且 saveParameter≠-1 → 置脏待持久化 */
  private writeParam(r: ParamRule, st: ParamState, core: ParamCore, v: number): void {
    const pr = this.parameterRange[r.parameter];
    const out = pr ? clamp(v, pr[0], pr[1]) : v;
    if (!Number.isFinite(out)) return;
    core.setParameterValueById?.(r.parameter, out); // 参数不存在时静默无效
    if (r.revert === -1 && r.saveParameter !== -1) {
      st.saved = out;
      st.dirty = true;
    }
  }

  /** 指数趋近系数：k = 1 - exp(-dt / smooth) */
  private k(dt: number, ms?: number, fallback: number = DEFAULT_SMOOTH): number {
    return 1 - Math.exp(-dt / (ms && ms > 0 ? ms : fallback));
  }
}
