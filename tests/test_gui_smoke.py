"""GUI 冒烟守卫：用 .venv-gui 的解释器离屏实例化启动器主窗口。

批 b 实踩回归（CharEntry 删 avatar 字段漏改 5 参调用点，静态三件套
rg/ast/ruff 均不可见，只有实例化能暴露）。主 venv 无 PySide6，无法进程内
import launcher，故以子进程调 .venv-gui 解释器执行；.venv-gui 缺失
（换机/新克隆未建）时 skip 并附重建指引——skip 非静默，理由可检索。
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUI_PYTHON = REPO_ROOT / ".venv-gui" / "Scripts" / "python.exe"

SNIPPET = """
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "launcher")
from PySide6.QtWidgets import QApplication
import OpenLLMVTuber_GUI as gui
app = QApplication.instance() or QApplication([])
win = gui.LauncherWindow()
print(f"GUI_SMOKE_OK entries={win.combo_character.count()}")
"""


def test_launcher_window_constructs_offscreen():
    """启动器主窗口必须能离屏构造完成（角色下拉含基础配置项）。"""
    if not GUI_PYTHON.is_file():
        pytest.skip(
            ".venv-gui 不存在，GUI 冒烟无法运行；"
            "重建：uv venv .venv-gui --seed 后安装 PySide6-Essentials ruamel.yaml psutil"
        )
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [str(GUI_PYTHON), "-c", SNIPPET],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert result.returncode == 0, (
        f"启动器离屏实例化失败：\n{(result.stderr or result.stdout)[-800:]}"
    )
    assert "GUI_SMOKE_OK" in result.stdout, f"冒烟标记缺失：{result.stdout[-300:]}"
