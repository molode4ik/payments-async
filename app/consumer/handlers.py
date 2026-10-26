import logging

from faststream.rabbit.annotations import RabbitMessage

from app.broker.rabbitmq import (
    BASE_RETRY_DELAY_SECONDS,
    DLQ_EXCHANGE,
    DLQ_ROUTING_KEY,
    MAIN_EXCHANGE,
    MAX_RETRIES,
    NEW_PAYMENT_QUEUE,
    RETRY_EXCHANGE,
    RETRY_ROUTING_KEY,
    broker,
)
from app.consumer.processor import PaymentProcessor
from app.consumer.schemas import PaymentEventPayload

logger = logging.getLogger(__name__)
processor = PaymentProcessor()


async def _retry_or_deadletter(payload: PaymentEventPayload, msg: RabbitMessage, error: Exception) -> None:
    attempt = int(msg.headers.get("x-retry-count", 0))

    if attempt < MAX_RETRIES:
        delay_seconds = BASE_RETRY_DELAY_SECONDS * (2**attempt)
        logger.warning(
            "payment %s processing failed (attempt %s), retrying in %ss: %s",
            payload.payment_id,
            attempt + 1,
            delay_seconds,
            error,
        )
        await broker.publish(
            payload.model_dump(mode="json"),
            exchange=RETRY_EXCHANGE,
            routing_key=RETRY_ROUTING_KEY,
            headers={"x-retry-count": attempt + 1},
            expiration=delay_seconds,
        )
    else:
        logger.error("payment %s exhausted retries, sending to DLQ: %s", payload.payment_id, error)
        await broker.publish(
            payload.model_dump(mode="json"),
            exchange=DLQ_EXCHANGE,
            routing_key=DLQ_ROUTING_KEY,
            headers={"x-retry-count": attempt, "x-error": str(error)},
        )


@broker.subscriber(NEW_PAYMENT_QUEUE, exchange=MAIN_EXCHANGE)
async def handle_new_payment(payload: PaymentEventPayload, msg: RabbitMessage) -> None:
    try:
        await processor.process(payload.payment_id)
    except Exception as exc:  # noqa: BLE001
        await _retry_or_deadletter(payload, msg, exc)
