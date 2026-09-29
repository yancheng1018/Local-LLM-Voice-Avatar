"""GSV 适配器 CLI 单测（temp_spec github-p2-precheck-d §3）。

scripts/ 非包，用 importlib 按路径加载（tests 不得 sys.path 注入）；
main 不在单测中真跑（subprocess 真启动属冒烟/人工项）。
"""

import importlib.util
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gpt_sovits" / "start_gsv_api.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("start_gsv_api", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_requires_root():
    """缺 --root 时 argparse 必填校验触发 SystemExit（exit 2），不等待输入。"""
    mod = _load_script()
    with pytest.raises(SystemExit):
        mod.parse_args([])


def test_fallback_latest_weight(tmp_path):
    """显式权重缺省时 find_one 取目录内 mtime 最新的候选。"""
    mod = _load_script()
    old = tmp_path / "old.ckpt"
    new = tmp_path / "new.ckpt"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    assert mod.find_one(tmp_path, "*.ckpt") == new


def test_build_config_text():
    """custom 7 键齐全、version 取参数、权重路径保持 posix 相对形式。"""
    mod = _load_script()
    text = mod.build_config_text(
        "GPT_weights_v4/xxx.ckpt", "SoVITS_weights_v4/xxx.pth", "v4"
    )
    assert "t2s_weights_path: GPT_weights_v4/xxx.ckpt" in text
    assert "vits_weights_path: SoVITS_weights_v4/xxx.pth" in text
    assert "version: v4" in text
    for key in (
        "bert_base_path",
        "cnhuhbert_base_path",
        "device",
        "is_half",
        "t2s_weights_path",
        "version",
        "vits_weights_path",
    ):
        assert f"{key}:" in text


def test_no_v4dpo_hardcode():
    """适配器源码不得残留旧权重筛选硬编码（E 裁决：私有命名痕迹清零）。"""
    assert "v4dpo" not in SCRIPT.read_text(encoding="utf-8")
