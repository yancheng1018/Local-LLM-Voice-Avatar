# 规格书 · stage4：circle 转盘手势（引擎精确语义）+ 热区可见性稳定化 + 信浓入列

> 供弱模型执行。stage3 v2 实现后人工验收失败：①光辉 TouchDrag 方向/幅度很不准；②部分原有的
> 点击热区不见了。主模型复核结论（§0）：症状①是 **circle 手势机制整个做错了**（引擎是"转盘"，
> 我们做成了"时间趋近"）；症状②是**透明度剔除 + 姿态波动**把区挤掉了（站点同款波动，但对本地
> 体验是净伤害，本次做有依据的偏离）。信浓（xinnong_6）本地数据**皮肤错配**，一并修复。
> 红线：不改 AGENTS.md、backend、官方 `frontend/`；不改 `l2d_touch.ts` 既有导出签名；命令一律 PowerShell。
> 测试集：guanghui_9 + wuqi_3 + **xinnong_6**。

## 0. 根因（均经 deob/数据核验，弱模型可复核）

1. **circle 手势 = 绕热区中心的"转盘"**（引擎 `live2DCircleDragParameterValue`，deob 原文）：
   `value = rangeMax × ((atan2(curX − cx, cy − curY) × 180/π + 360 − offsetCircle.start) mod 360) / 360`
   —— 指针相对**热区中心**（模型局部，实时包围盒中心）的**角度**直接线性映射参数值：画一圈
   = 全量程，顺/逆时针 = 增/减，拖拽轨迹即波形。引擎随拖拽每帧以 `setOfficialLive2DParameterTarget`
   平滑逼近该值。现实现（l2d_params.ts stepCircle）是"按住 → 时间趋近 circleTarget → 到位翻转"——
   与方向、轨迹、快慢完全无关 → 光辉 4/6 个可拖拽区（TouchDrag1/2/3/15）方向幅度必然不准。
   `offsetCircle` 字段当前三模型数据均无 → start 按 0。
2. **slide 管线 v2 已对**（stage1c §10.2 端到端实测通过：轴选择 |dx/offsetX|≥|dy/offsetY|、
   offset 为 0 按 1 兜底、模型局部位移、clampChain、smooth），**保持不动**。
3. **症状②**：stage1c §10.1/§10.4 已证区集合随冻结姿态波动（T=透明度≤0.01 / O=画布外），
   站点同款。但"按透明度剔除"是 stage3 我们引入的引擎行为，对本地是净伤害：Touch* 辅助绘画件
   透明度随姿态抖动（如光辉 TouchDrag4/5 本次姿态下 T → 拖拽区看不见点不着）。
   **本地偏离站点（标注为超越项 #3）：命中判定不再按透明度剔除**（可见性/画布外/交互门槛保留）；
   叠加层 T 标记降级为提示（区仍填充、仍可交互）。
4. **信浓数据错配**（主模型核验）：`live2d-models/xinnong_6/touch.json` 全部规则
   `shipSkinId=307082`，而模型 `info.json id=307085`（信浓·相融一梦）——与光辉当年同款问题。
   站点数据 URL 模式已验证可用：`/data/ships/CN/<shipId>.json`。

## 1. 文件清单

| 操作 | 路径 | 内容 |
|------|------|------|
| 数据替换 | `live2d-models/xinnong_6/touch.json` | 换成站点 skin 307085 的规则集（§4，备份 `.bak`） |
| 修改 | `frontend-minimal/src/renderer/l2d.ts` | circle hold 改转盘值计算下传；命中路径删透明度剔除 |
| 修改 | `frontend-minimal/src/renderer/l2d_params.ts` | stepCircle 重写：hold 中平滑趋近转盘值；释放 revert 语义 |
| 修改 | `frontend-minimal/src/renderer/l2d_touch_debug.ts` | T 状态改提示性（仍填充）；标签微调 |
| 新建 | `frontend-minimal/tests/test_l2d_hotzone_stage4.py` | pytest 断言（§5） |
| 修订 | `frontend-minimal/tests/test_l2d_hotzone_stage3.py` | 与 §3 冲突的断言（如透明度剔除、circle 时间趋近）改写，报告列出 |
| 不改 | `main.ts`、`l2d_touch.ts` | 保持 |

## 2. 转盘手势实现（核心）

### 2.1 数据流（保持 ParamDriver 纯逻辑，无 pixi 依赖）

- l2d.ts pointerdown：记 downHit **Zone**（含 drawIndex，不只是 rule）→ `beginHold(id)`。
- l2d.ts 指针移动（现有 accumulateDrag 路径，按下即累积）：若 downHit 是 circle 型规则 →
  **每帧**按 §2.2 公式计算 `dialValue` 并调 `driver.setHoldValue(id, dialValue)`；slide/type1/6/7
  规则仍走 `holdDelta(id, dx, dy)`。
- l2d.ts pointerup：`endHold(id)` + `save()`（不变）。

### 2.2 转盘公式（引擎原样，不要"修正"符号方向）

```ts
// cx,cy = downHit Zone 当前包围盒中心（模型局部，实时 getDrawableBounds）；
// curX,curY = 指针模型局部坐标（toModelPosition）；rangeMax = rule.range[1] ?? 1；
// angleOffset = rule.offsetCircle?.start ?? 0（当前数据均无此字段 → 0）
const deg = (Math.atan2(curX - cx, cy - curY) * 180) / Math.PI;
const angle = (((deg + 360 - angleOffset) % 360) + 360) % 360;
const dialValue = rangeMax * (angle / 360);
```

- driver：hold 中 `st.value += (holdValue - st.value) * k(dt, rule.smooth)`；`clampChain` +
  parameterRange 钳制照旧；**hold 中不做 target 回落**（值跟角度走）。
- 释放（endHold）：`revert === -1` → 值保留（现有 slide 释放分支同款）；否则回落 startValue。
- 快速单击（tap）仍走现有 `poke` 翻转（逼近 circleTarget → 回落 startValue）——与转盘并存：
  按住=转盘，单击=点戳。
- 自检口径：屏幕上**顺时针**绕区拖 → 值从 0 向 rangeMax 增（引擎公式如此；实测反了先查
  toModelPosition 的 y 翻转，不得擅改公式符号）。

### 2.3 slide 保持

`stepSlide`/`stepDrag`/轴选择/DRAG 增益（SCALE=1）全部保持 stage3 v2 现状（stage1c 实测通过）。

## 3. 热区可见性稳定化（修症状②）

1. **命中路径删除透明度剔除**：l2d.ts hitZoneAt 的 `OPACITY_CUTOFF` 分支删除（或仅保留在
   叠加层提示里）；保留：可见性、有限/非零包围盒、画布内、交互门槛（OE_TYPES/ATA.idle/放行）。
2. **叠加层**：T 状态改语义为「透明提示」（区仍填充=可交互，标签如 `TouchDrag4 [T:透明但可点]`）；
   O/H/G 状态含义不变（仍剔除）。
3. **姿态**：保持「加载播一次 idle → await 动作结束 → 冻结」（现实现已如此，确认即可）；
   删除透明度剔除后，跨会话区集波动源只剩位置类（O），波动幅度显著收敛。
4. 诊断日志（[Touch] 注册 N/M + 剔除原因）保留，原因枚举去掉 T。

## 4. 信浓数据修复（工具可完成）

```powershell
Copy-Item live2d-models\xinnong_6\touch.json live2d-models\xinnong_6\touch.json.bak -Force
curl.exe -s -o Temp\xinnong_30708.json https://l2d.su/data/ships/CN/30708.json
python -c "import json;d=json.load(open('Temp/xinnong_30708.json',encoding='utf-8'));skins=d['ship']['skins'];skin=[s for s in skins if s['id']==307085][0];json.dump(skin['model']['live2dTouch'],open('live2d-models/xinnong_6/touch.json','w',encoding='utf-8'),ensure_ascii=False);print(len(skin['model']['live2dTouch']['rules']))"
python -c "import json;t=json.load(open('live2d-models/xinnong_6/touch.json',encoding='utf-8'));print(set(r.get('shipSkinId') for r in t['rules']))"
```

- 预期：规则数打印（≥5），shipSkinId 集合 = `{307085}`。若 URL 返回 HTML/404：浏览器开
  `https://l2d.su/cn/skins/307085/` 从 Network 里抓真实舰船数据 URL 再取（报告记录实际 URL）；
  若站点彻底不可用：保留本地数据继续其余项，报告注明。

## 5. 测试用例（新建 `test_l2d_hotzone_stage4.py`；stage3 测试冲突断言改写并报告）

| # | 用例名 | 输入 | 预期 | 断言点 |
|---|--------|------|------|--------|
| 1 | test_circle_dial_formula | l2d.ts | 命中 | `atan2`、`180`（或 `180 / Math.PI`）、`% 360`、`range[1]`（转盘值计算） |
| 2 | test_circle_no_time_approach | l2d_params.ts | 不再命中 | hold 路径中「向 circleTarget 时间趋近」的旧逻辑不存在（poke 单击路径保留） |
| 3 | test_hold_value_api | l2d_params.ts | 命中 | `setHoldValue`（或等价）且 hold 中使用 |
| 4 | test_no_opacity_cull | l2d.ts | 不再命中 | 命中路径无 `OPACITY_CUTOFF` 判断（叠加层/日志用途除外） |
| 5 | test_overlay_T_info | l2d_touch_debug.ts | 命中 | T 状态区仍 `fill`（或等价可交互呈现） |
| 6 | test_xinnong_data | `live2d-models/xinnong_6/touch.json`（python json 读） | 命中 | shipSkinId 集合 == `{307085}` |
| 7 | test_regression_core | 各源文件 | 命中 | slide 轴选择；TouchChain 签名；`l2d-param:`/`l2d-touch:`；playAction；playIdleOnce；OE_TYPES；ATA.idle 门槛；poke 单击翻转 |
| 8 | test_build_and_bundle | `npm --prefix frontend-minimal run build` | exit 0 | 构建通过 |

## 6. 步骤分类

**工具可完成**：§4 数据修复命令；rg 定位；`npm --prefix frontend-minimal run build`；pytest 全部文件。
**需要判断**（报告说明取舍）：转盘方向自检（顺时针增）不符时先查 y 翻转再报告；转盘 smooth 手感
（rule.smooth）；信浓新数据的 type/offset 分布变化对门槛/链的影响（如有 type1 规则确认走 type1/4
分支）；站点不可用时的降级路径。

## 7. 验收口径（人工对照）

1. **转盘**（症状①）：光辉 TouchDrag1/2/15 按住绕区中心画圈 → touch_dragN 参数 0→1 随角度线性
   走、顺时针增、一圈全量程、可反复；TouchDrag3 全量程 0→10。方向、幅度、快慢跟随拖拽。
2. **slide**：光辉 TouchDrag4/5 与 wuqi_3 TouchDrag2/3/6/7 拖动响应不回归（stage1c 口径）。
3. **热区稳定**（症状②）：光辉叠加层 TouchDrag4/5 在 T 状态下仍填充可交互；跨两次刷新，ok 区
   集合一致（只剩 O 类波动）；默认区点击、body 连点链不回归。
4. **信浓**：数据换新后规则区注册数 ≥ 本地旧数据可用区、body 链可推进、无脚本报错。
5. `tests/` 全部 pytest 文件全绿 + `npm run build` 通过。

## 运行测试（弱模型原样执行，不要修改）

```
pytest frontend-minimal/tests/test_l2d_hotzone_stage4.py frontend-minimal/tests/test_l2d_hotzone_stage3.py frontend-minimal/tests/test_l2d_touch_chain.py frontend-minimal/tests/test_touch_debug_overlay.py -q --tb=short --maxfail=1 2>&1 | Select-Object -Last 80
"EXIT:$LASTEXITCODE"
```

如果 EXIT 不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。
