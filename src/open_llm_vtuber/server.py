"""
Open-LLM-VTuber Server
========================
This module contains the WebSocket server for Open-LLM-VTuber, which handles
the WebSocket connections, serves static files, and manages the web tool.
It uses FastAPI for the server and Starlette for static file serving.
"""

import os
import shutil

from fastapi import FastAPI
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .routes import init_client_ws_route, init_webtool_routes
from .service_context import ServiceContext
from .config_manager.utils import Config


# Create a custom StaticFiles class that adds CORS headers
class CORSStaticFiles(StarletteStaticFiles):
    """
    Static files handler that adds CORS headers to all responses.
    Needed because Starlette StaticFiles might bypass standard middleware.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"

        # html 每次都协商缓存：入口页引用带 hash 的 assets，避免浏览器启发式
        # 缓存把旧 index.html 留在手里、加载不到新构建
        if path.endswith(".html") or path == "" or path == "/":
            response.headers["Cache-Control"] = "no-cache"

        return response


class WebSocketServer:
    """
    API server for Open-LLM-VTuber. This contains the websocket endpoint for the client, hosts the web tool, and serves static files.

    Creates and configures a FastAPI app, registers all routes
    (WebSocket, web tools) and mounts static assets with CORS.

    Args:
        config (Config): Application configuration containing system settings.
        default_context_cache (ServiceContext, optional):
            Pre‑initialized service context for sessions' service context to reference to.
            **If omitted, `initialize()` method needs to be called to load service context.**

    Notes:
        - If default_context_cache is omitted, call `await initialize()` to load service context cache.
        - Use `clean_cache()` to clear and recreate the local cache directory.
    """

    def __init__(self, config: Config, default_context_cache: ServiceContext = None):
        self.app = FastAPI(
            title="Local-LLM-Voice-Avatar Server"
        )  # Added title for clarity
        self.config = config
        self.default_context_cache = (
            default_context_cache or ServiceContext()
        )  # Use provided context or initialize a new empty one waiting to be loaded
        # It will be populated during the initialize method call

        # Add global CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include routes, passing the context instance
        # The context will be populated during the initialize step
        self.app.include_router(
            init_client_ws_route(default_context_cache=self.default_context_cache),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=self.default_context_cache),
        )

        # Mount cache directory first (to ensure audio file access)
        if not os.path.exists("cache"):
            os.makedirs("cache")
        self.app.mount(
            "/cache",
            CORSStaticFiles(directory="cache"),
            name="cache",
        )

        # Mount static files with CORS-enabled handlers
        self.app.mount(
            "/live2d-models",
            CORSStaticFiles(directory="live2d-models"),
            name="live2d-models",
        )

        # Cubism Core（Live2D 专有许可，as-is 分发并保留版权头，条款见 LICENSE-Live2D.md）
        self.app.mount(
            "/libs",
            CORSStaticFiles(directory="static/libs"),
            name="libs",
        )

        # Mount web tool directory separately from frontend
        self.app.mount(
            "/web-tool",
            CORSStaticFiles(directory="web_tool", html=True),
            name="web_tool",
        )

        # Mount Spine models (阶段二：Spine 渲染器的模型目录)
        if os.path.exists("Spine-models"):
            self.app.mount(
                "/Spine-models",
                CORSStaticFiles(directory="Spine-models"),
                name="spine_models",
            )

        # Mount minimal frontend (frontend-minimal/, Vite 构建产物；需在 / 重定向前)
        if os.path.exists("frontend-minimal/dist"):
            # Starlette 不会为 mount 自动补尾斜杠，/m 会 404，这里显式重定向到 /m/
            self.app.add_route(
                "/m",
                lambda request: RedirectResponse(url="/m/", status_code=307),
            )
            self.app.mount(
                "/m",
                CORSStaticFiles(directory="frontend-minimal/dist", html=True),
                name="frontend_minimal",
            )
        else:
            logger.warning(
                "frontend-minimal/dist 未构建，/m/ 不可用。"
                "请先构建：cd frontend-minimal && npm install && npm run build"
            )

        # 旧官方前端（frontend/）已于 github-p1-robust 整体移除；
        # 根路径统一引导到极简前端 /m/（规范地址，GUI 与 README 均指向它）
        self.app.add_route(
            "/",
            lambda request: RedirectResponse(url="/m/", status_code=307),
        )

    async def initialize(self):
        """Asynchronously load the service context from config.
        Calling this function is needed if default_context_cache was not provided to the constructor."""
        await self.default_context_cache.load_from_config(self.config)

    @staticmethod
    def clean_cache():
        """Clean the cache directory by removing and recreating it."""
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
