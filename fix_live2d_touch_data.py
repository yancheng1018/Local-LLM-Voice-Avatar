#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重下 9 个错配模型的 touch.json（规格 temp_spec_live2d动作链条修正.md §4）。

背景：9/36 模型的本地 touch.json 实为站点**前一个编号皮肤**的数据（研究报告 §5.1b）。
本脚本按 prefab 精确匹配站点同名 live2d 皮肤，取 model.live2dTouch 原样写回。

依赖：docs/assets/su_ships-CN.json（prefab→shipGroupId 索引）、
      docs/assets/_ships_cache/site_<group>.json（站点 ship json 缓存）。
用法：python fix_live2d_touch_data.py <repo_root> [--fetch] [--apply]
      默认 dry-run 只打印 [PLAN]；--fetch 允许联网补缓存；--apply 才写盘（先备份 .bak）。
"""

import json
import os
import sys
import time
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://l2d.su/",
    "Accept": "application/json,*/*",
}
SITE = "https://l2d.su/data/ships/CN/{}.json"

# (模型名, 站点 shipGroupId, 站点应有规则数) —— 规则数来自研究报告 §5.1b 普查表
TARGETS = [
    ("shi_3", 20516, 71),
    ("feiteliedadi_4", 49902, 66),
    ("feiteliekaer_4", 40314, 107),
    ("mojiaduoer_4", 90107, 87),
    ("wuzang_4", 30510, 86),
    ("ougen_8", 40303, 47),
    ("tiancheng_cv_3", 30715, 44),
    ("dafeng_7", 30707, 35),
    ("guandao_3", 11802, 24),
]
ANNOTATE_ONLY = ["chaijun_4", "shengluyisi_4"]  # 站点无规则：保留旧数据仅打印标注


def load_prefab_index(ships_cn_path):
    """prefab → shipGroupId（同 survey：同一 prefab 出现在多皮肤时取首个）。"""
    d = json.load(open(ships_cn_path, encoding="utf-8"))
    idx = {}
    for ship in d.get("ships", []):
        g = ship.get("shipGroupId")
        for sk in ship.get("skins", []):
            p = sk.get("prefab")
            if p and p not in idx:
                idx[p] = g
    return idx


def fetch_ship(group, cache_dir, allow_fetch):
    """返回站点 ship json 路径；缓存命中即用，缺失且 allow_fetch 时下载（60s 超时、0.3s 间隔）。"""
    cache_dir = os.path.join(cache_dir, "_ships_cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "site_%s.json" % group)
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        try:
            json.load(open(path, encoding="utf-8"))
            return path
        except Exception:
            pass
    if not allow_fetch:
        return None
    req = urllib.request.Request(SITE.format(group), headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        open(path, "wb").write(data)
        time.sleep(0.3)
        return path
    except Exception as e:
        print("FETCHFAIL %s %s" % (group, e))
        return None


def pick_skin(site_json, prefab):
    """站点该 prefab 的 live2d 皮肤：prefab 匹配 + dynamicType=='live2d' + rules 非空。

    命中多条或多义返回 None（调用方 ABORT）；dynamicType 过滤后为空时降级为仅 rules
    非空并打印 WARN。返回 (skin_id, live2dTouch)。
    """
    sd = json.load(open(site_json, encoding="utf-8"))
    ship = sd.get("ship") or sd
    strict, loose = [], []
    for s in ship.get("skins", []):
        if s.get("prefab") != prefab:
            continue
        lt = (s.get("model") or {}).get("live2dTouch")
        if not (lt and lt.get("rules")):
            continue
        loose.append((s.get("id"), lt))
        if s.get("dynamicType") == "live2d":
            strict.append((s.get("id"), lt))
    if len(strict) == 1:
        return strict[0]
    if not strict and len(loose) == 1:
        print(
            "WARN %s dynamicType 过滤后无 live2d 候选，降级用仅 rules 非空条目" % prefab
        )
        return loose[0]
    if not strict and not loose:
        return None
    print("AMBIGUOUS %s strict=%d loose=%d" % (prefab, len(strict), len(loose)))
    return None


def _backup_name(path):
    """备份名：touch.json.bak；已存在则 touch.json.bak-<YYYYMMDD>，不覆盖历史 bak。"""
    bak = path + ".bak"
    if not os.path.exists(bak):
        return bak
    return "%s-%s" % (bak, time.strftime("%Y%m%d"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    allow_fetch = "--fetch" in sys.argv
    apply_ = "--apply" in sys.argv
    base = os.path.join(root, "live2d-models")
    assets = os.path.join(root, "docs", "assets")
    ships_cn = os.path.join(assets, "su_ships-CN.json")
    if not os.path.exists(ships_cn):
        ships_cn = "ships-CN.json"
    idx = load_prefab_index(ships_cn)

    failed = False
    for name, group_expect, count_expect in TARGETS:
        group = idx.get(name)
        if group != group_expect:
            print(
                "[ABORT] %s prefab 索引漂移：ships-CN.json 得 %s，研究时点 %s"
                % (name, group, group_expect)
            )
            failed = True
            continue
        site = fetch_ship(group, assets, allow_fetch)
        if not site:
            print("[ABORT] %s 无站点数据（需 --fetch）group=%s" % (name, group))
            failed = True
            continue
        cand = pick_skin(site, name)
        if cand is None:
            print("[ABORT] %s 候选皮肤不可唯一确定 group=%s" % (name, group))
            failed = True
            continue
        skin_id, live2d_touch = cand
        rules = live2d_touch["rules"]
        if len(rules) != count_expect:
            print(
                "[ABORT] %s 站点规则数已变：得 %d，研究时点 %d"
                % (name, len(rules), count_expect)
            )
            failed = True
            continue
        # 契约候选 A1：shipSkinId 与所选皮肤号不符即报错（缺失字段放行）
        bad = [
            r.get("shipSkinId")
            for r in rules
            if r.get("shipSkinId") is not None and r["shipSkinId"] != skin_id
        ]
        if bad:
            print(
                "[ABORT] %s shipSkinId 不符：皮肤 %s，规则内 %s"
                % (name, skin_id, sorted(set(bad)))
            )
            failed = True
            continue
        path = os.path.join(base, name, "touch.json")
        if not apply_:
            print(
                "[PLAN] %s group=%s skin=%s rules=%d -> %s"
                % (name, group, skin_id, len(rules), path)
            )
            continue
        bak = _backup_name(path)
        if os.path.exists(path):
            open(bak, "wb").write(open(path, "rb").read())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(live2d_touch, f, ensure_ascii=False)
        print(
            "[FIX] %s group=%s skin=%s rules=%d bak=%s"
            % (name, group, skin_id, len(rules), bak)
        )
    for name in ANNOTATE_ONLY:
        print("[KEEP] %s 站点无规则，保留本地数据（研究 §5.1b）" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
