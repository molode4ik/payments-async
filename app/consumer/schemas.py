import uuid

from pydantic import BaseModel


class PaymentEventPayload(BaseModel):
    payment_id: uuid.UUID
    amount: str
    currency: str
