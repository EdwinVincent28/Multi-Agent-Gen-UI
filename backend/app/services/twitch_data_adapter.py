import time
from collections import deque, Counter
from dataclasses import dataclass, field

from app.services.twitch_listener import ChatMessageEvent

DEFAULT_WINDOW_SECONDS = 60


@dataclass
class ChatWindowStats:
    """Stats computed from real events in the current sliding window"""

    window_seconds: int
    message_count: int
    unique_chatters: int
    top_emote_name: str | None
    top_emote_count: int


def _extract_emote_names(event: ChatMessageEvent) -> list[str]:
    """
    Extracts the literal emote text a user typed
    """
    if not event.emotes:
        return []

    names = []
    for emote_def in event.emotes.split("/"):
        if ":" not in emote_def:
            continue
        _emote_id, ranges = emote_def.split(":", 1)
        first_range = ranges.split(",")[0]
        if "-" not in first_range:
            continue
        try:
            start, end = (int(x) for x in first_range.split("-"))
            names.append(event.message[start : end + 1])
        except (ValueError, IndexError):
            continue

    return names


class TwitchChatAggregator:
    """
    Maintains a sliding window of recent chat events and computes stats
    over that window on demand. 
    """

    def __init__(self, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> None:
        self.window_seconds = window_seconds
        self._events: deque[ChatMessageEvent] = deque()

    def add_event(self, event: ChatMessageEvent) -> None:
        self._events.append(event)
        self._prune()

    def _prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        while self._events and self._events[0].timestamp < cutoff:
            self._events.popleft()

    def get_stats(self) -> ChatWindowStats:
        self._prune()

        message_count = len(self._events)
        unique_chatters = len({e.username for e in self._events})

        emote_counter: Counter[str] = Counter()
        for event in self._events:
            for name in _extract_emote_names(event):
                emote_counter[name] += 1

        if emote_counter:
            top_emote_name, top_emote_count = emote_counter.most_common(1)[0]
        else:
            top_emote_name, top_emote_count = None, 0

        return ChatWindowStats(
            window_seconds=self.window_seconds,
            message_count=message_count,
            unique_chatters=unique_chatters,
            top_emote_name=top_emote_name,
            top_emote_count=top_emote_count,
        )


def build_snapshot_row(chat_stats: ChatWindowStats, viewer_count: int, is_live: bool) -> dict:
    """
    Combines a chat window snapshot and current viewer count into one
    clean_data row, shaped consistently so it can accumulate into a
    growing list exactly like CSV rows already do.
    """
    return {
        "timestamp": time.time(),
        "viewer_count": viewer_count,
        "is_live": is_live,
        "messages_in_window": chat_stats.message_count,
        "window_seconds": chat_stats.window_seconds,
        "unique_chatters": chat_stats.unique_chatters,
        "top_emote": chat_stats.top_emote_name or "",
        "top_emote_count": chat_stats.top_emote_count,
    }