"""旧官方前端清除守卫：frontend/ mount、启动检查与 GUI 前端选择不得回潮。

github-p1-robust 裁决：旧官方前端（frontend/，不随仓库分发）整体退役，
根路径统一 307 引导到极简前端 /m/。本文件防止相关代码被重新引入。
"""

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_SRC = (REPO_ROOT / "src" / "open_llm_vtuber" / "server.py").read_text(
    encoding="utf-8"
)
RUN_SERVER_SRC = (REPO_ROOT / "run_server.py").read_text(encoding="utf-8")


def test_no_legacy_frontend_mount():
    """server.py 不得重新引入旧 frontend mount（含闭引号，区别于 frontend-minimal/dist）。"""
    assert 'directory="frontend"' not in SERVER_SRC


def test_no_legacy_frontend_check():
    """run_server.py 的子模块时代启动检查已删除，不得回来。"""
    assert "check_frontend_submodule" not in RUN_SERVER_SRC


def _build_tmp_layout(tmp_path: Path, with_dist: bool) -> None:
    """构造 WebSocketServer 可用的工作目录布局（conf.yaml + 必需目录）。"""
    shutil.copy(
        REPO_ROOT / "config_templates" / "conf.ZH.default.yaml",
        tmp_path / "conf.yaml",
    )
    shutil.copytree(REPO_ROOT / "characters", tmp_path / "characters")
    for empty_dir in ("live2d-models", "web_tool"):
        (tmp_path / empty_dir).mkdir()
    # /libs 挂载（Cubism Core）需要 static/libs 存在
    (tmp_path / "static" / "libs").mkdir(parents=True)
    if with_dist:
        dist = tmp_path / "frontend-minimal" / "dist"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text("<html></html>", encoding="utf-8")


def _routes_of(server):
    return [
        (getattr(route, "path", None), getattr(route, "name", None))
        for route in server.app.routes
    ]


def test_root_redirect_route_exists(tmp_path, monkeypatch):
    """dist 已构建：根路径必须有 "/" 重定向路由，且不存在名为 frontend 的 mount。"""
    _build_tmp_layout(tmp_path, with_dist=True)
    monkeypatch.chdir(tmp_path)
    from src.open_llm_vtuber.config_manager import (
        apply_default_character,
        read_yaml,
        validate_config,
    )
    from src.open_llm_vtuber.server import WebSocketServer

    config = validate_config(apply_default_character(read_yaml("conf.yaml")))
    server = WebSocketServer(config=config)

    routes = _routes_of(server)
    assert "/" in [path for path, _ in routes], "根路径重定向路由缺失"
    assert "/libs" in [path for path, _ in routes], "Cubism Core /libs 挂载缺失"
    assert "frontend" not in [name for _, name in routes], "旧 frontend mount 回潮"


def test_constructs_without_dist(tmp_path, monkeypatch):
    """dist 未构建：服务器仍可构造（只打警告），根重定向无条件存在。"""
    _build_tmp_layout(tmp_path, with_dist=False)
    monkeypatch.chdir(tmp_path)
    from src.open_llm_vtuber.config_manager import (
        apply_default_character,
        read_yaml,
        validate_config,
    )
    from src.open_llm_vtuber.server import WebSocketServer

    config = validate_config(apply_default_character(read_yaml("conf.yaml")))
    server = WebSocketServer(config=config)

    routes = _routes_of(server)
    assert "/" in [path for path, _ in routes]
    assert "frontend" not in [name for _, name in routes]


def test_en_template_validates(tmp_path, monkeypatch):
    """EN 模板走 ZH 同款全链校验（04-A3：EN 此前零守卫覆盖）。"""
    shutil.copy(
        REPO_ROOT / "config_templates" / "conf.default.yaml",
        tmp_path / "conf.yaml",
    )
    shutil.copytree(REPO_ROOT / "characters", tmp_path / "characters")
    for empty_dir in ("live2d-models", "web_tool"):
        (tmp_path / empty_dir).mkdir()
    (tmp_path / "static" / "libs").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    from src.open_llm_vtuber.config_manager import (
        apply_default_character,
        read_yaml,
        validate_config,
    )

    validate_config(apply_default_character(read_yaml("conf.yaml")))


RETIRED_FILES = (
    "src/open_llm_vtuber/proxy_handler.py",
    "src/open_llm_vtuber/proxy_message_queue.py",
    "src/open_llm_vtuber/live/",
    "legacy/README.md",
    "requirements.txt",
    ".pre-commit-config.yaml",
)
RETIRED_MARKERS = (  # (文件名后缀, 禁止子串)
    ("server.py", '"/bg"'),
    ("server.py", "AvatarStaticFiles"),
    ("websocket_handler.py", "fetch-backgrounds"),
    ("websocket_handler.py", "background-files"),
    ("websocket_handler.py", "delete-history"),
    ("websocket_handler.py", "history-deleted"),
    ("websocket_handler.py", "ai-speak-signal"),
    ("websocket_handler.py", "request-init-config"),
    ("routes.py", "/live2d-models/info"),
    ("routes.py", "init_proxy_route"),
    ("conversation_utils.py", "force-new-message"),
    ("service_context.py", '"config-switched"'),
    ("character.py", "avatar"),
    ("OpenLLMVTuber_GUI.py", "avatars"),
)


def test_retired_surfaces_absent():
    """github-p2-precheck-b 退役面防回潮（H1/F1 裁决，2026-09-30）。"""
    for path in RETIRED_FILES:
        assert not (REPO_ROOT / path).exists(), f"退役文件回潮: {path}"
    for suffix, marker in RETIRED_MARKERS:
        matches = list(REPO_ROOT.rglob(suffix))
        assert matches, f"锚文件不存在: {suffix}"
        for m in matches:
            if ".venv" in m.parts or "node_modules" in m.parts:
                continue
            assert marker not in m.read_text(encoding="utf-8", errors="replace"), (
                f"退役标记 {marker!r} 回潮于 {m}"
            )
