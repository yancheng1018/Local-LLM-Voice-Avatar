# config_manager/character.py
from pydantic import Field, field_validator
from typing import Dict, ClassVar
from .i18n import I18nMixin, Description
from .asr import ASRConfig
from .tts import TTSConfig
from .vad import VADConfig
from .tts_preprocessor import TTSPreprocessorConfig

from .agent import AgentConfig


class CharacterConfig(I18nMixin):
    """Character configuration settings."""

    conf_uid: str = Field(..., alias="conf_uid")
    live2d_model_name: str = Field(..., alias="live2d_model_name")
    character_name: str = Field(..., alias="character_name")
    human_name: str = Field(default="Human", alias="human_name")
    avatar: str = Field(default="", alias="avatar")
    language: str = Field(default="", alias="language")
    persona_prompt: str = Field(..., alias="persona_prompt")
    agent_config: AgentConfig = Field(..., alias="agent_config")
    asr_config: ASRConfig = Field(..., alias="asr_config")
    tts_config: TTSConfig = Field(..., alias="tts_config")
    vad_config: VADConfig = Field(..., alias="vad_config")
    tts_preprocessor_config: TTSPreprocessorConfig = Field(
        ..., alias="tts_preprocessor_config"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "conf_uid": Description(
            en="Unique identifier for the character configuration",
            zh="角色配置唯一标识符（同时用作聊天记录的存储目录名）",
        ),
        "live2d_model_name": Description(
            en="Name of the Live2D model to use", zh="使用的Live2D模型名称"
        ),
        "character_name": Description(
            en="Name of the AI character in conversation",
            zh="角色名。界面（含 Web UI 的角色列表）显示的就是它，需保持唯一",
        ),
        "persona_prompt": Description(
            en="Persona prompt. The persona of your character.", zh="角色人设提示词"
        ),
        "agent_config": Description(
            en="Configuration for the conversation agent", zh="对话代理配置"
        ),
        "asr_config": Description(
            en="Configuration for Automatic Speech Recognition", zh="语音识别配置"
        ),
        "tts_config": Description(
            en="Configuration for Text-to-Speech", zh="语音合成配置"
        ),
        "vad_config": Description(
            en="Configuration for Voice Activity Detection", zh="语音活动检测配置"
        ),
        "tts_preprocessor_config": Description(
            en="Configuration for Text-to-Speech Preprocessor",
            zh="语音合成预处理器配置",
        ),
        "human_name": Description(
            en="Name of the human user in conversation", zh="对话中人类用户的名字"
        ),
        "avatar": Description(
            en="Avatar image path for the character", zh="角色头像图片路径"
        ),
        "language": Description(
            en=(
                "Reply language of this character. The character always answers in this "
                "language regardless of the language the user writes in, and the TTS "
                "output uses it too. One of: '' (no restriction), zh, ja, en, ko, yue, "
                "auto. Select it in the launcher instead of typing."
            ),
            zh=(
                "该角色的回答语言。无论用户说什么语言，角色都只用该语言回答，"
                "TTS 也按该语言合成。可选值：''（不限制）/ zh / ja / en / ko / yue / auto。"
                "请在启动器里下拉选择，不要手写。"
            ),
        ),
    }

    @field_validator("persona_prompt")
    def check_default_persona_prompt(cls, v):
        if not v:
            raise ValueError(
                "Persona_prompt cannot be empty. Please provide a persona prompt."
            )
        return v

    @field_validator("character_name")
    def check_character_name(cls, v):
        # 角色名是界面上的唯一显示名，前端用它反查配置，不能为空
        if not v or not str(v).strip():
            raise ValueError(
                "character_name cannot be empty. It is the display name shown in "
                "the UI and must be unique among characters."
            )
        return v

    @field_validator("conf_uid")
    def check_conf_uid(cls, v):
        # conf_uid 会被用作 chat_history/<conf_uid>/ 的目录名
        if not v or not str(v).strip():
            raise ValueError("conf_uid cannot be empty.")
        invalid = set('\\/:*?"<>|')
        if any(ch in invalid for ch in str(v)):
            raise ValueError(
                f"conf_uid cannot contain path separators or reserved characters "
                f"({' '.join(sorted(invalid))}): {v!r}"
            )
        return v

    @field_validator("language")
    def check_language(cls, v):
        # 白名单校验：该字段应由启动器下拉选择，手写错误在这里就被拦住
        if v is None:
            return ""
        allowed = ("", "zh", "ja", "en", "ko", "yue", "auto")
        value = str(v).strip().lower()
        if value not in allowed:
            raise ValueError(
                f"language must be one of {allowed} (got {v!r}). "
                "Pick it from the dropdown in the launcher instead of typing."
            )
        return value
