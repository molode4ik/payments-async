import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.models.payment import Currency, Payment
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.payment_repository import PaymentRepository

NEW_PAYMENT_EVENT = "payments.new"


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.payments = PaymentRepository(session)
        self.outbox = OutboxRepository(session)

    async def create_payment(
        self,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        description: str | None,
        metadata: dict[str, Any] | None,
        webhook_url: str,
    ) -> Payment:
        existing = await self.payments.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        payment = Payment(
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            description=description,
            payment_metadata=metadata,
            webhook_url=webhook_url,
        )
        self.payments.add(payment)

        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.payments.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing
            raise

        self.outbox.add(
            OutboxEvent(
                aggregate_id=payment.id,
                event_type=NEW_PAYMENT_EVENT,
                payload={
                    "payment_id": str(payment.id),
                    "amount": str(payment.amount),
                    "currency": payment.currency.value,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.payments.get_by_id(payment_id)
