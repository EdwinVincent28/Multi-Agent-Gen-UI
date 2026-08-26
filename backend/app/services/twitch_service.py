import os
import time
import asyncio
from dataclasses import dataclass

import httpx
from loguru import logger

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"

TOKEN_REFRESH_BUFFER_SECONDS = 300


class TwitchAuthError(Exception):
    """Raised when Twitch authentication fails or required config is missing."""


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float 


class TwitchAuthClient:
    """
    Fetches and caches a Twitch app access token.

    """

    def __init__(self) -> None:
        self._cached_token: _CachedToken | None = None
        self._refresh_lock = asyncio.Lock()

    def _read_config(self) -> tuple[str, str]:
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise TwitchAuthError(
                "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set. "
                "Register an app at https://dev.twitch.tv/console/apps to "
                "get these."
            )

        return client_id, client_secret

    def _is_cache_valid(self) -> bool:
        if self._cached_token is None:
            return False
        return time.time() < (self._cached_token.expires_at - TOKEN_REFRESH_BUFFER_SECONDS)

    async def get_access_token(self) -> str:
        """
        Returns a valid app access token, fetching a new one only if the
        cached token is missing or close to expiry.
        """
        if self._is_cache_valid():
            return self._cached_token.access_token

        async with self._refresh_lock:
            if self._is_cache_valid():
                return self._cached_token.access_token

            return await self._fetch_new_token()

    async def _fetch_new_token(self) -> str:
        client_id, client_secret = self._read_config()

        logger.info("Fetching new Twitch app access token")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    TWITCH_TOKEN_URL,
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "client_credentials",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise TwitchAuthError(
                    f"Twitch token request failed with status "
                    f"{e.response.status_code}: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise TwitchAuthError(f"Twitch token request failed: {e}") from e

        payload = response.json()
        access_token = payload["access_token"]
        expires_in = payload["expires_in"]  # seconds

        self._cached_token = _CachedToken(
            access_token=access_token,
            expires_at=time.time() + expires_in,
        )

        logger.info(f"Twitch app access token acquired, expires in {expires_in}s")

        return access_token

twitch_auth = TwitchAuthClient()