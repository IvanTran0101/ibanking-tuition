# libs/rmq/consumer.py
from typing import Callable, Dict, Any, Optional
from .bus import declare_queue, start_consume

# Registry nhỏ để dễ đăng ký nhiều handler
class Subscription:
    def __init__(self, queue: str, routing_key: str,
                 handler: Callable[[Dict[str, Any], Dict[str, Any], str], None]):
        self.queue = queue
        self.routing_key = routing_key
        self.handler = handler

def subscribe(queue: str,
              routing_key: str,
              handler: Callable[[Dict[str, Any], Dict[str, Any], str], None],
              *,
              dead_letter: bool = True,
              prefetch: int = 32) -> Subscription:
    declare_queue(queue=queue, routing_key=routing_key,
                  dead_letter=dead_letter, prefetch=prefetch)
    return Subscription(queue, routing_key, handler)

def run(subscriptions: list[Subscription]) -> None:
    """
    Gọi khi service khởi động (có thể chạy mỗi subscription ở 1 thread nếu muốn).
    Ở bản tối giản này chạy tuần tự – mở 1 consumer/blocking.
    """
    # Nếu bạn muốn chạy song song nhiều queue:
    # tạo thread cho mỗi subscription để start_consume(sub.queue, sub.handler)
    for sub in subscriptions:
        start_consume(sub.queue, sub.handler)
