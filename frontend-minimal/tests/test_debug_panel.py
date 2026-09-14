# -*- coding: utf-8 -*-
"""仿 l2d.su 左侧调试栏：L1 静态接线（精确正则）+ L3 构建产物断言。
运行时行为（L2）在 test_debug_panel_runtime.py。"""
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
    assert 'id="debug-panel-btn"' in html
    assert "调试栏：关" in html


def test_ui_wiring():
    ui = read("src/ui.ts")
    assert re.search(r"debug-panel-btn'\) as HTMLButtonElement", ui)
    assert re.search(r"onToggleDebugPanel\?\.\(debugPanelBtn", ui)


def test_main_handler_block():
    main = read("src/main.ts")
    assert re.search(
        r"ui\.onToggleDebugPanel = \(on\) => \{[^}]*renderer\.setDebugPanel\?\.\(on\)", main
    )
    assert re.search(r"renderer\.setDebugPanel\?\.\(debugPanelOn\)", main)


def test_l2d_method():
    l2d = read("src/renderer/l2d.ts")
    assert re.search(r"new DebugPanel\(this\.container, \(\) => this\.model\)", l2d)
    assert re.search(r"this\.debugPanel\?\.onModelChanged\(\)", l2d)


def test_renderer_interface_optional():
    types = read("src/renderer/types.ts")
    assert re.search(r"setDebugPanel\?\(enabled: boolean\): void", types)


def test_id_path_fixed():
    panel = read("src/renderer/l2d_debug_panel.ts")
    assert "getModel?.()[field]?.ids" in panel
    assert "DebugCoreSource" in panel
    # 两种旧路径全根除：.model 访问器不存在；parameterIds / partIds 非公开属性
    assert not re.search(r"\.model\?\.", panel)
    assert "parameterIds" not in panel
    assert "partIds" not in panel


def test_library_cross_check():
    dts = (
        FM / "node_modules" / "pixi-live2d-display" / "types" / "index.d.ts"
    ).read_text(encoding="utf-8")
    assert "parameters: Parameters;" in dts
    assert "parts: Parts;" in dts
    assert "private _parameterIds;" in dts
    assert "getModel(): Live2DCubismCore.Model;" in dts
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "getModel().canvasinfo" in js


def test_css_source_and_dist():
    assert "#debug-panel" in read("src/style.css")
    css = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.css")
    )
    assert "#debug-panel" in css


def test_module_line_limit():
    assert read("src/renderer/l2d_debug_panel.ts").count("\n") <= 200


def test_types_module_split():
    types = read("src/renderer/l2d_debug_panel_types.ts")
    panel = read("src/renderer/l2d_debug_panel.ts")
    for name in (
        "export interface DebugCoreModel",
        "export interface DebugPanelModel",
        "export interface Row",
    ):
        assert name in types
    assert "from './l2d_debug_panel_types'" in panel
    assert "export type { DebugCoreModel, DebugPanelModel } from './l2d_debug_panel_types'" in panel


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
    assert "debug-panel-btn" in html
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "调试栏：开" in js
    # 库自身消费核心结构的路径进产物（本次根因的正确路径）
    assert ".parts.ids" in js
    assert ".parameters.ids" in js
