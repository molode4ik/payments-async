from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings

MAX_RETRIES = 3
BASE_RETRY_DELAY_SECONDS = 2

NEW_PAYMENT_ROUTING_KEY = "payments.new"
RETRY_ROUTING_KEY = "retry"
DLQ_ROUTING_KEY = "dlq"

MAIN_EXCHANGE = RabbitExchange("payments", type=ExchangeType.TOPIC, durable=True)
RETRY_EXCHANGE = RabbitExchange("payments.retry", type=ExchangeType.DIRECT, durable=True)
DLQ_EXCHANGE = RabbitExchange("payments.dlq", type=ExchangeType.DIRECT, durable=True)

NEW_PAYMENT_QUEUE = RabbitQueue("payments.new", durable=True, routing_key=NEW_PAYMENT_ROUTING_KEY)

RETRY_QUEUE = RabbitQueue(
    "payments.retry",
    durable=True,
    routing_key=RETRY_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": MAIN_EXCHANGE.name,
        "x-dead-letter-routing-key": NEW_PAYMENT_ROUTING_KEY,
    },
)

DLQ_QUEUE = RabbitQueue("payments.new.dlq", durable=True, routing_key=DLQ_ROUTING_KEY)

broker = RabbitBroker(settings.rabbitmq_url)


async def declare_topology() -> None:
    main_exchange = await broker.declare_exchange(MAIN_EXCHANGE)
    retry_exchange = await broker.declare_exchange(RETRY_EXCHANGE)
    dlq_exchange = await broker.declare_exchange(DLQ_EXCHANGE)

    new_queue = await broker.declare_queue(NEW_PAYMENT_QUEUE)
    await new_queue.bind(main_exchange, routing_key=NEW_PAYMENT_ROUTING_KEY)

    retry_queue = await broker.declare_queue(RETRY_QUEUE)
    await retry_queue.bind(retry_exchange, routing_key=RETRY_ROUTING_KEY)

    dlq_queue = await broker.declare_queue(DLQ_QUEUE)
    await dlq_queue.bind(dlq_exchange, routing_key=DLQ_ROUTING_KEY)
