/**
 * Live2D relationParameter 预设层（纯函数，无 pixi/localStorage 依赖）。
 * v2 §4.4 定案：type103 = relation_value[链步索引]（旧「数值线性映射」语义已废）；
 * type104 = 当前 idleIndex 匹配 rel.idle 时每帧写 rel.name = target ?? start ?? 0。
 * type101/102（拖动线性/y 轴）不做（spec-l2d-touch-engine.md §10）。
 */

/** relationParameter.list[] 中本层消费的条目（101/102 在 toRelationPresets 阶段被滤除） */
export interface RelationPreset {
  type: number;
  idle?: number;
  name: string;
  target?: number;
  start?: number;
  relation_value?: number[];
}

/** ParamDriver 的 ParamRule 结构兼容视图（结构化类型，避免循环 import） */
export interface RelationRuleView {
  id: number;
  startValue: number;
  revertOnIdle?: boolean;
  relations?: RelationPreset[];
}

export const RELATION_STEP_TYPE = 103;
export const RELATION_IDLE_TYPE = 104;

const clamp = (v: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, v));

/** 提取规则可消费的关系预设：非数组 / 无 name / type∉{103,104} 一律滤除；空结果返回 undefined。
 *  参数带索引签名以兼容 TouchRule 类的 [key:string]:unknown 规则透传结构 */
export function toRelationPresets(rule: {
  relationParameter?: unknown;
  [key: string]: unknown;
}): RelationPreset[] | undefined {
  const list = (rule.relationParameter as { list?: unknown } | undefined)?.list;
  if (!Array.isArray(list)) return undefined;
  const out: RelationPreset[] = [];
  for (const item of list) {
    const rel = item as Partial<RelationPreset>;
    if (typeof rel?.name !== 'string') continue;
    if (rel.type !== RELATION_STEP_TYPE && rel.type !== RELATION_IDLE_TYPE) continue;
    out.push({
      type: rel.type,
      idle: typeof rel.idle === 'number' ? rel.idle : undefined,
      name: rel.name,
      target: typeof rel.target === 'number' ? rel.target : undefined,
      start: typeof rel.start === 'number' ? rel.start : undefined,
      relation_value: Array.isArray(rel.relation_value) ? rel.relation_value : undefined,
    });
  }
  return out.length ? out : undefined;
}

/** 每帧关系覆写：type104 = idle 匹配 rel.idle 时写 target ?? start ?? 0；
 *  type103 = relation_value[链步索引]（stepOf 超表按 clamp 取末值） */
export function relationWrites(
  rules: readonly RelationRuleView[],
  idle: number,
  stepOf: (id: number) => number,
): { name: string; value: number }[] {
  const writes: { name: string; value: number }[] = [];
  for (const r of rules) {
    for (const rel of r.relations ?? []) {
      if (rel.type === RELATION_IDLE_TYPE) {
        if (rel.idle === idle) writes.push({ name: rel.name, value: rel.target ?? rel.start ?? 0 });
      } else if (rel.type === RELATION_STEP_TYPE && Array.isArray(rel.relation_value)) {
        const table = rel.relation_value;
        writes.push({ name: rel.name, value: table[clamp(stepOf(r.id), 0, table.length - 1)] ?? 0 });
      }
    }
  }
  return writes;
}

/** idle 变化帧需复位的规则（站点 resetLive2DRulesForIdle）；同帧无变化返回空。
 *  站点含数组形态「含新 idle」，全库 0 命中，不解析 */
export function revertingOnIdle<R extends RelationRuleView>(
  rules: readonly R[],
  prevIdle: number,
  newIdle: number,
): R[] {
  if (prevIdle === newIdle) return [];
  return rules.filter((r) => r.revertOnIdle === true);
}
