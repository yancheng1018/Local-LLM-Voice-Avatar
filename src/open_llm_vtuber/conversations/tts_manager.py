import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from loguru import logger

from ..agent.output_types import DisplayText, Actions
from ..live2d_model import Live2dModel
from ..tts.tts_interface import TTSInterface
from ..utils.stream_audio import prepare_audio_payload
from .types import WebSocketSend


class TTSTaskManager:
    """Buffer TTS requests during LLM streaming and process them sequentially."""

    def __init__(self) -> None:
        self.task_list: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        self._payload_queue: asyncio.Queue[Dict] = asyncio.Queue()
        self._sender_task: Optional[asyncio.Task] = None
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        self._pending_requests = []

    def _ensure_sender(self, websocket_send: WebSocketSend) -> None:
        if not self._sender_task or self._sender_task.done():
            self._sender_task = asyncio.create_task(
                self._process_payload_queue(websocket_send)
            )

    async def speak(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        websocket_send: WebSocketSend,
    ) -> None:
        """Buffer a TTS request without starting GPU inference."""
        current_sequence = self._sequence_counter
        self._sequence_counter += 1

        self._pending_requests.append(
            {
                "tts_text": tts_text,
                "display_text": display_text,
                "actions": actions,
                "live2d_model": live2d_model,
                "tts_engine": tts_engine,
                "websocket_send": websocket_send,
                "sequence_number": current_sequence,
            }
        )

        logger.debug(
            f"🏃Buffered TTS request #{current_sequence}: "
            f"'''{tts_text}''' (by {display_text.name})"
        )

    async def process_pending(self) -> None:
        """Run all buffered TTS requests sequentially."""
        if not self._pending_requests:
            return

        first_request = self._pending_requests[0]
        websocket_send = first_request["websocket_send"]
        self._ensure_sender(websocket_send)

        logger.info(
            f"🔊 Starting sequential TTS processing: "
            f"{len(self._pending_requests)} request(s)"
        )

        while self._pending_requests:
            request = self._pending_requests.pop(0)

            tts_text = request["tts_text"]
            display_text = request["display_text"]
            actions = request["actions"]
            live2d_model = request["live2d_model"]
            tts_engine = request["tts_engine"]
            sequence_number = request["sequence_number"]

            if len(re.sub(r'[\s.,!?，。！？\'"』」）】\s]+', "", tts_text)) == 0:
                logger.debug(
                    f"Empty TTS text for sequence #{sequence_number}, "
                    "sending silent display payload"
                )
                await self._send_silent_payload(
                    display_text=display_text,
                    actions=actions,
                    sequence_number=sequence_number,
                )
                continue

            logger.debug(
                f"🏃Generating TTS sequence #{sequence_number}: "
                f"'''{tts_text}'''"
            )

            tts_start = asyncio.get_running_loop().time()

            await self._process_tts(
                tts_text=tts_text,
                display_text=display_text,
                actions=actions,
                live2d_model=live2d_model,
                tts_engine=tts_engine,
                sequence_number=sequence_number,
            )

            tts_elapsed = asyncio.get_running_loop().time() - tts_start
            logger.info(
                f"🔊 TTS sequence #{sequence_number} completed in "
                f"{tts_elapsed:.2f}s: {tts_text!r}"
            )

        await self._payload_queue.join()
        logger.info("🔊 Sequential TTS processing completed.")

    async def _process_payload_queue(
        self,
        websocket_send: WebSocketSend,
    ) -> None:
        buffered_payloads: Dict[int, Dict] = {}

        while True:
            try:
                payload, sequence_number = await self._payload_queue.get()
                buffered_payloads[sequence_number] = payload

                while self._next_sequence_to_send in buffered_payloads:
                    next_payload = buffered_payloads.pop(
                        self._next_sequence_to_send
                    )
                    await websocket_send(json.dumps(next_payload))
                    self._next_sequence_to_send += 1

                self._payload_queue.task_done()

            except asyncio.CancelledError:
                break

    async def _send_silent_payload(
        self,
        display_text: DisplayText,
        actions: Optional[Actions],
        sequence_number: int,
    ) -> None:
        audio_payload = prepare_audio_payload(
            audio_path=None,
            display_text=display_text,
            actions=actions,
        )
        await self._payload_queue.put((audio_payload, sequence_number))

    async def _process_tts(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        sequence_number: int,
    ) -> None:
        audio_file_path = None

        try:
            audio_file_path = await self._generate_audio(
                tts_engine,
                tts_text,
            )

            payload = prepare_audio_payload(
                audio_path=audio_file_path,
                display_text=display_text,
                actions=actions,
            )

            await self._payload_queue.put(
                (payload, sequence_number)
            )

        except Exception as e:
            logger.error(f"Error preparing audio payload: {e}")

            payload = prepare_audio_payload(
                audio_path=None,
                display_text=display_text,
                actions=actions,
            )

            await self._payload_queue.put(
                (payload, sequence_number)
            )

        finally:
            if audio_file_path:
                tts_engine.remove_file(audio_file_path)
                logger.debug("Audio cache file cleaned.")

    async def _generate_audio(
        self,
        tts_engine: TTSInterface,
        text: str,
    ) -> str:
        logger.debug(f"🏃Generating audio for '''{text}'''...")
        generate_start = asyncio.get_running_loop().time()

        result = await tts_engine.async_generate_audio(
            text=text,
            file_name_no_ext=(
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                f"{str(uuid.uuid4())[:8]}"
            ),
        )

        generate_elapsed = asyncio.get_running_loop().time() - generate_start
        logger.info(
            f"🎙️ GPT-SoVITS generation took {generate_elapsed:.2f}s "
            f"for {len(text)} chars."
        )
        return result

    def clear(self) -> None:
        self.task_list.clear()
        self._pending_requests.clear()

        if self._sender_task:
            self._sender_task.cancel()

        self._sender_task = None
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        self._payload_queue = asyncio.Queue()
