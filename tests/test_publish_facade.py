"""发布门面守卫：项目身份（改名+版本）、README 门面、GUI/bat 门面与 bat CRLF 不得回退。

命名定案见 research_上传github前准备.md §6。
"""

import hashlib
import tomli
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NAME = "local-llm-voice-avatar"
EXPECTED_VERSION = "1.0.0"
README_ANCHORS = (
    "Local-LLM-Voice-Avatar",
    "pyttsx3",
    "Open-LLM-VTuber",
    "Live2D",
    "v1.2.1",
    "MIT",
)
README_FORBIDDEN = ("open-llm-vtuber-zh-local", "v1.2.1_Open-LLM-VTuber")


def _load_toml(rel_path: str) -> dict:
    """以二进制模式读取仓库根下指定 TOML 文件并解析（Python 3.10 无 tomllib，用 tomli）。"""
    with open(REPO_ROOT / rel_path, "rb") as f:
        return tomli.load(f)


def test_pyproject_identity():
    pyproject = _load_toml("pyproject.toml")
    assert pyproject["project"]["name"] == EXPECTED_NAME
    assert pyproject["project"]["version"] == EXPECTED_VERSION


def test_uv_lock_self_reference_matches_pyproject():
    """uv.lock 自引用条目（source.virtual == "."）必须与 pyproject 一致，防漏 uv sync。"""
    pyproject = _load_toml("pyproject.toml")
    uv_lock = _load_toml("uv.lock")
    self_refs = [
        entry
        for entry in uv_lock["package"]
        if entry.get("source", {}).get("virtual") == "."
    ]
    assert len(self_refs) == 1, f"自引用条目应恰有一个，实得 {len(self_refs)}"
    assert self_refs[0]["name"] == pyproject["project"]["name"]
    assert self_refs[0]["version"] == pyproject["project"]["version"]


def test_readme_required_sections():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for anchor in README_ANCHORS:
        assert anchor in readme, f"README 缺少关键内容锚点: {anchor}"


def test_readme_no_legacy_identity():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for legacy in README_FORBIDDEN:
        assert legacy not in readme, f"README 残留旧身份标识: {legacy}"


def test_tts_config_accepts_pyttsx3():
    """Literal 枚举必须收 pyttsx3_tts，且无引擎键时可校验（README 快速层路径）。"""
    from src.open_llm_vtuber.config_manager.tts import TTSConfig

    cfg = TTSConfig.model_validate({"tts_model": "pyttsx3_tts"})
    assert cfg.tts_model == "pyttsx3_tts"


def test_conf_template_pyttsx3_key():
    """模板 tts_config 必须有 pyttsx3_tts 空实键（GUI TTS 下拉数据源）。"""
    data = yaml.safe_load(
        (REPO_ROOT / "config_templates" / "conf.ZH.default.yaml").read_text(
            encoding="utf-8"
        )
    )
    tts_config = data["character_config"]["tts_config"]
    assert "pyttsx3_tts" in tts_config
    assert tts_config["pyttsx3_tts"] == {}


def test_conf_template_pyttsx3_key_en():
    """EN 模板同样必须有 pyttsx3_tts 空实键（04-A2，GUI 下拉契约）。"""
    data = yaml.safe_load(
        (REPO_ROOT / "config_templates" / "conf.default.yaml").read_text(
            encoding="utf-8"
        )
    )
    tts_config = data["character_config"]["tts_config"]
    assert "pyttsx3_tts" in tts_config
    assert tts_config["pyttsx3_tts"] == {}


def _nested_keys(node, prefix=""):
    """递归收集 YAML 键路径集合（值忽略，只比键集）。"""
    keys = set()
    if isinstance(node, dict):
        for k, v in node.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            keys.add(path)
            keys |= _nested_keys(v, path)
    return keys


def test_templates_keyset_consistency():
    """ZH/EN 模板键集必须一致（04-A3；历史分歧仅 pyttsx3 一节，C2 补齐后应零差）。"""
    zh = yaml.safe_load(
        (REPO_ROOT / "config_templates" / "conf.ZH.default.yaml").read_text(
            encoding="utf-8"
        )
    )
    en = yaml.safe_load(
        (REPO_ROOT / "config_templates" / "conf.default.yaml").read_text(
            encoding="utf-8"
        )
    )
    zh_keys, en_keys = _nested_keys(zh), _nested_keys(en)
    assert zh_keys == en_keys, (
        f"模板键集分歧: 仅ZH={sorted(zh_keys - en_keys)} 仅EN={sorted(en_keys - zh_keys)}"
    )


def test_gui_no_legacy_name():
    """GUI 与启动器 bat 不得残留旧项目名（bat 为 GBK 编码 + CRLF 换行）。"""
    gui = (REPO_ROOT / "launcher" / "OpenLLMVTuber_GUI.py").read_text(encoding="utf-8")
    bat = (REPO_ROOT / "启动器.bat").read_text(encoding="gbk")
    assert "Open-LLM-VTuber" not in gui
    assert "Open-LLM-VTuber" not in bat
    bat_raw = (REPO_ROOT / "启动器.bat").read_bytes()
    assert bat_raw.count(b"\r\n") == bat_raw.count(b"\n"), (
        "启动器.bat 必须保持 CRLF 换行（LF-only 会导致 cmd 解析错乱）"
    )


def test_facade_no_legacy_name():
    """server 标题 / 入口 argparse 描述 / 极简前端页面标题不得残留旧项目名。"""
    server = (REPO_ROOT / "src" / "open_llm_vtuber" / "server.py").read_text(
        encoding="utf-8"
    )
    run_server = (REPO_ROOT / "run_server.py").read_text(encoding="utf-8")
    html = (REPO_ROOT / "frontend-minimal" / "index.html").read_text(encoding="utf-8")
    assert 'FastAPI(title="Open-LLM-VTuber' not in server
    assert 'description="Open-LLM-VTuber' not in run_server
    assert "<title>Open-LLM-VTuber" not in html


def test_live2d_core_vendored():
    """static/libs 必须入库 Cubism Core（06 §0-C 裁决，P0 修复防回潮）。"""
    core = REPO_ROOT / "static" / "libs" / "live2dcubismcore.min.js"
    assert core.is_file(), "static/libs/live2dcubismcore.min.js 缺失（新克隆 Live2D 必挂）"
    data = core.read_bytes()
    assert len(data) == 206492, (
        f"core 字节数异常: {len(data)}（上游基准 206492，2026-09-30 裁决 jsdelivr 渠道）"
    )
    assert (
        hashlib.sha1(data).hexdigest()
        == "6b35977308b3219a4dd0bbcfb72026d54fc5d852"
    ), "core sha1 与上游基准不符"
    assert b"Live2D" in data[:600], "core 版权头缺失"
