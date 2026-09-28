# -*- coding: utf-8 -*-
"""live2d动作链条修正2 §7：关系预设层（type103 链步查表 / type104 idle 预设）+ ParamDriver 链同步。

静态锚点 + esbuild→node 运行时向量（规格书 §7 用例表；语义依据 spec-l2dsu-engine.md §4.4）。
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


def module_run(src_rel: str, body: str):
    """esbuild --bundle 编译渲染器模块 → node（stub localStorage 后执行 body），返回 OUT。"""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "rt.mjs"
        r = subprocess.run(
            [
                "node",
                str(ESBUILD),
                str(FM / "src" / "renderer" / src_rel),
                "--bundle",
                "--format=esm",
                f"--outfile={out}",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        code = (
            f"import * as m from {out.as_uri()!r};"
            "const store = new Map();"
            "globalThis.localStorage = {"
            "getItem:(k)=>(store.has(k)?store.get(k):null),"
            "setItem:(k,v)=>store.set(k,String(v)),"
            "removeItem:(k)=>store.delete(k)};"
            f"const OUT = (() => {{ {body} }})();"
            "console.log(JSON.stringify(OUT))"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout or "")[-500:] + (r.stderr or "")[-2000:]
        return json.loads(r.stdout.strip())


def test_relations_module_exists():
    src = read("src/renderer/l2d_params_relations.ts")
    for s in (
        "export function relationWrites",
        "export function revertingOnIdle",
        "export function toRelationPresets",
        "RELATION_STEP_TYPE = 103",
        "RELATION_IDLE_TYPE = 104",
    ):
        assert s in src


def test_relation_writes_runtime():
    body = (
        "const idle2 = {id:49902204, startValue:0, relations:["
        "{type:104, idle:2, name:'touch_drag15', target:0},"
        "{type:104, idle:2, name:'touch_drag16', target:1},"
        "{type:104, idle:2, name:'touch_drag17', target:1},"
        "{type:104, idle:2, name:'touch_drag18', target:0}]};"
        "const idle5 = {id:4234206, startValue:0, relations:["
        "{type:104, idle:5, name:'touch_drag15', target:0},"
        "{type:104, idle:5, name:'touch_drag16', target:1},"
        "{type:104, idle:5, name:'touch_drag17', target:0},"
        "{type:104, idle:5, name:'touch_drag18', target:1}]};"
        "const step = {id:1, startValue:0, relations:"
        "[{type:103, name:'touch_drag1', relation_value:[0,2.5,5,7,10,7,5,2.5]}]};"
        "return ["
        "m.relationWrites([idle2], 2, () => 0).map((w) => [w.name, w.value]),"
        "m.relationWrites([idle2], 5, () => 0),"
        "m.relationWrites([idle5], 5, () => 0).map((w) => [w.name, w.value]),"
        "m.relationWrites([step], 0, () => 2).map((w) => [w.name, w.value]),"
        "m.relationWrites([step], 0, () => 99).map((w) => [w.name, w.value])]"
    )
    got = module_run("l2d_params_relations.ts", body)
    # ① feiteliedadi_3 49902204 向量：idle=2 命中、idle=5 无输出
    assert got[0] == [
        ["touch_drag15", 0],
        ["touch_drag16", 1],
        ["touch_drag17", 1],
        ["touch_drag18", 0],
    ]
    assert got[1] == []
    # ② 4234206 型 idle=5 组
    assert got[2] == [
        ["touch_drag15", 0],
        ["touch_drag16", 1],
        ["touch_drag17", 0],
        ["touch_drag18", 1],
    ]
    # ③ type103 链步查表（guandao_3 真实向量）：步 2 → 表[2]=5；步 99 → clamp 表末 2.5
    assert got[3] == [["touch_drag1", 5]]
    assert got[4] == [["touch_drag1", 2.5]]


def test_reverting_on_idle_runtime():
    body = (
        "const a = {id:1, startValue:0, revertOnIdle:true};"
        "const b = {id:2, startValue:0};"
        "return ["
        "m.revertingOnIdle([a, b], 1, 2).map((r) => r.id),"
        "m.revertingOnIdle([a, b], 2, 2).length,"
        "m.revertingOnIdle([b], 1, 2).length]"
    )
    assert module_run("l2d_params_relations.ts", body) == [[1], 0, 0]


def test_to_relation_presets_filters():
    body = (
        "const mixed = m.toRelationPresets({relationParameter:{list:["
        "{type:101, name:'a'}, {type:102, name:'b'},"
        "{type:103, name:'c', relation_value:[0,1]}, {type:104, idle:2, name:'d', target:1}]}});"
        "const only101 = m.toRelationPresets({relationParameter:{list:[{type:101, name:'a'}]}});"
        "return [mixed.map((r) => r.type), only101,"
        "m.toRelationPresets({}), m.toRelationPresets({relationParameter:{}})]"
    )
    # 仅 103/104 保留；仅 101/102 → undefined（mojiaduoer_4 TouchDrag31 行为不变）
    assert module_run("l2d_params_relations.ts", body) == [[103, 104], None, None, None]


def test_driver_sync_and_presets_runtime():
    body = (
        "const writes = [];"
        "const core = {setParameterValueById:(n, v) => writes.push([n, v])};"
        "const d = new m.ParamDriver('l2d-param:');"
        "d.setRules(["
        "{id:-301, parameter:'touch_drag3', mode:1, startValue:0, range:[0,10],"
        "circleTarget:10, revert:-1, revertOnIdle:true},"
        "{id:-302, parameter:'empty', mode:1, startValue:0, range:[0,1], carrier:true,"
        "relations:[{type:104, idle:2, name:'touch_drag16', target:1}]}], {}, 'scope');"
        "d.poke(-301);"
        "for (let i = 0; i < 200; i++) d.update(16, core, {x:0, y:0});"
        "const t3 = writes.filter((w) => w[0] === 'touch_drag3');"
        "const lastHigh = t3[t3.length - 1][1];"
        "d.syncChainState(0, () => 0);"
        "d.syncChainState(1, () => 0);"
        "d.update(16, core, {x:0, y:0});"
        "d.save();"
        "d.update(16, core, {x:0, y:0});"
        "const t3After = writes.filter((w) => w[0] === 'touch_drag3');"
        "const persisted = JSON.parse(localStorage.getItem('l2d-param:scope'))['-301'];"
        "d.syncChainState(2, () => 0);"
        "d.update(16, core, {x:0, y:0});"
        "const has16 = writes.some((w) => w[0] === 'touch_drag16' && w[1] === 1);"
        "const hasEmpty = writes.some((w) => w[0] === 'empty');"
        "return [lastHigh, t3After[t3After.length - 1][1], persisted, has16, hasEmpty]"
    )
    got = module_run("l2d_params.ts", body)
    # ① poke 转盘收敛 ≥9.9；② idle 变化复位落地 + 持久化同步为 0
    assert got[0] >= 9.9
    assert got[1] == 0
    assert got[2] == 0
    # ③ type104 预设覆写生效；carrier 规则全程不写自身参数 'empty'
    assert got[3] is True
    assert got[4] is False


def test_l2d_capture_wiring():
    l2d = read("src/renderer/l2d.ts")
    assert "toRelationPresets(rule)" in l2d
    assert "rule.revertIdleIndex === 1 || rule.revertIdleIndex === '1'" in l2d
    assert "carrier: true" in l2d
    assert "syncChainState(this.chainIdleIndex(), this.chainStepIndex)" in l2d
    assert "chainStepIndex: (ruleId: number) => number = () => 0;" in l2d
    assert "touchChain.stepIndex(rid)" in read("src/main.ts")
