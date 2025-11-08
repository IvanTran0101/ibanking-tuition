import logging
from fastapi import FastAPI
import threading

from account_service.app.api import router as api_router
from account_service.app.messaging.consumer import start_consumers

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="account_service")
    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers in a background daemon thread so API remains responsive
        try:
            threading.Thread(target=start_consumers, name="rmq-consumer", daemon=True).start()
        except Exception:
            # Do not crash API startup if consumers fail; they can be restarted.
            pass

    return app


app = create_app()
