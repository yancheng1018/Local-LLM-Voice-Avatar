# -*- coding: utf-8 -*-
"""模型加载守护——GUI 人设空值拦截 / main.ts 模型名赋值时机 / model_dict 结构完整性。

依据：docs/context/research_minimal-frontend-bugs.md（F1.2 / F2b.2）。
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUI = ROOT / "launcher" / "OpenLLMVTuber_GUI.py"
MAIN_TS = ROOT / "frontend-minimal" / "src" / "main.ts"
MODEL_DICT = ROOT / "model_dict.json"


def method_body(source: str, signature: str, indent: str) -> str:
    m = re.search(
        re.escape(signature)
        + r"(?P<body>[\s\S]*?)\n"
        + re.escape(indent)
        + r"(?:async )?def ",
        source,
    )
    assert m, f"method body not found: {signature}"
    return m.group("body")


def test_gui_save_blocks_empty_persona():
    src = GUI.read_text(encoding="utf-8")
    body = method_body(src, "    def _save_character_inline", "        ")
    guard = body.find("persona_text = self.char_edit_persona.toPlainText().strip()")
    warn = body.find("人设不能为空")
    ret = body.find("return", warn)
    assign = body.find('cc["persona_prompt"] = persona_text')
    assert guard != -1 and warn != -1 and assign != -1
    assert guard < assign, "空值守卫必须位于 persona_prompt 写回之前"
    assert -1 < ret < assign, "守卫必须 return，阻止落盘"
    assert 'cc["persona_prompt"] = self.char_edit_persona.toPlainText()' not in body


def test_main_ts_assigns_model_name_after_load():
    src = MAIN_TS.read_text(encoding="utf-8")
    h = src.find("ws.register('set-model-and-conf'")
    assert h != -1
    then = src.find(".then(", h)
    catch = src.find(".catch(", h)
    assert then != -1 and catch != -1
    assigns = [
        m.start() for m in re.finditer(r"currentLive2DModelName = modelInfo\.name", src)
    ]
    assert assigns, "赋值语句必须存在"
    assert all(then < i < catch for i in assigns), "赋值必须且只能在 .then 内"
    catch_body = src[catch : catch + 600]
    assert "currentLive2DModelName = ''" in catch_body, "catch 必须清空当前模型名"
    head = src[h:then]
    assert "currentLive2DModelName = modelInfo.name" not in head, "加载前不得提前赋值"


def test_model_dict_entries_intact():
    data = json.loads(MODEL_DICT.read_text(encoding="utf-8"))
    for e in data:
        assert isinstance(e.get("name"), str) and isinstance(e.get("url"), str)
