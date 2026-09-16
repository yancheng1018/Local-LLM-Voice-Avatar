# -*- coding: utf-8 -*-
"""r4 §7.2-5：clampChain 运行时数值断言（站点 fixLive2DParameterTargetValue 三步链一致）。

esbuild 编译 l2d_params.ts → node 导入执行 clampChain → 与站点原文复刻实现对拍。
参考实现 = 站点反混淆原文（r4 §3.1c）：dragDirect 门控 → rangeAbs → range 钳幅。
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
ESBUILD = FM / "node_modules" / "esbuild" / "bin" / "esbuild"


def site_fix(value, dd, rabs, rng):
    """站点原文逐字复刻（r4 §3.1c），期望值来源。"""
    v = value
    if (v < 0 and dd == 1) or (v > 0 and dd == 2):
        v = 0
    if rabs == 1:
        v = abs(v)
    return min(rng[1], max(rng[0], v))


CASES = [
    (-12, 1, 1, [0, 30], "wuqi_3 TouchDrag6 上拖（症状②：v3 得 12，站点 0）"),
    (12, 1, 1, [0, 30], "wuqi_3 TouchDrag6 下拖"),
    (-6, 1, 1, [0, 30], "guanghui_9 TouchDrag5 上拖"),
    (2, 1, 1, [0, 10], "feiteliekaer_4 TouchDrag8 左拖（同号不触发门控）"),
    (-5, 2, 0, [-30, 30], "dd=2 门控正增量归零"),
    (5, 1, 0, [-30, 30], "dd=1 不拦正增量"),
    (-5, 1, 0, [-30, 30], "无 rangeAbs 保号（全库 range 跨零为 0 条，防御性）"),
    (40, 0, 1, [0, 30], "abs 后钳上限"),
    (-40, 0, 1, [0, 30], "负大值 abs 后钳上限"),
]


def test_clamp_chain_site_parity_runtime():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "l2d_params_rt.mjs"
        r = subprocess.run(
            ["node", str(ESBUILD), str(FM / "src" / "renderer" / "l2d_params.ts"),
             "--format=esm", f"--outfile={out}"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        vectors = ",".join(
            f"clampChain({v},{{range:{rng},rangeAbs:{rabs},dragDirect:{dd}}})"
            for v, dd, rabs, rng, _ in CASES
        )
        code = (
            f"import {{ clampChain }} from {out.as_uri()!r};"
            f"console.log(JSON.stringify([{vectors}]))"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        got = json.loads(r.stdout.strip())
        assert len(got) == len(CASES)
        for (v, dd, rabs, rng, why), g in zip(CASES, got):
            expect = site_fix(v, dd, rabs, rng)
            assert g == expect, (
                f"{why}: clampChain({v}, dd={dd}, rabs={rabs}, range={rng}) = {g}，站点期望 {expect}"
            )
