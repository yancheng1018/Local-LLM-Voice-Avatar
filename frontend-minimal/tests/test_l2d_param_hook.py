# -*- coding: utf-8 -*-
"""动作链条修正 §5.1：参数引擎挂点静态断言 + 写入生效性运行时对拍。

挂点语义见 temp_spec_live2d动作链条修正.md §2：ParamDriver 必须挂在
afterMotionUpdate（动作曲线之后、saveParameters 快照之前），否则帧末
loadParameters() 用快照还原，touch 参数恒 0（研究报告 §5.0）。
"""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"
ESBUILD = FM / "node_modules" / "esbuild" / "bin" / "esbuild"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def _body(src: str, sig: str, nxt: str) -> str:
    """截取 sig 到 nxt 之间的方法体（锚点以函数名定位，行号漂移不影响）。"""
    return src.split(sig, 1)[1].split(nxt, 1)[0]


def test_hook_event_constant_and_usage():
    src = read("src/renderer/l2d.ts")
    assert "const PARAM_DRIVE_EVENT = 'afterMotionUpdate';" in src
    attach = _body(
        src,
        "private attachParamDriver(): void {",
        "private detachParamDriver(): void {",
    )
    assert "im.on(PARAM_DRIVE_EVENT, this.paramHandler);" in attach
    detach = _body(
        src, "private detachParamDriver(): void {", "private layout(): void {"
    )
    assert "?.off?.(PARAM_DRIVE_EVENT, this.paramHandler);" in detach


def test_lipsync_hook_unchanged():
    src = read("src/renderer/l2d.ts")
    assert (
        "im.on('beforeModelUpdate', this.lipSyncHandler);" in src
    )  # 口型挂点不随参数迁移


def test_param_driver_write_reaches_core_runtime():
    """update() 每帧把内部值写进 core（挂点迁移后即模型读数）——防未来静默失效。"""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "l2d_params_rt.mjs"
        r = subprocess.run(
            [
                "node",
                str(ESBUILD),
                str(FM / "src" / "renderer" / "l2d_params.ts"),
                "--format=esm",
                f"--outfile={out}",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        driver = Path(tmp) / "drive.mjs"
        driver.write_text(
            f"import {{ ParamDriver }} from {out.as_uri()!r};\n"
            "globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };\n"
            "const writes = [];\n"
            "const core = { setParameterValueById: (id, v) => writes.push([id, v]) };\n"
            "const d = new ParamDriver('t:');\n"
            "d.setRules([{ id: -301, parameter: 'touch_drag3', mode: 1, startValue: 0,\n"
            "  range: [0, 10], circleTarget: 10, revert: -1 }], {}, 'x');\n"
            "d.poke(-301);\n"
            "for (let i = 0; i < 200; i++) d.update(16, core, { x: 0, y: 0 });\n"
            "console.log(JSON.stringify({ count: writes.length, last: writes.at(-1),\n"
            "  value: d.getValue('touch_drag3') }));\n",
            encoding="utf-8",
        )
        r = subprocess.run(["node", str(driver)], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        got = json.loads(r.stdout.strip())
    assert got["count"] > 0, (
        "update() 未向 core 写入任何参数（挂点迁移后模型读数将恒 0）"
    )
    assert got["last"][0] == "touch_drag3"
    assert got["last"][1] >= 9.9, (
        f"200 帧后写入值 {got['last'][1]} 未收敛到 circleTarget 10"
    )
    assert got["last"][1] == got["value"], "写入 core 的值与引擎内部值不一致"
