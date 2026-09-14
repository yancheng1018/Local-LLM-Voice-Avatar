# -*- coding: utf-8 -*-
"""Live2D 拖拽像素制 + circle 翻转开关 + 空参数区注册 + idle 单次化 stage5：静态断言 + 构建产物验证。

用例与断言点严格对应 docs/context/temp_spec_stage5.md §6 表格（不得增减语义）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def section(src: str, start: str, nxt: str = r"\n  (?:private|get |async |[a-zA-Z]+\()") -> str:
    """截取从 start 标记到下一个方法定义之间的源码段（方法体级断言用）。"""
    m = re.search(re.escape(start), src)
    assert m, f"marker not found: {start}"
    rest = src[m.start() :]
    m2 = re.search(nxt, rest[len(start) :])
    return rest[: len(start) + m2.start()] if m2 else rest


def test_slide_pixel_delta():
    src = read("src/renderer/l2d.ts")
    acc = section(src, "private accumulateDrag(")
    assert "clientX - this.prevDragPx.x" in acc  # 增量来自 clientX/Y
    assert "toModelPosition" not in acc  # slide 增量不经模型局部换算
    assert "DRAG_VALUE_SCALE" not in src  # 像素即引擎单位，恒 1 删除


def test_slide_y_up():
    src = read("src/renderer/l2d.ts")
    acc = section(src, "private accumulateDrag(")
    assert "this.prevDragPx.y - clientY" in acc  # y 上正（引擎 interaction.y − currentY）


def test_dial_screen_space():
    src = read("src/renderer/l2d.ts")
    dial = section(src, "private dialValueFor(")
    assert "worldTransform" in dial and "localTransform" in dial  # 屏幕换算链路
    assert "clientX - cx" in dial  # 指针 = 屏幕像素坐标
    assert "Math.atan2(" in dial and "* 180) / Math.PI" in dial and "% 360" in dial


def test_circle_toggle_stay():
    src = read("src/renderer/l2d_params.ts")
    step = section(src, "private stepCircle(")
    assert "pokeTarget = r.startValue" not in step  # 到位后无自动回落
    assert re.search(
        r"Math\.abs\(st\.value - r\.circleTarget\) < POKE_EPSILON \? r\.startValue : r\.circleTarget",
        src,
    )  # 翻转仅在 poke 入口


def test_empty_param_registered():
    src = read("src/renderer/l2d.ts")
    load = section(src, "private async loadTouchRules(")
    assert "group: param || name" in load  # 空参数规则照常注册空间热区
    assert "noParam" not in load  # 「参数空」跳过分支已删
    assert "noActionNoParam" in load  # 新计数：无动作且无参数
    prule = section(src, "private toParamRule(")
    assert "if (!param) return null" in prule  # ParamDriver 仍不收空参数（仅动作路径）


def test_idle_no_loop():
    src = read("src/renderer/l2d.ts")
    assert "setIsLoop(false)" in src  # 机制 2：已加载 motion 置非循环
    assert "disableIdleLoop" in src


def test_overlay_readout():
    debug = read("src/renderer/l2d_touch_debug.ts")
    assert "paramValue" in debug and "action=" in debug  # 标签读数
    l2d = read("src/renderer/l2d.ts")
    assert "paramDriver?.getValue(" in l2d  # ParamDriver 只读接口
    params = read("src/renderer/l2d_params.ts")
    assert "getValue(parameter: string): number | undefined" in params


def test_regression_core():
    touch = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        touch,
    )
    l2d = read("src/renderer/l2d.ts")
    for s in ("playAction", "OE_TYPES", "ataIdle !== this.chainIdleIndex()"):
        assert s in l2d
    params = read("src/renderer/l2d_params.ts")
    assert "PARAM_STORAGE_PREFIX = 'l2d-param:'" in params
    assert re.search(
        r"Math\.abs\(st\.value - r\.circleTarget\) < POKE_EPSILON \? r\.startValue : r\.circleTarget",
        params,
    )  # poke 翻转入口
    assert "l2d-touch:" in read("src/main.ts")
    t = json.loads((ROOT / "live2d-models/xinnong_6/touch.json").read_text(encoding="utf-8"))
    assert {r.get("shipSkinId") for r in t["rules"]} == {307085}


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
