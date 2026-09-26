# -*- coding: utf-8 -*-
"""r3 定案四缺陷修正：误杀/夺轴/归零/复位残留 + 起点锚定。静态断言 + 构建产物验证。

用例与断言点语义对应 docs/context/temp_spec_live2d-hotzone-touch-r2_v3.md §2。
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_no_action_rule_interactive():
    src = read("src/renderer/l2d.ts")
    assert "if (names.length === 0) return true;" in src  # r3 §3.1.1 站点 Oe 口径
    assert "return t.circle === true ||" not in src  # 旧误杀分支已删


def test_slide_registration_relaxed():
    src = read("src/renderer/l2d.ts")
    assert (
        "!at?.action && ((num(rule.offsetX) ?? 0) !== 0" in src
    )  # typed-无 action 可注册


def test_dragdirect_gate_restored():
    src = read("src/renderer/l2d_params.ts")
    assert (
        "if ((v < 0 && r.dragDirect === 1) || (v > 0 && r.dragDirect === 2)) v = 0;"
        in src
    )  # r4 §3.1c 门控恢复
    assert src.index("r.dragDirect === 1") < src.index(
        "r.rangeAbs === 1"
    )  # 门控在 rangeAbs 之前（站点次序）
    assert "if (r.rangeAbs === 1) v = Math.abs(v);" in src  # rangeAbs 链保留
    assert "return clamp(v, r.range[0], r.range[1]);" in src


def test_slide_axis_exclusion_and_anchor():
    src = read("src/renderer/l2d_params.ts")
    slide = src.split("private stepSlide(", 1)[1].split("private stepDrag(", 1)[0]
    assert "clampChain(this.holdBase + (lin ?? 0), r)" in slide  # 起点锚定 r3 §5.1
    assert (
        "r.startValue + lin" not in slide
    )  # slide 不再从 startValue 重锚（stepDrag 仍用，勿误伤）
    hold = src.split("beginHold(id: number): void", 1)[1].split("holdDelta(", 1)[0]
    assert "this.holdBase = this.states.get(id)?.dragAccum ?? r.startValue;" in hold


def test_reset_all():
    params = read("src/renderer/l2d_params.ts")
    assert "resetAll(): void" in params
    assert "localStorage.removeItem(this.storagePrefix + this.scopeName)" in params
    l2d = read("src/renderer/l2d.ts")
    m = re.search(r"resetToInitialMotion\(\): void \{(?P<body>[\s\S]*?)\n  \}", l2d)
    assert m, "resetToInitialMotion body not found"
    body = m.group("body")
    assert "this.paramDriver?.resetAll();" in body
    assert body.index("resetAll") < body.index(
        "playIdleOnce()"
    )  # 复位在回初始 idle 之前


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
    assert (
        "this.holdBase=" in js
    )  # 起点锚定字段入包（esbuild 剥注释，锚点=补丁标识符，dist 实测存活）
    assert "resetAll(){for(const" in js  # resetAll 方法体入包
