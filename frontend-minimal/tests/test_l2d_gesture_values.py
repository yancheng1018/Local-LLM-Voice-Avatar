# -*- coding: utf-8 -*-
"""Live2D 手势数值语义（像素拖拽/屏幕空间转盘/idle 循环/空参数注册）：静态断言。

用例与断言点语义对应 docs/context/spec-l2d-touch-engine.md（stage5 章节）。
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def section(
    src: str, start: str, nxt: str = r"\n  (?:private|get |async |[a-zA-Z]+\()"
) -> str:
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
    assert (
        "this.prevDragPx.y - clientY" in acc
    )  # y 上正（引擎 interaction.y − currentY）


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


def test_idle_loop_by_data():
    """research2 v2 §3 方案A′（2026-09-18 replan）：本地库解析 Meta.Loop 但不接线
    （cubism4.es.js _motionData.loop 无消费者），循环须 playIdleOnce 后显式 setIsLoop(true)
    落实，仅 idle 路径；idle 单次化机制废止——「站点播一次即冻结终帧」判定为误观察。"""
    src = read("src/renderer/l2d.ts")
    assert "setIsLoop(false)" not in src  # 机制 2 已删：不再强制置非循环
    assert "disableIdleLoop" not in src
    assert "Meta.Loop" in src  # 库不消费该标志的根因注释必须留档（A′ 依据）
    assert "setIsLoop(true)" in src  # A′：循环须显式落实（数据标志在本地库是死数据）
    assert "enableIdleLoop" in src
    assert (
        src.count("enableIdleLoop(pick.group, pick.index)") == 1
    )  # 接线唯一点=播放回调
    assert ".then((started)" in src  # 播放成功（started）才置循环，被抢占不置


def test_overlay_readout():
    debug = read("src/renderer/l2d_touch_debug_helpers.ts")
    assert "paramValue" in debug and "action=" in debug  # 标签读数
    l2d = read("src/renderer/l2d.ts")
    assert "paramDriver?.getValue(" in l2d  # ParamDriver 只读接口
    params = read("src/renderer/l2d_params.ts")
    assert "getValue(parameter: string): number | undefined" in params
