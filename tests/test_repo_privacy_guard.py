"""github-p0-privacy 守卫：私有资产不得回到 git 索引。

依据 research_上传github前准备.md §2（本地文档）与发布准备裁决：
voices/ 私有声音卡、launcher 运行时配置、本地新增角色 yaml、docs/assets 舰船缓存
均裁决不上传。防止后续 git add -A 或忽略规则回退把它们重新带入索引。
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PRIVATE_PATH_PREFIXES = (
    "voices/",
    "launcher/launcher_config.json",
    "characters/Friedrich.yaml",
    "characters/Illustrious.yaml",
    "characters/azuma.yaml",
    "characters/ja_test.yaml",  # github-p0-characters 批改名 shinano.yaml 后本条同步换名
    "characters/spine_test.yaml",
    "docs/assets/_ships_cache/",
    "docs/assets/su_ships-CN.json",
)


def _tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return {line for line in result.stdout.decode("utf-8").splitlines() if line}


def test_private_assets_absent_from_index():
    leaked = sorted(p for p in _tracked_files() if p.startswith(PRIVATE_PATH_PREFIXES))
    assert leaked == [], f"私有资产重新进入 git 索引: {leaked}"
