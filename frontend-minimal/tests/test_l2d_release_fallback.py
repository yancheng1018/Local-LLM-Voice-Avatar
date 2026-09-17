# -*- coding: utf-8 -*-
"""live2d动作链条-research3：tap 抬起命中回退（修复 drag3 卡中值三连锁）。

静态断言（temp_spec_live2d动作链条-research3.md §4，参照 test_l2d_type12_gate.py
wiring 用例口径，读源码全文断言）：
emitInteraction 增 pressedZone 可选参 + 命中失败回退按下区（drag 不回退），
pointerup 传局部变量 downHit（不得用已置 null 的 this.downHitZone）；
S3（pointerdown dial 写入延后）为待研究项，本阶段不做，断言防顺手改。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FM = ROOT / "frontend-minimal"


def read(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def test_release_fallback_wiring():
    src = read("src/renderer/l2d.ts")
    assert "pressedZone?: TouchZone | null" in src  # 签名（可选参）
    # 回退表达式逐字：抬起命中失败回退按下区；drag 不回退
    assert "?? (kind !== 'drag' ? (pressedZone ?? null) : null)" in src
    assert "this.paramDriver?.poke(hit.rule.id ?? 0)" in src  # poke 原位回归
    assert "research3 F1" in src  # 注释锚点关键词


def test_release_passes_downhit():
    src = read("src/renderer/l2d.ts")
    lines = src.split("\n")
    idx = next(i for i, ln in enumerate(lines) if "'pointerup'" in ln)
    window = "\n".join(lines[idx : idx + 31])  # 锚点后 30 行内
    assert "downHit," in window  # emitInteraction 第 4 实参
    call = window[window.index("this.emitInteraction(") :]
    call = call[: call.index(");")]
    assert "downHit" in call
    assert "this.downHitZone" not in call  # 防误用调用前已置 null 的字段


def test_press_dial_write_unchanged():
    src = read("src/renderer/l2d.ts")
    assert "this.dialValueFor(hit, e.clientX, e.clientY)" in src  # S3 不做，防顺手改
    assert "if (downRule.actionTrigger?.circle)" in src


def test_doc_research3_note():
    doc = (ROOT / "docs" / "context" / "minimal-frontend-live2d.md").read_text(
        encoding="utf-8"
    )
    assert "research3" in doc
    assert "自愈分层表述废止" in doc
