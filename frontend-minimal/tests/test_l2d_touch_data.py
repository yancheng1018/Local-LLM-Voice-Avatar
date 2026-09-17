# -*- coding: utf-8 -*-
"""动作链条修正 §5.3：9 个错配模型 touch.json 数据完整性回归。

数据来源 = 站点同名 prefab 皮肤的 model.live2dTouch（fix_live2d_touch_data.py 写入，
先备份 .bak）。规则数来自研究报告 §5.1b 普查表；被回退/再错配即失败。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
MODELS = ROOT / "live2d-models"

# (模型名, 站点规则数) —— 与 fix_live2d_touch_data.py TARGETS 同源
TARGETS = [
    ("shi_3", 71),
    ("feiteliedadi_4", 66),
    ("feiteliekaer_4", 107),
    ("mojiaduoer_4", 87),
    ("wuzang_4", 86),
    ("ougen_8", 47),
    ("tiancheng_cv_3", 44),
    ("dafeng_7", 35),
    ("guandao_3", 24),
]


def load(name: str) -> dict:
    return json.loads((MODELS / name / "touch.json").read_text(encoding="utf-8"))


def test_nine_models_rule_counts():
    for name, expect in TARGETS:
        got = len(load(name).get("rules", []))
        assert got == expect, f"{name} touch.json 规则数 {got}，站点应有 {expect}"


def test_ship_skin_id_single_skin():
    for name, _ in TARGETS:
        rules = load(name).get("rules", [])
        ids = {r["shipSkinId"] for r in rules if r.get("shipSkinId") is not None}
        assert len(ids) <= 1, (
            f"{name} 规则含多个 shipSkinId（跨皮肤拼接）：{sorted(ids)}"
        )
    shi = {
        r["shipSkinId"]
        for r in load("shi_3").get("rules", [])
        if r.get("shipSkinId") is not None
    }
    assert shi == {205162}, (
        f"shi_3 皮肤号应为 205162（研究 §5.1 实证），实得 {sorted(shi)}"
    )


# research2 §6 全库对照（2026-09-18，docs/assets/_ships_cache 快照口径）确认的
# 「站点无规则而本地有」错配模型，已清空为 {"rules": []}（契约候选 R2-d）
CLEARED = ["shengluyisi_4", "chaijun_4"]


def test_shengluyisi4_rules_empty():
    """shengluyisi_4 站点 rules=0（research2 §3.4），本地 54 条为 _5 错配数据。"""
    assert load("shengluyisi_4").get("rules") == []


def test_cleared_models_empty():
    """全部确认错配模型保持 rules=[]；若重新挂规则须走站点同源重下流程。"""
    for name in CLEARED:
        assert load(name).get("rules") == [], f"{name} 应保持清空（站点无规则）"
