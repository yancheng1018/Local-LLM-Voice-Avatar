/**
 * l2d.su 触摸规则引擎（纯逻辑，无 pixi 依赖）。
 * 复现 spec-l2dsu-engine.md §3/§6 的 actionTrigger 类型分发 + ATA 白名单/链状态机
 * + limitTime 冷却 + localStorage 持久化。仅消费 touch.json 的 rule 字段；
 * mode2/reactPosX/参数钳制/listenerData/relationParameter 留待 stage2。
 */

export interface TouchActionTriggerActive {
  enable?: string[];
  idle?: number;
  ignore?: string[];
  idle_enable?: Array<[number, string[]]>;
  idle_ignore?: Array<[number, string[]]>;
  /** 链步覆盖 ATA（站点 active_list[si] ?? ata；全库 0 命中，语义就绪） */
  active_list?: TouchActionTriggerActive[];
}

export interface TouchActionStep {
  num?: number;
  time?: number;
  /** stage3 透传：action_list 步骤可携带动作名（l2d.ts actionNamesOf 消费） */
  action?: string | string[];
}

export interface TouchActionTrigger {
  type?: number;
  action?: string | string[];
  action_list?: TouchActionStep[];
  num?: number;
  time?: number;
  circle?: boolean;
  target?: number;
}

export interface TouchRule {
  id?: number;
  drawAbleName?: string;
  parameter?: string;
  mode?: number;
  limitTime?: number;
  actionTrigger?: TouchActionTrigger | null;
  actionTriggerActive?: TouchActionTriggerActive | null;
  /** 其余字段（dragDirect/range/reactPosX/listenerData…）stage2 再消费，此处仅透传 */
  [key: string]: unknown;
}

export interface TouchData {
  rules?: TouchRule[];
  parameterRange?: Record<string, [number, number]>;
  [key: string]: unknown;
}

export class TouchChain {
  private idleIndex = 0;
  private activeRuleId: number | null = null;
  private enable: Set<string> | null = null;
  private ignore: Set<string> | null = null;
  private cooldowns = new Map<number, number>();
  /** action_list 链步索引（站点 live2dOfficialActionListIndices，(si+1)%len 循环） */
  private actionListIndices = new Map<number, number>();

  constructor(private readonly storageKey: string) {
    this.restore();
  }

  /** 当前链 idleIndex（只读；stage3 规则区 ATA.idle 门槛与 idle 回放组名使用，纯增量不改既有逻辑） */
  get currentIndex(): number {
    return this.idleIndex;
  }

  /** 规则当前链步（无 action_list 恒 0；ParamDriver type103 查表用） */
  stepIndex(ruleId: number): number {
    return this.actionListIndices.get(ruleId) ?? 0;
  }

  /** 触发一条命中的规则，返回本次应播放的动作组名；null = 被冷却/白名单/手势门控拦截，不播 */
  resolve(rule: TouchRule, kind: 'tap' | 'drag' | 'longpress', available: string[]): string | null {
    const id = rule.id ?? 0;
    const now = Date.now();
    const until = this.cooldowns.get(id);
    if (until !== undefined && now < until) return null; // ③ 冷却中，拦截
    const list = rule.actionTrigger?.action_list;
    const steps = Array.isArray(list) ? list : [];
    const stepAction = steps.length ? steps[this.stepIndex(id)]?.action : undefined;
    const action = this.dispatch(rule.actionTrigger, kind, available, stepAction);
    if (action === null) return null;
    if (rule.actionTriggerActive) {
      // ① 触发成功后才建白名单/链状态（r4 §10.4.4 时序）：白名单判定用触发前的全局
      // 状态——先应用会把规则自身 action 拒在自身 ATA.enable 外（wuqi TouchIdle1 类
      // 核心区自锁死锁，U3′ 实测站点确实播放）；触发失败不推进链状态。
      // ATA 链步覆盖（v2 §3.1：active_list[si] ?? rule.actionTriggerActive）
      const ataList = rule.actionTriggerActive.active_list;
      const ata = (Array.isArray(ataList) ? ataList[this.stepIndex(id)] : undefined) ??
        rule.actionTriggerActive;
      this.applyActive(ata, id);
      this.save();
    }
    if (steps.length > 0) {
      // 链步循环推进（v2 §3.1 ⑩）：(si+1)%len 无终止；被拒（action===null）不推进
      this.actionListIndices.set(id, (this.stepIndex(id) + 1) % steps.length);
      this.save();
    }
    const limitTime = rule.limitTime ?? 0;
    if (limitTime > 0) {
      this.cooldowns.set(id, now + limitTime * 1000); // ③ 记冷却（秒→毫秒）
      this.save();
    }
    return action;
  }

  /** 白名单判定：ignore 命中即拒；有 enable 白名单时白名单外拒；两者皆空则放行 */
  isActionAllowed(name: string): boolean {
    if (this.ignore?.has(name)) return false;
    if (this.enable && !this.enable.has(name)) return false;
    return true;
  }

  reset(): void {
    this.idleIndex = 0;
    this.activeRuleId = null;
    this.enable = null;
    this.ignore = null;
    this.cooldowns.clear();
    this.actionListIndices.clear();
    this.save();
  }

  restore(): void {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return;
      const s = JSON.parse(raw) as {
        idleIndex?: number;
        activeRuleId?: number | null;
        cooldowns?: Record<string, number>;
        steps?: Record<string, number>;
      };
      this.idleIndex = s.idleIndex ?? 0;
      this.activeRuleId = s.activeRuleId ?? null;
      this.cooldowns = new Map(
        Object.entries(s.cooldowns ?? {}).map(([k, v]) => [Number(k), v]),
      );
      this.actionListIndices = new Map(
        Object.entries(s.steps ?? {}).map(([k, v]) => [Number(k), v]),
      );
    } catch {
      // 持久化数据损坏时静默忽略，从头开始
    }
  }

  save(): void {
    try {
      localStorage.setItem(
        this.storageKey,
        JSON.stringify({
          idleIndex: this.idleIndex,
          activeRuleId: this.activeRuleId,
          cooldowns: Object.fromEntries(this.cooldowns),
          steps: Object.fromEntries(this.actionListIndices),
        }),
      );
    } catch {
      // localStorage 不可用时静默跳过
    }
  }

  /** ATA 应用：形态A（按 idleIndex 查 idle_enable/idle_ignore 表）或 形态B（直接设 enable/idle/ignore） */
  private applyActive(ata: TouchActionTriggerActive, id: number): void {
    const idleNew = typeof ata.idle === 'number' ? ata.idle : undefined;
    const key = idleNew ?? this.idleIndex; // 形态A 查表用目标 idle（站点先 Ue 后查表）
    if (ata.idle_enable !== undefined || ata.idle_ignore !== undefined) {
      const en = ata.idle_enable?.find(([s]) => s === key)?.[1] ?? [];
      const ig = ata.idle_ignore?.find(([s]) => s === key)?.[1] ?? [];
      this.enable = en.length ? new Set(en) : null;
      this.ignore = ig.length ? new Set(ig) : null;
      if (idleNew !== undefined) this.idleIndex = idleNew; // 带 idle 的形态A 同样推进（站点语义）
    } else {
      // 空数组 = 无白名单（站点 deob officialLive2DActionAllowed：enable.length > 0 才启用；
      // 与形态 A 的 en.length ? new Set(en) : null 对齐。stage1e 实测修正：光辉 ATA.enable=[]
      // 曾被当空白名单拦截一切动作）
      if (Array.isArray(ata.enable)) this.enable = ata.enable.length ? new Set(ata.enable) : null;
      if (ata.ignore) this.ignore = new Set(ata.ignore);
      if (typeof ata.idle === 'number') this.idleIndex = ata.idle;
    }
    this.activeRuleId = id;
  }

  /** actionTrigger 类型分发：手势门控 + 白名单 + 动作组存在性过滤 */
  private dispatch(
    t: TouchActionTrigger | null | undefined,
    kind: 'tap' | 'drag' | 'longpress',
    available: string[],
    stepAction?: string | string[],
  ): string | null {
    if (!t) return null;
    const type = t.type;
    const isDragType = type === 1 || type === 6 || type === 7;
    if (isDragType !== (kind === 'drag')) return null; // 手势门控：拖动型只认 drag，触摸型只认非 drag
    if (type === 6 || type === 7) return null; // 链占位/拖动主控：不直接播动作，交给链状态
    const name = this.pickAction(t.action) ?? this.pickAction(stepAction);
    if (!name) return null;
    if (!available.includes(name)) return null; // 模型缺该动作组则跳过
    if (!this.isActionAllowed(name)) return null;
    return name;
  }

  private pickAction(a: string | string[] | undefined): string | null {
    if (!a) return null;
    if (typeof a === 'string') return a;
    if (Array.isArray(a) && a.length) {
      return a[Math.floor(Math.random() * a.length)];
    }
    return null;
  }
}
