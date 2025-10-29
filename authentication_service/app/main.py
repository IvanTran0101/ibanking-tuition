from fastapi import FastAPI
from authentication_service.app.api import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="authentication_service")
    app.include_router(api_router)
    return app


app = create_app()
