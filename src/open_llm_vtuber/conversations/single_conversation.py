from typing import Union, List, Dict, Any, Optional
import asyncio
import json
import requests
from loguru import logger
import numpy as np

from .conversation_utils import (
    create_batch_input,
    process_agent_output,
    send_conversation_start_signals,
    process_user_input,
    finalize_conversation_turn,
    cleanup_conversation,
    EMOJI_LIST,
)
from .types import WebSocketSend
from .tts_manager import TTSTaskManager
from ..chat_history_manager import store_message
from ..service_context import ServiceContext

from ..agent.output_types import SentenceOutput, AudioOutput
from ..utils.language_guard import (
    build_retry_reminder,
    detect_language_mismatch,
    normalize_language,
)

# 重试前最多缓冲几句用于语言判定。句子太短时判据不足，多等一句再下结论。
_MAX_BUFFERED_SENTENCES = 3


def _plain_text(items) -> str:
    """把若干输出项的可显示文本拼起来，用于语言判定。"""
    return " ".join(
        getattr(getattr(i, "display_text", None), "text", "") or "" for i in items
    )


async def _language_checked_stream(agent, batch_input, target_lang):
    """包装 agent 的回复流：转发前先判定首句语言，不符则加强提示词重试一次。

    为什么要缓冲开头：回复会实时送到前端和 TTS，一旦把错误语言的句子转发出去就来不及了，
    所以先扣住头几句、判定通过后再原样转发（正常情况仍是流式，不增加延迟）。
    判据不足（句子太短）时会多等一句，最多缓冲 _MAX_BUFFERED_SENTENCES 句。

    重试手段：临时把强提醒追加到 agent 系统提示词的末尾（近因效应）。
    为避免 async generator 被提前中断时 finally 不立即执行、导致加强过的提示词泄漏到
    后续轮次，重试那一版是**先完整收完再还原提示词**，之后才向下游转发 —— 代价是
    重试时这一轮失去流式（约 4% 的偶发情况，可接受），换来确定的还原时机。
    只重试一次，避免与模型反复拉扯。
    """
    original_system = getattr(agent, "_system", None)
    can_retry = isinstance(original_system, str) and bool(original_system)

    # ── 第一次尝试：边转发边守住开头几句做判定 ──
    pending: list = []
    decided = False
    async for item in agent.chat(batch_input):
        if decided or not isinstance(item, SentenceOutput):
            yield item
            continue

        pending.append(item)
        verdict = detect_language_mismatch(_plain_text(pending), target_lang)

        if verdict is None and len(pending) < _MAX_BUFFERED_SENTENCES:
            continue  # 判据不足，再等一句
        if verdict is True and can_retry:
            logger.warning(
                f"Language guard: detected a reply not in '{target_lang}'; "
                "discarding it and retrying once with a stronger reminder."
            )
            break  # 丢弃这一版（它不会进记忆：assistant 文本只在流结束时写入）

        # 判定通过、或无法重试：原样放行缓冲内容
        decided = True
        for buffered in pending:
            yield buffered
        pending = []
    else:
        # 流正常结束：始终没能判定时也要放行，不能吞掉回复
        if not decided:
            for buffered in pending:
                yield buffered
        return

    # ── 重试：先把输出完整收下来（期间提示词是加强过的），还原后再转发 ──
    retry_items: list = []
    try:
        agent._system = f"{original_system}\n\n{build_retry_reminder(target_lang)}"
        async for item in agent.chat(batch_input):
            retry_items.append(item)
    finally:
        agent._system = original_system

    if detect_language_mismatch(_plain_text(retry_items), target_lang) is True:
        logger.error(
            f"Language guard: reply is still not in '{target_lang}' after retry; "
            "accepting it (check the model's instruction following)."
        )
    for item in retry_items:
        yield item


# Partial-GPU coexistence strategy:
#   1. Qwen is loaded with num_gpu=16 (about half the layers on GPU).
#   2. Keep Qwen resident between turns; do NOT unload/reload it.
#   3. GPT-SoVITS runs sequentially after the LLM stream is consumed.
#   4. TTSTaskManager buffers TTS during LLM streaming, so TTS does not
#      block consumption of the Ollama stream.
#
# This avoids the long reload/unload stalls seen when Qwen was fully removed
# from GPU between turns.
async def process_single_conversation(
    context: ServiceContext,
    websocket_send: WebSocketSend,
    client_uid: str,
    user_input: Union[str, np.ndarray],
    images: Optional[List[Dict[str, Any]]] = None,
    session_emoji: str = np.random.choice(EMOJI_LIST),
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Process a single-user conversation turn."""

    tts_manager = TTSTaskManager()
    full_response = ""

    try:
        await send_conversation_start_signals(websocket_send)
        logger.info(f"New Conversation Chain {session_emoji} started!")

        input_text = await process_user_input(
            user_input,
            context.asr_engine,
            websocket_send,
        )

        batch_input = create_batch_input(
            input_text=input_text,
            images=images,
            from_name=context.character_config.human_name,
            metadata=metadata,
        )

        skip_history = metadata and metadata.get("skip_history", False)

        if context.history_uid and not skip_history:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="human",
                content=input_text,
                name=context.character_config.human_name,
            )

        if skip_history:
            logger.debug(
                "Skipping storing user input to history (proactive speak)"
            )

        logger.info(f"User input: {input_text}")

        if images:
            logger.info(f"With {len(images)} images")

        try:
            # Start the LLM request directly. There is intentionally no
            # background Ollama preload to wait for here.
            # Keep consuming the LLM stream continuously.
            # TTSTaskManager.speak() only buffers TTS requests.
            #
            # 角色设置了 language 时，用 language guard 包一层：首句语言不对就
            # 丢弃并重试一次，避免小模型偶发跟随用户语言（详见 utils/language_guard.py）
            target_lang = normalize_language(context.character_config.language)
            if target_lang:
                agent_output_stream = _language_checked_stream(
                    context.agent_engine, batch_input, target_lang
                )
            else:
                agent_output_stream = context.agent_engine.chat(batch_input)

            async for output_item in agent_output_stream:
                if (
                    isinstance(output_item, dict)
                    and output_item.get("type") == "tool_call_status"
                ):
                    output_item["name"] = (
                        context.character_config.character_name
                    )
                    logger.debug(
                        f"Sending tool status update: {output_item}"
                    )
                    await websocket_send(json.dumps(output_item))

                elif isinstance(
                    output_item,
                    (SentenceOutput, AudioOutput),
                ):
                    response_part = await process_agent_output(
                        output=output_item,
                        character_config=context.character_config,
                        live2d_model=context.live2d_model,
                        tts_engine=context.tts_engine,
                        websocket_send=websocket_send,
                        tts_manager=tts_manager,
                        translate_engine=context.translate_engine,
                    )

                    response_part_str = (
                        str(response_part)
                        if response_part is not None
                        else ""
                    )
                    full_response += response_part_str

                else:
                    logger.warning(
                        "Received unexpected item type from agent chat "
                        f"stream: {type(output_item)}"
                    )
                    logger.debug(
                        f"Unexpected item content: {output_item}"
                    )

        except Exception as e:
            logger.exception(
                f"Error processing agent response stream: {e}"
            )

            await websocket_send(
                json.dumps(
                    {
                        "type": "error",
                        "message": (
                            f"Error processing agent response: {str(e)}"
                        ),
                    }
                )
            )

        # The LLM stream is now completely consumed.
        # IMPORTANT: do NOT unload Qwen here. Qwen is intentionally kept
        # resident with partial GPU offload (num_gpu=16) so that the next
        # turn does not need to reload the model. GPT-SoVITS can use the
        # remaining GPU memory. TTS requests are still processed serially.
        await tts_manager.process_pending()

        if tts_manager._sequence_counter > 0:
            await websocket_send(
                json.dumps({"type": "backend-synth-complete"})
            )

        await finalize_conversation_turn(
            tts_manager=tts_manager,
            websocket_send=websocket_send,
            client_uid=client_uid,
        )

        if context.history_uid and full_response:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=full_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            logger.info(f"AI response: {full_response}")

        return full_response

    except asyncio.CancelledError:
        logger.info(
            f"🤡👍 Conversation {session_emoji} cancelled because interrupted."
        )
        raise

    except Exception as e:
        logger.error(f"Error in conversation chain: {e}")
        await websocket_send(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Conversation error: {str(e)}",
                }
            )
        )
        raise

    finally:
        # No background Ollama preload task is used in this version.
        cleanup_conversation(tts_manager, session_emoji)
