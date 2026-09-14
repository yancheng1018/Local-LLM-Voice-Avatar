# -*- coding: utf-8 -*-
"""Live2D 拖拽参数管线补全 + 热区可见性诊断 stage3 v2：静态断言 + 构建产物验证。

用例与断言点严格对应 docs/context/temp_spec_stage3.md §4 表格（不得增减语义）。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_slide_rule_registered():
    src = read("src/renderer/l2d.ts")
    # toParamRule：无 actionTrigger 且 offset≠0 → slide 注册分支
    assert re.search(
        r"!at && \(\(num\(rule\.offsetX\) \?\? 0\) !== 0 \|\| \(num\(rule\.offsetY\) \?\? 0\) !== 0\)",
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
    assert re.search(r"holdAcc\.x / \(r\.slide\.ox \|\| 1\)", src)
    assert re.search(r"holdAcc\.y / \(r\.slide\.oy \|\| 1\)", src)
    assert re.search(r"Math\.abs\(xv\) >= Math\.abs\(yv\) \? xv : yv", src)  # 引擎同款轴选择


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
    assert "'ok' | 'H' | 'T' | 'O' | 'G'" in src  # 状态标记（原因字母）
    assert "getZoneStates" in src  # 全部已注册区都画（不再只画可用区）
    assert re.search(r"` \[\$\{a\.status\}\]`", src)  # 剔除区标签带原因标记（stage4：T 改提示仍带标）
    assert "if (r.fill)" in src and "beginFill(r.color, 0.18)" in src  # 可用区实色填充 / 剔除区只描边


def test_diag_log():
    src = read("src/renderer/l2d.ts")
    assert "`[Touch] ${modelInfo.name} 注册 ${zones.length}/${rules.length}：`" in src
    for reason in ("无绘画件名", "drawable缺失", "画布外", "无动作且无参数"):  # stage5：枚举去「参数空」
        assert reason in src  # 剔除原因计数
    assert "默认区缺失" in src  # §3.3.3 默认区缺失说明


def test_regression_core():
    touch = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        touch,
    )
    l2d = read("src/renderer/l2d.ts")
    for s in ("OE_TYPES", "ataIdle !== this.chainIdleIndex()", "playAction", "playIdleOnce"):
        assert s in l2d
    assert "PARAM_STORAGE_PREFIX = 'l2d-param:'" in read("src/renderer/l2d_params.ts")
    assert "l2d-touch:" in read("src/main.ts")


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
    assert "l2d-param:" in js
    assert "l2d-touch:" in js
