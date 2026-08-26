import asyncio
import random
import re
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

import websockets
from loguru import logger

TWITCH_IRC_WS_URL = "wss://irc-ws.chat.twitch.tv:443"

RECONNECT_DELAY_SECONDS = 5

_PRIVMSG_PATTERN = re.compile(
    r"^(?:@(?P<tags>\S+) )?"
    r":(?P<username>[^!]+)!\S+ PRIVMSG #(?P<channel>\S+) :(?P<message>.*)$"
)


@dataclass
class ChatMessageEvent:
    """A single parsed Twitch chat message, equivalent in shape to the
    `payload` object built in the previous tmi.js implementation."""

    channel: str
    username: str
    message: str
    timestamp: float
    color: str = "#ffffff"
    subscriber: bool = False
    mod: bool = False
    vip: bool = False
    emotes: str | None = None
    display_name: str | None = None


def _parse_irc_tags(raw_tags: str) -> dict[str, str]:
    """
    Parses Twitch's IRCv3 tag string (the part after '@', before the
    first space) into a dict. Format: key1=value1;key2=value2;...
    Escaped characters (\\s, \\:, \\\\) per IRCv3 spec are unescaped.
    """
    tags: dict[str, str] = {}
    for pair in raw_tags.split(";"):
        if "=" not in pair:
            continue
        key, _, value = pair.partition("=")
        value = value.replace("\\s", " ").replace("\\:", ";").replace("\\\\", "\\")
        tags[key] = value
    return tags


def _parse_privmsg_line(line: str) -> ChatMessageEvent | None:
    """Parses a single raw IRC line into a ChatMessageEvent, or None if
    the line isn't a chat message (e.g. PING, JOIN confirmations)."""
    match = _PRIVMSG_PATTERN.match(line)
    if not match:
        return None

    tags = _parse_irc_tags(match.group("tags") or "")

    return ChatMessageEvent(
        channel=match.group("channel"),
        username=match.group("username"),
        message=match.group("message"),
        timestamp=time.time(),
        color=tags.get("color") or "#ffffff",
        subscriber=tags.get("subscriber") == "1",
        mod=tags.get("mod") == "1",
        vip="vip" in tags and tags.get("vip") not in (None, "0"),
        emotes=tags.get("emotes") or None,
        display_name=tags.get("display-name") or None,
    )


class TwitchChatListener:
    """
    Anonymous, read-only Twitch chat listener over IRC-over-WebSocket.
    """

    def __init__(self, channel: str) -> None:
        self.channel = channel.lower().lstrip("#")

    async def listen(self) -> AsyncIterator[ChatMessageEvent]:
        while True:
            try:
                async for event in self._connect_and_listen():
                    yield event
            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                logger.warning(
                    f"Twitch chat connection lost for #{self.channel} "
                    f"({e}) — reconnecting in {RECONNECT_DELAY_SECONDS}s"
                )
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def _connect_and_listen(self) -> AsyncIterator[ChatMessageEvent]:
        anon_nick = f"justinfan{random.randint(10000, 99999)}"

        async with websockets.connect(TWITCH_IRC_WS_URL) as ws:
            await ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands")
            await ws.send(f"NICK {anon_nick}")
            await ws.send(f"JOIN #{self.channel}")

            logger.info(f"Twitch chat connected to #{self.channel} (anonymous)")

            async for raw_message in ws:
                for line in raw_message.strip().split("\r\n"):
                    if not line:
                        continue

                    if line.startswith("PING"):
                        await ws.send("PONG :tmi.twitch.tv")
                        continue

                    event = _parse_privmsg_line(line)
                    if event is not None:
                        yield event