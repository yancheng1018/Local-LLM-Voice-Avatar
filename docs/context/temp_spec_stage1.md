# 规格书 · stage1：完善复现 l2d.su 动作链条（规则驱动，替代组名启发式）

> 本规格书供**弱模型原样执行**。目标是**实现**（写代码），把 frontend-minimal 现在的「按动作组名启发式猜测」升级为「按 touch.json 规则数据驱动」，落地研究结论 `docs/context/spec-l2dsu-engine.md` §8 的优先级 ①②③。
> 本文件**覆盖**了上一份「研究阶段」的 stage1 规格书（研究 Temp/*.js 四文件），其结论已并入 `spec-l2dsu-engine.md`，无信息丢失。

## 0. 任务背景（主模型已确认，弱模型照此执行，勿重复推导）

- **现实现（已存在）**：`frontend-minimal/` 阶段四已实现「手势互动 + 递进链」的**启发式版本**，代码在：
  - `frontend-minimal/src/renderer/l2d.ts`：手势状态机（单击/拖动/长按）+ `touch.json` 加载（只用 `drawAbleName → parameter` 当动作组）。
  - `frontend-minimal/src/main.ts`：`touch_idleN` 按编号递进链 + `touch_drag*`/`touch_head`/`touch_special` 派发 + tapMotions 热区。
  - `frontend-minimal/src/renderer/l2d_touch_debug.ts`：热区调试覆盖层（只读 `touchAreas` 的 `drawIndex/group/name`，**本轮不用改**）。
- **研究结论（照抄）**：精确引擎 90% 价值集中在 4 件事，本轮做前 3 件：
  - ② **actionTrigger 类型分发**（type 1 拖动 / 2 触摸即发 / 6 链占位 / 7 拖动主控）——替代 `name.startsWith('TouchDrag')` 猜测与 `touch_idleN` 编号递进。
  - ① **actionTriggerActive（ATA）白名单 + idleIndex 链状态机**（形态A `idle_enable/idle_ignore` 按状态查表；形态B `enable/idle/ignore`）。
  - ③ **limitTime 冷却 + localStorage 持久化**（链进度跨刷新/换模型保留）。
  - **推迟到 stage2**：④ mode2/reactPosX 位置反应、参数钳制（dragDirect/range/smooth/rangeAbs）、listenerData、relationParameter、顶层 parameterRange、游戏机。
- **数据源与验证模型**：`live2d-models/guanghui_9/touch.json`（31 条 rule；type 分布 `{2:24, 6:2, 1:1, 7:1, null:3}`；ATA 形态B 13 条 + 形态A 1 条=TouchDrag8）。该模型无 HitAreas、无 Idle/Talk 组、0 条 Expressions，互动只能走 touch.json 规则引擎路径。
- **硬约束**：只改 `frontend-minimal/` 内的 TypeScript 与测试；**禁止改** `docs/`（除本规格书外）、后端 Python、`model_dict.json`、任何 `.model3.json`/`touch.json`。禁止 WebFetch/WebSearch。

## 1. 需要新建/修改的文件

| 操作 | 路径 | 说明 |
|------|------|------|
| **新建** | `frontend-minimal/src/renderer/l2d_touch.ts` | 纯模块（无 pixi 依赖）：touch.json 类型 + `TouchChain` 状态机（唯一核心产出） |
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | `loadTouchRules` 缓存完整 `TouchRule`；`onInteraction` 透传 `rule` 替代 `ruleGroup` |
| 修改 | `frontend-minimal/src/main.ts` | 用 `TouchChain.resolve()` 替代启发式链；保留无 touch.json 模型的启发式兜底 |
| **新建** | `frontend-minimal/tests/test_l2d_touch_chain.py` | pytest 静态断言 + `npm run build` 构建产物断言 |

> `l2d_touch_debug.ts` **不改**：其 `getTouchAreas` 参数类型是 `{drawIndex; group; name}[]`，本轮的 `touchAreas` 元素是它的**超集**（多 `boundsArea` 与 `rule` 字段），TS 结构子类型兼容，无需改动。

## 2. 数据结构 / 函数签名

### 2.1 新建 `frontend-minimal/src/renderer/l2d_touch.ts`（**整文件复制，逐字照抄**）

```ts
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
}

export interface TouchActionStep {
  num?: number;
  time?: number;
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

  constructor(private readonly storageKey: string) {
    this.restore();
  }

  /** 触发一条命中的规则，返回本次应播放的动作组名；null = 被冷却/白名单/手势门控拦截，不播 */
  resolve(rule: TouchRule, kind: 'tap' | 'drag' | 'longpress', available: string[]): string | null {
    const id = rule.id ?? 0;
    const now = Date.now();
    const until = this.cooldowns.get(id);
    if (until !== undefined && now < until) return null; // ③ 冷却中，拦截
    if (rule.actionTriggerActive) {
      this.applyActive(rule.actionTriggerActive, id); // ① 先建白名单/状态
      this.save();
    }
    const action = this.dispatch(rule.actionTrigger, kind, available);
    if (action === null) return null;
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
      };
      this.idleIndex = s.idleIndex ?? 0;
      this.activeRuleId = s.activeRuleId ?? null;
      this.cooldowns = new Map(
        Object.entries(s.cooldowns ?? {}).map(([k, v]) => [Number(k), v]),
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
        }),
      );
    } catch {
      // localStorage 不可用时静默跳过
    }
  }

  /** ATA 应用：形态A（按 idleIndex 查 idle_enable/idle_ignore 表）或 形态B（直接设 enable/idle/ignore） */
  private applyActive(ata: TouchActionTriggerActive, id: number): void {
    if (ata.idle_enable !== undefined || ata.idle_ignore !== undefined) {
      const en = ata.idle_enable?.find(([s]) => s === this.idleIndex)?.[1] ?? [];
      const ig = ata.idle_ignore?.find(([s]) => s === this.idleIndex)?.[1] ?? [];
      this.enable = en.length ? new Set(en) : null;
      this.ignore = ig.length ? new Set(ig) : null;
    } else {
      if (ata.enable) this.enable = new Set(ata.enable);
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
  ): string | null {
    if (!t) return null;
    const type = t.type;
    const isDragType = type === 1 || type === 6 || type === 7;
    if (isDragType !== (kind === 'drag')) return null; // 手势门控：拖动型只认 drag，触摸型只认非 drag
    if (type === 6 || type === 7) return null; // 链占位/拖动主控：不直接播动作，交给链状态
    const name = this.pickAction(t.action);
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
```

### 2.2 修改 `frontend-minimal/src/renderer/l2d.ts`（5 处编辑）

**编辑 1 — 加 import**（在 `import type { ModelInfo, CharacterRenderer } from './types';` 之后）：

```ts
import type { TouchRule, TouchData } from './l2d_touch';
```

**编辑 2 — `touchAreas` 元素类型加 `rule` 字段**（原 28~30 行）：

```ts
  private touchAreas:
    | { drawIndex: number; group: string; name: string; boundsArea: number; rule: TouchRule }[]
    | null = null;
```

**编辑 3 — `onInteraction` 类型：`ruleGroup: string | null` → `rule: TouchRule | null`**（原 35~45 行，含上方注释里的「ruleGroup=」字样一并改掉）：

```ts
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
```

**编辑 4 — `emitInteraction` 把 `ruleGroup` 改成 `rule`，删除按名猜手势的修正**（原 103~134 行，整段替换）：

```ts
  private emitInteraction(kind: 'tap' | 'drag' | 'longpress', clientX: number, clientY: number): void {
    const rect = (this.app.view as HTMLCanvasElement).getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const areas = this.model ? this.model.hitTest(x, y) : [];
    let region: 'head' | 'body' = 'body';
    let rule: TouchRule | null = null;
    if (this.model) {
      const b = this.model.getBounds();
      region = y < b.top + b.height * 0.3 ? 'head' : 'body';
      // live2dTouch 规则热区（碧蓝航线游戏同款区域数据）：命中则把完整 rule 交给 TouchChain 分发
      if (this.touchAreas?.length) {
        const canvas = this.model.toModelPosition(new Point(x, y));
        const hits = this.touchAreas.filter(
          (a) =>
            this.isDrawableVisible(a.drawIndex) &&
            this.pointInDrawable(a.drawIndex, canvas.x, canvas.y),
        );
        // 多个重叠时取包围盒最小的（最具体的触摸区）
        hits.sort((a, b) => a.boundsArea - b.boundsArea);
        const hit = hits[0];
        if (hit) rule = hit.rule;
      }
    }
    this.onInteraction?.({ kind, areas, region, rule });
  }
```

> 说明：删掉原 `if (hit.name.startsWith('TouchDrag')) kind='drag' …` 那段——手势类型改由 `rule.actionTrigger.type` 在 `TouchChain.dispatch` 里门控，不再按绘画件名猜。`kind` 保持原始手势（tap/drag/longpress）作为门控输入。

**编辑 5 — `loadTouchRules` 解析成 `TouchRule[]`，push 时带上 `rule`**（原 162~206 行两处小改）：

把：
```ts
      const data = await resp.json();
      const rules = (data?.rules ?? []) as {
        drawAbleName?: string;
        parameter?: string;
      }[];
```
改成：
```ts
      const data = (await resp.json()) as TouchData;
      const rules = data.rules ?? [];
```

把 `areas.push({ ... })` 那段（原 200~205 行）在对象里**加一行 `rule,`**：
```ts
        areas.push({
          drawIndex,
          group: param,
          name,
          boundsArea: Math.max(b.width, 0) * Math.max(b.height, 0),
          rule,
        });
```

> 循环变量 `rule`（`for (const rule of rules)`）现在就是完整 `TouchRule`，`rule.drawAbleName`/`rule.parameter` 取值不变。

### 2.3 修改 `frontend-minimal/src/main.ts`（3 处编辑）

**编辑 1 — 加 import**（在 `import type { CharacterRenderer, ModelInfo } from './renderer/types';` 之后）：

```ts
import { TouchChain } from './renderer/l2d_touch';
```

**编辑 2 — 新增 `touchChain` 实例**（在原 `const chain = { index: 0, lastAt: 0, exhaustedAt: 0 };` 之后插入）：

```ts
    // 规则驱动链：按模型名作用域持久化（链进度/冷却跨刷新与换模型保留）
    const touchChain = new TouchChain(`l2d-touch:${modelInfo.name}`);
```

**编辑 3 — 回调解构改 `rule`，规则命中分支改走 `TouchChain`**（原 119~140 行）：

把 `renderer.onInteraction = ({ kind, areas, region, ruleGroup }) => {` 改成：
```ts
    renderer.onInteraction = ({ kind, areas, region, rule }) => {
```

把原「规则热区命中」分支（原 133~138 行）替换为：
```ts
      // touch.json 规则热区命中（游戏同款数据）：交给 TouchChain 按 actionTrigger 类型
      // + ATA 白名单 + limitTime 冷却决定播什么（null=被拦截，不播）
      if (rule) {
        play(touchChain.resolve(rule, kind, groups));
        return;
      }
      // 有规则数据的模型：点在规则区域之外（如场景背景）不反应（游戏同款）
      if (renderer.hasTouchRules) return;
```

> 其余启发式兜底（`kind === 'drag'`/`'longpress'`、tapMotions、头/身、`touch_idleN` 递进链 `chain`/`chainGroups`）**原样保留不动**——它们只会在「模型无 touch.json」时走到。

## 3. 核心逻辑（伪代码 / 分步）

弱模型按 6 步执行：

```
Step1 新建 l2d_touch.ts：把 §2.1 整段代码原样写入（逐字，不要改签名与字符串字面量）。

Step2 改 l2d.ts：按 §2.2 的 5 处编辑逐条落地，确认全文不再出现「ruleGroup」。

Step3 改 main.ts：按 §2.3 的 3 处编辑逐条落地。

Step4 新建测试文件 tests/test_l2d_touch_chain.py：把 §4 后的完整代码原样写入。

Step5 构建验证：npm run build（含 tsc --noEmit 类型检查 + vite 打包）。
       类型错误/未用变量都会让这一步失败——是预期的拦错手段，逐个修到通过。

Step6 跑测试：§6 命令块原样执行；EXIT 非 0 只汇报失败用例名/断言差异/最后 20 行 traceback。
```

`TouchChain` 运行语义（供理解，勿改实现）：

```
resolve(rule, kind, available):
  id = rule.id ?? 0; now = Date.now()
  冷却命中且未到期 → return null                        # ③
  if rule.actionTriggerActive: applyActive(ata, id); save()  # ①
  action = dispatch(rule.actionTrigger, kind, available)
  action == null → return null
  limitTime > 0 → cooldowns.set(id, now + limitTime*1000); save()  # ③
  return action

applyActive(ata, id):
  形态A(idle_enable/idle_ignore 存在): 按 idleIndex 查表 → enable/ignore（空则 null）
  形态B: enable→Set; ignore→Set; typeof idle==='number' → idleIndex=idle
  activeRuleId = id

dispatch(t, kind, available):
  t == null → null
  isDrag = type in {1,6,7}; isDrag !== (kind==='drag') → null   # 手势门控
  type 6/7 → null（链占位/拖动主控不直接播）
  name = pickAction(t.action); name 空 → null
  name ∉ available → null; isActionAllowed(name)==false → null
  return name
```

## 4. 测试用例（输入 → 预期 → 断言点）

新建 `frontend-minimal/tests/test_l2d_touch_chain.py`（**整文件复制**）：

```python
# -*- coding: utf-8 -*-
"""l2d.su 动作链条（TouchChain）stage1：静态断言 + 构建产物验证。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_touch_module_exists():
    src = read("src/renderer/l2d_touch.ts")
    assert "export class TouchChain" in src


def test_touch_types():
    src = read("src/renderer/l2d_touch.ts")
    for name in ("TouchRule", "TouchActionTrigger", "TouchActionTriggerActive", "TouchData"):
        assert name in src


def test_resolve_signature():
    src = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        src,
    )


def test_is_action_allowed():
    src = read("src/renderer/l2d_touch.ts")
    assert re.search(r"isActionAllowed\(name: string\): boolean", src)


def test_ata_both_forms():
    src = read("src/renderer/l2d_touch.ts")
    assert "idle_enable" in src
    assert "idle_ignore" in src
    assert "typeof ata.idle" in src  # 形态B 的 idle 数字分支


def test_persistence():
    src = read("src/renderer/l2d_touch.ts")
    assert "localStorage" in src
    assert "cooldowns" in src
    assert "limitTime" in src


def test_l2d_caches_full_rule():
    l2d = read("src/renderer/l2d.ts")
    assert "rule: TouchRule" in l2d
    assert "./l2d_touch" in l2d


def test_l2d_emits_rule_not_rulegroup():
    l2d = read("src/renderer/l2d.ts")
    assert re.search(r"rule: TouchRule \| null", l2d)
    assert "ruleGroup" not in l2d


def test_main_uses_touch_chain():
    main = read("src/main.ts")
    assert "new TouchChain(" in main
    assert "touchChain.resolve(" in main


def test_build_and_bundle():
    r = subprocess.run(
        "npm --prefix frontend-minimal run build",
        shell=True,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "")[-2000:])
        sys.stderr.write((r.stderr or "")[-2000:])
    assert r.returncode == 0
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "l2d-touch:" in js  # 存储键前缀，字符串字面量抗压缩，证明链被实际打包
```

| 用例 | 断言点（文件 + 子串/正则） | 预期 |
|------|------|------|
| T1 | l2d_touch.ts 含 `export class TouchChain` | 命中 |
| T2 | 含 `TouchRule`/`TouchActionTrigger`/`TouchActionTriggerActive`/`TouchData` | 命中 |
| T3 | `resolve` 签名正则（含 `kind: 'tap' \| 'drag' \| 'longpress'`） | 命中 |
| T4 | `isActionAllowed(name: string): boolean` | 命中 |
| T5 | `idle_enable` + `idle_ignore` + `typeof ata.idle` | 命中 |
| T6 | `localStorage` + `cooldowns` + `limitTime` | 命中 |
| T7 | l2d.ts 含 `rule: TouchRule` 且 import `./l2d_touch` | 命中 |
| T8 | l2d.ts 含 `rule: TouchRule \| null` 且 **不含** `ruleGroup` | 命中 |
| T9 | main.ts 含 `new TouchChain(` 且 `touchChain.resolve(` | 命中 |
| T10 | `npm run build` 退出码 0；dist JS 含 `l2d-touch:` | 命中 |

## 5. 步骤分类

### 5.1 「工具可完成」—— 弱模型直接执行这些命令（PowerShell）

```powershell
# 前置：确认 Node 在 PATH（v24；Git Bash 里需 export PATH="/c/Program Files/nodejs:$PATH"）
node --version

# 类型检查（比整构建快，先跑它定位类型错误）
npm --prefix frontend-minimal run build

# 只做类型检查、不打 bundle（可选，更快）
npx --prefix frontend-minimal tsc --noEmit -p frontend-minimal/tsconfig.json

# 自检：确认关键字符串已落地（每条应各自命中）
Select-String -Path .\frontend-minimal\src\renderer\l2d_touch.ts -Pattern 'export class TouchChain','isActionAllowed','idle_enable','localStorage' -SimpleMatch
Select-String -Path .\frontend-minimal\src\renderer\l2d.ts -Pattern 'rule: TouchRule','./l2d_touch' -SimpleMatch
Select-String -Path .\frontend-minimal\src\main.ts -Pattern 'new TouchChain(','touchChain.resolve(' -SimpleMatch

# 确认 l2d.ts 里已无 ruleGroup（应无输出）
Select-String -Path .\frontend-minimal\src\renderer\l2d.ts -Pattern 'ruleGroup' -SimpleMatch
```

### 5.2 「需要判断」—— 留给弱模型（工具无法替代的语义理解）

1. **手势门控方向**：`dispatch` 里 `isDragType !== (kind === 'drag')` 表示——type 1/6/7（拖动类）只在 `kind==='drag'` 时放行；type 2（触摸即发）只在非 drag（tap/longpress）时放行。这是把 `actionTrigger.type` 与手势 `kind` 正确对位的关键，别写反。
2. **白名单持续语义**：某 rule **无** `actionTriggerActive` 时，`applyActive` 不执行，`enable/ignore` 保留上一条 ATA 的值（对应 l2d.su 的 `live2dOfficialEnableActions` 持续生效直到被覆盖）。不要「无 ATA 就清空白名单」。
3. **存储键作用域**：`l2d-touch:${modelInfo.name}` —— 按模型名隔离，换模型/换角色互不污染，同模型刷新后链进度恢复。
4. **冷却单位**：`limitTime` 是秒，`cooldowns` 存的是「到期时间戳（毫秒）」，所以 `now + limitTime * 1000`；读取时 `now < until` 才拦截。别把秒/毫秒搞混。
5. **动作组存在性**：`available`（= `renderer.getMotionGroups()`）里没有的动作组直接 `return null`，因为 `setAnimation` 对不存在的组是空操作。这一步保证「模型缺某编号时自动跳过」。
6. **形态A vs 形态B 判定**：以 `idle_enable`/`idle_ignore` **是否为 `undefined`** 判定走哪条分支（不是「数组非空」——空数组 `[]` 也应走形态A分支，且查表命中空时 `enable/ignore` 置 null）。

## 6. 测试运行命令块

### 运行测试（弱模型原样执行，不要修改）

```powershell
cd C:\Coding\Application\v1.2.1_Open-LLM-VTuber-v1.2.1-zh
pytest frontend-minimal/tests/test_l2d_touch_chain.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

**回归**（本轮改动不得破坏既有断言，同样跑一遍）：

```powershell
cd C:\Coding\Application\v1.2.1_Open-LLM-VTuber-v1.2.1-zh
pytest frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

> **如果 EXIT 不是 0**：只汇报失败用例名（test_xxx）、断言差异（expected vs 实际 `assert` 报错行）、以及最后 20 行 traceback。若 T10（构建）失败，额外附上 `r.stdout`/`r.stderr` 末尾 2000 字符里的 `error TSxxxx` 首条信息。
>
> 注意：`tsconfig.json` 开了 `strict` + `noUnusedLocals` + `noUnusedParameters`——未使用的 import/变量/参数会直接让 `tsc` 报 `TS6133` 导致 T10 失败，属预期拦错，删掉未用项即可，不要关编译器选项。
