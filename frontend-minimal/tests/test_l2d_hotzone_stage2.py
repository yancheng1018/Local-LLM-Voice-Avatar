# -*- coding: utf-8 -*-
"""Live2D 热区与动作链条升级 stage2（参数驱动引擎）：静态断言 + 构建产物验证。

用例与断言点语义对应 docs/context/spec-l2d-touch-engine.md（stage2 章节，原 temp_spec_stage2.md 已并入；不得增减语义）。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_params_module_exists():
    src = read("src/renderer/l2d_params.ts")
    for s in (
        "export class ParamDriver",
        "export function clampChain",
        "export function lookup103",
        "export function reactSum",
        "export function canvasNorm",
        "PARAM_STORAGE_PREFIX",
    ):
        assert s in src


def test_touchchain_signatures_intact():
    src = read("src/renderer/l2d_touch.ts")
    assert "export class TouchChain" in src
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        src,
    )


def test_no_motion_group_gate():
    src = read("src/renderer/l2d.ts")
    assert "!valid.has(param)" not in src


def test_no_oncanvas_gate():
    src = read("src/renderer/l2d.ts")
    assert "onCanvas" not in src


def test_default_zones_registered():
    src = read("src/renderer/l2d.ts")
    for name in ("'TouchSpecial'", "'TouchHead'", "'TouchBody'"):
        assert src.count(name) >= 1


def test_render_order_pick():
    src = read("src/renderer/l2d.ts")
    assert "getDrawableRenderOrder" in src
    assert re.search(r"b\.renderOrder - a\.renderOrder", src)  # 渲染序降序取最上层


def test_usable_bounds():
    src = read("src/renderer/l2d.ts")
    assert "isFinite" in src
    assert "width > 0" in src
    assert "height > 0" in src


def test_react_mode2():
    src = read("src/renderer/l2d_params.ts")
    assert "mode === 2" in src
    assert "reactPosX" in src


def test_circle_gesture():
    src = read("src/renderer/l2d_params.ts")
    assert "circleTarget" in src
    assert "0.05" in src


def test_relation103():
    src = read("src/renderer/l2d_params.ts")
    assert "relationValue" in src
    assert "103" in src


def test_param_range_clamp():
    src = read("src/renderer/l2d_params.ts")
    assert "parameterRange" in src


def test_param_persist():
    src = read("src/renderer/l2d_params.ts")
    assert "localStorage" in src
    assert "l2d-param:" in src


def test_frame_hook():
    src = read("src/renderer/l2d.ts")
    assert "beforeModelUpdate" in src
    assert "paramDriver.update(" in src


def test_main_fallback_intact():
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
    assert "l2d-param:" in js  # 参数持久化前缀字面量，证明参数引擎被实际打包
    assert "l2d-touch:" in js  # TouchChain 存储键前缀（stage1 回归保护）
