# -*- coding: utf-8 -*-
"""动作链条修正 §5.2：库 idle 自动播放关闭（idleMotionGroup 哨兵组）静态断言。

库仅在 idleMotionGroup truthy 时覆盖 groups.idle（cubism4.es.js:8540），故哨兵
必须是非空字面量；不存在的组名使 startRandomMotion 安全返回 false（:8683）。
idle 播放统一走本地 playIdleOnce()。语义见 temp_spec_live2d动作链条修正.md §3。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根
L2D = ROOT / "frontend-minimal" / "src" / "renderer" / "l2d.ts"


def read() -> str:
    return L2D.read_text(encoding="utf-8")


def test_idle_motion_group_sentinel():
    src = read()
    opts = src.split("Live2DModel.from(modelInfo.url, {", 1)[1].split("});", 1)[0]
    assert "idleMotionGroup: '__no_auto_idle__'," in opts
    assert "autoFocus: true" in opts
    assert "idleMotionGroup: ''" not in src  # 空串 truthy 检查不过 = 无效（库不覆盖）


def test_idle_group_name_logic_unchanged():
    src = read()
    assert (
        "return idx > 0 ? 'idle' + idx : 'idle';" in src
    )  # playIdleOnce 选组逻辑未被波及
