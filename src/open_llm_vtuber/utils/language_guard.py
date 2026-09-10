"""角色语言的兜底保护：检测回复语言，不符合时触发一次重试。

背景：小模型（如 qwen3.5:9b）即使 system prompt 里明确要求"只用日语回答"，
在用户说中文 + 人设是中文时，仍会以约 4% 的概率跟随输入语言改用中文。
提示词层面的调优（把指令放末尾、降低温度）实测都无法把它降到 0，所以这里在
应用层做确定性兜底：第一句就被判定为错误语言时，丢弃并重试一次。

判定用字符种类启发式，够快且对 CJK 场景准确：
- 目标日语：出现假名即视为正确；整句只有汉字则判为中文
- 目标中文/粤语：只有汉字、无假名即视为正确
- 目标英语：只有拉丁字母视为正确
- 目标韩语：出现谚文视为正确
样本太短（判据不足）时返回 None（不判定），避免误杀。
"""

import re
from typing import Optional

# 判定所需的最少有效字符数，太短不下结论
_MIN_CHARS = 6

_KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")
# 表情/动作关键词 [joy] 与 <think> 标签里的内容不参与语言判定
_BRACKETS = re.compile(r"\[[^\[\]]*\]")
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# 语言代码 -> (英文名, 该语言自称)
_LANGUAGE_NAMES = {
    "zh": ("Chinese", "中文"),
    "ja": ("Japanese", "日本語"),
    "en": ("English", "English"),
    "ko": ("Korean", "한국어"),
    "yue": ("Cantonese", "粤语"),
}

# 各语言的重试提醒：用该语言自身的祈使句 + 中文补充，对中文语境的模型约束力最强
_RETRY_BODY = {
    "ja": "必ず日本語のみで回答してください。",
    "zh": "必须只用中文回答。",
    "en": "You must reply only in English.",
    "ko": "반드시 한국어로만 답변하세요.",
    "yue": "必須只用粵語回答。",
}


def _strip_noise(text: str) -> str:
    """去掉表情关键词与 think 标签，只留自然语言部分。"""
    return _THINK.sub("", _BRACKETS.sub("", text or ""))


def normalize_language(language: Optional[str]) -> str:
    """把配置里的 language 归一化成受支持的语言代码；不支持或为空返回空串。"""
    lang = (language or "").strip().lower()
    if lang in ("", "auto"):
        return ""
    return lang if lang in _LANGUAGE_NAMES else ""


def detect_language_mismatch(text: str, target: str) -> Optional[bool]:
    """判断 text 的语言是否与 target 不符。

    Returns:
        True  = 明确不符（应重试）
        False = 符合
        None  = 样本不足或无法判定（不干预）
    """
    target = normalize_language(target)
    if not target:
        return None

    cleaned = _strip_noise(text)
    n_kana = len(_KANA.findall(cleaned))
    n_hangul = len(_HANGUL.findall(cleaned))
    n_cjk = len(_CJK.findall(cleaned))
    n_latin = len(_LATIN.findall(cleaned))

    if n_kana + n_hangul + n_cjk + n_latin < _MIN_CHARS:
        return None

    if target == "ja":
        if n_kana > 0:
            return False
        # 一个假名都没有、却有大段汉字 → 判为中文
        return True if n_cjk >= _MIN_CHARS else None

    if target in ("zh", "yue"):
        if n_kana > 0:
            return True
        return False if n_cjk >= _MIN_CHARS else None

    if target == "ko":
        if n_hangul > 0:
            return False
        return True if (n_cjk + n_kana) >= _MIN_CHARS else None

    if target == "en":
        if n_cjk + n_kana + n_hangul >= _MIN_CHARS:
            return True
        return False if n_latin >= _MIN_CHARS else None

    return None


def build_retry_reminder(target: str) -> str:
    """构造重试时追加到 system prompt 末尾的强提醒。

    放在末尾是为了利用近因效应；同时给出该语言的祈使句和中文说明。
    """
    target = normalize_language(target)
    if not target:
        return ""
    english, native = _LANGUAGE_NAMES[target]
    body = _RETRY_BODY.get(target, f"You must reply only in {english}.")
    return (
        "[Language Requirement — 重要 / 再確認]\n"
        f"{body}\n"
        f"无论用户使用什么语言，你都只能使用{native}（{english}）回答，"
        "绝对不要使用其他语言。"
    )
