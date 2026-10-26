# Payment Processing Service

Асинхронный микросервис процессинга платежей: принимает запросы на оплату, эмулирует
обработку через внешний платёжный шлюз и уведомляет клиента о результате через webhook.

## Архитектура

Слоистая архитектура:

- `app/api` — HTTP-эндпоинты (FastAPI), схемы запросов/ответов
- `app/core` — сквозные задачи (аутентификация по API-ключу)
- `app/services` — бизнес-логика (создание платежа, эмуляция шлюза, отправка webhook)
- `app/repositories` — доступ к данным (SQLAlchemy)
- `app/models` — ORM-модели (`payments`, `outbox_events`)
- `app/broker` — топология RabbitMQ (exchange/queue/DLQ) и брокер FastStream
- `app/outbox` — relay, публикующий события из таблицы outbox в очередь
- `app/consumer` — обработчик очереди `payments.new`

Гарантированная доставка событий реализована через **Outbox pattern**: при создании
платежа в одной транзакции с записью в `payments` создаётся запись в `outbox_events`.
Фоновый relay-процесс внутри API-сервиса опрашивает таблицу и публикует неотправленные
события в RabbitMQ, помечая их как опубликованные.

### Топология RabbitMQ

- `payments` (topic exchange) → очередь `payments.new` — основная очередь обработки
- `payments.retry` (direct exchange) → очередь `payments.retry` — задержка перед
  повтором (per-message TTL), с `x-dead-letter-exchange` обратно на `payments`
- `payments.dlq` (direct exchange) → очередь `payments.new.dlq` — сообщения,
  не обработанные после 3 попыток

При ошибке обработки consumer публикует сообщение в `payments.retry` с экспоненциальной
задержкой (2с, 4с, 8с). После исчерпания 3 попыток сообщение уходит в DLQ.

Обработка платежа идемпотентна: если статус платежа уже выставлен (succeeded/failed),
повторная обработка сообщения не запускает эмуляцию шлюза заново, а только повторяет
отправку webhook.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Поднимутся: `postgres`, `rabbitmq` (management UI на `localhost:15672`, guest/guest),
`api` (применяет миграции и стартует на `localhost:8000`), `consumer`.

## Аутентификация

Все эндпоинты требуют заголовок `X-API-Key` (значение задаётся переменной окружения
`API_KEY`, по умолчанию `change-me`).

## Примеры запросов

Создание платежа:

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: 8f14e45f-ceea-4e51-9d1b-1c1c1c1c1c1c" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.50",
    "currency": "RUB",
    "description": "Order #42",
    "metadata": {"order_id": "42"},
    "webhook_url": "https://example.com/webhooks/payments"
  }'
```

Ответ `202 Accepted`:

```json
{
  "payment_id": "b2d3c1e4-...",
  "status": "pending",
  "created_at": "2026-07-02T12:00:00Z"
}
```

Получение платежа:

```bash
curl http://localhost:8000/api/v1/payments/b2d3c1e4-... \
  -H "X-API-Key: change-me"
```

Повторный запрос с тем же `Idempotency-Key` вернёт тот же платёж без создания дубля.

## Миграции

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic revision -m "message"
```
