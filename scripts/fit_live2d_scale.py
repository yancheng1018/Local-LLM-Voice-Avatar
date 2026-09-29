"""根据 moc3 画布尺寸自动计算 model_dict.json 里每个模型的 kScale。

前端渲染缩放 = moc3 逻辑画布尺寸 × CurrentKScale（= kScale×2），
逻辑画布 = CanvasInfo 像素尺寸 / PixelsPerUnit。逻辑画布大小因模型而异
（mao_pro 高 1.45 单位、xinnong_6 高 20 单位），共用 kScale 必然有的模型溢出屏幕。

标定基准：mao_pro 在 kScale=0.5 时显示正常 → 目标系数
    kScale = 0.724 / 逻辑高度（0.724 = 0.5 × 8400/5800），宽度兜底 kScale ≤ 1.0/逻辑宽度。

游戏系模型修正：碧蓝航线等游戏模型画布含大量动画余量，人物主体只占画布一部分，
按整画布适配会偏小。逻辑画布高 > GAME_UNITS_THRESHOLD 的模型额外乘 GAME_FACTOR
（1.8，2026-09-11 用户目测校准）。小画布模型（mao_pro 1.45 / shizuku 1.08 /
oppai_bunny 0.38）与游戏系（12~32）之间有清晰断层，阈值取 5。

注：曾尝试解析 moc3 顶点数据自动求人物包围盒，因 keyform 多层间接索引未果而
放弃（详见 ZCODE_CONTEXT.md），目测倍率是当前可行方案。

CanvasInfo 解析（依据 OpenL2D/moc3ingbird 的 moc3 格式逆向，v3~v5 通用）：
    u32 @0x44 → CanvasInfo 偏移；该处 5 个 float = PixelsPerUnit, OriginX, OriginY,
    CanvasWidth(px), CanvasHeight(px)。

用法：uv run python scripts/fit_live2d_scale.py   （自动备份 model_dict.json 为 .bak）
"""

import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ 上一级 = 仓库根
MODEL_DICT_PATH = os.path.join(ROOT, "model_dict.json")

# 标定系数：0.5 × mao_pro 逻辑画布高（8400px / 5800ppu = 1.4483 单位）
TARGET_FACTOR = 0.7241
KSCALE_MIN, KSCALE_MAX = 0.01, 3.0
GAME_UNITS_THRESHOLD = 5.0  # 逻辑画布高超过此值视为游戏系大画布模型
GAME_FACTOR = 1.8  # 2026-09-11 用户目测校准


def parse_canvas_info(moc3_path: str):
    """返回 (pixelsPerUnit, originX, originY, canvasWidth, canvasHeight)，失败返回 None。"""
    with open(moc3_path, "rb") as f:
        data = f.read()
    if len(data) < 0x48 or data[:4] != b"MOC3":
        return None
    (offset,) = struct.unpack_from("<I", data, 0x44)
    if not 0 < offset < len(data) - 20:
        return None
    ppu, origin_x, origin_y, width, height = struct.unpack_from("<5f", data, offset)
    return ppu, origin_x, origin_y, width, height


def find_moc3(model3_rel_url: str) -> str | None:
    """从 model_dict.json 的 url（/live2d-models/.../xxx.model3.json）定位 moc3。"""
    rel = model3_rel_url.lstrip("/").removesuffix(".model3.json")
    base = os.path.join(ROOT, os.path.dirname(rel))
    name = os.path.basename(rel)
    candidate = os.path.join(base, name + ".moc3")
    if os.path.isfile(candidate):
        return candidate
    # 回退：在模型目录里找同名或任意 moc3（取层级最浅）
    best = None
    for dirpath, _dirs, files in os.walk(base):
        depth = dirpath[len(base) :].count(os.sep)
        for fn in files:
            if fn.endswith(".moc3") and (fn == name + ".moc3" or best is None):
                if best is None or depth < best[0]:
                    best = (depth, os.path.join(dirpath, fn))
                break
    return best[1] if best else None


def compute_kscale(ppu, width, height) -> float | None:
    if not ppu or ppu <= 0 or width <= 0 or height <= 0:
        return None
    units_h, units_w = height / ppu, width / ppu
    if not (0.2 <= units_h <= 100):
        return None
    k = min(TARGET_FACTOR / units_h, 1.0 / units_w)
    if units_h > GAME_UNITS_THRESHOLD:
        k *= GAME_FACTOR
    return round(min(max(k, KSCALE_MIN), KSCALE_MAX), 4)


def main() -> None:
    with open(MODEL_DICT_PATH, encoding="utf-8") as f:
        models = json.load(f)

    # 备份当前 model_dict.json
    bak = MODEL_DICT_PATH + ".bak"
    with (
        open(MODEL_DICT_PATH, encoding="utf-8") as src,
        open(bak, "w", encoding="utf-8") as dst,
    ):
        dst.write(src.read())

    print(
        f"{'模型':<22} {'画布(px)':<15} {'逻辑高/宽':<13} {'类型':<6} "
        f"{'旧kScale':<9} 新kScale"
    )
    changed = 0
    for m in models:
        name = m.get("name", "?")
        old = m.get("kScale")
        moc3 = find_moc3(m.get("url", ""))
        info = parse_canvas_info(moc3) if moc3 else None
        if info is None:
            print(f"{name:<22} 解析失败（无 moc3 或格式异常），保留原值 {old}")
            continue
        ppu, _ox, _oy, w, h = info
        new = compute_kscale(ppu, w, h)
        if new is None:
            print(f"{name:<22} {f'{w:.0f}x{h:.0f}':<15} 数值异常，保留原值 {old}")
            continue
        game = "游戏系" if h / ppu > GAME_UNITS_THRESHOLD else "标准"
        m["kScale"] = new
        changed += 1
        mark = "" if old == new else "  <-"
        print(
            f"{name:<22} {f'{w:.0f}x{h:.0f}':<15} "
            f"{f'{h / ppu:.2f} / {w / ppu:.2f}':<13} {game:<6} {old:<9} {new}{mark}"
        )

    if changed:
        with open(MODEL_DICT_PATH, "w", encoding="utf-8") as f:
            json.dump(models, f, indent=4, ensure_ascii=False)
    print(f"\n已更新 {changed}/{len(models)} 个条目（备份: model_dict.json.bak）")


if __name__ == "__main__":
    main()
