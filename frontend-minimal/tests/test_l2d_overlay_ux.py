# -*- coding: utf-8 -*-
"""热区叠加层可读性与未命中提示：静态断言（子串/正则）+ 构建产物验证。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"
MAIN = "src/renderer/l2d_touch_debug.ts"
HELPERS = "src/renderer/l2d_touch_debug_helpers.ts"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_helpers_module():
    helpers = read(HELPERS)
    main = read(MAIN)
    assert "export interface TouchDebugModel" in helpers
    for fn in (
        "modelPointToScreen",
        "modelRectToScreen",
        "firstModelPoint",
        "selfCheckConversion",
        "collectHitAreas",
    ):
        assert f"export function {fn}" in helpers
    assert "export type { TouchDebugModel }" in main
    for gone in (
        "private modelPointToScreen",
        "private modelRectToScreen",
        "private selfCheck",
        "private firstModelPoint",
    ):
        assert gone not in main


def test_empty_not_label_prefix():
    main = read(MAIN)
    l2d = read("src/renderer/l2d.ts")
    assert "a.group === 'empty' ? a.name :" in main
    assert "group: param || name" in l2d  # 注册语义回归锚点（spec-l2d-touch-engine §3）


def test_dim_noninteractive_labels():
    main = read(MAIN)
    assert "dim: boolean" in read(
        HELPERS
    )  # Region 声明已迁 helpers（leftover-triage_stage2 §B1）
    assert "dim: !fill" in main
    assert "alpha = r.dim ? 0.45 : 1" in main


def test_no_hit_hint():
    main = read(MAIN)
    assert "notifyNoHit(canvasX: number, canvasY: number): void" in main
    assert "const HINT_TEXT = '未命中可交互热区'" in main
    assert "const HINT_MS = 1200" in main
    assert "performance.now() + HINT_MS" in main
    uh = main.split("private updateHint", 1)[1]
    assert "this.hintText.visible = remain > 0" in uh
    assert "this.hintText.alpha = Math.min(1, remain / HINT_MS)" in uh
    rl = main.split("private removeLayer", 1)[1].split("private ensureLayer", 1)[0]
    assert "this.hintText = null" in rl


def test_l2d_wiring_single_point():
    l2d = read("src/renderer/l2d.ts")
    assert l2d.count("notifyNoHit(x, y)") == 1
    before = l2d[: l2d.index("notifyNoHit(x, y)")].splitlines()
    assert "kind === 'tap' && this.hasTouchRules" in "\n".join(before[-5:])


def test_redline_untouched():
    touch = read("src/renderer/l2d_touch.ts")
    l2d = read("src/renderer/l2d.ts")
    assert "if (!t) return null" in touch  # 无 actionTrigger → null 语义未动
    assert "private isRuleInteractive" in l2d  # 判定层未动锚点
    assert "DRAG_THRESHOLD = 40" in l2d


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
    assert "未命中可交互热区" in js
