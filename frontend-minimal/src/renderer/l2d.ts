import { Application, Point, Ticker } from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display/cubism4';
import { TouchDebugOverlay } from './l2d_touch_debug';
import type { TouchDebugModel, TouchZoneState } from './l2d_touch_debug';
import type { ModelInfo, CharacterRenderer } from './types';
import type { TouchRule, TouchData, TouchActionStep } from './l2d_touch';
import { type12Decision } from './l2d_touch';
import { ParamDriver, canvasNorm, PARAM_STORAGE_PREFIX } from './l2d_params';
import type { ParamRule, ParamCore } from './l2d_params';
import { toRelationPresets } from './l2d_params_relations';
import { DebugPanel } from './l2d_debug_panel';

/** 空间热区条目：touch.json 规则（或默认热区伪规则）+ 对应绘画件索引。
 *  渲染序/包围盒/可见性不缓存——命中判定时逐 drawable 现读（spec stage3 §3.1） */
interface TouchZone {
  drawIndex: number;
  group: string;
  name: string;
  rule: TouchRule;
}

/** model3.json FileReferences.Motions 条目展开（动作名索引用，spec stage3 §3.3） */
interface MotionEntry {
  group: string;
  index: number;
  name?: string;
  fileStem?: string;
}

/** 规则区交互门槛（引擎全套）：actionTrigger.type 允许集（stage1b §0.3） */
const OE_TYPES = new Set([1, 2, 3, 4, 6, 8, 9, 11, 14, 15]);
/** 透明度剔除阈值：opacity <= 0.01 视为不可交互（deob 证实，stage1b §0.6） */
const OPACITY_CUTOFF = 0.01;
/** 动作结束事件等待的死锁保护（motionFinish 事件丢失时按此上限放行） */
const MOTION_FINISH_TIMEOUT_MS = 15000;

/** 参数引擎帧驱动挂点：动作曲线写完后、saveParameters 快照前（beforeModelUpdate 的
 *  写入会被帧末 loadParameters() 用快照还原，touch 参数恒 0——研究报告 §5.0） */
const PARAM_DRIVE_EVENT = 'afterMotionUpdate';

/** 动作名归一化（stage1b §9.7 口径）：剥路径与 .motion3.json 等扩展名 → trim → [-\s]+→_ → lowercase */
function normalizeMotionName(s: string): string {
  return s
    .replace(/^.*[\\/]/, '')
    .replace(/\.motion\d*\.json$/i, '')
    .trim()
    .replace(/[-\s]+/g, '_')
    .toLowerCase();
}

/** 规则可播动作名集：actionTrigger.action 与 action_list[].action 合并 */
function actionNamesOf(rule: TouchRule): string[] {
  const t = rule.actionTrigger;
  if (!t) return [];
  const out: string[] = [];
  const push = (a: unknown): void => {
    if (typeof a === 'string' && a) out.push(a);
    else if (Array.isArray(a)) for (const x of a) if (typeof x === 'string' && x) out.push(x);
  };
  push(t.action);
  for (const step of (t.action_list ?? []) as TouchActionStep[]) push(step.action);
  return out;
}

// pixi-live2d-display 需要 pixi 的 Ticker 驱动模型更新
Live2DModel.registerTicker(Ticker);

/**
 * Live2D 渲染器。
 *
 * 缩放语义与原前端（Cubism 官方 sample 改）对齐：模型逻辑画布高 H（= CanvasHeight /
 * PixelsPerUnit）在视口中占屏高的比例 = kScale × H / 2 × CurrentKScale… 化简后
 * pixi 侧 scale = kScale × 屏高 / PixelsPerUnit（推导见 ZCODE_CONTEXT.md）。
 * mao_pro（kScale 0.5）应与原前端 / 页面显示大小一致，联调时以此目测校准。
 */
export class L2DRenderer implements CharacterRenderer {
  private app: Application;
  private model: Live2DModel | null = null;
  private kScale = 0.5;
  private xShift = 0;
  private yShift = 0;
  private observer: ResizeObserver | null = null;
  private lipSyncHandler: (() => void) | null = null;
  private gesture = { down: false, x: 0, y: 0, t: 0, dragging: false };
  /** 拖动增量像素化的前一次指针屏幕位置（spec stage5 §2.1） */
  private prevDragPx: { x: number; y: number } | null = null;
  /** live2dTouch 规则热区（touch.json，游戏同款数据）+ 默认热区；null=模型无此数据 */
  private touchAreas: TouchZone[] | null = null;
  /** touch.json 原始规则数组（含未注册为区的规则；链步进 findChainRule 查找用，spec stage6 §2.1） */
  private touchRules: TouchRule[] | null = null;
  /** 参数驱动引擎（touch.json 的 circle/drag/mode2 参数规则）；null=无可驱动参数 */
  private paramDriver: ParamDriver | null = null;
  private paramHandler: (() => void) | null = null;
  private lastParamAt = 0;
  /** 指针画布归一化位置（canvasNorm），供 mode2 位置反应每帧消费 */
  private pointerNorm = { x: 0, y: 0 };
  /** pointerdown 时命中的 Zone（含 drawIndex 供转盘中心计算）：拖动型（type 1/6/7）
   *  在拖动路径累积参数，circle 型走转盘值 */
  private downHitZone: TouchZone | null = null;
  /** mode2 反应规则是否存在（无空间热区但有反应参数的模型也要抑制兜底） */
  private hasParamRules = false;
  private touchDebugOverlay: TouchDebugOverlay | null = null;
  private debugPanel: DebugPanel | null = null;
  /** load() 时缓存，供 tapMotions 查询 */
  private modelInfo: ModelInfo | null = null;
  /** 动作名索引（load 后从 FileReferences.Motions 展开，spec stage3 §3.3） */
  private motionEntries: MotionEntry[] = [];
  /** 触摸动作播放门控状态（§3.4.1）：播放中只放行命中区自身规则链 */
  private touchPlay: { active: boolean; ruleId: number | null } = { active: false, ruleId: null };
  /** main.ts 注入：触摸链动作白名单判定（规则区交互门槛用）；未注入默认全放行 */
  actionAllowed: (name: string) => boolean = () => true;
  /** main.ts 注入：触摸链当前 idleIndex（ATA.idle 门槛 + idle 回放组名用） */
  chainIdleIndex: () => number = () => 0;
  /** 规则链步只读回调（main.ts 注入 TouchChain.stepIndex；未注入恒 0 = 站点 || 0 缺省） */
  chainStepIndex: (ruleId: number) => number = () => 0;
  /** main.ts 注入：触摸链状态归零（复位时用，不持有 TouchChain 实例） */
  resetTouchChain: (() => void) | null = null;

  /** 手势互动回调：tap=单击、drag=按住拖动超阈值、longpress=按住 ≥800ms。
   *  areas=Live2D 命名热区；region=包围盒估计的头/身区域；
   *  rule=touch.json 命中的完整规则（含 actionTrigger/actionTriggerActive，供 TouchChain 分发） */
  onInteraction:
    | ((info: {
        kind: 'tap' | 'drag' | 'longpress';
        areas: string[];
        region: 'head' | 'body';
        rule: TouchRule | null;
      }) => void)
    | null = null;

  /** 拖动阈值（px）与长按时长（ms）；拖动增量单位 = CSS 像素（引擎同款，spec stage5 §2.1） */
  private static readonly DRAG_THRESHOLD = 40;
  private static readonly LONGPRESS_MS = 800;

  constructor(
    private container: HTMLElement,
    private getVolume: () => number = () => 0,
  ) {
    this.app = new Application({
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      resizeTo: container,
    });
    this.container.appendChild(this.app.view as HTMLCanvasElement);

    // pixi v7 事件派发需要 stage 显式可命中，否则模型上的指针事件时有时无
    this.app.stage.eventMode = 'static';
    this.app.stage.hitArea = this.app.screen;

    this.attachGestures(this.app.view as HTMLCanvasElement);

    this.observer = new ResizeObserver(() => this.layout());
    this.observer.observe(container);
  }

  /** 手势状态机（挂在 canvas 上，跨模型复用）：区分单击 / 拖动 / 长按 */
  private attachGestures(canvas: HTMLCanvasElement): void {
    const g = this.gesture;

    canvas.addEventListener('pointerdown', (e) => {
      g.down = true;
      g.dragging = false;
      g.x = e.clientX;
      g.y = e.clientY;
      g.t = Date.now();
      this.updatePointerNorm(e.clientX, e.clientY);
      const hit = this.hitZoneAt(e.clientX, e.clientY);
      this.downHitZone = hit;
      const downRule = hit?.rule ?? null;
      this.prevDragPx = { x: e.clientX, y: e.clientY };
      if (hit && downRule) {
        this.paramDriver?.beginHold(downRule.id ?? 0);
        // circle 转盘：按下即给按下点角度对应值（引擎每帧随角度；无移动时保持）
        if (downRule.actionTrigger?.circle) {
          const dial = this.dialValueFor(hit, e.clientX, e.clientY);
          if (dial !== null) this.paramDriver?.setHoldValue(downRule.id ?? 0, dial);
        }
      }
    });

    canvas.addEventListener('pointermove', (e) => {
      this.updatePointerNorm(e.clientX, e.clientY); // mode2 位置反应每帧消费最新值
      if (!g.down) return;
      // hold 管线从按下即累积（引擎同款）；40px 阈值只用于派发 drag 交互事件
      this.accumulateDrag(e.clientX, e.clientY);
      if (g.dragging) return;
      if (Math.hypot(e.clientX - g.x, e.clientY - g.y) > L2DRenderer.DRAG_THRESHOLD) {
        g.dragging = true;
        this.emitInteraction('drag', e.clientX, e.clientY);
      }
    });

    canvas.addEventListener('pointerup', (e) => {
      if (!g.down) return;
      g.down = false;
      const downHit = this.downHitZone;
      const downRule = downHit?.rule ?? null;
      this.paramDriver?.endHold(downRule?.id ?? -1);
      // type1/4 通用分支（spec stage3 v2 §3.1.5）：拖拽结束时触发一次其 action
      //（num/time 简化为 1 次；无 action 则无操作）
      const t = downRule?.actionTrigger;
      if (g.dragging && t && (t.type === 1 || t.type === 4)) {
        const names = downRule ? actionNamesOf(downRule) : [];
        if (names.length) void this.playAction(names[0], downRule?.id);
      }
      this.paramDriver?.save(); // revert=-1 的拖动累积参数按 l2d.su 语义落盘
      this.downHitZone = null;
      this.prevDragPx = null;
      if (g.dragging) return; // 拖动已在超过阈值时触发过
      const dur = Date.now() - g.t;
      this.emitInteraction(
        dur >= L2DRenderer.LONGPRESS_MS ? 'longpress' : 'tap',
        e.clientX,
        e.clientY,
        downHit,
      );
    });
  }

  /**
   * circle 转盘值（引擎 live2DCircleDragParameterValue 逐字公式，spec stage5 §2.2）：
   * center 与指针同为**屏幕像素**坐标（y 下），区中心 = 包围盒四角投影屏幕后的几何中心
   * （与 l2d_touch_debug.modelRectToScreen 同款换算链路）。公式不修正符号方向。
   */
  private dialValueFor(zone: TouchZone, clientX: number, clientY: number): number | null {
    if (!this.model) return null;
    const rule = zone.rule;
    const range = rule.range as [number, number] | undefined;
    const rangeMax = Array.isArray(range) && typeof range[1] === 'number' ? range[1] : 1;
    const angleOffset =
      (rule.offsetCircle as { start?: number } | undefined)?.start ?? 0;
    const b = this.drawableBounds(zone.drawIndex);
    if (!b) return null;
    const im = this.model.internalModel as unknown as {
      localTransform?: { apply(p: Point): Point };
    };
    const wt = this.model.worldTransform;
    const local = im?.localTransform;
    const toScreen = (x: number, y: number): Point =>
      wt.apply(local ? local.apply(new Point(x, y)) : new Point(x, y));
    const corners = [
      toScreen(b.x, b.y),
      toScreen(b.x + b.width, b.y),
      toScreen(b.x, b.y + b.height),
      toScreen(b.x + b.width, b.y + b.height),
    ];
    const xs = corners.map((p) => p.x);
    const ys = corners.map((p) => p.y);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const deg = (Math.atan2(clientX - cx, cy - clientY) * 180) / Math.PI;
    const angle = (((deg + 360 - angleOffset) % 360) + 360) % 360;
    return rangeMax * (angle / 360);
  }

  /** 拖动路径（hold 管线，spec stage5 §2.1）：增量 = CSS 像素（x 右正、y 上正，引擎
   *  live2DUnityDragDelta 同构）；circle 型每帧下传转盘值；非参数规则由驱动器自过滤 */
  private accumulateDrag(clientX: number, clientY: number): void {
    const zone = this.downHitZone;
    if (!zone || !this.model) return;
    const rule = zone.rule;
    if (rule.actionTrigger?.circle) {
      const dial = this.dialValueFor(zone, clientX, clientY);
      if (dial !== null) this.paramDriver?.setHoldValue(rule.id ?? 0, dial);
      return;
    }
    if (this.prevDragPx) {
      const dxPx = clientX - this.prevDragPx.x; // 右正
      const dyPx = this.prevDragPx.y - clientY; // 上正（引擎 interaction.y − currentY）
      if (dxPx !== 0 || dyPx !== 0) this.paramDriver?.holdDelta(rule.id ?? 0, dxPx, dyPx);
    }
    this.prevDragPx = { x: clientX, y: clientY };
  }

  private updatePointerNorm(clientX: number, clientY: number): void {
    const rect = (this.app.view as HTMLCanvasElement).getBoundingClientRect();
    this.pointerNorm = canvasNorm(clientX, clientY, rect);
  }

  /** coreModel 的防御式子集（逐 drawable 现读可见性/透明度/渲染序，spec stage3 §3.1；
   *  0.5.0-beta 的 coreModel 无 getDrawableVisibility/getDrawableRenderOrder(i)，真实渲染序 API 为
   *  getDrawableRenderOrders()（复数无参、整条 Int32Array），原始数组在 _model.drawables，spec stage6 §2.2） */
  private touchCore(): {
    getDrawableVisibility?(i: number): boolean;
    getDrawableOpacity?(i: number): number;
    getParameterValueById?(id: string): number;
    getDrawableRenderOrder?(i: number): number;
    getDrawableRenderOrders?(): Int32Array;
    drawables?: { renderOrders?: Int32Array; dynamicFlags?: Int32Array };
    _model?: { drawables?: { renderOrders?: Int32Array; dynamicFlags?: Int32Array } };
  } | null {
    return (
      (this.model?.internalModel as unknown as { coreModel?: object })?.coreModel ?? null
    ) as {
      getDrawableVisibility?(i: number): boolean;
      getDrawableOpacity?(i: number): number;
      getParameterValueById?(id: string): number;
      getDrawableRenderOrder?(i: number): number;
      getDrawableRenderOrders?(): Int32Array;
      drawables?: { renderOrders?: Int32Array; dynamicFlags?: Int32Array };
      _model?: { drawables?: { renderOrders?: Int32Array; dynamicFlags?: Int32Array } };
    } | null;
  }

  /** type12 扩展判定（读 ParamDriver 内部值 = 本地参数权威层，契约候选 R2-a；research2 §3.1） */
  type12DecisionOf(name: string): boolean | undefined {
    return type12Decision(this.touchRules ?? [], name, (p) => this.paramDriver?.getValue(p));
  }

  /** 站点 officialLive2DActionAllowed 同构组合闸：type12 优先，回落注入的 ATA 全局名单 */
  actionAllowedWithParamGate(name: string): boolean {
    const ext = this.type12DecisionOf(name);
    if (typeof ext === 'boolean') return ext;
    return this.actionAllowed(name);
  }

  /** 规则区交互门槛（引擎全套，spec stage3 §3.2；默认热区伪规则豁免=站点可交互面） */
  private isRuleInteractive(rule: TouchRule): boolean {
    if ((rule.id ?? 0) < 0) return true; // 默认热区伪规则：站点可交互面（TouchHead/Body/Special）
    const t = rule.actionTrigger;
    if (!t) return (rule.offsetX ?? 0) !== 0 || (rule.offsetY ?? 0) !== 0; // slide 型
    if (!OE_TYPES.has(t.type ?? -1)) return false;
    // ATA.idle 防重复（r4 §4.3 源码定案：站点 live2DActiveDataRepeatsCurrentIdle 只在
    // 目标 idle == 当前链状态时跳过——防重复播同一 idle；v3「不匹配即拒」方向相反，
    // 锁死 453/874 条 typed 规则，是症状①主因）
    const ataIdle = rule.actionTriggerActive?.idle;
    if (typeof ataIdle === 'number' && ataIdle === this.chainIdleIndex()) return false;
    const names = actionNamesOf(rule);
    // 无 action 规则直接放行（r3 §3.1.1）：站点 live2DRulePointerEnabled 对 typed 规则只要求
    // type∈Oe（上文已判），不要求 action；无 offset 的该类区站点同样可点但无效果（语义一致）
    if (names.length === 0) return true;
    return names.some((n) => this.actionAllowedWithParamGate(n));
  }

  /**
   * l2d.su 同款命中判据（stage3 实时化）：指针 → 模型局部坐标 → 逐 drawable 现读
   * 包围盒/可见性/透明度/渲染序 → 候选集（画布内 + 可见 + opacity>0.01 + 交互门槛）→
   * 按实时渲染序降序取最上层 → 同 id 组内按「规则区(offset≠0) → 有可播动作区 → 首个」择一。
   * 不经 pixi hitTest，不使用注册期缓存。
   */
  private hitZoneAt(clientX: number, clientY: number): (TouchZone & { boundsArea: number; renderOrder: number }) | null {
    if (!this.touchAreas?.length || !this.model) return null;
    const core = this.touchCore();
    const rect = (this.app.view as HTMLCanvasElement).getBoundingClientRect();
    const p = this.model.toModelPosition(new Point(clientX - rect.left, clientY - rect.top));
    const im = this.model.internalModel as unknown as { originalWidth?: number; originalHeight?: number };
    const canvasW = typeof im?.originalWidth === 'number' ? im.originalWidth : Number.POSITIVE_INFINITY;
    const canvasH = typeof im?.originalHeight === 'number' ? im.originalHeight : Number.POSITIVE_INFINITY;
    const hits: (TouchZone & { boundsArea: number; renderOrder: number })[] = [];
    for (const zone of this.touchAreas) {
      // visibility ?? true：0.5.0-beta native 无 getDrawableVisibility；透明度剔除已恢复
      //（r2 收回 D1）；drawables.dynamicFlags 位义未逐字核实故不启用（spec stage6 §2.2）
      if (!(core?.getDrawableVisibility?.(zone.drawIndex) ?? true)) continue;
      // 透明度剔除（r2 收回 D1，站点同款）：透明 TouchIdleN 虚拟标记不进命中池——
      // 死区点击与标记截胡主因（research r2 §5 C1）；阈值与叠加层 T 判定同源
      if ((core?.getDrawableOpacity?.(zone.drawIndex) ?? 1) <= OPACITY_CUTOFF) continue;
      if (!this.isRuleInteractive(zone.rule)) continue;
      const b = this.drawableBounds(zone.drawIndex);
      if (!b) continue;
      if (
        !Number.isFinite(b.x) ||
        !Number.isFinite(b.y) ||
        !Number.isFinite(b.width) ||
        !Number.isFinite(b.height)
      )
        continue;
      if (!(b.width > 0) || !(b.height > 0)) continue;
      // 画布外（逻辑画布不相交）剔除
      if (
        Number.isFinite(canvasW) &&
        Number.isFinite(canvasH) &&
        !(b.x + b.width > 0 && b.x < canvasW && b.y + b.height > 0 && b.y < canvasH)
      )
        continue;
      if (p.x < b.x || p.x > b.x + b.width || p.y < b.y || p.y > b.y + b.height) continue;
      hits.push({
        ...zone,
        boundsArea: b.width * b.height,
        // 真实渲染序取链（spec stage6 §2.2 + stage1e 实测修正）：0.5.0-beta 无
        // getDrawableRenderOrder(i)；真实 API = getDrawableRenderOrders()（复数无参，整条
        // Int32Array，实测取值 0..N-1 全不同）；原始数组在 _model.drawables.renderOrders
        renderOrder:
          core?.getDrawableRenderOrder?.(zone.drawIndex) ??
          core?.getDrawableRenderOrders?.()?.[zone.drawIndex] ??
          core?._model?.drawables?.renderOrders?.[zone.drawIndex] ??
          core?.drawables?.renderOrders?.[zone.drawIndex] ??
          0,
      });
    }
    hits.sort((a, b) => b.renderOrder - a.renderOrder || a.boundsArea - b.boundsArea);
    if (hits.length > 1) {
      // 重叠区择序证据（spec stage6 §5 C9）：打印前几个候选的实际 renderOrder 值
      console.info(
        `[Touch] 命中重叠 ${hits.length} 区：` +
          hits
            .slice(0, 3)
            .map((h) => `${h.name}=${h.renderOrder}`)
            .join(' / '),
      );
    }
    if (!hits.length) return null;
    // 同 id 组内择一（spec stage3 §3.1.3）：组 = 命中候选里与最上层同 rule.id 的区
    const topId = hits[0].rule.id;
    const group = hits.filter((z) => z.rule.id === topId);
    return (
      group.find((z) => (z.rule.offsetX ?? 0) !== 0 || (z.rule.offsetY ?? 0) !== 0) ??
      group.find((z) => actionNamesOf(z.rule).length > 0) ??
      group[0]
    );
  }

  private emitInteraction(
    kind: 'tap' | 'drag' | 'longpress',
    clientX: number,
    clientY: number,
    pressedZone?: TouchZone | null,
  ): void {
    const rect = (this.app.view as HTMLCanvasElement).getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const areas = this.model ? this.model.hitTest(x, y) : [];
    let region: 'head' | 'body' = 'body';
    let rule: TouchRule | null = null;
    if (this.model) {
      const b = this.model.getBounds();
      region = y < b.top + b.height * 0.3 ? 'head' : 'body';
      // 规则热区命中（l2d.su 判据见 hitZoneAt）：完整 rule 交给 TouchChain 分发动作，
      // circle 型（点戳）同时驱动参数引擎
      // 抬起命中回退（research3 F1，2026-09-18）：circle 按下即写角度派生值，值驱动 drawable
      // 几何（值→几何自反馈），抬起时重命中常失配 → poke 丢失 → 值冻在中值、type12 门死锁。
      // 抬起命中失败时回退到按下区（站点 pressedRules 语义=手势作用于按下区）；drag 不回退。
      const hit = this.hitZoneAt(clientX, clientY) ?? (kind !== 'drag' ? (pressedZone ?? null) : null);
      if (hit) {
        rule = hit.rule;
        if (kind !== 'drag' && hit.rule.actionTrigger?.circle) {
          this.paramDriver?.poke(hit.rule.id ?? 0);
        }
      } else if (kind === 'tap' && this.hasTouchRules) {
        // 点击未命中可交互热区（被 G 门槛锁死的区在 hitZoneAt 收集阶段已剔除，也落到这里）。
        // hasTouchRules 为真时 main.ts 不播兜底（游戏同款），点击会「没反应」——
        // 叠加层轻提示解释原因；拖拽/长按未命中保持静默（提示会刷屏）
        this.touchDebugOverlay?.notifyNoHit(x, y);
      }
    }
    this.onInteraction?.({ kind, areas, region, rule });
  }

  /** 是否加载了 touch.json 规则（空间热区或 mode2 反应规则存在时：区域外点击不触发兜底动作） */
  get hasTouchRules(): boolean {
    return !!this.touchAreas?.length || this.hasParamRules;
  }

  /** 触摸热区可视化开关：懒创建叠加层后开/关 */
  setTouchDebug(enabled: boolean): void {
    this.touchDebugOverlay ??= new TouchDebugOverlay(
      this.app.ticker,
      () => this.app.stage,
      () => this.model as unknown as TouchDebugModel | null,
      () => this.touchZoneStates(),
      () =>
        this.modelInfo?.tapMotions as Record<string, Record<string, number>> | undefined,
      () => this.chainIdleIndex(),
    );
    this.touchDebugOverlay.setEnabled(enabled);
  }

  /** 仿 l2d.su 左侧调试栏（显示/动作/参数/部件）。仅 L2D。 */
  setDebugPanel(enabled: boolean): void {
    if (!enabled) {
      this.debugPanel?.destroy();
      this.debugPanel = null;
      return;
    }
    if (!this.debugPanel) this.debugPanel = new DebugPanel(this.container, () => this.model);
  }

  /** 叠加层每帧消费（spec stage3 v2 §3.3.1）：全部已注册区 + 实时剔除原因。
   *  ok=可用；H=不可见；T=透明度≤0.01；O=画布外/包围盒无效；G=交互门槛拦截 */
  touchZoneStates(): TouchZoneState[] {
    if (!this.touchAreas || !this.model) return [];
    const core = this.touchCore();
    const im = this.model.internalModel as unknown as { originalWidth?: number; originalHeight?: number };
    const canvasW = typeof im?.originalWidth === 'number' ? im.originalWidth : Number.NaN;
    const canvasH = typeof im?.originalHeight === 'number' ? im.originalHeight : Number.NaN;
    return this.touchAreas.map((zone) => {
      const i = zone.drawIndex;
      // 验收仪表盘读数（spec stage5 §2.6）：有参数区带实时值，无参数区带动作名
      const param = (zone.rule.parameter ?? '') as string;
      const hasParam = !!param && param !== 'empty';
      const paramValue = hasParam ? this.paramDriver?.getValue(param) : undefined;
      // core 写入值列（research2 §5-Q5）：ParamDriver 内部值 vs core 实际值层间分歧可视化
      const coreValue = hasParam ? core?.getParameterValueById?.(param) : undefined;
      const actionName =
        hasParam || paramValue !== undefined
          ? undefined
          : (actionNamesOf(zone.rule)[0] ??
            (zone.rule.actionTrigger?.action as string | undefined));
      const base = { ...zone, paramValue, coreValue, actionName };
      if (!(core?.getDrawableVisibility?.(i) ?? true)) return { ...base, status: 'H' as const };
      if (!this.isRuleInteractive(zone.rule)) {
        // G 前移（r2 C2）：透明+门槛锁死区原显示 T「可点」，系统性高估可点性
        // blocked:enable 标注（spec stage6 §2.1/§2.3）：动作全被 ATA 白名单拒（如吾妻
        // touch_drag12 vs enable[touch_idle*]）＝数据疑点，仅仪表盘标注，不改代码绕过
        const names = actionNamesOf(zone.rule);
        const blockedEnable =
          names.length > 0 && names.every((n) => !this.actionAllowedWithParamGate(n));
        return { ...base, status: 'G' as const, blockedEnable };
      }
      if ((core?.getDrawableOpacity?.(i) ?? 1) <= OPACITY_CUTOFF) return { ...base, status: 'T' as const };
      const b = this.drawableBounds(i);
      if (
        !b ||
        ![b.x, b.y, b.width, b.height].every(Number.isFinite) ||
        !(b.width > 0) ||
        !(b.height > 0) ||
        (Number.isFinite(canvasW) &&
          Number.isFinite(canvasH) &&
          !(b.x + b.width > 0 && b.x < canvasW && b.y + b.height > 0 && b.y < canvasH))
      ) {
        return { ...base, status: 'O' as const };
      }
      return { ...base, status: 'ok' as const };
    });
  }

  /**
   * live2dTouch 规则注册（l2d.su 站点同款）：
   * - 空间热区：有 drawAbleName 且绘画件存在的规则全部注册（画布外由几何命中自然排除）；
   * - 默认热区：TouchSpecial/TouchHead/TouchBody 绘画件存在且未被规则占用 → 伪规则映射动作组；
   * - 参数规则：circle 点戳 / drag 累积（type 1/6/7）/ mode2 位置反应 → ParamDriver。
   */
  private async loadTouchRules(modelInfo: ModelInfo): Promise<void> {
    this.touchAreas = null;
    this.touchRules = null;
    this.hasParamRules = false;
    this.paramDriver = null;
    try {
      const url = new URL(modelInfo.url, location.href);
      const touchUrl = new URL('touch.json', url).href;
      const resp = await fetch(touchUrl);
      if (!resp.ok) return;
      const data = (await resp.json()) as TouchData;
      const rules = data.rules ?? [];
      this.touchRules = rules; // 原始数组全量挂载（含未注册为区的规则），findChainRule 查找用
      const core = (
        this.model?.internalModel as unknown as {
          coreModel?: {
            getDrawableIndex(id: string): number;
          };
        }
      )?.coreModel;
      if (!core) return;
      const zones: TouchZone[] = [];
      const paramRules: ParamRule[] = [];
      const occupied = new Set(
        rules.map((r) => r.drawAbleName).filter((n): n is string => !!n),
      );
      // 诊断计数（spec stage3 v2 §2.1）：逐规则剔除原因，注册后输出一行汇总
      const im = this.model?.internalModel as unknown as { originalWidth?: number; originalHeight?: number };
      const canvasW = typeof im?.originalWidth === 'number' ? im.originalWidth : Number.NaN;
      const canvasH = typeof im?.originalHeight === 'number' ? im.originalHeight : Number.NaN;
      let noDrawableName = 0;
      let missingDrawable = 0;
      let noActionNoParam = 0;
      let outOfCanvas = 0;
      for (const rule of rules) {
        const name = rule.drawAbleName ?? '';
        if (!name) {
          noDrawableName++;
          continue;
        }
        const drawIndex = core.getDrawableIndex(name);
        if (drawIndex < 0) {
          missingDrawable++;
          continue;
        }
        // 空参数规则照常注册（引擎按 drawable 注册、不看 parameter，spec stage5 §2.4）；
        // 无 parameter 时不进 ParamDriver，仅走 TouchChain 动作路径
        const param = (rule.parameter ?? '') as string;
        zones.push({ drawIndex, group: param || name, name, rule });
        if ((!param || param === 'empty') && !actionNamesOf(rule).length) {
          noActionNoParam++;
        }
        const b = this.drawableBounds(drawIndex);
        if (
          !b ||
          !Number.isFinite(canvasW) ||
          !Number.isFinite(canvasH) ||
          !(b.x + b.width > 0 && b.x < canvasW && b.y + b.height > 0 && b.y < canvasH)
        ) {
          outOfCanvas++;
        }
        const pr = this.toParamRule(rule);
        if (pr) paramRules.push(pr);
      }
      // 默认热区（l2d.su 站点无条件注册这 3 区）：映射同名动作组，走 TouchChain
      const missingDefaults: string[] = [];
      (['TouchSpecial', 'TouchHead', 'TouchBody'] as const).forEach((name, i) => {
        if (occupied.has(name)) return;
        const drawIndex = core.getDrawableIndex(name);
        if (drawIndex < 0) {
          missingDefaults.push(name);
          return;
        }
        const lower = name.toLowerCase();
        zones.push({
          drawIndex,
          group: lower,
          name,
          rule: {
            id: -(i + 1),
            drawAbleName: name,
            parameter: lower,
            actionTrigger: { type: 2, action: lower },
          } as TouchRule,
        });
      });
      if (!zones.length && !paramRules.length) return;
      this.touchAreas = zones;
      this.hasParamRules = paramRules.length > 0;
      this.paramDriver = new ParamDriver(PARAM_STORAGE_PREFIX);
      this.paramDriver.setRules(paramRules, data.parameterRange ?? {}, modelInfo.name);
      this.attachParamDriver();
      // 诊断汇总（spec stage3 v2 §2.1/§3.3.2）：常驻一行，不刷屏
      console.info(
        `[Touch] ${modelInfo.name} 注册 ${zones.length}/${rules.length}：` +
          `无绘画件名${noDrawableName}、drawable缺失${missingDrawable}、` +
          `画布外${outOfCanvas}、无动作且无参数${noActionNoParam}（其余成功，参数规则 ${paramRules.length} 条）`,
      );
      // 默认区缺失说明（spec stage3 v2 §3.3.3）：部分模型没有默认区 = 站点同款，不是缺陷
      if (missingDefaults.length) {
        console.info(
          `[Touch] ${modelInfo.name} 默认区缺失：${missingDefaults.join('/')}（站点同款，该模型无此绘画件）`,
        );
      }
    } catch (e) {
      console.info('[Touch] 无 touch.json，使用启发式区域:', e);
    }
  }

  /** touch.json 规则 → 参数规则：circle 点戳 / mode1+type1/6/7 拖动 / mode2 位置反应 */
  private toParamRule(rule: TouchRule): ParamRule | null {
    const param = rule.parameter;
    if (!param) return null;
    const at = rule.actionTrigger;
    const mode = typeof rule.mode === 'number' ? rule.mode : 1;
    const num = (v: unknown): number | undefined => (typeof v === 'number' ? v : undefined);
    const pr: ParamRule = {
      id: num(rule.id) ?? 0,
      parameter: param,
      mode,
      startValue: num(rule.startValue) ?? 0,
      range: (rule.range as [number, number] | undefined) ?? [0, 1],
      rangeAbs: num(rule.rangeAbs),
      dragDirect: num(rule.dragDirect),
      smooth: num(rule.smooth),
      revertSmooth: num(rule.revertSmooth),
      revert: num(rule.revert),
      saveParameter: num(rule.saveParameter),
      reactPosX: num(rule.reactPosX),
      reactPosY: num(rule.reactPosY),
    };
    const relations = toRelationPresets(rule);
    if (relations) pr.relations = relations;
    if (rule.revertIdleIndex === 1 || rule.revertIdleIndex === '1') pr.revertOnIdle = true;
    if (rule.revertActionIndex === 1) pr.revertOnStep = true;
    if (at?.circle) pr.circleTarget = num(at.target) ?? 1;
    if (pr.circleTarget !== undefined) return pr; // 点戳/画圈手势（type 2 + circle）
    if (mode === 1 && (at?.type === 1 || at?.type === 6 || at?.type === 7)) return pr; // 拖动型
    if (mode === 2 && (pr.reactPosX !== undefined || pr.reactPosY !== undefined)) return pr;
    // slide 型（spec stage3 v2 §3.1.1 + r3 §3.1/§5.1）：无 action（有无 actionTrigger 均可）且
    // offset≠0，offsetX/Y 是拖拽轴灵敏度；typed-无action（如 feiteliedadi TouchDrag2/7）站点走线性拖动
    if (!at?.action && ((num(rule.offsetX) ?? 0) !== 0 || (num(rule.offsetY) ?? 0) !== 0)) {
      return { ...pr, slide: { ox: num(rule.offsetX) || 0, oy: num(rule.offsetY) || 0 } };
    }
    // 载体规则：自身无手势驱动面但携带关系预设（如 feiteliedadi_3 TouchDrag1/3/4/5 等
    // type2 无 circle/offset），必须登记进 ParamDriver 预设层才能每帧覆写
    return relations ? { ...pr, carrier: true } : null;
  }

  /** 绘画件当前包围盒（canvas 空间，顶点实时随姿势更新） */
  private drawableBounds(drawIndex: number): { x: number; y: number; width: number; height: number } | null {
    const im = this.model?.internalModel as unknown as {
      getDrawableBounds?(
        i: number,
        b?: { x: number; y: number; width: number; height: number },
      ): { x: number; y: number; width: number; height: number };
    };
    return im?.getDrawableBounds?.(drawIndex) ?? null;
  }

  async load(modelInfo: ModelInfo): Promise<void> {
    this.kScale = typeof modelInfo.kScale === 'number' ? modelInfo.kScale : 0.5;
    this.xShift = typeof modelInfo.initialXshift === 'number' ? modelInfo.initialXshift : 0;
    this.yShift = typeof modelInfo.initialYshift === 'number' ? modelInfo.initialYshift : 0;
    this.modelInfo = modelInfo;

    this.detachLipSync();
    this.detachParamDriver();
    this.model?.destroy();
    this.model = null;
    this.touchAreas = null;
    this.touchRules = null;
    this.hasParamRules = false;
    this.paramDriver = null;
    this.downHitZone = null;
    this.prevDragPx = null;
    this.pointerNorm = { x: 0, y: 0 };
    this.touchPlay = { active: false, ruleId: null };

    // autoFocus：目光跟随鼠标；点击/手势由 canvas 层状态机处理（不依赖库的
    // 'hit' 事件——它只在命中热区时才发，会把无 HitAreas 模型的兜底挡死）
    const model = await Live2DModel.from(modelInfo.url, {
      autoHitTest: false,
      autoFocus: true,
      // 关闭库的 Idle 组自动随机播放（部分模型 Idle 组多达 15 条，静置自动跳——研究报告 §5.5）。
      // 只能是非空字面量：库仅在 truthy 时覆盖 groups.idle（cubism4.es.js:8540）；不存在的组名
      // 使 startRandomMotion 安全返回 false（:8683）。idle 播放统一走本地 playIdleOnce()。
      idleMotionGroup: '__no_auto_idle__',
    });
    this.model = model;
    model.anchor.set(0.5);
    this.app.stage.addChild(model);
    this.touchDebugOverlay?.onModelChanged();
    this.debugPanel?.onModelChanged();
    this.layout();
    this.attachLipSync(model);
    this.buildMotionIndex();
    this.playIdleOnce(); // 加载完成播一次 idle（stage1b §0.4；循环由 Meta.Loop 数据驱动）
    void this.loadTouchRules(modelInfo); // 游戏同款触摸规则（可 404）
  }

  /** 从 settings 的 FileReferences.Motions 展开动作名索引（spec stage3 §3.3.1） */
  private buildMotionIndex(): void {
    this.motionEntries = [];
    const settings = this.model?.internalModel.settings as unknown as {
      motions?: Record<string, { File?: string; file?: string; Name?: string; name?: string }[]>;
      motionGroups?: Record<string, { File?: string; file?: string; Name?: string; name?: string }[]>;
    };
    const groups = settings?.motions ?? settings?.motionGroups;
    if (!groups) return;
    for (const [group, defs] of Object.entries(groups)) {
      (defs ?? []).forEach((def, index) => {
        const file = def?.File ?? def?.file;
        const fileStem =
          typeof file === 'string' && file
            ? file.replace(/^.*[\\/]/, '').replace(/\.motion\d*\.json$/i, '')
            : undefined;
        const name = def?.Name ?? def?.name;
        this.motionEntries.push({
          group,
          index,
          name: typeof name === 'string' && name ? name : undefined,
          fileStem,
        });
      });
    }
  }

  /** 动作匹配（spec stage3 §3.3.2）：group/name/fileStem 原值或归一化值与 action 相等即命中（去重） */
  private matchEntries(action: string): MotionEntry[] {
    const g = normalizeMotionName(action);
    const seen = new Set<string>();
    const out: MotionEntry[] = [];
    for (const e of this.motionEntries) {
      const keys = [e.group, e.name, e.fileStem].filter((k): k is string => !!k);
      if (!keys.some((k) => k === action || normalizeMotionName(k) === g)) continue;
      const key = `${e.group}#${e.index}`;
      if (!seen.has(key)) {
        seen.add(key);
        out.push(e);
      }
    }
    return out;
  }

  /**
   * 按动作名播放（spec stage3 §3.3.3）：命中条目顺序连播（FORCE 优先级，上一条
   * motionFinish 后播下一条）；无命中返回 false。带 ruleId 时设置触摸播放门控状态
   * （§3.4.1），结束后清状态并回放一次 idle。
   */
  async playAction(action: string, ruleId?: number): Promise<boolean> {
    const entries = this.matchEntries(action);
    if (!entries.length || !this.model) return false;
    if (ruleId !== undefined) this.touchPlay = { active: true, ruleId };
    try {
      for (let i = 0; i < entries.length; i++) {
        if (!this.model) break;
        const started = await this.model.motion(entries[i].group, entries[i].index, 3);
        if (!started) break;
        if (i < entries.length - 1) await this.waitMotionFinish();
      }
    } finally {
      this.touchPlay = { active: false, ruleId: null };
      this.playIdleOnce(); // 官方触摸动作结束后回放一次 idle（循环由 Meta.Loop 数据驱动）
    }
    return true;
  }

  /** 等待当前动作 motionFinish（API 不可得时立即放行 = 只保证连播首条起播） */
  private waitMotionFinish(): Promise<void> {
    const mm = (
      this.model?.internalModel as unknown as {
        motionManager?: {
          once?(event: string, fn: () => void): unknown;
          off?(event: string, fn: () => void): unknown;
        };
      }
    )?.motionManager;
    return new Promise((resolve) => {
      if (!mm || typeof mm.once !== 'function') {
        resolve();
        return;
      }
      const done = (): void => {
        clearTimeout(timer);
        mm.off?.('motionFinish', handler);
        resolve();
      };
      const handler = (): void => done();
      const timer = setTimeout(done, MOTION_FINISH_TIMEOUT_MS);
      mm.once('motionFinish', handler);
    });
  }

  /** idle 回放组名：idleIndex > 0 ? 'idle'+idleIndex : 'idle'（stage1b §0.4） */
  private idleGroupName(): string {
    const idx = this.chainIdleIndex();
    return idx > 0 ? 'idle' + idx : 'idle';
  }

  /**
   * 从 idle 组随机播一条；循环由 enableIdleLoop 显式 setIsLoop(true) 落实（A′，research2
   * v2 §0：本地库不消费 Meta.Loop，站点行为=仅 idle 循环）。库自动随机播放仍由
   * '__no_auto_idle__' 哨兵禁用（test_l2d_idle_autoplay）。组不存在静默跳过。
   */
  private playIdleOnce(): void {
    const gname = this.idleGroupName();
    const list = this.motionEntries.filter((e) => e.group === gname);
    if (!list.length || !this.model) return;
    const pick = list[Math.floor(Math.random() * list.length)];
    void this.model.motion(pick.group, pick.index, 2).then((started) => {
      if (started) this.enableIdleLoop(pick.group, pick.index);
    });
  }

  /** idle 循环（A′，2026-09-18 replan）：本地库解析 Meta.Loop 但不接线（cubism4.es.js
   *  :3283→3822 存 _motionData.loop 无消费者，播放判定只读 _isLoop 默认 false），「尊重
   *  数据标志」须显式 setIsLoop 落实；仅 idle 路径调用——全库动作数据 Loop=true 而站点
   *  动作单次（v2 §0-2），循环不得外溢到触摸/主线动作。 */
  private enableIdleLoop(group: string, index: number): void {
    const motion = (
      this.model?.internalModel as unknown as {
        motionManager?: { motionGroups?: Record<string, (unknown | null)[]> };
      }
    )?.motionManager?.motionGroups?.[group]?.[index] as
      | { setIsLoop?: (loop: boolean) => void }
      | null
      | undefined;
    motion?.setIsLoop?.(true);
  }

  /** 播放门控状态查询（main.ts 互动分发用，spec stage3 §3.4.1） */
  get isPlayingTouchAction(): boolean {
    return this.touchPlay.active;
  }

  get playingTouchRuleId(): number | null {
    return this.touchPlay.ruleId;
  }

  /** 全部可匹配 action 名集（组名∪条目名∪文件名去重），供 TouchChain.resolve 的 available */
  getPlayableActionNames(): string[] {
    const set = new Set<string>();
    for (const e of this.motionEntries) {
      if (e.group) set.add(e.group);
      if (e.name) set.add(e.name);
      if (e.fileStem) set.add(e.fileStem);
    }
    return [...set];
  }

  /** 链步进找规则（r2 C3-①：action 含组名优先）：action 匹配=真链成员（如 TouchIdle20
   *  播 touch_idle1）；驼峰化 drawAbleName 降为兜底——原数组序使 TouchIdle1 抢先匹配
   *  touch_idle1，tap1 即 idleIndex 0→11 直跳（research r2 §2.2） */
  findChainRule(groupName: string): TouchRule | null {
    const cap = groupName.replace(/^touch_/, 'Touch');
    return (
      this.touchRules?.find((r) => actionNamesOf(r).includes(groupName)) ??
      this.touchRules?.find(
        (r) => r.parameter === groupName || (r.drawAbleName ?? '').toLowerCase() === cap.toLowerCase(),
      ) ??
      null
    );
  }

  /** 当前模型的动作组名列表（供 tapMotions 缺失时挑选兜底动作） */
  getMotionGroups(): string[] {
    const motions = (
      this.model?.internalModel.settings as unknown as {
        motions?: Record<string, unknown[]>;
        motionGroups?: Record<string, unknown[]>;
      }
    );
    const groups = motions?.motions ?? motions?.motionGroups;
    return groups ? Object.keys(groups) : [];
  }

  /**
   * 口型同步：在每帧 model.update 前把音量写入模型的 LipSync 参数组。
   * 0.5.0-beta 不暴露 lipSyncIds，参数从 settings.groups 的 LipSync 组取
   * （mao_pro 为 ParamA，Cubism 2 系 shizuku 为 PARAM_MOUTH_OPEN_Y）。
   */
  private attachLipSync(model: Live2DModel): void {
    const im = model.internalModel as unknown as {
      settings?: { groups?: { Name: string; Ids: string[] }[] };
      lipSyncIds?: string[];
      on?: (event: string, fn: () => void) => void;
      off?: (event: string, fn: () => void) => void;
      coreModel?: { setParameterValueById(id: string, v: number): void };
    };
    const groups = im.settings?.groups;
    const ids =
      groups?.find((g) => g.Name === 'LipSync')?.Ids ?? im.lipSyncIds ?? [];
    if (!ids.length || !im.on) return;
    this.lipSyncHandler = () => {
      const v = this.getVolume();
      for (const id of ids) {
        im.coreModel?.setParameterValueById(id, v);
      }
    };
    im.on('beforeModelUpdate', this.lipSyncHandler);
  }

  private detachLipSync(): void {
    if (!this.lipSyncHandler) return;
    (
      this.model?.internalModel as unknown as {
        off?: (event: string, fn: () => void) => void;
      }
    )?.off?.('beforeModelUpdate', this.lipSyncHandler);
    this.lipSyncHandler = null;
  }

  /** 参数引擎帧驱动：挂在动作曲线写完后、saveParameters 快照前的 afterMotionUpdate
   *  （库 update 次序 motionManager.update → emit('afterMotionUpdate') → saveParameters →
   *  眨眼/物理/姿势 → emit('beforeModelUpdate') → model.update → loadParameters 还原；
   *  挂 beforeModelUpdate 的写入会被帧末快照覆盖，参数恒 0——研究报告 §5.0） */
  private attachParamDriver(): void {
    if (!this.paramDriver) return;
    const im = this.model?.internalModel as unknown as {
      on?: (event: string, fn: () => void) => void;
      off?: (event: string, fn: () => void) => void;
      coreModel?: ParamCore;
    };
    if (!im?.on) return;
    this.detachParamDriver();
    this.lastParamAt = performance.now();
    this.paramHandler = () => {
      if (!this.paramDriver) return;
      const now = performance.now();
      const dt = Math.min(now - this.lastParamAt, 100);
      this.lastParamAt = now;
      const core = (this.model?.internalModel as unknown as { coreModel?: ParamCore })?.coreModel;
      if (core) {
        this.paramDriver.syncChainState(this.chainIdleIndex(), this.chainStepIndex);
        this.paramDriver.update(dt, core, this.pointerNorm);
      }
    };
    im.on(PARAM_DRIVE_EVENT, this.paramHandler);
  }

  private detachParamDriver(): void {
    if (!this.paramHandler) return;
    (
      this.model?.internalModel as unknown as {
        off?: (event: string, fn: () => void) => void;
      }
    )?.off?.(PARAM_DRIVE_EVENT, this.paramHandler);
    this.paramHandler = null;
  }

  /** 依据 kScale / 视口大小重新计算缩放与位置 */
  private layout(): void {
    const model = this.model;
    if (!model) return;

    const screenH = this.app.screen.height;
    const screenW = this.app.screen.width;
    const ppu = this.pixelsPerUnit(model);
    // displayHeight = kScale × 逻辑高 × 屏高（原前端语义），scale = displayHeight / 原生像素高
    const scale = (this.kScale * screenH) / ppu;
    model.scale.set(scale);

    // 2 个逻辑单位 = 一屏高；xShift/yShift 以逻辑单位计（当前 model_dict 全为 0）
    const unitPx = screenH / 2;
    model.position.set(screenW / 2 + this.xShift * unitPx, screenH / 2 + this.yShift * unitPx);
  }

  private pixelsPerUnit(model: Live2DModel): number {
    const im = model.internalModel as unknown as { pixelsPerUnit?: number };
    if (typeof im.pixelsPerUnit === 'number' && im.pixelsPerUnit > 0) {
      return im.pixelsPerUnit;
    }
    // 兜底：直接读 moc3 canvasinfo（setupLayout 之前也可能需要）
    const info = (im as unknown as { coreModel?: { model?: { canvasinfo?: { PixelsPerUnit?: number } } } })
      .coreModel?.model?.canvasinfo;
    return info?.PixelsPerUnit ?? 1;
  }

  setExpression(value: number | string): void {
    try {
      this.model?.expression(value);
    } catch (e) {
      console.warn('setExpression failed:', value, e);
    }
  }

  setAnimation(group: string, priority: number = 2): void {
    const model = this.model;
    if (!model) return;
    const motions = (
      model.internalModel.settings as unknown as {
        motions?: Record<string, unknown[]>;
        motionGroups?: Record<string, unknown[]>;
      }
    );
    const groups = motions?.motions ?? motions?.motionGroups;
    if (groups && groups[group]?.length) {
      // priority: 2=NORMAL(说话), 3=FORCE(点击动作盖过待机)
      void model.motion(group, undefined, priority);
    }
  }

  /** 一键复位：停止当前动作、清除表情和触摸链，再播放初始待机动作。 */
  resetToInitialMotion(): void {
    const mm = (
      this.model?.internalModel as unknown as {
        motionManager?: { stopAllMotions?: () => void } | null;
      }
    )?.motionManager;
    mm?.stopAllMotions?.();
    this.touchPlay = { active: false, ruleId: null };
    this.resetExpression();
    try {
      // 链状态归零由 main.ts 注入，失败也不得阻断下面的初始 idle 回放
      this.resetTouchChain?.();
    } catch (e) {
      console.error('resetTouchChain failed:', e);
    }
    // 参数引擎复位（r3 §6.3 R-1/R-2/R-5）：清拖拽参数值与持久化残留，防刷新回填
    this.paramDriver?.resetAll();
    this.playIdleOnce();
  }

  resetExpression(): void {
    const em = (
      this.model?.internalModel as unknown as {
        motionManager?: { expressionManager?: { resetExpression(): void } | null };
      }
    )?.motionManager?.expressionManager;
    em?.resetExpression();
  }

  dispose(): void {
    this.observer?.disconnect();
    this.observer = null;
    this.detachLipSync();
    this.detachParamDriver();
    this.debugPanel?.destroy();
    this.debugPanel = null;
    this.touchDebugOverlay?.destroy();
    this.touchDebugOverlay = null;
    this.model?.destroy();
    this.model = null;
    this.app.destroy(true, { children: true, texture: true, baseTexture: true });
    this.container.replaceChildren();
  }
}
