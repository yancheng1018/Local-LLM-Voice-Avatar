import { Container, Graphics, Text } from 'pixi.js';
import type { Ticker } from 'pixi.js';
import { firstModelPoint, modelRectToScreen, selfCheckConversion, collectHitAreas, zoneLabelParts } from './l2d_touch_debug_helpers';
import type { TouchDebugModel, TouchZoneState } from './l2d_touch_debug_helpers';
export type { TouchDebugModel };
export type { TouchZoneState };

/** 屏幕坐标下的一个待画区域；fill=false 只描边（被剔除区）；dim=非交互区（O/H/G）标签降透明度（research §7 候选 B） */
interface Region { x: number; y: number; w: number; h: number; color: number; label: string; fill: boolean; dim: boolean }

const TEXT_STYLE = {
  fontSize: 12, fill: '#ffffff', stroke: '#000000', strokeThickness: 3,
  fontFamily: "'Segoe UI', 'Microsoft YaHei', sans-serif",
};

const HINT_TEXT = '未命中可交互热区';
const HINT_MS = 1200;

/** 触摸热区可视化叠加层：全部已注册区每帧重画——可用区实色彩框 + 动作组标签，
 *  被剔除区描边 + 原因标记（O/T/G/H）；只做显示，不改 l2d.ts 判定逻辑；层 eventMode='none' 不拦截指针 */
export class TouchDebugOverlay {
  private enabled = false;
  private layer: Container | null = null;
  private rects: Graphics | null = null;
  private labels: Text[] = [];
  /** 左上角固定读数：链 idleIndex 实时刷新（spec stage6 §2.3） */
  private idleText: Text | null = null;
  private hintText: Text | null = null; // 无命中点击轻提示（research §7 候选 C）
  private hintUntil = 0;
  private hitAreas: { name: string; drawIndex: number }[] = [];
  private warned = false; // 坐标自检失败：只警告一次，后续帧跳过依赖换算的框

  constructor(
    private readonly ticker: Ticker,
    private readonly getStage: () => Container,
    private readonly getModel: () => TouchDebugModel | null,
    private readonly getZoneStates: () => TouchZoneState[] | null,
    private readonly getTapMotions: () => Record<string, Record<string, number>> | undefined,
    private readonly getChainIdleIndex: () => number,
  ) {}

  setEnabled(enabled: boolean): void {
    if (enabled === this.enabled) return;
    this.enabled = enabled;
    if (enabled) {
      this.ensureLayer();
      this.loadHitAreas();
      this.ticker.add(this.tick);
    } else this.removeLayer();
  }

  /** 换模型后：层重新置顶（盖住新模型）+ 重建 HitArea 映射 */
  onModelChanged(): void {
    if (this.layer) this.getStage().addChild(this.layer);
    this.loadHitAreas();
  }

  /** 点击未命中任何可交互热区的轻提示（research §7 候选 C）：叠加层开着才显示，HINT_MS 淡出；
   *  只做显示，判定逻辑在 l2d.ts。坐标 = 画布内 CSS 像素（与 zone 投影同空间） */
  notifyNoHit(canvasX: number, canvasY: number): void {
    if (!this.enabled || !this.layer) return;
    this.hintText ??= new Text(HINT_TEXT, { ...TEXT_STYLE, fontSize: 13 });
    if (!this.hintText.parent) this.layer.addChild(this.hintText);
    this.hintText.position.set(canvasX + 10, canvasY - 14);
    this.hintUntil = performance.now() + HINT_MS;
  }

  destroy(): void {
    this.removeLayer();
  }
  private removeLayer(): void {
    this.ticker.remove(this.tick);
    this.layer?.destroy({ children: true });
    this.layer = this.rects = this.idleText = this.hintText = null;
    this.labels = [];
  }

  private ensureLayer(): void {
    this.layer = new Container();
    this.layer.eventMode = 'none'; // 必须 'none'：否则挡住 canvas 手势与目光跟随
    this.layer.addChild((this.rects = new Graphics()));
    // 固定读数行（左上角）：链 idleIndex 随步进实时刷新（spec stage6 §2.3）
    this.idleText = new Text('', { ...TEXT_STYLE, fontSize: 13 });
    this.idleText.position.set(6, 6);
    this.layer.addChild(this.idleText);
    this.getStage().addChild(this.layer);
  }

  /** 只收集 Name 非空且绘画件存在的 HitArea（与 main.ts「键名非空才算定向热区」一致） */
  private loadHitAreas(): void {
    const m = this.getModel();
    this.hitAreas = m ? collectHitAreas(m) : [];
  }

  private tick = (): void => {
    if (!this.enabled) return;
    const m = this.getModel();
    if (!m) return;
    if (!this.warned) {
      const idxs = [
        ...(this.getZoneStates() ?? []).map((a) => a.drawIndex),
        ...this.hitAreas.map((h) => h.drawIndex),
      ];
      if (!selfCheckConversion(m, firstModelPoint(m, idxs))) {
        this.warned = true;
        console.warn('[TouchDebug] 坐标换算疑似错误，仅显示头/身启发式框');
      }
    }
    if (this.idleText) {
      // 链入口出视口提示（r2 C3-②）：TouchBody 是连点链唯一入口，动作冻结终帧可将其
      // 带出视口使链卡死；rect 无效时不告警（避免误报）
      const entry = (this.getZoneStates() ?? []).find((z) => z.name === 'TouchBody');
      const eb = entry
        ? modelRectToScreen(m, m.internalModel.getDrawableBounds?.(entry.drawIndex) ?? { x: 0, y: 0, width: 0, height: 0 })
        : null;
      const gone =
        !!eb && (eb.y + eb.h < 0 || eb.y > window.innerHeight || eb.x + eb.w < 0 || eb.x > window.innerWidth);
      this.idleText.text = `idleIndex=${this.getChainIdleIndex()}${gone ? ' ⚠链入口出视口' : ''}`;
    }
    this.updateHint();
    this.draw(this.collectRegions(m));
  };

  /** 每帧淡出：到期隐藏，剩余时间线性降透明度 */
  private updateHint(): void {
    if (!this.hintText) return;
    const remain = this.hintUntil - performance.now();
    this.hintText.visible = remain > 0;
    if (remain > 0) this.hintText.alpha = Math.min(1, remain / HINT_MS);
  }

  private collectRegions(m: TouchDebugModel): Region[] {
    const out: Region[] = [];
    const im = m.internalModel;
    // 每帧现读可见性 + 透明度（opacity<=0 视为不可用，区数随姿态 0~N 波动为正确行为）
    const visible = (i: number) =>
      (im.coreModel?.getDrawableVisibility?.(i) ?? true) &&
      (im.coreModel?.getDrawableOpacity?.(i) ?? 1) > 0;
    const push = (r: { x: number; y: number; w: number; h: number }, color: number, label: string, fill = true) =>
      out.push({ ...r, color, label, fill, dim: !fill });
    if (!this.warned) {
      // A. touch.json 规则热区（橙=规则 / 粉=拖动 / 紫=特殊）：全部已注册区都画——
      //    可用区实色填充；被剔除区只描边 + 原因标记（O=画布外 T=透明 G=门槛 H=不可见）
      for (const a of this.getZoneStates() ?? []) {
        const b = im.getDrawableBounds?.(a.drawIndex);
        if (!b) continue;
        const r = modelRectToScreen(m, b);
        if (!r) continue;
        const color = a.name.startsWith('TouchDrag') ? 0xf472b6 : a.name.startsWith('TouchSpecial') ? 0xa78bfa : 0xf59e0b;
        // T=透明剔除（r2 收回 D1/D3）：透明标记不进命中池，与 O/G 同为不可交互，只描边
        const interactive = a.status === 'ok';
        const { mark, readout } = zoneLabelParts(a);
        // 'empty' 是 parameter 哨兵值非组名（research §2）：不作标签前缀，免掩盖动作名
        const prefix = a.group === 'empty' ? a.name : `${a.group}（${a.name}）`;
        push(r, color, `${prefix}${mark}${readout}`, interactive);
      }
      // B. model3.json HitAreas（红）；标签附 tapMotions 里首个权重>0 的动作组
      const tm = this.getTapMotions();
      for (const h of this.hitAreas) {
        const b = visible(h.drawIndex) ? im.getDrawableBounds?.(h.drawIndex) : undefined;
        if (!b) continue;
        const r = modelRectToScreen(m, b);
        if (!r) continue;
        const weights = tm?.[h.name];
        const motionKey = weights ? Object.keys(weights).find((k) => weights[k] > 0) : undefined;
        push(r, 0xf87171, h.name + (motionKey ? ` → ${motionKey}` : '（tapMotions 未配置）'));
      }
    }
    // C. 头/身启发式（绿/蓝）：仅无 touch 规则时画（有规则时画会误导）；
    //    getBounds() 已是屏幕坐标，不依赖换算，自检失败也保留
    if (!this.getZoneStates()?.length) {
      const b = m.getBounds();
      push({ x: b.x, y: b.y, w: b.width, h: b.height * 0.3 }, 0x4ade80, '头 → touch_head/touch_special/touch_*');
      push({ x: b.x, y: b.y + b.height * 0.3, w: b.width, h: b.height * 0.7 }, 0x60a5fa, '身 → touch_idle 递进链 / touch_body');
    }
    return out;
  }

  private draw(regions: Region[]): void {
    if (!this.layer || !this.rects) return;
    this.rects.clear();
    this.syncLabels(regions.length);
    regions.forEach((r, i) => {
      this.rects!.lineStyle(2, r.color, r.fill ? 0.9 : 0.6);
      if (r.fill) this.rects!.beginFill(r.color, 0.18);
      this.rects!.drawRect(r.x, r.y, r.w, r.h);
      if (r.fill) this.rects!.endFill();
      this.labels[i].text = r.label;
      this.labels[i].position.set(r.x + 6, r.y + 12);
      this.labels[i].alpha = r.dim ? 0.45 : 1;
    });
  }

  /** Text 复用：不足则新建入层，多余则销毁 */
  private syncLabels(n: number): void {
    while (this.labels.length < n) {
      const t = new Text('', TEXT_STYLE);
      t.anchor.set(0, 0.5);
      this.labels.push(this.layer!.addChild(t));
    }
    while (this.labels.length > n) this.labels.pop()?.destroy();
  }
}
