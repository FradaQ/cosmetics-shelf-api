from fastapi import FastAPI

from app.config import get_settings
from app.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Cosmetics Shelf API",
        version=settings.app_version,
        description="Product lookup and batch-code estimation for Cosmetics Shelf.",
    )
    app.include_router(router)
    return app


app = create_app()

