"""Live2D 模型数据契约测试：在用模型必须能被前端正确加载与播放动作。

契约来源：docs/context/live2d.md「前端动作（motion）触发约定」（2026-09-10 实测）。
前端是已构建产物、硬编码动作组名 `Idle` / `Talk`，与 model3.json 的组名**大小写完全
一致**才会播放；组名缺失或不匹配时，空闲时模型静止、说话无伴随动作（静默失效）。
故本文件对「在用模型」钉死两条：入口能被解析、且 Motions 含非空精确 `Idle` 组。

长期回归价值：新角色或新模型入用即受本契约约束（`live2d_model_name` 指向的模型
必须真实存在且带精确 Idle 组）。
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = ROOT / "characters"
MODEL_DICT = ROOT / "model_dict.json"


def registered_model_urls() -> dict[str, str]:
    """已登记的 Live2D 模型 name -> url；按 list_frontend_models 的口径排除 Spine（.skel）。"""
    with open(MODEL_DICT, encoding="utf-8") as f:
        entries = json.load(f)
    return {
        e["name"]: e["url"]
        for e in entries
        if isinstance(e.get("name"), str)
        and isinstance(e.get("url"), str)
        and not e["url"].endswith(".skel")
    }


def in_use_model_names() -> set[str]:
    names: set[str] = set()
    for path in sorted(CHARACTERS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = data.get("character_config") or {}
        single = config.get("live2d_model_name")
        if isinstance(single, str):
            names.add(single)
        multi = config.get("live2d_model_names")
        if isinstance(multi, list):
            names.update(n for n in multi if isinstance(n, str))
    return names & set(registered_model_urls())


def motion_groups(model_name: str) -> dict[str, list]:
    url = registered_model_urls()[model_name]
    with open(ROOT / url.lstrip("/"), encoding="utf-8") as f:
        data = json.load(f)
    return data["FileReferences"]["Motions"]


def test_inuse_names_resolved_and_nonempty() -> None:
    names = in_use_model_names()
    assert names, "未解析出任何在用 Live2D 模型名"
    known = {
        "wuqi_3",
        "guanghui_9",
        "feiteliedadi_3",
        "feiteliedadi_4",
        "mao_pro",
        "xinnong_6",
    }
    assert known <= names, f"解析结果缺少已知在用模型: {sorted(known - names)}"


def test_inuse_models_have_exact_idle_group() -> None:
    violations = []
    for name in sorted(in_use_model_names()):
        groups = motion_groups(name)
        if "Idle" not in groups:
            variants = sorted(g for g in groups if g.lower() == "idle")
            violations.append(
                f"{name}: 无精确 Idle 组（大小写变体: {variants or '无'}）"
            )
        elif not groups["Idle"]:
            violations.append(f"{name}: Idle 组为空")
    assert not violations, (
        "在用模型缺少可用 Idle 组（空闲动作不会播放）：\n" + "\n".join(violations)
    )
