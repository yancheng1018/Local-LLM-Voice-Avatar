# -*- coding: utf-8 -*-
"""调试叠加层家族文件行数契约：每文件 ≤200 行（r2 硬上限，leftover-triage_stage2 固化）。

口径说明：仅约束下列三个调试家族文件（r2 规格对本家族按文件粒度执行硬上限）；
全仓「单模块 ≤200 行」口径待 N14 裁决（research_leftover-triage.md），不在此扩面。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
RENDERER = ROOT / "frontend-minimal" / "src" / "renderer"
LIMIT = 200


def _count(name: str) -> int:
    return len((RENDERER / name).read_text(encoding="utf-8").splitlines())


def test_touch_debug_line_budget():
    assert _count("l2d_touch_debug.ts") <= LIMIT


def test_touch_debug_helpers_line_budget():
    assert _count("l2d_touch_debug_helpers.ts") <= LIMIT


def test_debug_panel_line_budget():
    assert _count("l2d_debug_panel.ts") <= LIMIT
