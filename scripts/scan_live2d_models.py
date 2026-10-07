"""只读扫描 live2d-models/ 下所有模型，生成 markdown 报告。

报告内容：表情清单、动作组名、Idle/Talk 组是否可用（前端硬编码这两个组名）、
HitAreas、emotionMap / tapMotions 配置状态、model_dict.json 登记一致性。

用法：uv run python scripts/scan_live2d_models.py
输出：项目根目录 live2d_scan_report.md
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ 上一级 = 仓库根
MODELS_DIR = os.path.join(ROOT, "live2d-models")
MODEL_DICT_PATH = os.path.join(ROOT, "model_dict.json")
REPORT_PATH = os.path.join(ROOT, "live2d_scan_report.md")


def find_entry_file(model_dir: str) -> str | None:
    """找层级最浅的 .model3.json 入口文件。"""
    candidates: list[tuple[int, str]] = []
    for dirpath, _dirnames, filenames in os.walk(model_dir):
        for fn in filenames:
            if fn.endswith(".model3.json"):
                rel = os.path.relpath(os.path.join(dirpath, fn), model_dir)
                candidates.append((rel.count(os.sep), rel))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def scan_model_dir(model_dir: str) -> dict | None:
    rel_entry = find_entry_file(model_dir)
    if rel_entry is None:
        return None
    entry_path = os.path.join(model_dir, rel_entry)
    try:
        with open(entry_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"entry": rel_entry, "error": f"解析失败: {e}"}

    fr = data.get("FileReferences", {})
    motions = fr.get("Motions", {}) or {}
    expressions = [e.get("Name", "?") for e in (fr.get("Expressions") or [])]
    # Cubism 规范中 HitAreas 是 model3.json 顶层键
    hit_areas = data.get("HitAreas") or []

    groups_lower = {g.lower(): g for g in motions}
    idle_actual = groups_lower.get("idle")
    talk_actual = groups_lower.get("talk")

    return {
        "entry": rel_entry,
        "motions": {g: len(v) for g, v in motions.items()},
        "expressions": expressions,
        "hit_areas": [h.get("Id", "?") for h in hit_areas],
        "idle_exact": "Idle" in motions,
        "idle_actual": idle_actual,
        "talk_exact": "Talk" in motions,
        "talk_actual": talk_actual,
    }


def main() -> None:
    local = os.path.join(ROOT, "model_dict.local.json")
    # local 存在即整份取代基准（规则权威见 live2d_model.resolve_model_dict_path；与 fit_live2d_scale.py 内联副本互指）
    dict_path = local if os.path.isfile(local) else MODEL_DICT_PATH
    with open(dict_path, encoding="utf-8") as f:
        model_dict = json.load(f)
    registered = {m["name"]: m for m in model_dict}

    dir_names = sorted(
        d for d in os.listdir(MODELS_DIR) if os.path.isdir(os.path.join(MODELS_DIR, d))
    )

    lines = [
        "# Live2D 模型扫描报告",
        "",
        "> 由 `scan_live2d_models.py` 只读扫描生成。前端（已构建产物）硬编码：",
        "> 空闲动作找 `Idle` 组、说话动作找 `Talk` 组、点击动作读 model_dict.json 的",
        "> `tapMotions`（值格式 `热区 → {动作组: 权重}`），表情只取每句 `expressions[0]`。",
        "",
    ]

    unregistered = []
    for name in dir_names:
        if name not in registered:
            unregistered.append(name)
    if unregistered:
        lines += ["## 未登记在 model_dict.json 的模型文件夹", ""]
        lines += [f"- `{n}`" for n in unregistered]
        lines += [""]

    for name in dir_names:
        info = registered.get(name)
        scan = scan_model_dir(os.path.join(MODELS_DIR, name))
        lines.append(f"## {name}")
        lines.append("")
        if scan is None:
            lines.append(
                "- ⚠️ 未找到 `.model3.json` 入口文件（可能是 Cubism 2.1 或缺文件）"
            )
        elif "error" in scan:
            lines.append(f"- ⚠️ {scan['entry']} {scan['error']}")
        else:
            if info is None:
                lines.append("- ⚠️ **未登记**在 model_dict.json，前端无法加载")
            else:
                url_ok = info.get("url", "").endswith(".model3.json")
                lines.append(
                    f"- 登记: ✅ (url 以 .model3.json 结尾: {'✅' if url_ok else '❌'})"
                )
            n_exp = len(scan["expressions"])
            lines.append(
                f"- 表情 ({n_exp}): {', '.join(scan['expressions']) if n_exp else '无'}"
            )
            lines.append(
                f"- 动作组 ({len(scan['motions'])}): "
                + ", ".join(f"{g}({c})" for g, c in scan["motions"].items())
            )
            if scan["idle_exact"]:
                lines.append("- Idle 组: ✅")
            elif scan["idle_actual"]:
                lines.append(
                    f"- Idle 组: ⚠️ 大小写不匹配（实际为 `{scan['idle_actual']}`），"
                    "空闲动作不会播放，可加 `Idle` 别名组"
                )
            else:
                lines.append("- Idle 组: ❌ 缺失，空闲时模型静止")
            if scan["talk_exact"]:
                lines.append("- Talk 组: ✅")
            elif scan["talk_actual"]:
                lines.append(
                    f"- Talk 组: ⚠️ 大小写不匹配（实际为 `{scan['talk_actual']}`），"
                    "说话动作不会播放，可加 `Talk` 别名组"
                )
            else:
                lines.append("- Talk 组: ❌ 缺失，说话时无伴随动作")
            if scan["hit_areas"]:
                lines.append(f"- HitAreas: {', '.join(scan['hit_areas'])}")
            else:
                lines.append(
                    "- HitAreas: 无（tapMotions 走「未命中热区→合并权重」分支）"
                )
            if info is not None:
                emo = info.get("emotionMap") or {}
                tap = info.get("tapMotions") or {}
                lines.append(
                    f"- emotionMap: {len(emo)} 个键"
                    + ("（空，情绪关键词不会触发表情）" if not emo else "")
                )
                lines.append(
                    f"- tapMotions: {'已配置' if tap else '未配置（点击无动作反应）'}"
                )
        lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"报告已写入 {REPORT_PATH}（共 {len(dir_names)} 个模型文件夹）")


if __name__ == "__main__":
    main()
