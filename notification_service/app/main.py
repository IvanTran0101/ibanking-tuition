from fastapi import FastAPI

from notification_service.app.messaging.consumer import start_consumers


def create_app() -> FastAPI:
    app = FastAPI(title="notification_service")

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
