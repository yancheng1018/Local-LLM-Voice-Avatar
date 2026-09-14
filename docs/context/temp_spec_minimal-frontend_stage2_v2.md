# 规格书 · minimal-frontend stage2 v2：调试栏取数路径再修正（`getModel()` 访问器）

> 2026-09-14。**取代 temp_spec_minimal-frontend_stage2.md（v1）**——v1 的路径修正仍错，
> 实现报告的疑点 A 即其症状。执行者只按本文件实现；有冲突停下来汇报。
> 弱模型 stage2 实现忠实执行了 v1，无实现问题；v1 的三处错误见 §6 勘误。

## 0. 新根因与证据（v1 为什么仍错）

v1 把 `parameterIds` 修正为 `parameters.ids`，但保留了 **`.model` 这个不存在的访问器**。
框架 CubismModel（即 `internalModel.coreModel`）公开取核心模型的唯一途径是 **`getModel()` 方法**：

1. **typings**（pixi-live2d-display/types/index.d.ts:3349）：`getModel(): Live2DCubismCore.Model;`
   ——无 `get model()`、无公开 `model` 字段（内部字段 `_model` 为 private）。
2. **本仓库 dist 产物中库自身代码**（生产实际执行）：
   `this.pixelsPerUnit=this.coreModel.getModel().canvasinfo.PixelsPerUnit`、
   `this._model.parts.ids`、`this._model.parameters.ids`。
3. **核心模型结构**（typings `class Model`）：`parameters: Parameters; parts: Parts;`
   ——`parameters.ids` / `parts.ids` 这半段 v1 是对的，错只在 `.model` 这一跳。

**v1 引用的「先例 l2d.ts canvasinfo」是死代码**：l2d.ts:940 生产路径先读
`internalModel.pixelsPerUnit`（库属性，由 `getModel().canvasinfo` 算出）即返回；
944 行 `coreModel?.model?.canvasinfo` 是**从未执行的兜底**——它「存在」但从未验证过 `.model`。

**连带错误**：v1 附录 A 假核心模型把 `model:` 属性焊进形状 → 77 个测试全绿但生产参数/部件区仍空；
v1 §6 自检命令死在同一跳（`coreModel.model` 为 undefined → 读 `.parameters` 抛 TypeError）。
**疑点 A 关闭**：`renderer.model` 是 TS private，运行时可访问，没问题；错的是中间那跳。

## 1. 修正范围（硬性契约）

| 文件 | 动作 |
|------|------|
| `frontend-minimal/src/renderer/l2d_debug_panel_types.ts` | 追加 `DebugCoreSource` 接口（+4 行，现 33 行余量充足） |
| `frontend-minimal/src/renderer/l2d_debug_panel.ts` | 改 2 行（import 行 + `ids()` 体 1 行）；**行数净增 0，改后必须仍 ≤200（现恰 200）** |
| `frontend-minimal/tests/debug_panel_runtime.test.mjs` | 假核心模型改形（§3.1），其余不动 |
| `frontend-minimal/tests/test_debug_panel.py` | 用例 6/7 断言更新（§3.2），其余不动 |

禁改：l2d.ts / ui.ts / main.ts / types.ts / index.html / style.css / test_debug_panel_runtime.py /
mini-DOM 与其余 10 个 mjs 用例；不新增依赖；不 git commit。

## 2. 代码修正（精确改前/改后）

`l2d_debug_panel_types.ts` 在 `DebugCoreModel` 接口之后追加：

```ts
/** 核心 Live2DCubismCore.Model 的最小取形：经框架 getModel() 取，parameters.ids / parts.ids */
export interface DebugCoreSource {
  getModel?(): Record<string, { ids?: string[] }>;
}
```

`l2d_debug_panel.ts` 第 3 行 import 改为（同 1 行）：

```ts
import type { DebugCoreModel, DebugCoreSource, DebugPanelModel, Row } from './l2d_debug_panel_types';
```

`ids()` 体内第 110 行（1 行换 1 行，**勿折行**——用例 6 正则按单行写）：

```ts
// 改前（.model 访问器不存在，恒返回 [] → 参数/部件区永远空）
const raw = (core as unknown as { model?: Record<string, { ids?: string[] }> }).model?.[field]?.ids;
// 改后（框架公开访问器是 getModel() 方法；dist 内库自身 this.coreModel.getModel() 同源）
const raw = (core as unknown as DebugCoreSource).getModel?.()[field]?.ids;
```

改完立即核对：`(Get-Content frontend-minimal/src/renderer/l2d_debug_panel.ts).Count` 仍为 200。

## 3. 测试修正

### 3.1 `tests/debug_panel_runtime.test.mjs`——假核心改形（其余全部不动）

```js
// 改前（错误形状：把 .model 属性焊进假模型，测试形同虚设）
  const coreModel = {
    model: { parameters: { ids: paramIds }, parts: { ids: partIds } },
    ...（方法不变）
  };

// 改后（真实形状：getModel() 方法返回核心对象；绝无 .model 属性）
  const coreRaw = { parameters: { ids: paramIds }, parts: { ids: partIds } };
  const coreModel = {
    getModel: () => coreRaw,
    ...（方法不变）
  };
```

用例 2（`参数/部件滑条按核心结构生成（路径错误的回归用例）`）函数体开头追加一行：

```js
assert.ok(!('model' in f.coreModel), '假核心不得带 .model 属性（防回归）');
```

### 3.2 `tests/test_debug_panel.py`——用例 6/7 更新

- **用例 6 test_id_path_fixed** 改为：面板文件含 `getModel?.()[field]?.ids`、含 `DebugCoreSource`；
  **不含** `\.model\?\.`、`parameterIds`、`partIds`（两种旧路径全根除）。
- **用例 7 test_library_cross_check** 在原三条断言外追加两条：typings 含
  `getModel(): Live2DCubismCore.Model;`；构建后 dist JS 合并文本含 `getModel().canvasinfo`
  （v1 缺这条，accessor 跳从未被验证——本次补上锚点）。

## 4. 运行测试（弱模型原样执行，不要修改）

```
npm --prefix frontend-minimal run build
pytest frontend-minimal/tests/test_debug_panel.py frontend-minimal/tests/test_debug_panel_runtime.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

EXIT 非 0 时只汇报：失败用例名、断言差异、最后 20 行输出。

## 5. 人工验收（命令已换新，测试全绿后）

1. Ctrl+F5 强刷 `http://localhost:12393/m/`。
2. 控制台自检（**v2 命令**）：
   `__vtuber.renderer.model.internalModel.coreModel.getModel().parameters.ids.length` → 应 > 0。
3. 面板参数区应出现大量滑条（不再是「（未暴露 ID 列表）」）；拖 `ParamAngleX` → 头实时转；
   部件区任一行滑到 0 → 部位消失。
4. 其余同 v1 §6：行为开关、动作 ▶、切角色重建、Spine 面板消失、物理/呼吸驱动参数被回写属预期。

## 6. v1 勘误与遗留观察

| v1 位置 | 错误 | 本版处置 |
|---------|------|----------|
| §0/§2 路径 `coreModel.model.parameters.ids` | `.model` 访问器不存在 | §2 改 `getModel()[...]` |
| 附录 A 假核心带 `model:` 属性 | 假模型焊死错误形状，测试无效 | §3.1 改形 + 防回归断言 |
| §6 自检命令 | 同样死在 `.model`（TypeError） | §5 换新命令 |

遗留观察（不在本次范围，勿动）：l2d.ts:944-945 的死兜底 `.model?.canvasinfo` 永不执行，
可留待未来清理（改 `getModel()` 或删）；现由 940 行主路径覆盖，无功能影响。
行数零余量：本次净增 0 行维持 200；后续加功能前先决策（220 例外 or 拆分）。
