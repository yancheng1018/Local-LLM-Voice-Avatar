# -*- coding: utf-8 -*-
"""live2d动作链条-research2 §3/§7：type12 全局动作裁决 + TouchChain paramGate 组合闸。

静态锚点 + esbuild→node 运行时向量（语义依据 spec-l2dsu-engine-v2.md §3.2、
research_live2d动作链条-research2.md §3.1；契约候选 R2-a/R2-b）。
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"
ESBUILD = FM / "node_modules" / "esbuild" / "bin" / "esbuild"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def section(src: str, start: str, nxt: str = r"\n  (?:private|get |async |[a-zA-Z]+\()") -> str:
    """截取从 start 标记到下一个方法定义之间的源码段（方法体级断言用）。"""
    m = re.search(re.escape(start), src)
    assert m, f"marker not found: {start}"
    rest = src[m.start():]
    m2 = re.search(nxt, rest[len(start):])
    return rest[: len(start) + m2.start()] if m2 else rest


def touch_run(setup: str):
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
            f"import {{ TouchChain, type12Decision }} from {out.as_uri()!r};"
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


RULE12 = (
    "const R12 = {id:701, actionTrigger:{type:12, num:[0.01,10], parameter:'touch_drag3'},"
    "actionTriggerActive:{ignore:['touch_head','touch_body']}};"
)


def test_trigger_parameter_field_static():
    src = read("src/renderer/l2d_touch.ts")
    m = re.search(r"export interface TouchActionTrigger \{[^}]+\}", src)
    assert m, "TouchActionTrigger 接口缺失"
    assert re.search(r"parameter\?: string;", m.group(0))


def test_type12_decision_pure():
    setup = (
        RULE12
        + "const rules = [R12];"
        "const f = (v) => () => v;"
        "return ["
        "type12Decision(rules, 'touch_head', f(5)),"
        "type12Decision(rules, 'touch_body', f(5)),"
        "type12Decision(rules, 'other', f(5)),"
        "type12Decision(rules, 'touch_head', f(0)),"
        "type12Decision(rules, 'touch_head', f(undefined))]"
    )
    # 区间命中且 ignore 含 → false；ignore 外 → undefined；区间外/无值 → undefined
    assert touch_run(setup) == [False, False, None, None, None]


def test_type12_half_open():
    setup = (
        RULE12
        + "const rules = [R12];"
        "return ["
        "type12Decision(rules, 'touch_head', () => 0.01),"
        "type12Decision(rules, 'touch_head', () => 10)]"
    )
    # 半开区间 lo<v<=hi：0.01 不命中（严格大于），10 命中
    assert touch_run(setup) == [None, False]


def test_type12_enable_override():
    setup = (
        "const R = {id:702, actionTrigger:{type:12, num:[0.01,10], parameter:'p'},"
        "actionTriggerActive:{enable:['touch_head']}};"
        "return type12Decision([R], 'touch_head', () => 5)"
    )
    assert touch_run(setup) is True


def test_chain_param_gate_reject():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "chain.paramGate = () => false;"
        "const rule = {id:711, actionTrigger:{type:2, action:'zz'}};"
        "return chain.resolve(rule, 'tap', ['zz'])"
    )
    # type12 拒优先于全局放行 → null（不播、不推进链状态）
    assert touch_run(setup) is None


def test_chain_param_gate_short_circuit():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "chain.paramGate = () => true;"
        "const rule = {id:712, actionTrigger:{type:2, action:'zz'},"
        "actionTriggerActive:{ignore:['zz']}};"
        "return chain.resolve(rule, 'tap', ['zz'])"
    )
    # ext=true 短路全局名单（站点扩展判定返回布尔即 return，v2 spec §3.2）
    assert touch_run(setup) == "zz"


def test_chain_param_gate_unset():
    setup = (
        "const chain = new TouchChain('l2d-touch:t');"
        "const rule = {id:713, actionTrigger:{type:2, action:'zz'},"
        "actionTriggerActive:{ignore:['zz']}};"
        "const first = chain.resolve(rule, 'tap', ['zz']);"
        "const second = chain.resolve(rule, 'tap', ['zz']);"
        "return [first, second]"
    )
    # 未注入 paramGate = 无 type12 约束：全局名单行为不回归（r4 §10.4.4：ATA 在触发后
    # 应用——首次播、次次被自身 ignore 拦）
    assert touch_run(setup) == ["zz", None]


def test_type12_wiring_static():
    l2d = read("src/renderer/l2d.ts")
    assert "type12Decision" in l2d
    assert "getParameterValueById" in l2d
    assert "actionAllowedWithParamGate" in l2d
    inter = section(l2d, "private isRuleInteractive(")
    assert "this.actionAllowed(" not in inter  # 命中门槛走组合闸（type12 优先）
    assert "actionAllowedWithParamGate" in inter
    states = section(l2d, "touchZoneStates(): TouchZoneState[] {")
    assert "this.actionAllowed(" not in states  # blockedEnable 同样走组合闸
    assert "actionAllowedWithParamGate" in states
    main_src = read("src/main.ts")
    assert "touchChain.paramGate = " in main_src
    head = section(main_src, "param === 'touchhead'")
    assert "const canonical = param === 'touchhead' ? 'touch_head' : 'touch_special';" in head
    assert "actionAllowedWithParamGate(canonical)" in head  # 默认区过闸（规格 §3.3b 伪代码）
    body = section(main_src, "param === 'touchbody'")
    assert "actionAllowedWithParamGate('touch_body')" in body
    fallback = section(main_src, "const chainRule = activeRenderer.findChainRule(gname)")
    assert "actionAllowedWithParamGate(gname)" in fallback  # 直播兜底不过闸=绕过名单，禁止
