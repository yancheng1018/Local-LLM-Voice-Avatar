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
