from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.broker.rabbitmq import broker, declare_topology
from app.outbox.relay import outbox_relay


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    await declare_topology()
    outbox_relay.start()
    yield
    await outbox_relay.stop()
    await broker.stop()


app = FastAPI(title="Payment Processing Service", lifespan=lifespan)
app.include_router(api_router)
