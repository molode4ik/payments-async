import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 10


class WebhookDeliveryError(Exception):
    pass


class WebhookSender:
    async def send(self, url: str, payload: dict[str, Any]) -> None:
        last_error: Exception | None = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("webhook delivery attempt %s failed: %s", attempt + 1, exc)
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(BASE_DELAY_SECONDS * (2**attempt))

        raise WebhookDeliveryError(str(last_error))
