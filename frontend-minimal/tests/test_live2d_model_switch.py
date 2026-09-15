# -*- coding: utf-8 -*-
"""stage4：同角色切换 Live2D 模型（后端驱动）——静态契约 + 运行时白名单过滤 + 构建产物。

契约依据：docs/context/live2d.md 硬性契约第 8/9 条——Agent 重绑定必须走
BasicMemoryAgent.set_live2d_model() / set_system()，禁止直写私有属性。

stage5：一角色多模型 allowlist（本文件新增 5 用例）。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
FM = ROOT / "frontend-minimal"
BACKEND = ROOT / "src" / "open_llm_vtuber"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_fm(rel: str) -> str:
    return (FM / rel).read_text(encoding="utf-8")


def method_body(source: str, signature: str, indent: str = "    ") -> str:
    """截取到下一个同级 def/async def；避免全文件比较误伤同名调用。"""
    m = re.search(
        re.escape(signature) + r"(?P<body>[\s\S]*?)\n" + indent + r"(?:async )?def ",
        source,
    )
    assert m, f"method body not found: {signature}"
    return m.group("body")


# ---- 后端：live2d_model.py ----


def test_model_list_filters_spine():
    src = read(BACKEND / "live2d_model.py")
    assert "def list_frontend_models" in src
    body = method_body(src, "def list_frontend_models", indent="    ")
    for frag in (
        "isinstance(raw, list)",
        "isinstance(name, str)",
        "isinstance(url, str)",
        '.endswith(".skel")',
        '{"name": name}',
    ):
        assert frag in body, frag


def test_list_frontend_models_runtime_filters(tmp_path):
    """运行时真实过滤：只读临时文件，不依赖本机 model_dict.json。"""
    model_dict = tmp_path / "model_dict.json"
    model_dict.write_text(
        json.dumps(
            [
                {"name": "good", "url": "/live2d-models/good/good.model3.json"},
                {"name": "bad_spine", "url": "/Spine-models/x/x.skel"},
                {"name": "no_url"},
                "not-a-dict",
                {"name": 123, "url": "/live2d-models/n/n.model3.json"},
            ]
        ),
        encoding="utf-8",
    )

    sys.path.insert(0, str(ROOT / "src"))
    try:
        from open_llm_vtuber.live2d_model import Live2dModel
    finally:
        sys.path.pop(0)

    assert Live2dModel.list_frontend_models(str(model_dict)) == [{"name": "good"}]


# ---- 后端：basic_memory_agent.py（v2 §2）----


def test_basic_memory_agent_rebinds_decorator_pipeline():
    src = read(BACKEND / "agent" / "agents" / "basic_memory_agent.py")
    assert "def set_live2d_model(self, live2d_model)" in src
    body = method_body(src, "def set_live2d_model(self, live2d_model)")
    assert body.index("self._live2d_model = live2d_model") < body.index(
        "self.chat = self._chat_function_factory()"
    )
    assert "_memory" not in body
    assert "_set_llm" not in body


def test_pipeline_captures_private_model_field():
    src = read(BACKEND / "agent" / "agents" / "basic_memory_agent.py")
    body = method_body(src, "def _chat_function_factory")
    assert "display_processor(live2d_model=self._live2d_model)" in body
    assert "actions_extractor(self._live2d_model)" in body


# ---- 后端：service_context.py（v2 §3）----


def test_context_switch_uses_public_agent_contract():
    src = read(BACKEND / "service_context.py")
    body = method_body(src, "async def switch_live2d_model")
    # 断言调用而非书写格式：ruff format 可能把带尾注释的调用折成多行
    assert re.search(r"agent\.set_live2d_model\(\s*candidate\s*\)", body)
    assert re.search(r"agent\.set_system\(\s*prompt\s*\)", body)
    assert "agent.live2d_model =" not in body
    assert "agent._system =" not in body
    # 不绑定 getattr 的写法细节（可能被格式化成多行）
    assert '"set_live2d_model"' in body and "callable" in body
    assert "old_model" in body


def test_context_switch_is_atomic_and_refreshes_agent():
    src = read(BACKEND / "service_context.py")
    body = method_body(src, "async def switch_live2d_model")
    assert body.index("candidate = Live2dModel(model_name)") < body.index(
        "self.live2d_model = candidate"
    )
    assert "init_agent(" not in body
    assert "load_from_config(" not in body
    # 回滚必须真实存在：agent 回滚 + context 三处复位 + 原异常继续抛出。
    # 不能断言裸 "try:"——方法体切片以 try: 开头，该断言恒真。
    assert "except Exception:" in body
    assert body.count("agent.set_live2d_model(old_model)") == 1
    assert body.count("agent.set_system(old_system_prompt)") == 1
    assert "self.live2d_model = old_model" in body
    assert "self.character_config.live2d_model_name = old_model_name" in body
    assert "self.system_prompt = old_system_prompt" in body
    assert re.search(r"except Exception:[\s\S]*?raise\b", body)


# ---- 后端：websocket_handler.py（v1 §2/§3.3）----


def test_ws_protocol_registered():
    src = read(BACKEND / "websocket_handler.py")
    assert re.search(
        r'CONFIG = \[[^\]]*"fetch-live2d-models"[^\]]*"switch-live2d-model"', src
    )
    assert '"fetch-live2d-models": self._handle_fetch_live2d_models' in src
    assert '"switch-live2d-model": self._handle_live2d_model_switch' in src
    assert re.search(
        r"async def _handle_fetch_live2d_models\(\s*self, websocket: WebSocket, client_uid: str, data: WSMessage\s*\) -> None",
        src,
    )
    assert re.search(
        r"async def _handle_live2d_model_switch\(\s*self, websocket: WebSocket, client_uid: str, data: WSMessage\s*\) -> None",
        src,
    )


def test_ws_whitelist_and_error_contract():
    src = read(BACKEND / "websocket_handler.py")
    body = method_body(src, "async def _handle_live2d_model_switch")
    assert "list_frontend_models" not in body, "白名单校验应留在持锁的方法体内"
    assert "active_model_switches" in body
    assert "current_conversation_tasks" not in body, "对话中判断应留在持锁的方法体内"
    # 取锁与持锁调用之间不得有 await（两者紧邻）；先证切片非空再切，防空切片恒真
    add_at = body.index("active_model_switches.add")
    call_at = body.index("await self._switch_live2d_model_locked")
    assert add_at < call_at
    assert "await " not in body[add_at:call_at]

    inner = method_body(src, "async def _switch_live2d_model_locked")
    assert "resolve_allowed_model_names" in inner
    assert "model_name not in allowed" in inner
    assert "current_conversation_tasks" in inner
    assert "Live2D 模型切换失败" in inner
    assert "set-model-and-conf" in inner
    # conf_name/conf_uid 必须取自局部快照，而非切换后 context 的残余状态
    assert re.search(r"conf_name = context\.character_config", inner)
    assert re.search(r'"conf_name": conf_name', inner)
    assert re.search(r'"conf_uid": conf_uid', inner)


# ---- 前端：index.html / ui.ts ----


def test_model_selector_markup_and_ui():
    html = read_fm("index.html")
    assert re.search(r'id="model-select"[^>]*disabled', html)
    ui = read_fm("src/ui.ts")
    for frag in (
        "Live2DModelOption",
        "onSwitchLive2DModel",
        "setLive2DModels",
        "setLive2DModelEnabled",
        "models.length < 2",
    ):
        assert frag in ui, frag


def test_main_protocol_and_load_gating():
    main = read_fm("src/main.ts")
    for frag in (
        "fetch-live2d-models",
        "live2d-models",
        "switch-live2d-model",
        "currentLive2DModelName",
        "setLive2DModelEnabled(false)",
    ):
        assert frag in main, frag
    assert re.search(r"\.then\(\(\) => \{[\s\S]*?setLive2DModelEnabled\(true\)", main)
    # 成功分支：先报连接成功再解锁并刷新列表
    assert re.search(
        r"已连接[\s\S]*?setLive2DModelEnabled\(true\)[\s\S]*?fetch-live2d-models", main
    )
    # catch 分支单独解锁，且不带 fetch
    catch_body = re.search(r"\.catch\(\(e\) => \{[\s\S]*?\n    \}\);", main)
    assert catch_body, ".catch block not found"
    assert "setLive2DModelEnabled(true)" in catch_body.group(0)
    assert "fetch-live2d-models" not in catch_body.group(0)


def test_no_frontend_only_renderer_load():
    main = read_fm("src/main.ts")
    m = re.search(
        r"ui\.onSwitchLive2DModel = \(modelName\) => \{(?P<body>[\s\S]*?)\n\};", main
    )
    assert m, "ui.onSwitchLive2DModel block not found"
    body = m.group("body")
    assert "ws.send({ type: 'switch-live2d-model'" in body
    assert ".load(" not in body


def test_css_reuses_select_rules():
    css = read_fm("src/style.css")
    assert re.search(r"#char-select,\s*\n#model-select \{", css)
    # 合并选择器里也含 "#model-select {"，先摘掉表头再找独立规则
    css_wo_merged = re.sub(r"#char-select,\s*\n#model-select \{", "", css)
    m = re.search(r"#model-select \{(?P<body>[^}]*)\}", css_wo_merged)
    assert m, "#model-select standalone rule not found"
    assert "max-width" in m.group("body")
    assert "margin-left" not in m.group("body")


def test_build_and_bundle():
    r = subprocess.run(
        "npm --prefix frontend-minimal run build",
        shell=True,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "")[-2000:])
        sys.stderr.write((r.stderr or "")[-2000:])
    assert r.returncode == 0
    html = (FM / "dist" / "index.html").read_text(encoding="utf-8")
    assert "model-select" in html
    js = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.js")
    )
    assert "switch-live2d-model" in js
    assert "fetch-live2d-models" in js
    css = "".join(
        p.read_text(encoding="utf-8") for p in (FM / "dist" / "assets").glob("*.css")
    )
    assert "#model-select" in css


# ---- stage5：一角色多模型 allowlist ----


def test_resolver_runtime_allowlist(tmp_path):
    model_dict = tmp_path / "model_dict.json"
    model_dict.write_text(
        json.dumps(
            [
                {"name": "mao", "url": "/live2d-models/mao/mao.model3.json"},
                {"name": "shizuku", "url": "/live2d-models/s/s.model3.json"},
                {"name": "spine1", "url": "/Spine-models/x/x.skel"},
            ]
        ),
        encoding="utf-8",
    )

    sys.path.insert(0, str(ROOT / "src"))
    try:
        from open_llm_vtuber.websocket_handler import resolve_allowed_model_names
    finally:
        sys.path.pop(0)

    p = str(model_dict)
    assert resolve_allowed_model_names([], "mao", p) == ["mao", "shizuku"]
    assert resolve_allowed_model_names(["shizuku", "ghost", "mao"], "shizuku", p) == [
        "shizuku",
        "mao",
    ]
    assert resolve_allowed_model_names(["mao"], "shizuku", p) == ["mao", "shizuku"]
    assert resolve_allowed_model_names(["mao"], "spine1", p) == ["mao"]
    assert resolve_allowed_model_names(["ghost"], "ghost", p) == []


def test_character_config_model_names_field():
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from open_llm_vtuber.config_manager.character import CharacterConfig
    finally:
        sys.path.pop(0)

    assert "live2d_model_names" in CharacterConfig.model_fields
    assert CharacterConfig.model_fields["live2d_model_names"].default_factory is list
    assert CharacterConfig.check_live2d_model_names(["a", " ", "a", "b"]) == ["a", "b"]
    assert CharacterConfig.check_live2d_model_names(None) == []


def test_ws_fetch_uses_character_allowlist():
    src = read(BACKEND / "websocket_handler.py")
    body = method_body(src, "async def _handle_fetch_live2d_models")
    assert "resolve_allowed_model_names" in body
    assert "live2d_model_names" in body
    assert "list_frontend_models" not in body


def test_ws_switch_validates_character_allowlist():
    src = read(BACKEND / "websocket_handler.py")
    body = method_body(src, "async def _switch_live2d_model_locked")
    assert "resolve_allowed_model_names" in body
    assert "live2d_model_names" in body
    assert "list_frontend_models" not in body


def test_launcher_editor_handles_model_names():
    src = read(ROOT / "launcher" / "OpenLLMVTuber_GUI.py")
    assert re.search(r'cc\["live2d_model_names"\]\s*=\s*model_names', src)
    assert re.search(r'join\(cc\.get\("live2d_model_names"\)\s*or\s*\[\]\)', src)
    assert 'char_edit_fields["live2d_model_names"]' not in src


# ---- stage5 修复：切换角色不得继承上一角色的 allowlist ----


def test_config_switch_merges_from_base_not_current():
    src = read(BACKEND / "service_context.py")
    # handle_config_switch 是类内最后一个方法，其后是模块级 def deep_merge
    # （0 缩进），method_body 的同级 def 终止符（4 空格缩进）匹配不到，
    # 故局部切片截取到下一个模块级 def
    start = src.index("async def handle_config_switch")
    body = src[start : src.index("\ndef ", start)]
    # 旧形态（当前角色配置作 merge 底）不得回归：可选键会跨角色残留
    assert "self.config.character_config.model_dump(), alt_config_data" not in body
    # 新形态：merge 底 = conf.yaml 自身块；不得套默认角色指针
    # （默认角色的可选键会泄漏给所有未定义该键的角色——fix1 实测翻车点）
    assert not re.search(r"base_character_data\s*=\s*apply_default_character", body)
    assert re.search(
        r'base_character_data\s*=\s*read_yaml\(\s*"conf\.yaml"\s*\)'
        r'\s*\.get\(\s*"character_config"\s*\)',
        body,
    )
    assert re.search(
        r"deep_merge\(\s*base_character_data\s*,\s*alt_config_data\s*\)", body
    )
