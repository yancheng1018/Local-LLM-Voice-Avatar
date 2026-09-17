#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l2d.su touch.json 皮肤匹配普查脚本（2026-09-17 本轮研究产物）。

用途：核验 live2d-models/<name>/touch.json 是否与站点同名 prefab 皮肤逐字节一致。
背景：发现 9/36 模型错配（本地数据 = 同名皮肤的前一编号皮肤），详见
docs/context/research_live2d动作链条修正.md §5.1b。

依赖：ships-CN.json（站点全量索引，可从 https://l2d.su/data/ships-CN.json 下载）。
用法：python su_survey_touch_json.py <repo_root> [--fetch]
      --fetch 时对缺失的站点 ship json 现场下载（需网络；否则只用本地缓存 site_<group>.json）
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


def load_prefab_index(ships_cn_path):
    """prefab → shipGroupId（同一 prefab 出现在多皮肤时取首个，足够定位 group）。"""
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


def site_rules_for(ship_json, prefab):
    """取站点该 prefab 的 live2dTouch（筛「带 rules 的 live2d 条目」，可能多条）。"""
    sd = json.load(open(ship_json, encoding="utf-8"))
    ship = sd.get("ship") or sd
    out = []
    for s in ship.get("skins", []):
        if s.get("prefab") != prefab:
            continue
        lt = (s.get("model") or {}).get("live2dTouch")
        if lt and lt.get("rules"):
            out.append((s.get("id"), lt))
    return ship, out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    allow_fetch = "--fetch" in sys.argv
    base = os.path.join(root, "live2d-models")
    ships_cn = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "su_ships-CN.json"
    )
    if not os.path.exists(ships_cn):
        ships_cn = "ships-CN.json"
    idx = load_prefab_index(ships_cn)
    models = sorted(
        n
        for n in os.listdir(base)
        if os.path.isdir(os.path.join(base, n))
        and os.path.exists(os.path.join(base, n, "touch.json"))
    )
    ok, bad = [], []
    for m in models:
        g = idx.get(m)
        if not g:
            bad.append((m, "-", "NO_PREFAB", None))
            continue
        sj = fetch_ship(g, os.path.dirname(os.path.abspath(__file__)), allow_fetch)
        if not sj:
            bad.append((m, g, "NO_DATA", None))
            continue
        ship, cands = site_rules_for(sj, m)
        loc = json.load(open(os.path.join(base, m, "touch.json"), encoding="utf-8"))
        lr = loc.get("rules", [])
        lsid = sorted({r.get("shipSkinId") for r in lr if r.get("shipSkinId")})
        if not cands:
            bad.append((m, g, "SITE_NO_RULES", len(lr)))
            continue
        hit = next(
            (
                sid
                for sid, lt in cands
                if json.dumps(lt, sort_keys=True) == json.dumps(loc, sort_keys=True)
            ),
            None,
        )
        if hit:
            ok.append((m, g, hit, len(lr)))
        else:
            src = None
            for s in ship.get("skins", []):
                if s.get("id") in lsid:
                    src = (s.get("id"), s.get("prefab"))
            bad.append(
                (
                    m,
                    g,
                    "MISMATCH",
                    (len(lr), lsid, src, [(c[0], len(c[1]["rules"])) for c in cands]),
                )
            )
    print("OK: %d/%d" % (len(ok), len(models)))
    print("%-20s %-8s %-14s %s" % ("model", "group", "status", "detail"))
    for r in bad:
        print("%-20s %-8s %-14s %s" % r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
