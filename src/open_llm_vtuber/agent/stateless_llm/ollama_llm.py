import atexit
import requests
from loguru import logger

from .ollama_native_llm import AsyncLLM


class OllamaLLM(AsyncLLM):
    """Ollama provider using native /api/chat with configurable GPU offload."""

    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
        keep_alive: float | str = -1,
        unload_at_exit: bool = True,
        num_gpu: int = 16,
        num_ctx: int = 4096,
        think: bool = False,
        preload: bool = True,
    ):
        self.keep_alive = keep_alive
        self.unload_at_exit = bool(unload_at_exit)
        self.num_gpu = int(num_gpu)
        self.num_ctx = int(num_ctx)
        self.think = bool(think)
        self.preload = bool(preload)
        self.cleaned = False

        super().__init__(
            model=model,
            base_url=base_url,
            llm_api_key=llm_api_key,
            organization_id=organization_id,
            project_id=project_id,
            temperature=temperature,
            keep_alive=keep_alive,
            num_gpu=self.num_gpu,
            num_ctx=self.num_ctx,
            think=self.think,
        )

        if self.preload:
            self._preload_model()

        if self.unload_at_exit:
            atexit.register(self.cleanup)

    def _native_api_url(self) -> str:
        url = self.base_url.rstrip("/")
        if url.endswith("/v1"):
            return url[:-3] + "/api"
        if url.endswith("/api"):
            return url
        return url + "/api"

    def _preload_model(self) -> None:
        """Load the configured model using the same num_gpu/num_ctx as chat."""
        url = f"{self._native_api_url()}/generate"
        payload = {
            "model": self.model,
            "prompt": "",
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "num_gpu": self.num_gpu,
                "num_ctx": self.num_ctx,
            },
        }
        try:
            logger.info(
                f"Ollama preload | model={self.model} | "
                f"num_gpu={self.num_gpu} | num_ctx={self.num_ctx} | "
                f"keep_alive={self.keep_alive}"
            )
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            logger.info("Ollama preload complete.")
        except requests.exceptions.RequestException as exc:
            logger.error(f"Failed to preload Ollama model: {exc}")
            logger.warning(
                "Open-LLM-VTuber will still try to use Ollama on demand."
            )
        except Exception as exc:
            logger.error(f"Failed to preload Ollama model: {exc}")

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass

    def cleanup(self):
        if not self.cleaned and self.unload_at_exit:
            try:
                logger.info(f"Ollama: Unloading model: {self.model}")
                requests.post(
                    f"{self._native_api_url()}/generate",
                    json={
                        "model": self.model,
                        "prompt": "",
                        "stream": False,
                        "keep_alive": 0,
                    },
                    timeout=30,
                )
            except Exception as exc:
                logger.error(f"Failed to unload Ollama model: {exc}")
            finally:
                self.cleaned = True
