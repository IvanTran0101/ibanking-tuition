import logging
import threading
from fastapi import FastAPI

from otp_service.app.api import router as api_router
from otp_service.app.messaging.consumer import start_consumers


logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="otp_service")
    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers in a daemon thread so FastAPI can finish booting
        try:
            threading.Thread(target=start_consumers, name="rmq-consumer", daemon=True).start()
        except Exception:
            # Do not crash API startup if consumers fail; they can be restarted.
            pass

    return app


app = create_app()
