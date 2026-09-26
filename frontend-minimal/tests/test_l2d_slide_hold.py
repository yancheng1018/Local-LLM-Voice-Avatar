# -*- coding: utf-8 -*-
"""Live2D slide/hold 拖拽管线 + 诊断日志 + 动作路径核心锚：静态断言。

用例与断言点语义对应 docs/context/spec-l2d-touch-engine.md（stage3 章节）。
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_slide_rule_registered():
    src = read("src/renderer/l2d.ts")
    # toParamRule：无 action（有无 actionTrigger 均可，r3 §3.1）且 offset≠0 → slide 注册分支
    assert re.search(
        r"!at\?\.action && \(\(num\(rule\.offsetX\) \?\? 0\) !== 0 \|\| \(num\(rule\.offsetY\) \?\? 0\) !== 0\)",
        src,
    )
    assert "slide: { ox:" in src
    params = read("src/renderer/l2d_params.ts")
    assert "slide?: { ox: number; oy: number }" in params


def test_hold_pipeline():
    l2d = read("src/renderer/l2d.ts")
    params = read("src/renderer/l2d_params.ts")
    for s in ("beginHold", "holdDelta", "endHold"):
        assert s in l2d
        assert s in params
    # accumulateDrag 不再限 type1/6/7（旧守卫已删除，驱动器自过滤）
    assert "if (t !== 1 && t !== 6 && t !== 7) return;" not in l2d
    assert "paramDriver?.holdDelta(" in l2d


def test_slide_axis_choice():
    src = read("src/renderer/l2d_params.ts")
    # r3 §5.4.5：offset=0 的轴不参与（undefined），非 ||1 兜底
    assert re.search(r"ox !== 0 \? this\.holdAcc\.x / r\.slide\.ox : undefined", src)
    assert re.search(r"oy !== 0 \? this\.holdAcc\.y / r\.slide\.oy : undefined", src)
    assert re.search(
        r"Math\.abs\(xv\) >= Math\.abs\(yv\) \? xv : yv", src
    )  # 引擎同款轴选择


def test_circle_drag_loop():
    """stage4 修订：hold 改转盘值（setHoldValue 下传），原「到位翻转时间趋近」断言已废；
    poke 单击翻转语义保留。"""
    src = read("src/renderer/l2d_params.ts")
    assert re.search(r"st\.holdValue - st\.value", src)  # hold 中趋近转盘值
    assert re.search(
        r"Math\.abs\(st\.value - r\.circleTarget\) < POKE_EPSILON \? r\.startValue : r\.circleTarget",
        src,
    )  # poke 单击翻转保留


def test_type14_branch():
    src = read("src/renderer/l2d.ts")
    assert re.search(r"t\.type === 1 \|\| t\.type === 4", src)  # 拖拽结束触发 action
    assert "actionNamesOf(downRule)" in src


def test_overlay_status():
    src = read("src/renderer/l2d_touch_debug.ts")
    helpers = read("src/renderer/l2d_touch_debug_helpers.ts")
    # 状态标记（原因字母）：r2 重构已迁 helpers（授权的第三处锚点迁移，性质同 §2.7）
    assert "'ok' | 'H' | 'T' | 'O' | 'G'" in helpers
    assert "getZoneStates" in src  # 全部已注册区都画（不再只画可用区）
    # 剔除区标签带原因标记（stage4：T 改提示仍带标）；r2 迁 zoneLabelParts（helpers）
    assert re.search(r"` \[\$\{a\.status\}\]`", helpers)
    assert (
        "if (r.fill)" in src and "beginFill(r.color, 0.18)" in src
    )  # 可用区实色填充 / 剔除区只描边


def test_diag_log():
    src = read("src/renderer/l2d.ts")
    assert "`[Touch] ${modelInfo.name} 注册 ${zones.length}/${rules.length}：`" in src
    for reason in (
        "无绘画件名",
        "drawable缺失",
        "画布外",
        "无动作且无参数",
    ):  # stage5：枚举去「参数空」
        assert reason in src  # 剔除原因计数
    assert "默认区缺失" in src  # §3.3.3 默认区缺失说明


def test_action_core_anchors():
    """regression_core 去重后唯一存活锚：OE_TYPES 交互门槛类型集 + playAction 播放入口。"""
    src = read("src/renderer/l2d.ts")
    assert "OE_TYPES" in src
    assert "playAction" in src
