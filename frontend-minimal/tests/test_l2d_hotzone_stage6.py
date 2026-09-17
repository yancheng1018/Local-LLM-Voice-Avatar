# -*- coding: utf-8 -*-
"""链推进修复（ATA 按 drawAbleName 应用）+ 真实渲染序 + 仪表盘 idleIndex stage6：静态断言 + 构建产物验证。

用例与断言点语义对应 docs/context/spec-l2d-touch-engine.md（stage6 章节，原 temp_spec_stage6.md 已并入；不得增减语义）。
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


def section(src: str, start: str, nxt: str = r"\n  (?:private|get |async |[a-zA-Z]+\()") -> str:
    """截取从 start 标记到下一个方法定义之间的源码段（方法体级断言用）。"""
    m = re.search(re.escape(start), src)
    assert m, f"marker not found: {start}"
    rest = src[m.start() :]
    m2 = re.search(nxt, rest[len(start) :])
    return rest[: len(start) + m2.start()] if m2 else rest


def test_chain_rule_lookup():
    l2d = read("src/renderer/l2d.ts")
    assert re.search(r"findChainRule\(groupName: string\): TouchRule \| null", l2d)
    fn = section(l2d, "findChainRule(")
    assert "replace(/^touch_/, 'Touch')" in fn  # 驼峰化：touch_idle17 → TouchIdle17
    assert "r.parameter === groupName" in fn  # 三字段之一：parameter 匹配
    assert "actionNamesOf(r).includes(groupName)" in fn  # 三字段之一：action 匹配
    main = read("src/main.ts")
    assert "findChainRule(gname)" in main  # main.ts 链步进调用它
    assert "findRuleByParameter" not in main  # 旧查找已替换


def test_touch_rules_kept():
    l2d = read("src/renderer/l2d.ts")
    assert re.search(r"private touchRules: TouchRule\[\] \| null", l2d)  # 原始数组挂 renderer
    load = section(l2d, "private async loadTouchRules(")
    assert "this.touchRules = rules" in load  # loadTouchRules 时全量挂载
    assert "this.touchRules = null" in load  # 加载前重置


def test_real_render_order():
    l2d = read("src/renderer/l2d.ts")
    core = section(l2d, "private touchCore(")
    assert "drawables?:" in core and "renderOrders?: Int32Array" in core  # 原生数组访问类型
    assert "getDrawableRenderOrders?(): Int32Array" in core  # stage1e 实测：真实 API 名（复数无参）
    hit = section(l2d, "private hitZoneAt(")
    assert "drawables?.renderOrders" in hit or re.search(r"renderOrders\?\.\[", hit)
    assert "getDrawableRenderOrders?.()?.[" in hit  # 实测 API 优先
    assert "getDrawableRenderOrder?.(zone.drawIndex) ??" in hit  # 方法优先，数组兜底
    assert "?? 0" in hit  # 终值兜底
    assert "dynamicFlags 位义未逐字核实故不启用" in l2d  # visibility 注释保持 ?? true


def test_idle_readout():
    debug = read("src/renderer/l2d_touch_debug.ts")
    assert "idleIndex=" in debug  # 左上角固定读数渲染
    assert "getChainIdleIndex" in debug  # 数据源 chainIdleIndex 注入
    helpers = read("src/renderer/l2d_touch_debug_helpers.ts")
    assert "blocked:enable" in helpers  # §2.3 白名单拦截标注（r2 迁入 helpers）
    l2d = read("src/renderer/l2d.ts")
    states = section(l2d, "touchZoneStates(): TouchZoneState[] {")
    assert "blockedEnable" in states  # l2d.ts 提供 blocked 状态
    assert "() => this.chainIdleIndex()" in l2d  # 注入链读数回调


def test_regression_core():
    l2d = read("src/renderer/l2d.ts")
    acc = section(l2d, "private accumulateDrag(")
    assert "clientX - this.prevDragPx.x" in acc  # 像素增量（stage5）
    assert "this.prevDragPx.y - clientY" in acc  # y 上正
    dial = section(l2d, "private dialValueFor(")
    assert "Math.atan2(" in dial and "* 180) / Math.PI" in dial  # 转盘 atan2
    params = read("src/renderer/l2d_params.ts")
    assert re.search(
        r"Math\.abs\(st\.value - r\.circleTarget\) < POKE_EPSILON \? r\.startValue : r\.circleTarget",
        params,
    )  # poke 翻转停留
    assert "setIsLoop(false)" not in l2d  # Meta.Loop 单次化废止（research2 §3.3 方案A）
    load = section(l2d, "private async loadTouchRules(")
    assert "group: param || name" in load  # 空参数区注册
    assert "ataIdle === this.chainIdleIndex()" in l2d  # ATA.idle 防重复（r4 §4.3 方向翻转）
    touch = read("src/renderer/l2d_touch.ts")
    assert re.search(
        r"resolve\(rule: TouchRule,\s*kind: 'tap' \| 'drag' \| 'longpress',\s*available: string\[\]\): string \| null",
        touch,
    )  # TouchChain 签名
    assert "l2d-touch:" in read("src/main.ts")  # 存储键字面量
    assert "PARAM_STORAGE_PREFIX = 'l2d-param:'" in params  # 构建字面量
    t = json.loads((ROOT / "live2d-models/xinnong_6/touch.json").read_text(encoding="utf-8"))
    assert {r.get("shipSkinId") for r in t["rules"]} == {307085}  # xinnong 皮肤 id


def test_empty_enable_no_whitelist():
    """stage1e 实测修正（用户批准）：ATA.enable=[] 应为「无白名单放行」（站点 deob 同款），
    不得建空白名单拦截一切动作；形态 A/B 语义对齐。"""
    touch = read("src/renderer/l2d_touch.ts")
    assert "Array.isArray(ata.enable)" in touch
    assert "ata.enable.length ? new Set(ata.enable) : null" in touch
    assert "if (ata.enable) this.enable" not in touch  # 旧空白名单分支已删


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
    assert "blocked:enable" in js  # 新标注字面量已打包
    assert "l2d-touch:" in js  # 链存储键不回退
