# libs/rmq/consumer.py
import threading
from typing import Callable, Dict, Any, Optional
from .bus import declare_queue, start_consume

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

# --- NEW: chạy mỗi subscription trên 1 thread ---
_threads: list[threading.Thread] = []

def run(subscriptions: list[Subscription], *, join: bool = False) -> None:
    """
    Khởi động tất cả consumer song song (mỗi queue 1 thread).
    - join=True: dùng cho script/worker đứng độc lập (giữ process không thoát).
    - join=False: dùng trong FastAPI (không block event loop của web server).
    """
    global _threads
    for sub in subscriptions:
        t = threading.Thread(
            target=start_consume,
            args=(sub.queue, sub.handler),
            name=f"rmq-consumer:{sub.queue}",
            daemon=True  # dừng theo process, tránh treo khi shutdown
        )
        t.start()
        _threads.append(t)

    if join:
        for t in _threads:
            t.join()
