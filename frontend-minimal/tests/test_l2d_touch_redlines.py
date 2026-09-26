# -*- coding: utf-8 -*-
"""r2 收回透明剔除（D1/D3）+ G/T 状态序 + 链步进优先级：静态断言 + 构建产物验证。

用例与断言点语义对应 docs/context/temp_spec_live2d-hotzone-touch-r2.md §4.1。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"
L2D = "src/renderer/l2d.ts"
MAIN = "src/renderer/l2d_touch_debug.ts"
HELPERS = "src/renderer/l2d_touch_debug_helpers.ts"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_g_before_t():
    src = read(L2D)
    assert src.index("'G' as const") < src.index("'T' as const")


def test_chain_action_priority():
    src = read(L2D)
    body = src.split("findChainRule(groupName", 1)[1]
    assert body.index("actionNamesOf(r).includes(groupName)") < body.index(
        "r.parameter === groupName"
    )


def test_t_not_interactive():
    main = read(MAIN)
    helpers = read(HELPERS)
    assert "const interactive = a.status === 'ok';" in main
    assert "透明剔除" in main
    assert "zoneLabelParts(a)" in main
    assert "export type { TouchZoneState };" in main
    assert "透明但可点" not in main
    assert "a.status === 'ok' || a.status === 'T'" not in main
    assert "export function zoneLabelParts" in helpers
    assert "export interface TouchZoneState" in helpers


def test_body_entry_hint():
    main = read(MAIN)
    assert "链入口出视口" in main
    assert "z.name === 'TouchBody'" in main


def test_redline_untouched():
    touch = read("src/renderer/l2d_touch.ts")
    assert "if (!t) return null" in touch
    src = read(L2D)
    assert (
        "ataIdle === this.chainIdleIndex()" in src
    )  # 防重复方向（r4 §4.3 翻转 v3 门槛）
    assert "group: param || name" in src  # 注册语义锚点


def test_line_limits():
    assert len(read(MAIN).splitlines()) <= 220
    assert len(read(HELPERS).splitlines()) <= 200


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
    assert "透明剔除" in js
    assert "链入口出视口" in js
