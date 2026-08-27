import asyncio
from typing import Optional

from loguru import logger

from app.services.twitch_listener import TwitchChatListener
from app.services.twitch_data_adapter import TwitchChatAggregator, build_snapshot_row
from app.services.twitch_service import get_stream_info, TwitchAPIError

DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 5
DEFAULT_WINDOW_SECONDS = 60

MAX_ROWS_KEPT = 720


class TwitchLiveSession:
    """
    Orchestrates one live Twitch data session for a single channel.

    Usage:
        session = TwitchLiveSession(channel="tarik")
        first_row = await session.take_snapshot_now()  # seed initial data
        await session.start()  # begin continuous background updates
        ...
        current_rows = session.rows  # read anytime
        ...
        await session.stop()
    """

    def __init__(
        self,
        channel: str,
        snapshot_interval_seconds: int = DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.channel = channel
        self.snapshot_interval_seconds = snapshot_interval_seconds
        self._aggregator = TwitchChatAggregator(window_seconds=window_seconds)
        self._listener = TwitchChatListener(channel=channel)
        self._rows: list[dict] = []
        self._listener_task: Optional[asyncio.Task] = None
        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False

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
        """Begins continuous background updates: the chat listener and
        the periodic snapshot loop both run until stop() is called."""
        if self._running:
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._run_chat_listener())
        self._snapshot_task = asyncio.create_task(self._run_snapshot_loop())
        logger.info(f"Twitch live session started for #{self.channel}")

    async def stop(self) -> None:
        self._running = False
        for task in (self._listener_task, self._snapshot_task):
            if task is not None:
                task.cancel()
        logger.info(f"Twitch live session stopped for #{self.channel}")

    async def _run_chat_listener(self) -> None:
        async for event in self._listener.listen():
            self._aggregator.add_event(event)

    async def _run_snapshot_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.snapshot_interval_seconds)
            try:
                row = await self._build_row()
                self._rows.append(row)
                self._trim_rows()
            except TwitchAPIError as e:
                logger.warning(f"Twitch snapshot failed for #{self.channel}: {e}")

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