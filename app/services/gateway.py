import asyncio
import random

MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5
SUCCESS_RATE = 0.9


class PaymentGatewayClient:
    async def charge(self) -> bool:
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
        return random.random() < SUCCESS_RATE
