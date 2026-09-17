import { Point } from 'pixi.js';
import type { Matrix } from 'pixi.js';

/** 模型侧最小接口（自 l2d_touch_debug.ts 迁入，字段原样不改） */
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

/** 反向链（T1 已确认）：toModelPosition = worldTransform.applyInverse → localTransform.applyInverse，
 *  故反向为 localTransform.apply → worldTransform.apply */
export function modelPointToScreen(m: TouchDebugModel, x: number, y: number): Point {
  const local = m.internalModel.localTransform;
  return m.worldTransform.apply(local ? local.apply(new Point(x, y)) : new Point(x, y));
}

export function modelRectToScreen(
  m: TouchDebugModel,
  b: { x: number; y: number; width: number; height: number },
): { x: number; y: number; w: number; h: number } | null {
  const corners = [
    modelPointToScreen(m, b.x, b.y),
    modelPointToScreen(m, b.x + b.width, b.y),
    modelPointToScreen(m, b.x, b.y + b.height),
    modelPointToScreen(m, b.x + b.width, b.y + b.height),
  ];
  const xs = corners.map((p) => p.x), ys = corners.map((p) => p.y);
  const x = Math.min(...xs), y = Math.min(...ys);
  const w = Math.max(...xs) - x, h = Math.max(...ys) - y;
  return w > 0 && h > 0 ? { x, y, w, h } : null;
}

/** 首个有效热区绘画件的模型空间中心（touch 规则区优先，其次 HitArea）；
 *  idxs = 调用方收集的 drawIndex 列表 */
export function firstModelPoint(m: TouchDebugModel, idxs: number[]): Point | null {
  for (const i of idxs) {
    const b = m.internalModel.getDrawableBounds?.(i);
    if (b) return new Point(b.x + b.width / 2, b.y + b.height / 2);
  }
  return null;
}

/** 运行时自检：模型点 → 屏幕点 → toModelPosition 回代，误差 >2px 返回 false（换算疑似错误）；
 *  center 为 null（无有效绘画件）返回 true（无法检查，不算失败） */
export function selfCheckConversion(m: TouchDebugModel, center: Point | null): boolean {
  if (!center) return true;
  const s = modelPointToScreen(m, center.x, center.y);
  const back = m.toModelPosition(new Point(s.x, s.y), new Point(), true);
  return Math.hypot(back.x - center.x, back.y - center.y) <= 2;
}

/** 收集 Name 非空且绘画件存在的 HitArea（与 main.ts「键名非空才算定向热区」一致） */
export function collectHitAreas(m: TouchDebugModel): { name: string; drawIndex: number }[] {
  const out: { name: string; drawIndex: number }[] = [];
  for (const h of m.internalModel.settings?.hitAreas ?? []) {
    const idx = m.internalModel.coreModel?.getDrawableIndex(h.Id ?? '') ?? -1;
    if (h.Name && idx >= 0) out.push({ name: h.Name, drawIndex: idx });
  }
  return out;
}

/** 区状态（l2d.ts 每帧提供，spec stage3 v2 §3.3.1）：
 *  ok=可用；H=不可见；T=透明度≤0.01（透明剔除，不可交互；r2 收回 D1/D3）；O=画布外/包围盒无效；G=交互门槛拦截。
 *  paramValue=参数实时值（验收仪表盘）；coreValue=core 实际写入值（research2 §5-Q5，
 *  层间分歧可视化）；actionName=无参数区的动作名（spec stage5 §2.6）；
 *  blockedEnable=G 且动作全被动作闸拒（spec stage6 §2.3 标注 blocked:enable） */
export interface TouchZoneState {
  drawIndex: number;
  group: string;
  name: string;
  status: 'ok' | 'H' | 'T' | 'O' | 'G';
  paramValue?: number;
  coreValue?: number;
  actionName?: string;
  blockedEnable?: boolean;
}

/** 标签两件套（r2 自 collectRegions 拆出）：mark=状态/剔除标记；readout=参数值或动作名读数 */
export function zoneLabelParts(a: TouchZoneState): { mark: string; readout: string } {
  const mark =
    a.status === 'ok'
      ? ''
      : a.status === 'T'
        ? ' [T:透明剔除]'
        : a.blockedEnable
          ? ' [blocked:enable]'
          : ` [${a.status}]`;
  // 双显（research2 §5-Q5）：|内部值-core值|>0.05 时 `内部→core`，层间分歧一眼可见
  //（ε 与 ParamDriver POKE_EPSILON 同源语义）；core 值缺失（旧 core 无 API）只显内部值
  const dual =
    a.paramValue !== undefined &&
    a.coreValue !== undefined &&
    Math.abs(a.paramValue - a.coreValue) > 0.05;
  const readout =
    a.paramValue !== undefined
      ? dual
        ? ` ${a.group}=${a.paramValue.toFixed(1)}→${a.coreValue!.toFixed(1)}`
        : ` ${a.group}=${a.paramValue.toFixed(1)}`
      : a.actionName
        ? ` action=${a.actionName}`
        : '';
  return { mark, readout };
}

/** 屏幕坐标下的一个待画区域；fill=false 只描边（被剔除区）；dim=非交互区（O/H/G）标签降透明度（research §7 候选 B）（自 l2d_touch_debug.ts 迁入，字段原样不改） */
export interface Region { x: number; y: number; w: number; h: number; color: number; label: string; fill: boolean; dim: boolean }

/** 标签/提示文本样式（自 l2d_touch_debug.ts 迁入，内容原样不改） */
export const TEXT_STYLE = {
  fontSize: 12, fill: '#ffffff', stroke: '#000000', strokeThickness: 3,
  fontFamily: "'Segoe UI', 'Microsoft YaHei', sans-serif",
};
