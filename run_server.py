import os
import sys
import atexit
import asyncio
import argparse
from pathlib import Path
import tomli
import uvicorn
from loguru import logger

from src.open_llm_vtuber.server import WebSocketServer
from src.open_llm_vtuber.config_manager import (
    Config,
    read_yaml,
    validate_config,
    apply_default_character,
)

os.environ["HF_HOME"] = str(Path(__file__).parent / "models")
os.environ["MODELSCOPE_CACHE"] = str(Path(__file__).parent / "models")


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    return pyproject["project"]["version"]


def init_logger(console_log_level: str = "INFO") -> None:
    logger.remove()
    # Console output
    logger.add(
        sys.stderr,
        level=console_log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {message}",
        colorize=True,
    )

    # File output
    logger.add(
        "logs/debug_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
        backtrace=True,
        diagnose=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Local-LLM-Voice-Avatar Server")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--hf_mirror", action="store_true", help="Use Hugging Face mirror"
    )
    return parser.parse_args()


@logger.catch
def run(console_log_level: str):
    init_logger(console_log_level)
    logger.info(f"Local-LLM-Voice-Avatar, version v{get_version()}")

    # 已移除上游的配置同步（sync_user_config）：不再自动创建/备份/合并 conf.yaml。
    # 因此这里必须自己给出可执行的指引 —— 否则新克隆的仓库只会收到一个
    # FileNotFoundError("conf.yaml")，看不出下一步该做什么。
    if not Path("conf.yaml").is_file():
        template = Path("config_templates/conf.ZH.default.yaml")
        logger.critical(
            "未找到 conf.yaml，服务器无法启动。\n"
            f"请先复制配置模板：copy {template} conf.yaml\n"
            "（模板位于 config_templates/，zh 版为 conf.ZH.default.yaml，"
            "英文版为 conf.default.yaml）"
        )
        sys.exit(1)

    atexit.register(WebSocketServer.clean_cache)

    # Load configurations from yaml file
    # conf.yaml 只存默认角色的"指针"，这里把它合并到基础 character_config 之上
    config: Config = validate_config(apply_default_character(read_yaml("conf.yaml")))
    server_config = config.system_config

    # Initialize the WebSocket server (synchronous part)
    server = WebSocketServer(config=config)

    # Perform asynchronous initialization (loading context, etc.)
    logger.info("Initializing server context...")
    try:
        asyncio.run(server.initialize())
        logger.info("Server context initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize server context: {e}")
        sys.exit(1)  # Exit if initialization fails

    # Run the Uvicorn server
    logger.info(f"Starting server on {server_config.host}:{server_config.port}")
    uvicorn.run(
        app=server.app,
        host=server_config.host,
        port=server_config.port,
        log_level=console_log_level.lower(),
    )


if __name__ == "__main__":
    args = parse_args()
    console_log_level = "DEBUG" if args.verbose else "INFO"
    if args.verbose:
        logger.info("Running in verbose mode")
    else:
        logger.info(
            "Running in standard mode. For detailed debug logs, use: uv run run_server.py --verbose"
        )
    if args.hf_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    run(console_log_level=console_log_level)
