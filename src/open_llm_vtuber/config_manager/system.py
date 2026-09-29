# config_manager/system.py
from pydantic import Field, model_validator
from typing import Dict, ClassVar
from .i18n import I18nMixin, Description


class SystemConfig(I18nMixin):
    """System configuration settings."""

    conf_version: str = Field(..., alias="conf_version")
    host: str = Field(..., alias="host")
    port: int = Field(..., alias="port")
    config_alts_dir: str = Field(..., alias="config_alts_dir")
    default_character: str = Field("", alias="default_character")
    tool_prompts: Dict[str, str] = Field(..., alias="tool_prompts")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "conf_version": Description(en="Configuration version", zh="配置文件版本"),
        "host": Description(en="Server host address", zh="服务器主机地址"),
        "port": Description(en="Server port number", zh="服务器端口号"),
        "config_alts_dir": Description(
            en="Directory for alternative configurations", zh="备用配置目录"
        ),
        "default_character": Description(
            en=(
                "Filename of the character to load by default (e.g. 'mao_pro.yaml'). "
                "It is merged over this file's own character_config at startup. "
                "Leave empty to use the character_config below as-is."
            ),
            zh=(
                "默认加载的角色文件名（如 'mao_pro.yaml'），启动时会把它合并到本文件自身的 "
                "character_config 之上。留空表示直接使用下面的 character_config。"
            ),
        ),
        "tool_prompts": Description(
            en="Tool prompts to be inserted into persona prompt",
            zh="要插入到角色提示词中的工具提示词",
        ),
    }

    @model_validator(mode="after")
    def check_port(cls, values):
        port = values.port
        if port < 0 or port > 65535:
            raise ValueError("Port must be between 0 and 65535")
        return values
