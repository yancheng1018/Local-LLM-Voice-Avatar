"""为 live2d-models/ 下每个 model3.json 补大小写精确的 Idle/Talk 别名组。

契约来源：docs/context/live2d.md「前端动作（motion）触发约定」——前端（已构建产物）
硬编码 `Idle` / `Talk` 两个动作组名，与 model3.json 里的组名**大小写完全一致**才会播放；
组名缺失或大小写不符时，空闲时模型静止、说话无伴随动作。修复方式：加同名别名组，
引用原有动作文件（纯数据改动）。

用法：uv run python fix_live2d_idle_groups.py

幂等：精确组名已存在即跳过，不重复追加；无大小写变体可复制的模型只报告不修改。
安全：只在确实要新增别名组时才写回，写回前把原文件整字节备份为 `<entry>.bak`；
只新增别名组键，不改动任何既有键。
"""

import copy
import json
import os
import shutil

from scan_live2d_models import MODELS_DIR, find_entry_file

TARGET_GROUPS = ("Idle", "Talk")


def fix_entry(entry_path: str) -> list[str]:
    """对单个 model3.json 补别名组；返回实际新增的组名列表（空 = 无改动，不写回）。"""
    with open(entry_path, encoding="utf-8") as f:
        data = json.load(f)
    motions = data.get("FileReferences", {}).get("Motions") or {}
    variant_of = {g.lower(): g for g in motions}
    added = []
    for target in TARGET_GROUPS:
        if target in motions:
            continue
        variant = variant_of.get(target.lower())
        if variant is None:
            continue
        motions[target] = copy.deepcopy(motions[variant])
        added.append(target)
    if not added:
        return []
    shutil.copyfile(entry_path, entry_path + ".bak")
    with open(entry_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return added


def main() -> None:
    """遍历 MODELS_DIR 全部模型子目录，逐行打印结果并汇总（fixed/skipped/no-variant/no-entry）。"""
    dir_names = sorted(
        d for d in os.listdir(MODELS_DIR)
        if os.path.isdir(os.path.join(MODELS_DIR, d))
    )
    fixed: list[str] = []
    skipped: list[str] = []
    no_variant: list[str] = []
    no_entry: list[str] = []
    errors: list[str] = []

    for name in dir_names:
        model_dir = os.path.join(MODELS_DIR, name)
        rel_entry = find_entry_file(model_dir)
        if rel_entry is None:
            no_entry.append(name)
            print(f"{name}: no-entry")
            continue
        try:
            added = fix_entry(os.path.join(model_dir, rel_entry))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(name)
            print(f"{name}: error {e}")
            continue
        if added:
            fixed.append(name)
            print(f"{name}: fixed [{', '.join(added)}]")
            continue
        with open(os.path.join(model_dir, rel_entry), encoding="utf-8") as f:
            motions = json.load(f).get("FileReferences", {}).get("Motions") or {}
        missing = [
            f"{t}（无变体: {', '.join(g for g in motions if g.lower() == t.lower()) or '无'}）"
            for t in TARGET_GROUPS
            if t not in motions
        ]
        if missing:
            no_variant.append(name)
            print(f"{name}: no-variant {', '.join(missing)}")
        else:
            skipped.append(name)
            print(f"{name}: skipped")

    print()
    print(f"汇总: fixed={len(fixed)} skipped={len(skipped)} "
          f"no-variant={len(no_variant)} no-entry={len(no_entry)} error={len(errors)}")
    print(f"fixed: {', '.join(fixed) or '无'}")
    print(f"skipped: {', '.join(skipped) or '无'}")
    print(f"no-variant: {', '.join(no_variant) or '无'}")
    print(f"no-entry: {', '.join(no_entry) or '无'}")
    if errors:
        print(f"error: {', '.join(errors)}")


if __name__ == "__main__":
    main()
