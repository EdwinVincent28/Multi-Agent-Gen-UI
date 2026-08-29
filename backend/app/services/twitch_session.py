"""
Twitch API integration — live session orchestration.

Ties together the chat listener (twitch_listener.py), the sliding-
window aggregator (twitch_data_adapter.py), and the viewer count fetch
(twitch_service.py) into one running background session: continuously
listen to chat, and periodically combine chat stats + viewer count into
a new clean_data-shaped row.

Also runs a third background task that periodically indexes the session
into Qdrant for RAG-based Q&A (memory_service.py's
store_twitch_context_batch) — a deterministic stats summary plus a
filtered chat excerpt, every INDEXING_INTERVAL_SECONDS.

This class only produces data and indexes it — it doesn't know about
the swarm graph or WebSockets. Those are separate concerns, wired in
elsewhere.
"""

import asyncio
import os
import time
from typing import Optional

from loguru import logger

from app.services.twitch_listener import TwitchChatListener
from app.services.twitch_data_adapter import TwitchChatAggregator, build_snapshot_row
from app.services.twitch_service import get_stream_info, TwitchAPIError
from app.services.memory_service import store_twitch_context_batch

DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 5
DEFAULT_WINDOW_SECONDS = 60
INDEXING_INTERVAL_SECONDS = int(os.getenv("TWITCH_INDEXING_INTERVAL_SECONDS", "300"))

MAX_ROWS_KEPT = 720

MIN_SUBSTANTIVE_MESSAGE_LENGTH = 15

MAX_CHAT_TEXT_CHARS = 3000


def _is_substantive_message(text: str) -> bool:
    return len(text.strip()) >= MIN_SUBSTANTIVE_MESSAGE_LENGTH


def _build_stats_text(rows_in_window: list[dict]) -> str:
    """
    Deterministic (non-LLM) summary of a batch of snapshot rows into one
    sentence-shaped blurb for embedding
    """
    if not rows_in_window:
        return "No data recorded in this window."

    viewer_counts = [r["viewer_count"] for r in rows_in_window]
    min_v, max_v = min(viewer_counts), max(viewer_counts)
    avg_v = sum(viewer_counts) / len(viewer_counts)

    msg_counts = [r["messages_in_window"] for r in rows_in_window]
    avg_msgs = sum(msg_counts) / len(msg_counts) if msg_counts else 0

    emote_totals: dict[str, int] = {}
    for r in rows_in_window:
        emote = r.get("top_emote")
        if emote:
            emote_totals[emote] = emote_totals.get(emote, 0) + r.get("top_emote_count", 0)
    top_emote = max(emote_totals, key=emote_totals.get) if emote_totals else None

    text = f"Viewers ranged {min_v}-{max_v} (avg {avg_v:.0f}). Average chat activity: {avg_msgs:.0f} messages per window."
    if top_emote:
        text += f" Most-used emote: {top_emote} ({emote_totals[top_emote]} uses)."
    return text


def _build_chat_text(messages: list[str]) -> Optional[str]:
    """Joins buffered chat messages into one blob for embedding, capped
    to a reasonable length. Returns None if there was no substantive
    chat activity in the window — no point storing an empty chunk."""
    if not messages:
        return None
    joined = " | ".join(messages)
    if len(joined) > MAX_CHAT_TEXT_CHARS:
        joined = joined[:MAX_CHAT_TEXT_CHARS] + "... [truncated]"
    return joined


class TwitchLiveSession:
    """
    Orchestrates one live Twitch data session for a single channel.
    """

    def __init__(
        self,
        channel: str,
        session_id: str,
        snapshot_interval_seconds: int = DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.channel = channel
        self.session_id = session_id
        self.snapshot_interval_seconds = snapshot_interval_seconds
        self._aggregator = TwitchChatAggregator(window_seconds=window_seconds)
        self._listener = TwitchChatListener(channel=channel)
        self._rows: list[dict] = []
        self._listener_task: Optional[asyncio.Task] = None
        self._snapshot_task: Optional[asyncio.Task] = None
        self._indexing_task: Optional[asyncio.Task] = None
        self._running = False
        self._chat_text_buffer: list[str] = []
        self._last_index_time: float = time.time()

    @property
    def rows(self) -> list[dict]:
        """Current accumulated snapshot rows, shaped like clean_data.
        Returns a copy so callers can't mutate internal state."""
        return list(self._rows)

    async def take_snapshot_now(self) -> dict:
        """
        Builds and appends one row immediately, without waiting for the
        periodic loop. Used to seed real data before the very first swarm
        generation runs, so it isn't starting from an empty list.
        """
        row = await self._build_row()
        self._rows.append(row)
        self._trim_rows()
        return row

    async def start(self) -> None:
        """Begins continuous background updates: the chat listener, the
        periodic snapshot loop, and the RAG indexing loop all run until
        stop() is called."""
        if self._running:
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._run_chat_listener())
        self._snapshot_task = asyncio.create_task(self._run_snapshot_loop())
        self._indexing_task = asyncio.create_task(self._run_indexing_loop())
        logger.info(f"Twitch live session started for #{self.channel}")

    async def stop(self) -> None:
        self._running = False
        for task in (self._listener_task, self._snapshot_task, self._indexing_task):
            if task is not None:
                task.cancel()
        logger.info(f"Twitch live session stopped for #{self.channel}")

    async def _run_chat_listener(self) -> None:
        async for event in self._listener.listen():
            self._aggregator.add_event(event)
            if _is_substantive_message(event.message):
                self._chat_text_buffer.append(event.message)

    async def _run_snapshot_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.snapshot_interval_seconds)
            try:
                row = await self._build_row()
                self._rows.append(row)
                self._trim_rows()
            except TwitchAPIError as e:
                logger.warning(f"Twitch snapshot failed for #{self.channel}: {e}")

    async def _run_indexing_loop(self) -> None:
        while self._running:
            await asyncio.sleep(INDEXING_INTERVAL_SECONDS)
            try:
                window_start = self._last_index_time
                window_end = time.time()

                rows_in_window = [r for r in self._rows if window_start <= r["timestamp"] <= window_end]
                stats_text = _build_stats_text(rows_in_window)

                chat_messages = self._chat_text_buffer
                self._chat_text_buffer = []
                chat_text = _build_chat_text(chat_messages)

                await asyncio.to_thread(
                    store_twitch_context_batch,
                    session_id=self.session_id,
                    channel=self.channel,
                    window_start=window_start,
                    window_end=window_end,
                    stats_text=stats_text,
                    chat_text=chat_text,
                )
                self._last_index_time = window_end
            except Exception as e:
                logger.warning(f"Twitch RAG indexing failed for #{self.channel}: {e}")

    async def _build_row(self) -> dict:
        stats = self._aggregator.get_stats()
        stream_info = await get_stream_info(self.channel)
        return build_snapshot_row(
            chat_stats=stats,
            viewer_count=stream_info["viewer_count"],
            is_live=stream_info["is_live"],
        )

    def _trim_rows(self) -> None:
        if len(self._rows) > MAX_ROWS_KEPT:
            self._rows = self._rows[-MAX_ROWS_KEPT:]