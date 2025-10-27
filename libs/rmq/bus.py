# libs/rmq/bus.py
import json, os, threading, time, uuid
from typing import Callable, Optional, Dict, Any
import pika

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/%2f")
EXCHANGE = os.getenv("EVENT_EXCHANGE", "ibanking.events")       # topic exchange
DLX      = os.getenv("EVENT_DLX", "ibanking.dlx")               # dead-letter exchange

# Singleton connection/channel cho cả process
class _Rmq:
    _conn: Optional[pika.BlockingConnection] = None
    _lock = threading.Lock()

    @classmethod
    def _connect(cls) -> pika.BlockingConnection:
        params = pika.URLParameters(RABBIT_URL)
        params.heartbeat = 30
        params.blocked_connection_timeout = 60
        return pika.BlockingConnection(params)

    @classmethod
    def channel(cls) -> pika.adapters.blocking_connection.BlockingChannel:
        with cls._lock:
            if cls._conn is None or cls._conn.is_closed:
                cls._conn = cls._connect()
            ch = cls._conn.channel()
            # Topology: exchanges
            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            ch.exchange_declare(exchange=DLX, exchange_type="topic", durable=True)
            return ch

def declare_queue(queue: str, routing_key: str, *,
                  dead_letter: bool = True,
                  prefetch: int = 32) -> None:
    """
    Khai báo queue và bind vào exchange chính; tự gắn DLQ nếu dead_letter=True.
    DLQ tên: <queue>.dlq -> bind vào DLX với cùng routing_key.
    """
    ch = _Rmq.channel()

    args = {}
    if dead_letter:
        args["x-dead-letter-exchange"] = DLX
        args["x-dead-letter-routing-key"] = routing_key

    ch.queue_declare(queue=queue, durable=True, arguments=args)
    ch.queue_bind(queue=queue, exchange=EXCHANGE, routing_key=routing_key)

    # DLQ
    dlq = f"{queue}.dlq"
    ch.queue_declare(queue=dlq, durable=True)
    ch.queue_bind(queue=dlq, exchange=DLX, routing_key=routing_key)

    ch.basic_qos(prefetch_count=prefetch)

def publish(routing_key: str,
            body: Dict[str, Any],
            headers: Optional[Dict[str, Any]] = None,
            message_id: Optional[str] = None,
            content_type: str = "application/json",
            persistent: bool = True) -> None:
    """
    Publish một event JSON lên topic exchange.
    """
    ch = _Rmq.channel()
    props = pika.BasicProperties(
        content_type=content_type,
        delivery_mode=2 if persistent else 1,
        headers=headers or {},
        message_id=message_id or str(uuid.uuid4())
    )
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(body).encode("utf-8"),
        properties=props
    )

def start_consume(queue: str, on_message: Callable[[Dict[str, Any], Dict[str, Any], str], None]) -> None:
    """
    Bắt đầu consume; `on_message(payload, headers, message_id)` phải raise Exception nếu xử lý fail.
    Hệ thống sẽ nack (không requeue) để đẩy sang DLQ theo cấu hình.
    """
    ch = _Rmq.channel()

    def _callback(ch_, method, props, body_bytes):
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
            headers = props.headers or {}
            msg_id = props.message_id
            on_message(payload, headers, msg_id)
            ch_.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as ex:
            # Mark retry count (header x-retry) để bạn có thể monitor
            h = props.headers or {}
            retries = int(h.get("x-retry", 0))
            h["x-retry"] = retries + 1

            # NACK không requeue -> sang DLQ (nhờ x-dead-letter-exchange)
            ch_.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    ch.basic_consume(queue=queue, on_message_callback=_callback, auto_ack=False)
    # Blocking loop—nên gọi trong thread của service khi start app
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        try:
            ch.stop_consuming()
        except Exception:
            pass
