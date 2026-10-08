"""live2d_model=None 降级守卫契约测试（github-p3-public-h，spec v2 §4）。

init_live2d 对未登记模型容错后 live2d_model 停留 None（service_context.py:335-342），
历史行为=连接链无守卫解引用 None.model_info 砖死全部 WS 连接。本文件钉死三条契约：
① 容错后 None 态可检（init_live2d 失败不赋值）；② 所有 set-model-and-conf 发送点对
None 守卫（model_info 发 null，前端 main.ts 现成降级）；③ switch_live2d_model 从
None 态可恢复（重选任意已登记模型），未登记名抛 KeyError 且状态不变。
静态断言（⑥⑦）书写纪律：空白不敏感正则（minimal-frontend-model-switch.md:16-20）。
"""

import asyncio
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.open_llm_vtuber.live2d_model import Live2dModel
from src.open_llm_vtuber.service_context import ServiceContext
from src.open_llm_vtuber.websocket_handler import WebSocketHandler

ROOT = Path(__file__).resolve().parents[1]


class FakeWS:
    """收集 send_text 的最小 WebSocket 替身。"""

    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


class StubAgent:
    """记录 set_live2d_model / set_system 调用的最小 agent 替身。"""

    def __init__(self):
        self.model_calls = []
        self.system_calls = []

    def set_live2d_model(self, model):
        self.model_calls.append(model)

    def set_system(self, prompt):
        self.system_calls.append(prompt)


def _make_handler():
    handler = WebSocketHandler.__new__(WebSocketHandler)

    async def _noop_group_update(websocket, client_uid):
        pass

    handler.send_group_update = _noop_group_update
    return handler


def _make_ctx_none_model():
    ctx = ServiceContext.__new__(ServiceContext)
    ctx.live2d_model = None
    ctx.character_config = SimpleNamespace(
        character_name="風雲", conf_uid="kazagumo_001"
    )
    return ctx


def _make_switch_ctx():
    """None 态 ServiceContext：属性逐个显式挂上（__new__ 绕开 __init__ 无任何属性）。"""
    ctx = ServiceContext.__new__(ServiceContext)
    ctx.live2d_model = None
    ctx.character_config = SimpleNamespace(
        live2d_model_name="fengyun_4",
        persona_prompt="p",
        language="ja",
        human_name="指揮官",
    )
    ctx.agent_engine = StubAgent()
    ctx.system_prompt = "old"

    async def _fake_construct(persona_prompt, language="", human_name=""):
        return "new-prompt"

    ctx.construct_system_prompt = _fake_construct
    return ctx


def test_init_live2d_unknown_model_leaves_none():
    ctx = ServiceContext.__new__(ServiceContext)
    ctx.live2d_model = None
    ctx.character_config = SimpleNamespace()
    ctx.init_live2d("no_such_model_xyz")
    assert ctx.live2d_model is None


def test_send_initial_messages_none_model_sends_null_model_info():
    handler = _make_handler()
    ws = FakeWS()
    ctx = _make_ctx_none_model()
    asyncio.run(handler._send_initial_messages(ws, "uid-1", ctx))
    assert len(ws.sent) == 3
    assert json.loads(ws.sent[0]) == {
        "type": "full-text",
        "text": "Connection established",
    }
    model_msg = json.loads(ws.sent[1])
    assert model_msg["type"] == "set-model-and-conf"
    assert model_msg["model_info"] is None
    assert model_msg["conf_name"] == "風雲"
    assert model_msg["conf_uid"] == "kazagumo_001"
    assert model_msg["client_uid"] == "uid-1"
    assert json.loads(ws.sent[2]) == {"type": "control", "text": "start-mic"}


def test_send_initial_messages_with_model_passes_model_info():
    handler = _make_handler()
    ws = FakeWS()
    ctx = _make_ctx_none_model()
    ctx.live2d_model = SimpleNamespace(model_info={"name": "mao_pro", "url": "/x"})
    asyncio.run(handler._send_initial_messages(ws, "uid-1", ctx))
    model_msg = json.loads(ws.sent[1])
    assert model_msg["model_info"] == {"name": "mao_pro", "url": "/x"}


def test_switch_live2d_model_from_none_state_recovers():
    ctx = _make_switch_ctx()
    asyncio.run(ctx.switch_live2d_model("mao_pro"))
    assert isinstance(ctx.live2d_model, Live2dModel)
    assert ctx.live2d_model.live2d_model_name == "mao_pro"
    assert ctx.character_config.live2d_model_name == "mao_pro"
    agent = ctx.agent_engine
    assert agent.model_calls and agent.model_calls[0] is ctx.live2d_model
    assert agent.system_calls == ["new-prompt"]
    assert ctx.system_prompt == "new-prompt"


def test_switch_live2d_model_bad_name_from_none_raises_state_unchanged():
    ctx = _make_switch_ctx()
    with pytest.raises(KeyError):
        asyncio.run(ctx.switch_live2d_model("no_such_model_xyz"))
    assert ctx.live2d_model is None
    assert ctx.character_config.live2d_model_name == "fengyun_4"


def test_handle_config_switch_model_info_guard_static():
    src = (ROOT / "src" / "open_llm_vtuber" / "service_context.py").read_text(
        encoding="utf-8"
    )
    assert re.search(
        r'"model_info":\s*self\.live2d_model\.model_info\s+if\s+self\.live2d_model\s+else\s+None',
        src,
    )


def test_switch_model_send_site_unreachable_none_documented():
    src = (ROOT / "src" / "open_llm_vtuber" / "websocket_handler.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r"await context\.switch_live2d_model\(model_name\)", src)
    assert match, "switch 调用点消失"
    after_lines = src[match.end() :].splitlines()[:20]
    assert any("Live2D 模型切换失败：模型加载失败" in line for line in after_lines), (
        "切换失败回退路径改变，发送点非 None 论证前提失效"
    )
