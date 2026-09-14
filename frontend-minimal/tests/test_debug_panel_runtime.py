# -*- coding: utf-8 -*-
"""运行时行为测试编排：tsc 编译面板模块到 tests/__tsout__ → node --test 执行附录 A 用例。
输出目录放在 frontend-minimal 包内（package.json type=module），编译产物才是 ESM。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
OUT = FM / "tests" / "__tsout__"


def run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True)


def test_runtime_behavior():
    compile_cmd = (
        f'node "{FM / "node_modules/typescript/bin/tsc"}" '
        f'"{FM / "src/renderer/l2d_debug_panel.ts"}" '
        f'--outDir "{OUT}" --rootDir "{FM / "src/renderer"}" '
        f"--module es2020 --target es2020 --skipLibCheck"
    )
    r = run(compile_cmd)
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "")[-1500:])
        sys.stderr.write((r.stderr or "")[-1500:])
    assert r.returncode == 0, "tsc 编译失败"

    js = OUT / "l2d_debug_panel.js"
    assert js.exists(), f"编译产物缺失：{js}"

    r2 = run(f'node --test "{FM / "tests/debug_panel_runtime.test.mjs"}"')
    if r2.returncode != 0:
        sys.stderr.write((r2.stdout or "")[-3000:])
        sys.stderr.write((r2.stderr or "")[-3000:])
    assert r2.returncode == 0, "node --test 运行时用例失败"
