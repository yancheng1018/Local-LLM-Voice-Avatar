# -*- coding: utf-8 -*-
"""Live2D circle 转盘手势 + 热区可见性稳定化 + 信浓入列 stage4：静态断言 + 构建产物验证。

用例与断言点语义对应 docs/context/spec-l2d-touch-engine.md（stage4 章节，原 temp_spec_stage4.md 已并入；不得增减语义）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_circle_dial_formula():
    src = read("src/renderer/l2d.ts")
    assert "Math.atan2(" in src  # 转盘角度公式
    assert re.search(r"\* 180\) / Math\.PI", src)
    assert re.search(r"% 360", src)
    assert "rangeMax" in src  # range[1] 全量程映射
    assert "dialValueFor" in src


def test_circle_no_time_approach():
    src = read("src/renderer/l2d_params.ts")
    # 旧 hold「向 circleTarget 时间趋近 + 到位翻转」逻辑已删
    assert "st.pokeTarget === r.circleTarget ? r.startValue : r.circleTarget" not in src
    # poke 单击路径保留（翻转比较分支仍在）
    assert re.search(
        r"Math\.abs\(st\.value - r\.circleTarget\) < POKE_EPSILON \? r\.startValue : r\.circleTarget",
        src,
    )


def test_hold_value_api():
    params = read("src/renderer/l2d_params.ts")
    assert "setHoldValue(id: number, value: number): void" in params
    assert re.search(r"st\.holdValue - st\.value", params)  # hold 中使用转盘值
    l2d = read("src/renderer/l2d.ts")
    assert "setHoldValue(" in l2d  # l2d.ts 每帧下传


def test_opacity_cull_restored():
    src = read("src/renderer/l2d.ts")
    # r2 收回 D1：命中路径恢复透明度剔除（站点同款）；叠加层 T 判定同源阈值
    assert re.search(r"<= OPACITY_CUTOFF\) continue", src)
    assert re.search(r"<= OPACITY_CUTOFF\) return", src)


def test_overlay_T_not_interactive():
    src = read("src/renderer/l2d_touch_debug.ts")
    assert "透明剔除" in src  # r2：T=透明剔除，不再「可点」
    assert "透明但可点" not in src
    assert re.search(r"const interactive = a\.status === 'ok';", src)  # 仅 ok 填充


def test_xinnong_data():
    t = json.loads((ROOT / "live2d-models/xinnong_6/touch.json").read_text(encoding="utf-8"))
    assert {r.get("shipSkinId") for r in t["rules"]} == {307085}


def test_regression_core():
    params = read("src/renderer/l2d_params.ts")
    assert re.search(r"Math\.abs\(xv\) >= Math\.abs\(yv\) \? xv : yv", params)  # slide 轴选择
    touch = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        touch,
    )
    l2d = read("src/renderer/l2d.ts")
    for s in ("playAction", "playIdleOnce", "OE_TYPES", "ataIdle === this.chainIdleIndex()"):
        assert s in l2d
    assert "PARAM_STORAGE_PREFIX = 'l2d-param:'" in params
    assert "l2d-touch:" in read("src/main.ts")


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
    assert "l2d-param:" in js
    assert "l2d-touch:" in js
