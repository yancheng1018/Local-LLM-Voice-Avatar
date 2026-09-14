# -*- coding: utf-8 -*-
"""Live2D 一键复位：静态契约（子串/正则/序列顺序）+ 构建产物验证。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_reset_button_markup():
    html = read("index.html")
    assert 'id="reset-model-btn"' in html
    assert "↺ 复位模型" in html
    assert "初始待机动作" in html


def test_ui_reset_wiring():
    ui = read("src/ui.ts")
    for frag in (
        "onResetModel",
        "reset-model-btn",
        "setResetStatus",
        "模型已复位",
        "当前模型不支持复位",
    ):
        assert frag in ui, frag


def test_renderer_interface_optional():
    types = read("src/renderer/types.ts")
    assert re.search(r"resetToInitialMotion\?\(\): void", types)
    assert re.search(r"resetExpression\(\): void", types)


def test_l2d_reset_sequence():
    l2d = read("src/renderer/l2d.ts")
    m = re.search(r"resetToInitialMotion\(\): void \{(?P<body>[\s\S]*?)\n  \}", l2d)
    assert m, "resetToInitialMotion body not found"
    body = m.group("body")
    # 复位序列：先停 motion，再清播放门控与表情，再清链（失败不阻断），最后回初始 idle
    # 用调用形态匹配，避免命中方法内 motionManager 类型字面量里的 stopAllMotions
    frags = (
        "stopAllMotions?.()",
        "this.touchPlay = { active: false, ruleId: null }",
        "this.resetExpression()",
        "this.resetTouchChain?.()",
        "this.playIdleOnce()",
    )
    idx = [body.index(f) for f in frags]
    assert idx == sorted(idx), idx
    assert re.search(r"^\s*resetTouchChain: \(\(\) => void\) \| null = null;", l2d, re.M)


def test_main_resets_chain_and_audio_only():
    main = read("src/main.ts")
    assert "activeRenderer.resetTouchChain = () => touchChain.reset()" in main
    m = re.search(r"ui\.onResetModel = \(\) => \{(?P<body>[\s\S]*?)\n\};", main)
    assert m, "ui.onResetModel block not found"
    body = m.group("body")
    for frag in ("audioQueue.interrupt()", "renderer.resetToInitialMotion()", "ui.setResetStatus(true)"):
        assert frag in body, frag
    assert "interrupt-signal" not in body
    assert "ws.send" not in body


def test_css_uses_existing_button_style():
    css = read("src/style.css")
    assert re.search(r"#debug-panel-btn,\s*\n#reset-model-btn,", css)
    assert re.search(r"#debug-panel-btn:hover,\s*\n#reset-model-btn:hover,", css)


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
    assert "reset-model-btn" in html
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "模型已复位" in js
    css = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.css")
    )
    assert "#reset-model-btn" in css
