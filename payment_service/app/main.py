from fastapi import FastAPI

from payment_service.app.api import router as api_router
from payment_service.app.messaging.consumer import start_consumers


def create_app() -> FastAPI:
    app = FastAPI(title="payment_service")
    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers in background threads
        try:
            start_consumers()
        except Exception:
            # Do not crash API startup if consumers fail; they can be restarted.
            pass

    return app


app = create_app()
