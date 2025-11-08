import logging
import sys
from fastapi import FastAPI

from notification_service.app.messaging.consumer import start_consumers

logger = logging.getLogger("notification_service")
logger.setLevel(logging.INFO)

# Reuse uvicorn handlers when available, otherwise fall back to stdout.
uvicorn_logger = logging.getLogger("uvicorn.error")
if uvicorn_logger.handlers:
    for handler in uvicorn_logger.handlers:
        logger.addHandler(handler)
else:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(stream_handler)


def create_app() -> FastAPI:
    app = FastAPI(title="notification_service")

    @app.on_event("startup")
    def _startup() -> None:
        # Start RMQ consumers in background threads. If this fails we want to know,
        # otherwise emails will silently stop flowing.
        try:
            start_consumers()
            logger.info("Notification consumers started.")
        except Exception as exc:
            logger.exception("Failed to start notification consumers", exc_info=exc)
            raise

    return app


app = create_app()
