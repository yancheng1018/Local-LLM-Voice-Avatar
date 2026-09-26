# -*- coding: utf-8 -*-
"""触摸热区可视化开关：静态断言（子串/正则）+ 构建产物验证。"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_button_in_status_bar():
    html = read("index.html")
    assert 'id="touch-debug-btn"' in html
    assert "热区：关" in html


def test_ui_wiring():
    ui = read("src/ui.ts")
    assert "onToggleTouchDebug" in ui
    assert "setTouchDebugEnabled" in ui
    assert "touch-debug-btn" in ui


def test_renderer_interface_optional():
    types = read("src/renderer/types.ts")
    assert re.search(r"setTouchDebug\?\(enabled: boolean\): void", types)


def test_l2d_and_overlay_module():
    l2d = read("src/renderer/l2d.ts")
    overlay = read("src/renderer/l2d_touch_debug.ts")
    assert "TouchDebugOverlay" in l2d
    assert "TouchDebugOverlay" in overlay
    assert re.search(r"setTouchDebug\(enabled: boolean\): void", l2d)
    assert "'none'" in overlay


def test_main_state_reapply():
    main = read("src/main.ts")
    assert "ui.onToggleTouchDebug" in main
    assert "setTouchDebug?.(" in main
    assert "touchDebugOn" in main


def test_css_selector():
    css = read("src/style.css")
    assert "#touch-debug-btn" in css


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
    html = (FM / "dist" / "index.html").read_text(encoding="utf-8")
    assert "touch-debug-btn" in html
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "热区：开" in js
