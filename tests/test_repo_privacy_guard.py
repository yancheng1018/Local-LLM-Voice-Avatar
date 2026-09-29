"""github-p0-privacy 守卫：私有资产不得回到 git 索引。

依据 research_上传github前准备.md §2（本地文档）与发布准备裁决：
voices/ 私有声音卡、launcher 运行时配置、本地新增角色 yaml、docs/assets 舰船缓存
均裁决不上传。防止后续 git add -A 或忽略规则回退把它们重新带入索引。
"""

import pytest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PRIVATE_PATH_PREFIXES = (
    "voices/",
    "launcher/launcher_config.json",
    "characters/Friedrich.yaml",
    "characters/Illustrious.yaml",
    "characters/azuma.yaml",
    "characters/shinano.yaml",  # github-p0-characters 改名后条目（本地保留角色，不得回索引）
    "characters/spine_test.yaml",
    "docs/assets/_ships_cache/",
    "docs/assets/su_ships-CN.json",
    # github-p0 开发文档（含私有明细/过程细节，仅存本地；research 终态处置见路线图 stage 6）
    "docs/context/finalize_exec_github-p0-",
    "docs/context/research_上传github前准备",
    "docs/context/research_plan_上传github前准备",
)


PRIVATE_NAMES_FILE = Path(__file__).parent / "private_names.local.txt"


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


def _git_grep(pattern: str) -> tuple[int, str]:
    """在被跟踪文件工作区内容中固定字符串搜索；git grep 退出码 0=命中 1=无 ≥2=错误。"""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "grep", "-I", "-F", "-n", "-e", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout.decode("utf-8", errors="replace")


def _load_private_names() -> list[str]:
    if not PRIVATE_NAMES_FILE.is_file():
        pytest.skip(
            f"{PRIVATE_NAMES_FILE.name} 不存在（公开克隆语义，守卫空转）。"
            "本机请创建 tests/private_names.local.txt："
            "UTF-8 编码，每行一个私有声音名，# 开头行为注释"
        )
    lines = PRIVATE_NAMES_FILE.read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def test_private_names_absent_from_tracked_content():
    """私有声音名不得出现在被跟踪文件内容中（github-p0-decouple 落位）。

    阳性对照先行（ASCII 与 CJK 各一条，均锚本文件自身），证明 grep 管道与
    参数往返正常，防止名单扫描假绿。
    """
    rc, out = _git_grep("PRIVATE_PATH_PREFIXES")
    assert rc == 0 and "tests/test_repo_privacy_guard.py" in out, (
        "grep 管道失效（ASCII 阳性对照未命中）"
    )
    rc, _ = _git_grep("私有资产不得回到")
    assert rc == 0, "CJK 参数往返失效，名单扫描结果不可信"
    names = _load_private_names()
    assert names, (
        "名单文件存在但为空（全为注释/空行）；确无私有名时应删除该文件转为 skip"
    )
    for name in names:
        rc, out = _git_grep(name)
        if rc >= 2:
            pytest.fail(f"git grep 调用失败 rc={rc}: {out.strip()}")
        assert rc == 1, f"私有声音名出现在被跟踪文件中（{name}）:\n{out.strip()}"


# A1+A3 裁决（2026-09-29）：接受 3 处存量私有名消息体残留，守卫只拦增量。
KNOWN_HISTORICAL_OFFENDERS = frozenset({
    "acc5198f44a0b4da835757816ce5cac737e27e08",
    "67770bf011a4d137fb7c06300050d482023b5ce3",
    "be1ef5e6cffd3df6d5abe226cade36ea91c8cf46",
})


def _commit_messages() -> list[tuple[str, str]]:
    # %x01 作条目分隔（消息体不可能含 \x01）：git 的 %H%x00%B 中 \0 只分隔
    # hash 与消息体，条目之间没有分隔符，仅靠 \0 切分会错位。
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "log", "--all", "--format=%x01%H%x00%B"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    out = result.stdout.decode("utf-8", errors="replace")
    pairs = []
    for record in out.split("\x01"):
        record = record.strip("\n")
        if not record:
            continue
        commit_hash, _, body = record.partition("\x00")
        if commit_hash.strip():
            pairs.append((commit_hash.strip(), body))
    return pairs


def test_private_names_absent_from_commit_messages():
    """私有名不得再进入新的提交信息体（拦增量不除存量，06 §0-A 裁决）。"""
    names = _load_private_names()
    assert names, "名单文件存在但为空时沿用 test_private_names_absent_from_tracked_content 的口径"
    messages = _commit_messages()
    assert len(messages) > 0, "git log --all 未返回任何提交，扫描管道可疑"
    leaked = sorted(
        h for h, msg in messages
        if any(name in msg for name in names) and h not in KNOWN_HISTORICAL_OFFENDERS
    )
    assert leaked == [], f"私有名进入新的提交信息体: {leaked}"
