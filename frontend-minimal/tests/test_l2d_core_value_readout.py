# -*- coding: utf-8 -*-
"""live2d动作链条-research2 §5/§7：验收仪表 core 写入值列 + ⚠写入失效标志。

静态锚点 + esbuild→node 运行时向量（zoneLabelParts 双显；helpers 的 pixi.js 导入
用 stub 替身 --alias bundle，zoneLabelParts 本身不依赖 pixi 运行时）。
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
ESBUILD = FM / "node_modules" / "esbuild" / "bin" / "esbuild"

STUB = "export class Point { constructor(x = 0, y = 0) { this.x = x; this.y = y; } }\n"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def section(src: str, start: str, nxt: str = r"\n  (?:private|get |async |[a-zA-Z]+\()") -> str:
    """截取从 start 标记到下一个方法定义之间的源码段（方法体级断言用）。"""
    m = re.search(re.escape(start), src)
    assert m, f"marker not found: {start}"
    rest = src[m.start():]
    m2 = re.search(nxt, rest[len(start):])
    return rest[: len(start) + m2.start()] if m2 else rest


def helpers_run(setup: str):
    """esbuild --bundle 编译 helpers（pixi.js→Point stub）→ node 执行 setup，返回 OUT。"""
    with tempfile.TemporaryDirectory() as tmp:
        stub = Path(tmp) / "pixi_stub.mjs"
        stub.write_text(STUB, encoding="utf-8")
        out = Path(tmp) / "helpers_rt.mjs"
        r = subprocess.run(
            [
                "node",
                str(ESBUILD),
                str(FM / "src" / "renderer" / "l2d_touch_debug_helpers.ts"),
                "--bundle",
                "--format=esm",
                f"--alias:pixi.js={stub.as_posix()}",
                f"--outfile={out}",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        code = (
            f"import {{ zoneLabelParts }} from {out.as_uri()!r};"
            f"const OUT = (() => {{ {setup} }})();"
            "console.log(JSON.stringify(OUT))"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        return json.loads(r.stdout.strip())


def test_zone_state_core_field():
    src = read("src/renderer/l2d_touch_debug_helpers.ts")
    assert "coreValue?: number;" in src


def test_readout_dual_display():
    setup = (
        "return ["
        "zoneLabelParts({group:'touch_drag3', name:'TouchDrag3', status:'ok',"
        "paramValue:2.6, coreValue:0}).readout,"
        "zoneLabelParts({group:'g', name:'n', status:'ok',"
        "paramValue:1.0, coreValue:1.02}).readout,"
        "zoneLabelParts({group:'g', name:'n', status:'ok', paramValue:1.0}).readout]"
    )
    # 双显：|内-核|>0.05 → `内→核`；|差|≤0.05 或缺核值（旧 core 无 API）→ 单显
    assert helpers_run(setup) == [" touch_drag3=2.6→0.0", " g=1.0", " g=1.0"]


def test_l2d_core_read():
    l2d = read("src/renderer/l2d.ts")
    states = section(l2d, "touchZoneStates(): TouchZoneState[] {")
    assert "getParameterValueById" in states
    assert "const coreValue = hasParam ?" in states  # 仅 hasParam 区读 core


def test_write_fail_flag():
    src = read("src/renderer/l2d_touch_debug.ts")
    assert "⚠写入失效" in src
    assert "this.writeFailFrames = diverged ? this.writeFailFrames + 1 : 0;" in src  # 无分歧归零
    assert re.search(r"writeFailFrames >= 60", src)  # ≈1s 持续分歧才告警（防瞬时误报）
    assert "> 0.05" in src  # 分歧阈值
