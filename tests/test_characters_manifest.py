"""github-p0-characters 守卫：角色批改名落地与默认测试角色入库。

覆盖三件事：① .gitignore 完成 ja_test→shinano 换名（clone 安全）；
② 默认测试角色 zh_demo.yaml 入库且字段有效、Live2D 模型指针在 model_dict.json
可解析；③ characters/*.yaml 身份字段唯一——前端按 character_name 反查配置文件，
重名会切错角色（docs/context/config-system.md「角色标识方案」）。
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTERS_DIR = REPO_ROOT / "characters"

DEMO_FILE = "zh_demo.yaml"
DEMO_CONF_UID = "zh_demo_001"
DEMO_NAME = "小语"
DEMO_LANGUAGE = "zh"
DEMO_MODEL = "mao_pro"

# 公开克隆标记：与 test_repo_privacy_guard.py 的 skip 同口径
# （private_names.local.txt 仅存在于本机，公开克隆缺失 → 本地语义用例 skip）
PRIVATE_NAMES_FILE = Path(__file__).parent / "private_names.local.txt"


def _load_character_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name} 顶层不是映射"
    assert "character_config" in data, f"{path.name} 缺 character_config 键"
    return data["character_config"]


def _tracked_character_files() -> set[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "characters/"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return {line for line in result.stdout.decode("utf-8").splitlines() if line}


def test_demo_character_tracked_and_valid():
    assert f"characters/{DEMO_FILE}" in _tracked_character_files()
    cfg = _load_character_config(CHARACTERS_DIR / DEMO_FILE)
    assert cfg["conf_uid"] == DEMO_CONF_UID
    assert cfg["character_name"] == DEMO_NAME
    assert cfg["language"] == DEMO_LANGUAGE
    assert cfg["live2d_model_name"] == DEMO_MODEL
    assert isinstance(cfg["persona_prompt"], str) and cfg["persona_prompt"].strip()
    model_list = json.loads((REPO_ROOT / "model_dict.json").read_text(encoding="utf-8"))
    assert isinstance(model_list, list), "model_dict.json 须为模型对象数组"
    assert any(m["name"] == DEMO_MODEL for m in model_list), (
        f"{DEMO_MODEL} 不在 model_dict.json"
    )


def test_character_identity_unique_on_disk():
    files = sorted(CHARACTERS_DIR.glob("*.yaml"))
    assert len(files) >= 2, "characters/ 角色文件异常缺失"
    conf_uids = []
    names = []
    for path in files:
        cfg = _load_character_config(path)
        conf_uids.append(cfg["conf_uid"])
        names.append(cfg["character_name"])
    assert len(set(conf_uids)) == len(conf_uids), f"conf_uid 重复: {conf_uids}"
    assert len(set(names)) == len(names), f"character_name 重复: {names}"


def test_gitignore_uses_shinano_not_ja_test():
    lines = [
        line.strip()
        for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    ]
    assert "characters/shinano.yaml" in lines
    assert "characters/ja_test.yaml" not in lines


def test_local_shinano_renamed():
    if not PRIVATE_NAMES_FILE.is_file():
        pytest.skip(
            f"{PRIVATE_NAMES_FILE.name} 不存在（公开克隆语义）。"
            "本机应存在 characters/shinano.yaml（ja_test.yaml 改名，本地保留不入库）"
        )
    assert (CHARACTERS_DIR / "shinano.yaml").is_file()
    assert not (CHARACTERS_DIR / "ja_test.yaml").exists()
