"""Native Ollama /api/chat transport for Open-LLM-VTuber.

Ollama-specific options (num_gpu, num_ctx, etc.) are sent through the native
/api/chat endpoint instead of the OpenAI-compatible /v1 endpoint.

Configuration is supplied by OllamaLLM in ollama_llm.py.
"""

import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List

import httpx
from loguru import logger
from openai import NotGiven, NOT_GIVEN

from .stateless_llm_interface import StatelessLLMInterface
from ...mcpp.types import ToolCallObject


class AsyncLLM(StatelessLLMInterface):
    """Direct Ollama native API client with configurable runtime options."""

    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
        keep_alive: float | str = -1,
        num_gpu: int = 16,
        num_ctx: int = 4096,
        think: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/v1"):
            self.api_base_url = self.base_url[:-3] + "/api"
        elif self.base_url.endswith("/api"):
            self.api_base_url = self.base_url
        else:
            self.api_base_url = self.base_url + "/api"

        self.model = model
        self.temperature = float(temperature)
        self.keep_alive = keep_alive
        self.num_gpu = int(num_gpu)
        self.num_ctx = int(num_ctx)
        self.think = bool(think)
        self.llm_api_key = llm_api_key
        self.organization_id = organization_id
        self.project_id = project_id
        self.support_tools = True

        self.timeout = httpx.Timeout(
            connect=10.0,
            read=600.0,
            write=30.0,
            pool=10.0,
        )

        logger.info(
            f"Initialized native Ollama AsyncLLM: {self.api_base_url}, {self.model}"
        )
        logger.info(
            "Ollama native transport | "
            f"num_gpu={self.num_gpu} | num_ctx={self.num_ctx} | "
            f"keep_alive={self.keep_alive} | think={self.think}"
        )

    def _options(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "num_gpu": self.num_gpu,
            "num_ctx": self.num_ctx,
        }

    @staticmethod
    def _normalize_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str):
                return text
        return str(content)

    @classmethod
    def _normalize_messages(
        cls, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for message in messages:
            item: Dict[str, Any] = {
                "role": message.get("role", "user"),
                "content": cls._normalize_content(message.get("content")),
            }

            if item["role"] == "tool":
                tool_name = message.get("name") or message.get("tool_name")
                if tool_name:
                    item["tool_name"] = tool_name

            tool_calls = message.get("tool_calls")
            if tool_calls:
                native_calls = []
                for call in tool_calls:
                    function = call.get("function") or {}
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {"_raw_arguments": arguments}
                    native_calls.append(
                        {
                            "function": {
                                "name": function.get("name", ""),
                                "arguments": arguments,
                            }
                        }
                    )
                item["tool_calls"] = native_calls

            normalized.append(item)
        return normalized

    @staticmethod
    def _tool_call_to_dict(tool_call: Dict[str, Any], index: int) -> Dict[str, Any]:
        function = tool_call.get("function") or {}
        name = function.get("name") or ""
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            arguments_text = arguments
        else:
            arguments_text = json.dumps(arguments, ensure_ascii=False)

        return {
            "index": index,
            "id": tool_call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
            "type": tool_call.get("type") or "function",
            "function": {
                "name": name,
                "arguments": arguments_text,
            },
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system: str = None,
        tools: List[Dict[str, Any]] | NotGiven = NOT_GIVEN,
    ) -> AsyncIterator[str | List[Any]]:
        request_id = str(uuid.uuid4())[:8]
        request_start = time.perf_counter()
        first_chunk_time = None
        line_count = 0
        content_chunks = 0
        content_chars = 0
        thinking_chars = 0
        tool_calls_seen = 0
        accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}

        try:
            messages_with_system = self._normalize_messages(messages)
            if system:
                messages_with_system = [
                    {"role": "system", "content": self._normalize_content(system)},
                    *messages_with_system,
                ]

            available_tools = tools if self.support_tools else NOT_GIVEN
            url = f"{self.api_base_url}/chat"

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": messages_with_system,
                "stream": True,
                "think": self.think,
                "keep_alive": self.keep_alive,
                "options": self._options(),
            }
            if available_tools is not NOT_GIVEN:
                payload["tools"] = available_tools

            logger.info(
                f"NATIVE-LLM[{request_id}] START | "
                f"url={url} | model={self.model} | "
                f"messages={len(messages_with_system)} | "
                f"tools={0 if available_tools is NOT_GIVEN else len(available_tools)} | "
                f"num_gpu={self.num_gpu} | num_ctx={self.num_ctx} | "
                f"think={self.think} | keep_alive={self.keep_alive}"
            )

            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                connect_start = time.perf_counter()
                async with client.stream(
                    "POST",
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/x-ndjson",
                    },
                    json=payload,
                ) as response:
                    header_elapsed = time.perf_counter() - connect_start
                    logger.info(
                        f"NATIVE-LLM[{request_id}] HTTP RESPONSE HEADERS | "
                        f"status={response.status_code} | headers_call={header_elapsed:.2f}s"
                    )

                    if response.status_code >= 400:
                        body = await response.aread()
                        logger.error(
                            f"NATIVE-LLM[{request_id}] HTTP ERROR {response.status_code} | "
                            f"body={body[:4000]!r}"
                        )
                        yield (
                            "Error calling Ollama native chat endpoint: "
                            f"HTTP {response.status_code}. See logs for details."
                        )
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        line_count += 1

                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            logger.error(
                                f"NATIVE-LLM[{request_id}] JSON parse error: {exc} | "
                                f"line={line[:2000]}"
                            )
                            continue

                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                            logger.info(
                                f"NATIVE-LLM[{request_id}] FIRST CHUNK | "
                                f"TTFC={first_chunk_time - request_start:.2f}s"
                            )

                        message = data.get("message") or {}

                        thinking = message.get("thinking") or ""
                        if thinking:
                            thinking_chars += len(thinking)
                            if self.think:
                                yield thinking

                        content = message.get("content")
                        if content:
                            content_chunks += 1
                            content_chars += len(content)
                            yield content

                        native_tool_calls = message.get("tool_calls") or []
                        if native_tool_calls:
                            for idx, tool_call in enumerate(native_tool_calls):
                                accumulated_tool_calls[idx] = self._tool_call_to_dict(
                                    tool_call, idx
                                )
                            tool_calls_seen += len(native_tool_calls)

                        if data.get("done"):
                            break

                    if accumulated_tool_calls:
                        complete_tool_calls = [
                            ToolCallObject.from_dict(item)
                            for item in accumulated_tool_calls.values()
                        ]
                        logger.info(
                            f"NATIVE-LLM[{request_id}] TOOL CALLS | "
                            f"count={len(complete_tool_calls)}"
                        )
                        yield complete_tool_calls

            total_elapsed = time.perf_counter() - request_start
            ttfc = (
                first_chunk_time - request_start
                if first_chunk_time is not None
                else None
            )
            logger.info(
                f"NATIVE-LLM[{request_id}] STREAM COMPLETE | "
                f"total={total_elapsed:.2f}s | "
                f"TTFC={ttfc:.2f}s | lines={line_count} | "
                f"content_chunks={content_chunks} | content_chars={content_chars} | "
                f"thinking_chars={thinking_chars} | tool_calls={tool_calls_seen}"
            )

        except httpx.ConnectTimeout as exc:
            logger.error(f"NATIVE-LLM connection timeout: {exc}")
            yield "Error calling Ollama native chat endpoint: Connection timeout."
        except httpx.ConnectError as exc:
            logger.error(f"NATIVE-LLM connection error: {exc}")
            yield "Error calling Ollama native chat endpoint: Connection error."
        except httpx.ReadTimeout as exc:
            logger.error(f"NATIVE-LLM read timeout: {exc}")
            yield "Error calling Ollama native chat endpoint: Read timeout."
        except httpx.HTTPError as exc:
            logger.error(f"NATIVE-LLM HTTP error: {exc}")
            yield "Error calling Ollama native chat endpoint: HTTP error."
        except Exception as exc:
            logger.exception(f"NATIVE-LLM unexpected error: {exc}")
            yield "Error calling Ollama native chat endpoint: Error occurred while generating response."
