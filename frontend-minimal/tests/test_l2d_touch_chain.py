# -*- coding: utf-8 -*-
"""l2d.su 动作链条（TouchChain）stage1：静态断言 + 构建产物验证。"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_touch_module_exists():
    src = read("src/renderer/l2d_touch.ts")
    assert "export class TouchChain" in src


def test_touch_types():
    src = read("src/renderer/l2d_touch.ts")
    for name in (
        "TouchRule",
        "TouchActionTrigger",
        "TouchActionTriggerActive",
        "TouchData",
    ):
        assert name in src


def test_resolve_signature():
    src = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        src,
    )


def test_is_action_allowed():
    src = read("src/renderer/l2d_touch.ts")
    assert re.search(r"isActionAllowed\(name: string\): boolean", src)


def test_ata_both_forms():
    src = read("src/renderer/l2d_touch.ts")
    assert "idle_enable" in src
    assert "idle_ignore" in src
    assert "typeof ata.idle" in src  # 形态B 的 idle 数字分支


def test_persistence():
    src = read("src/renderer/l2d_touch.ts")
    assert "localStorage" in src
    assert "cooldowns" in src
    assert "limitTime" in src


def test_l2d_caches_full_rule():
    l2d = read("src/renderer/l2d.ts")
    assert "rule: TouchRule" in l2d
    assert "./l2d_touch" in l2d


def test_l2d_emits_rule_not_rulegroup():
    l2d = read("src/renderer/l2d.ts")
    assert re.search(r"rule: TouchRule \| null", l2d)
    assert "ruleGroup" not in l2d


def test_main_uses_touch_chain():
    main = read("src/main.ts")
    assert "new TouchChain(" in main
    assert "touchChain.resolve(" in main


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
    assert "l2d-touch:" in js  # 存储键前缀，字符串字面量抗压缩，证明链被实际打包
