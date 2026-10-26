import asyncio
import logging

from app.broker.rabbitmq import MAIN_EXCHANGE, NEW_PAYMENT_ROUTING_KEY, broker
from app.db.session import async_session_maker
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 0.5
BATCH_SIZE = 50


class OutboxRelay:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._publish_batch()
            except Exception:
                logger.exception("outbox relay iteration failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _publish_batch(self) -> None:
        async with async_session_maker() as session, session.begin():
            repo = OutboxRepository(session)
            events = await repo.fetch_unpublished(BATCH_SIZE)
            for event in events:
                await broker.publish(
                    event.payload,
                    exchange=MAIN_EXCHANGE,
                    routing_key=NEW_PAYMENT_ROUTING_KEY,
                )
                await repo.mark_published(event.id)


outbox_relay = OutboxRelay()
