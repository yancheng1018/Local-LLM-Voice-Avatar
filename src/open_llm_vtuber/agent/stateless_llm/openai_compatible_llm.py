"""Description: This file contains the implementation of the `AsyncLLM` class.
This class is responsible for handling asynchronous interaction with OpenAI API compatible
endpoints for language generation.
"""

import time
import uuid
import json
import httpx
from typing import AsyncIterator, List, Dict, Any
from openai import NotGiven, NOT_GIVEN
from openai.types.chat import ChatCompletionChunk
from loguru import logger

from .stateless_llm_interface import StatelessLLMInterface
from ...mcpp.types import ToolCallObject



class AsyncLLM(StatelessLLMInterface):
    """
    Diagnostic transport for OpenAI-compatible LLM endpoints.

    This version intentionally bypasses AsyncOpenAI and talks to the
    /chat/completions endpoint directly with httpx.  It is designed to
    determine whether the long delay seen in Open-LLM-VTuber is caused by
    the OpenAI Python SDK transport/client layer.

    Important:
    - stream=True is preserved.
    - reasoning_effort="none" is preserved.
    - tools are preserved when supplied.
    - No automatic SDK retries are used.
    - trust_env=False prevents Windows HTTP(S)_PROXY environment variables
      from affecting localhost Ollama requests.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.llm_api_key = llm_api_key
        self.organization_id = organization_id
        self.project_id = project_id
        self.support_tools = True

        # Long read timeout is intentional: it prevents the diagnostic client
        # from hiding a slow Ollama response, while connect/pool/write remain short.
        self.timeout = httpx.Timeout(
            connect=10.0,
            read=600.0,
            write=30.0,
            pool=10.0,
        )

        logger.info(
            f"Initialized diagnostic AsyncLLM with parameters: "
            f"{self.base_url}, {self.model}"
        )
        logger.debug(
            "🧪 LLM HTTP transport: direct httpx | "
            "trust_env=False | retries=0 | reasoning_effort=none"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system: str = None,
        tools: List[Dict[str, Any]] | NotGiven = NOT_GIVEN,
    ) -> AsyncIterator[str | List[Any]]:
        """
        Directly calls the OpenAI-compatible /chat/completions endpoint and
        parses the Server-Sent Events stream.

        The yielded values remain strings for normal content and lists of
        ToolCallObject for completed tool calls, matching the existing
        Open-LLM-VTuber contract.
        """
        accumulated_tool_calls = {}
        in_tool_call = False

        try:
            messages_with_system = messages
            if system:
                messages_with_system = [
                    {"role": "system", "content": system},
                    *messages,
                ]

            available_tools = tools if self.support_tools else NOT_GIVEN

            request_id = str(uuid.uuid4())[:8]
            request_start = time.perf_counter()
            first_chunk_time = None
            chunk_count = 0
            content_chunk_count = 0
            content_char_count = 0
            tool_chunk_count = 0

            message_count = len(messages_with_system)
            system_char_count = 0
            user_char_count = 0
            assistant_char_count = 0

            for diagnostic_message in messages_with_system:
                diagnostic_content = diagnostic_message.get("content")
                diagnostic_chars = (
                    len(diagnostic_content)
                    if isinstance(diagnostic_content, str)
                    else 0
                )
                role = diagnostic_message.get("role")
                if role == "system":
                    system_char_count += diagnostic_chars
                elif role == "user":
                    user_char_count += diagnostic_chars
                elif role == "assistant":
                    assistant_char_count += diagnostic_chars

            if available_tools is NOT_GIVEN:
                tool_count = 0
            elif isinstance(available_tools, list):
                tool_count = len(available_tools)
            else:
                tool_count = -1

            url = f"{self.base_url}/chat/completions"

            payload = {
                "model": self.model,
                "messages": messages_with_system,
                "stream": True,
                "temperature": self.temperature,
                "reasoning_effort": "none",
            }
            if available_tools is not NOT_GIVEN:
                payload["tools"] = available_tools

            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            if self.llm_api_key:
                headers["Authorization"] = f"Bearer {self.llm_api_key}"

            logger.debug(
                f"🧪 HTTP-LLM[{request_id}] START | "
                f"url={url} | model={self.model} | "
                f"messages={message_count} | "
                f"system_chars={system_char_count} | "
                f"user_chars={user_char_count} | "
                f"assistant_chars={assistant_char_count} | "
                f"tools={tool_count} | "
                f"temperature={self.temperature} | "
                f"reasoning_effort=none"
            )
            logger.debug(
                f"HTTP-LLM[{request_id}] payload: {json.dumps(payload, ensure_ascii=False)}"
            )

            # trust_env=False is deliberate. If a system/user HTTP proxy is
            # configured, localhost traffic should not be routed through it.
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                connect_start = time.perf_counter()

                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    header_elapsed = time.perf_counter() - connect_start

                    logger.debug(
                        f"🧪 HTTP-LLM[{request_id}] HTTP RESPONSE HEADERS | "
                        f"status={response.status_code} | "
                        f"headers_call={header_elapsed:.2f}s"
                    )

                    if response.status_code == 429:
                        body = await response.aread()
                        logger.error(
                            f"HTTP-LLM[{request_id}] HTTP 429 | body={body[:2000]!r}"
                        )
                        yield "Error calling the chat endpoint: Rate limit exceeded. Please try again later. See the logs for details."
                        return

                    if response.status_code >= 400:
                        body = await response.aread()
                        logger.error(
                            f"HTTP-LLM[{request_id}] HTTP ERROR {response.status_code} | "
                            f"body={body[:4000]!r}"
                        )
                        if (
                            response.status_code in (400, 404)
                            and b"does not support tools" in body
                        ):
                            self.support_tools = False
                            logger.warning(
                                f"{self.model} does not support tools. "
                                "Disabling tool support for subsequent requests."
                            )
                            yield "__API_NOT_SUPPORT_TOOLS__"
                            return

                        yield (
                            "Error calling the chat endpoint: "
                            f"HTTP {response.status_code}. See the logs for details."
                        )
                        return

                    logger.info(
                        f"🧪 HTTP-LLM[{request_id}] STREAM CONNECTED | "
                        f"headers_elapsed={header_elapsed:.2f}s"
                    )

                    async for line in response.aiter_lines():
                        if line == "":
                            continue

                        if not line.startswith("data:"):
                            logger.debug(
                                f"HTTP-LLM[{request_id}] non-data SSE line: {line[:500]}"
                            )
                            continue

                        data = line[5:].strip()
                        if not data:
                            continue

                        if data == "[DONE]":
                            logger.debug(
                                f"HTTP-LLM[{request_id}] received [DONE]"
                            )
                            break

                        try:
                            chunk_data = json.loads(data)
                            chunk = ChatCompletionChunk.model_validate(chunk_data)
                        except Exception as parse_error:
                            logger.error(
                                f"🧪 HTTP-LLM[{request_id}] SSE JSON/Pydantic parse error: "
                                f"{parse_error} | data={data[:2000]}"
                            )
                            continue

                        chunk_count += 1

                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                            logger.debug(
                                f"🧪 HTTP-LLM[{request_id}] FIRST CHUNK | "
                                f"TTFC={first_chunk_time - request_start:.2f}s"
                            )

                        if len(chunk.choices) == 0:
                            logger.debug(
                                f"HTTP-LLM[{request_id}] Empty chunk received"
                            )
                            continue

                        delta = chunk.choices[0].delta
                        has_tool_calls = bool(
                            getattr(delta, "tool_calls", None)
                        )

                        if self.support_tools and has_tool_calls:
                            tool_chunk_count += 1
                            in_tool_call = True

                            for tool_call in delta.tool_calls:
                                index = (
                                    tool_call.index
                                    if hasattr(tool_call, "index")
                                    and tool_call.index is not None
                                    else 0
                                )

                                if index not in accumulated_tool_calls:
                                    accumulated_tool_calls[index] = {
                                        "index": index,
                                        "id": getattr(tool_call, "id", None),
                                        "type": getattr(tool_call, "type", None),
                                        "function": {
                                            "name": "",
                                            "arguments": "",
                                        },
                                    }

                                if (
                                    hasattr(tool_call, "id")
                                    and tool_call.id
                                ):
                                    accumulated_tool_calls[index]["id"] = tool_call.id

                                if (
                                    hasattr(tool_call, "type")
                                    and tool_call.type
                                ):
                                    accumulated_tool_calls[index]["type"] = tool_call.type

                                if hasattr(tool_call, "function"):
                                    function = tool_call.function
                                    if (
                                        hasattr(function, "name")
                                        and function.name
                                    ):
                                        accumulated_tool_calls[index][
                                            "function"
                                        ]["name"] = function.name

                                    if (
                                        hasattr(function, "arguments")
                                        and function.arguments
                                    ):
                                        accumulated_tool_calls[index][
                                            "function"
                                        ]["arguments"] += function.arguments

                            logger.debug(
                                f"HTTP-LLM[{request_id}] tool chunk: "
                                f"{delta.tool_calls}"
                            )
                            continue

                        if self.support_tools and in_tool_call and not has_tool_calls:
                            in_tool_call = False
                            logger.info(
                                f"HTTP-LLM[{request_id}] Complete tool calls: "
                                f"{accumulated_tool_calls}"
                            )
                            complete_tool_calls = [
                                ToolCallObject.from_dict(tool_data)
                                for tool_data in accumulated_tool_calls.values()
                            ]
                            yield complete_tool_calls
                            accumulated_tool_calls = {}

                        content = delta.content
                        if content is None:
                            content = ""

                        content_chunk_count += 1
                        content_char_count += len(content)
                        yield content

            total_elapsed = time.perf_counter() - request_start
            first_chunk_elapsed = (
                first_chunk_time - request_start
                if first_chunk_time is not None
                else None
            )

            if first_chunk_elapsed is not None:
                logger.debug(
                    f"🧪 HTTP-LLM[{request_id}] STREAM COMPLETE | "
                    f"total={total_elapsed:.2f}s | "
                    f"TTFC={first_chunk_elapsed:.2f}s"
                )
            else:
                logger.debug(
                    f"🧪 HTTP-LLM[{request_id}] STREAM COMPLETE | "
                    f"total={total_elapsed:.2f}s | TTFC=NO_CHUNK"
                )

            logger.debug(
                f"🧪 HTTP-LLM[{request_id}] STATS | "
                f"chunks={chunk_count} | "
                f"content_chunks={content_chunk_count} | "
                f"content_chars={content_char_count} | "
                f"tool_chunks={tool_chunk_count}"
            )

            if in_tool_call and accumulated_tool_calls:
                logger.info(
                    f"HTTP-LLM[{request_id}] Final tool call at stream end: "
                    f"{accumulated_tool_calls}"
                )
                complete_tool_calls = [
                    ToolCallObject.from_dict(tool_data)
                    for tool_data in accumulated_tool_calls.values()
                ]
                yield complete_tool_calls

        except httpx.ConnectTimeout as e:
            logger.error(
                f"🧪 HTTP-LLM connection timeout: {e}"
            )
            yield "Error calling the chat endpoint: Connection timeout. See the logs for details."

        except httpx.ConnectError as e:
            logger.error(
                f"🧪 HTTP-LLM connection error: {e}"
            )
            yield "Error calling the chat endpoint: Connection error. See the logs for details."

        except httpx.ReadTimeout as e:
            logger.error(
                f"🧪 HTTP-LLM read timeout: {e}"
            )
            yield "Error calling the chat endpoint: Read timeout. See the logs for details."

        except httpx.HTTPError as e:
            logger.error(
                f"🧪 HTTP-LLM HTTP error: {e}"
            )
            yield "Error calling the chat endpoint: HTTP error. See the logs for details."

        except Exception as e:
            logger.exception(
                f"🧪 HTTP-LLM unexpected error: {e}"
            )
            yield "Error calling the chat endpoint: Error occurred while generating response. See the logs for details."
