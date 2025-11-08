import logging
import sys
import threading
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
        # Start RMQ consumers in a daemon thread. If this fails we still want the
        # exception to bubble so deployment can fail fast.
        try:
            threading.Thread(target=start_consumers, name="notification-consumer", daemon=True).start()
            logger.info("Notification consumers started.")
        except Exception as exc:
            logger.exception("Failed to start notification consumers", exc_info=exc)
            raise

    return app


app = create_app()
