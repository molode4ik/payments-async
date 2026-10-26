import uuid
from datetime import datetime, timezone

from app.db.session import async_session_maker
from app.models.payment import PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.services.gateway import PaymentGatewayClient
from app.services.webhook_sender import WebhookSender

gateway = PaymentGatewayClient()
webhook_sender = WebhookSender()


class PaymentProcessor:
    async def process(self, payment_id: uuid.UUID) -> None:
        async with async_session_maker() as session:
            repo = PaymentRepository(session)
            payment = await repo.get_by_id(payment_id)
            if payment is None:
                return

            if payment.status == PaymentStatus.PENDING:
                succeeded = await gateway.charge()
                new_status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
                await repo.update_status(payment.id, new_status, datetime.now(timezone.utc))
                await session.commit()
                await session.refresh(payment)

            await webhook_sender.send(
                payment.webhook_url,
                {
                    "payment_id": str(payment.id),
                    "status": payment.status.value,
                    "amount": str(payment.amount),
                    "currency": payment.currency.value,
                    "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                },
            )
