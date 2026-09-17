# -*- coding: utf-8 -*-
"""live2d动作链条修正2 §7：TouchChain 链步状态机（action_list 循环步进 + ATA 覆盖 + 形态A 目标 idle）。

静态锚点 + esbuild→node 运行时向量（规格书 §7 用例表；语义依据 spec-l2dsu-engine-v2.md §3.1/§3.2）。
"""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
ESBUILD = FM / "node_modules" / "esbuild" / "bin" / "esbuild"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def chain_run(setup: str):
    """esbuild 编译 l2d_touch.ts → node（stub localStorage 后执行 setup），返回 OUT。"""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "l2d_touch_rt.mjs"
        r = subprocess.run(
            [
                "node",
                str(ESBUILD),
                str(FM / "src" / "renderer" / "l2d_touch.ts"),
                "--format=esm",
                f"--outfile={out}",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        code = (
            f"import {{ TouchChain }} from {out.as_uri()!r};"
            "const store = new Map();"
            "globalThis.localStorage = {"
            "getItem:(k)=>(store.has(k)?store.get(k):null),"
            "setItem:(k,v)=>store.set(k,String(v)),"
            "removeItem:(k)=>store.delete(k)};"
            f"const OUT = (() => {{ {setup} }})();"
            "console.log(JSON.stringify(OUT))"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        return json.loads(r.stdout.strip())


def test_step_index_api():
    src = read("src/renderer/l2d_touch.ts")
    assert "stepIndex(ruleId: number): number" in src
    assert "actionListIndices" in src
    assert "(this.stepIndex(id) + 1) % steps.length" in src
    assert "active_list?: TouchActionTriggerActive[]" in src


def test_steps_persisted():
    src = read("src/renderer/l2d_touch.ts")
    assert "steps: Object.fromEntries(this.actionListIndices)" in src
    assert "s.steps" in src
    assert "actionListIndices.clear()" in src


def test_form_a_uses_target_idle_static():
    src = read("src/renderer/l2d_touch.ts")
    assert "idleNew ?? this.idleIndex" in src  # 形态A 查表用目标 idle
    assert "idle_enable" in src  # §3.6 语义随迁后必须保留的锚点
    assert "idle_ignore" in src
    assert "typeof ata.idle" in src


def test_step_cycle_runtime():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "const rule = {id:601, actionTrigger:{type:3, action_list:"
        "[{action:'touch_drag1'},{action:'touch_drag2'}]}};"
        "const a1 = chain.resolve(rule, 'tap', ['touch_drag1','touch_drag2']);"
        "const s1 = chain.stepIndex(601);"
        "const a2 = chain.resolve(rule, 'tap', ['touch_drag1','touch_drag2']);"
        "const s2 = chain.stepIndex(601);"
        "const steps = JSON.parse(localStorage.getItem('l2d-touch:t')).steps;"
        "return [a1, s1, a2, s2, steps['601']]"
    )
    # 触发 → 播 step 0 动作并步进到 1；再触发 → step 1 动作并循环回 0；steps 持久化
    assert chain_run(setup) == ["touch_drag1", 1, "touch_drag2", 0, 0]


def test_step_action_fallback_and_precedence_runtime():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "const A = {id:611, actionTrigger:{type:3, action_list:"
        "[{action:'step_a'},{action:'step_b'}]}};"
        "const B = {id:612, actionTrigger:{type:3, action:'x', action_list:[{action:'y'}]}};"
        "return ["
        "chain.resolve(A, 'tap', ['step_a','step_b']),"
        "chain.resolve(B, 'tap', ['x','y'])]"
    )
    # A：无 at.action 带链表 → step.action（7 条死区激活路径）；B：at.action 优先于 step.action
    assert chain_run(setup) == ["step_a", "x"]


def test_active_list_override_runtime():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "const rule = {id:602, actionTrigger:{type:2, action:'zz', action_list:[{},{}]},"
        "actionTriggerActive:{idle:0, active_list:[{idle:7}]}};"
        "const r1 = chain.resolve(rule, 'tap', ['zz']);"
        "const c1 = chain.currentIndex;"
        "const r2 = chain.resolve(rule, 'tap', ['zz']);"
        "const c2 = chain.currentIndex;"
        "return [r1, c1, r2, c2]"
    )
    # 第 1 步 active_list[0] 覆盖 → idle 7；第 2 步表项缺位（undefined）→ ?? 回落整条 ata → idle 0
    assert chain_run(setup) == ["zz", 7, "zz", 0]


def test_form_a_target_idle_runtime():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "const rule = {id:603, actionTrigger:{type:2, action:'zz'},"
        "actionTriggerActive:{idle:5, idle_enable:[[5,['aa']]]}};"
        "const r = chain.resolve(rule, 'tap', ['zz']);"
        "return [r, chain.currentIndex, chain.isActionAllowed('aa'), chain.isActionAllowed('bb')]"
    )
    # 形态A 用推进后的目标 idle=5 查表（非查触发前旧值）
    assert chain_run(setup) == ["zz", 5, True, False]
