# config_manager/utils.py
import yaml
from pathlib import Path
from typing import Union, Dict, Any, TypeVar
from pydantic import BaseModel, ValidationError
import os
import re
import chardet
from loguru import logger

from .main import Config

T = TypeVar("T", bound=BaseModel)


def read_yaml(config_path: str) -> Dict[str, Any]:
    """
    Read the specified YAML configuration file with environment variable substitution
    and guess encoding. Return the configuration data as a dictionary.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Configuration data as a dictionary.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        IOError: If the configuration file cannot be read.
    """

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    content = load_text_file_with_guess_encoding(config_path)
    if not content:
        raise IOError(f"Failed to read configuration file: {config_path}")

    # Replace environment variables
    pattern = re.compile(r"\$\{(\w+)\}")

    def replacer(match):
        env_var = match.group(1)
        return os.getenv(env_var, match.group(0))

    content = pattern.sub(replacer, content)

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.critical(f"Error parsing YAML file: {e}")
        raise e


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into a copy of ``base``.

    Values in ``override`` win; nested dicts are merged instead of replaced.
    """
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def apply_default_character(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the character named by ``system_config.default_character`` over the base config.

    ``conf.yaml`` only stores a *pointer* to the default character file so that it
    stays pristine — repeatedly switching characters would otherwise accumulate
    leftovers, because merging is always done against the current (already merged)
    config.

    The pointer file is resolved inside ``system_config.config_alts_dir``.
    An empty pointer, a missing file, or malformed content leaves the config
    untouched (a warning is logged) so a bad pointer can never block startup.

    Args:
        raw_config: The raw (not yet validated) configuration dict.

    Returns:
        A new config dict with the default character merged into ``character_config``.
    """
    system_cfg = raw_config.get("system_config") or {}
    pointer = str(system_cfg.get("default_character") or "").strip()
    if not pointer:
        return raw_config

    alts_dir = str(system_cfg.get("config_alts_dir") or "characters")
    char_path = Path(alts_dir) / pointer
    if not char_path.is_file():
        logger.warning(
            f"default_character points to a missing file, ignoring it: {char_path}"
        )
        return raw_config

    try:
        char_config = read_yaml(str(char_path))
    except Exception as e:
        logger.warning(f"Failed to read default character {char_path}: {e}")
        return raw_config

    alt_cc = (char_config or {}).get("character_config")
    if not isinstance(alt_cc, dict) or not alt_cc:
        logger.warning(
            f"default character {char_path} has no usable character_config, ignoring it"
        )
        return raw_config

    merged = dict(raw_config)
    base_cc = merged.get("character_config") or {}
    merged["character_config"] = _deep_merge(base_cc, alt_cc)
    logger.info(f"Applied default character '{pointer}' from {alts_dir}/")
    return merged


def validate_config(config_data: dict) -> Config:
    """
    Validate configuration data against the Config model.

    Args:
        config_data: Configuration data to validate.

    Returns:
        Validated Config object.

    Raises:
        ValidationError: If the configuration fails validation.
    """
    try:
        return Config(**config_data)
    except ValidationError as e:
        logger.critical(f"Error validating configuration: {e}")
        logger.error("Configuration data:")
        logger.error(config_data)
        raise e


def load_text_file_with_guess_encoding(file_path: str) -> str | None:
    """
    Load a text file with guessed encoding.

    Parameters:
    - file_path (str): The path to the text file.

    Returns:
    - str: The content of the text file or None if an error occurred.
    """
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii", "cp936"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    # If common encodings fail, try chardet to guess the encoding
    try:
        with open(file_path, "rb") as file:
            raw_data = file.read()
        detected = chardet.detect(raw_data)
        if detected["encoding"]:
            return raw_data.decode(detected["encoding"])
    except Exception as e:
        logger.error(f"Error detecting encoding for config file {file_path}: {e}")
    return None


def save_config(config: BaseModel, config_path: Union[str, Path]):
    """
    Saves a Pydantic model to a YAML configuration file.

    Args:
        config: The Pydantic model to save.
        config_path: Path to the YAML configuration file.
    """
    config_file = Path(config_path)
    config_data = config.model_dump(
        by_alias=True, exclude_unset=True, exclude_none=True
    )

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error writing YAML file: {e}")


def _character_display_name(config: dict | None, fallback: str) -> str:
    """取角色的显示名。

    前端把列表项的 label 与"身份标识"绑成一个字段，并靠它反查配置文件，
    所以这里必须返回稳定且唯一的值：优先 character_name，其次 conf_uid，最后文件名。
    """
    if not config:
        return fallback
    cc = config.get("character_config", config)
    return str(cc.get("character_name") or cc.get("conf_uid") or fallback)


def scan_config_alts_directory(config_alts_dir: str) -> list[dict]:
    """
    Scan the config_alts directory and return a list of config information.
    Each config info contains the filename and its display name from the config.

    The display name is the character's ``character_name`` (falling back to
    ``conf_uid`` then the filename). The Web UI renders this value *and* uses it
    to map back to a filename, so it must be unique across all entries.

    Parameters:
    - config_alts_dir (str): The path to the config_alts directory.

    Returns:
    - list[dict]: A list of dicts containing config info:
        - filename: The actual config file name
        - name: Display name from config, falls back to the filename
    """
    config_files = []
    seen_names = set()

    # 先扫描角色文件，让它们的名字优先于 conf.yaml 的基础条目
    for root, _, files in os.walk(config_alts_dir):
        for file in files:
            if file.endswith(".yaml"):
                config: dict = read_yaml(os.path.join(root, file))
                name = _character_display_name(config, file)
                seen_names.add(name)
                config_files.append({"filename": file, "name": name})

    # 只有当 conf.yaml 的角色没有被任何角色文件代表时才插入它。
    # 否则列表里会出现两个同名条目，而前端按名字反查文件名时取首个匹配，
    # 会解析到错误的配置。
    default_config = read_yaml("conf.yaml")
    default_name = _character_display_name(default_config, "conf.yaml")
    if default_name not in seen_names:
        config_files.insert(0, {"filename": "conf.yaml", "name": default_name})
    logger.debug(f"Found config files: {config_files}")
    return config_files
