import logging
from fastapi import FastAPI
import threading

from tuition_service.app.api import router as api_router
from tuition_service.app.messaging.consumer import start_consumers

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="tuition_service")
    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers in a background daemon thread so API remains responsive
        try:
            threading.Thread(target=start_consumers, name="rmq-consumer", daemon=True).start()
        except Exception:
            # Do not crash API startup if consumer thread fails to start
            pass

    return app


app = create_app()
