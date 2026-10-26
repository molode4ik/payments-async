from faststream import FastStream

from app.broker.rabbitmq import broker, declare_topology
from app.consumer import handlers  # noqa: F401

app = FastStream(broker)


@app.after_startup
async def _setup_topology() -> None:
    await declare_topology()
