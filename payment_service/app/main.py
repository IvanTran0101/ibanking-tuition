import logging
import threading
from fastapi import FastAPI

from payment_service.app.api import router as api_router
from payment_service.app.messaging.consumer import start_consumers


logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="payment_service")
    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers on a daemon thread so FastAPI can finish starting
        try:
            threading.Thread(target=start_consumers, name="rmq-consumer", daemon=True).start()
        except Exception:
            # Do not crash API startup if consumers fail; they can be restarted.
            pass

    return app


app = create_app()
