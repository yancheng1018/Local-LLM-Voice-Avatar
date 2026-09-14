import { Container, Graphics, Point, Text } from 'pixi.js';
import type { Matrix, Ticker } from 'pixi.js';

/** 模型侧最小接口（L2DRenderer 用 as unknown as 转入，与 l2d.ts 现有风格一致） */
export interface TouchDebugModel {
  worldTransform: Matrix;
  getBounds(): { x: number; y: number; width: number; height: number };
  toModelPosition(position: Point, result?: Point, skipUpdate?: boolean): Point;
  internalModel: {
    settings?: { hitAreas?: { Id?: string; Name?: string }[] };
    originalWidth?: number;
    originalHeight?: number;
    coreModel?: {
      getDrawableIndex(id: string): number;
      getDrawableVisibility?(i: number): boolean;
      getDrawableOpacity?(i: number): number;
    };
    getDrawableBounds?(i: number, b?: { x: number; y: number; width: number; height: number }): { x: number; y: number; width: number; height: number };
    localTransform?: Matrix; // 运行时已确认存在（查阅任务 T1）
  };
}

/** 区状态（l2d.ts 每帧提供，spec stage3 v2 §3.3.1）：
 *  ok=可用；H=不可见；T=透明度≤0.01（提示，仍可交互）；O=画布外/包围盒无效；G=交互门槛拦截。
 *  paramValue=参数实时值（验收仪表盘）；actionName=无参数区的动作名（spec stage5 §2.6）；
 *  blockedEnable=G 且动作全被 ATA 白名单拒（spec stage6 §2.3 标注 blocked:enable） */
export interface TouchZoneState {
  drawIndex: number;
  group: string;
  name: string;
  status: 'ok' | 'H' | 'T' | 'O' | 'G';
  paramValue?: number;
  actionName?: string;
  blockedEnable?: boolean;
}

/** 屏幕坐标下的一个待画区域 { x, y, w, h, color, label, fill }；fill=false 只描边（被剔除区） */
interface Region { x: number; y: number; w: number; h: number; color: number; label: string; fill: boolean }

const TEXT_STYLE = {
  fontSize: 12, fill: '#ffffff', stroke: '#000000', strokeThickness: 3,
  fontFamily: "'Segoe UI', 'Microsoft YaHei', sans-serif",
};

/** 触摸热区可视化叠加层：全部已注册区每帧重画——可用区实色彩框 + 动作组标签，
 *  被剔除区描边 + 原因标记（O/T/G/H）；只做显示，不改 l2d.ts 判定逻辑；层 eventMode='none' 不拦截指针 */
export class TouchDebugOverlay {
  private enabled = false;
  private layer: Container | null = null;
  private rects: Graphics | null = null;
  private labels: Text[] = [];
  /** 左上角固定读数：链 idleIndex 实时刷新（spec stage6 §2.3） */
  private idleText: Text | null = null;
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

  destroy(): void {
    this.removeLayer();
  }
  private removeLayer(): void {
    this.ticker.remove(this.tick);
    this.layer?.destroy({ children: true });
    this.layer = this.rects = this.idleText = null;
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
    this.hitAreas = [];
    const m = this.getModel();
    if (!m) return;
    for (const h of m.internalModel.settings?.hitAreas ?? []) {
      const idx = m.internalModel.coreModel?.getDrawableIndex(h.Id ?? '') ?? -1;
      if (h.Name && idx >= 0) this.hitAreas.push({ name: h.Name, drawIndex: idx });
    }
  }

  private tick = (): void => {
    if (!this.enabled) return;
    const m = this.getModel();
    if (!m) return;
    if (!this.warned) this.selfCheck(m);
    if (this.idleText) this.idleText.text = `idleIndex=${this.getChainIdleIndex()}`;
    this.draw(this.collectRegions(m));
  };
  /** 运行时自检：模型点 → 屏幕点 → toModelPosition 回代，误差 >2px 视为换算错误 */
  private selfCheck(m: TouchDebugModel): void {
    const c = this.firstModelPoint(m);
    if (!c) return;
    const s = this.modelPointToScreen(m, c.x, c.y);
    const back = m.toModelPosition(new Point(s.x, s.y), new Point(), true);
    if (Math.hypot(back.x - c.x, back.y - c.y) > 2) {
      this.warned = true;
      console.warn('[TouchDebug] 坐标换算疑似错误，仅显示头/身启发式框');
    }
  }

  /** 首个有效热区绘画件的模型空间中心（touch 规则区优先，其次 HitArea） */
  private firstModelPoint(m: TouchDebugModel): Point | null {
    const idxs = [
      ...(this.getZoneStates() ?? []).map((a) => a.drawIndex),
      ...this.hitAreas.map((h) => h.drawIndex),
    ];
    for (const i of idxs) {
      const b = m.internalModel.getDrawableBounds?.(i);
      if (b) return new Point(b.x + b.width / 2, b.y + b.height / 2);
    }
    return null;
  }
  /** 反向链（T1 已确认）：toModelPosition = worldTransform.applyInverse → localTransform.applyInverse，
   *  故反向为 localTransform.apply → worldTransform.apply */
  private modelPointToScreen(m: TouchDebugModel, x: number, y: number): Point {
    const local = m.internalModel.localTransform;
    return m.worldTransform.apply(local ? local.apply(new Point(x, y)) : new Point(x, y));
  }
  private modelRectToScreen(m: TouchDebugModel, b: { x: number; y: number; width: number; height: number }) {
    const corners = [
      this.modelPointToScreen(m, b.x, b.y),
      this.modelPointToScreen(m, b.x + b.width, b.y),
      this.modelPointToScreen(m, b.x, b.y + b.height),
      this.modelPointToScreen(m, b.x + b.width, b.y + b.height),
    ];
    const xs = corners.map((p) => p.x), ys = corners.map((p) => p.y);
    const x = Math.min(...xs), y = Math.min(...ys);
    const w = Math.max(...xs) - x, h = Math.max(...ys) - y;
    return w > 0 && h > 0 ? { x, y, w, h } : null;
  }

  private collectRegions(m: TouchDebugModel): Region[] {
    const out: Region[] = [];
    const im = m.internalModel;
    // 每帧现读可见性 + 透明度（opacity<=0 视为不可用，区数随姿态 0~N 波动为正确行为）
    const visible = (i: number) =>
      (im.coreModel?.getDrawableVisibility?.(i) ?? true) &&
      (im.coreModel?.getDrawableOpacity?.(i) ?? 1) > 0;
    const push = (r: { x: number; y: number; w: number; h: number }, color: number, label: string, fill = true) =>
      out.push({ ...r, color, label, fill });
    if (!this.warned) {
      // A. touch.json 规则热区（橙=规则 / 粉=拖动 / 紫=特殊）：全部已注册区都画——
      //    可用区实色填充；被剔除区只描边 + 原因标记（O=画布外 T=透明 G=门槛 H=不可见）
      for (const a of this.getZoneStates() ?? []) {
        const b = im.getDrawableBounds?.(a.drawIndex);
        if (!b) continue;
        const r = this.modelRectToScreen(m, b);
        if (!r) continue;
        const color = a.name.startsWith('TouchDrag') ? 0xf472b6 : a.name.startsWith('TouchSpecial') ? 0xa78bfa : 0xf59e0b;
        // T=透明提示：仍填充=可交互（超越项 #3）；O/H/G 仍剔除，只描边
        const interactive = a.status === 'ok' || a.status === 'T';
        const mark =
          a.status === 'ok'
            ? ''
            : a.status === 'T'
              ? ' [T:透明但可点]'
              : a.blockedEnable
                ? ' [blocked:enable]'
                : ` [${a.status}]`;
        // 验收仪表盘（spec stage5 §2.6）：有参数区显示实时值，无参数区显示动作名
        const readout =
          a.paramValue !== undefined
            ? ` ${a.group}=${a.paramValue.toFixed(1)}`
            : a.actionName
              ? ` action=${a.actionName}`
              : '';
        push(r, color, `${a.group}（${a.name}）${mark}${readout}`, interactive);
      }
      // B. model3.json HitAreas（红）；标签附 tapMotions 里首个权重>0 的动作组
      const tm = this.getTapMotions();
      for (const h of this.hitAreas) {
        const b = visible(h.drawIndex) ? im.getDrawableBounds?.(h.drawIndex) : undefined;
        if (!b) continue;
        const r = this.modelRectToScreen(m, b);
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
