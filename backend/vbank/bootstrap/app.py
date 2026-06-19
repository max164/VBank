from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vbank.shared.api.exceptions import register_exception_handlers
from vbank.shared.api.middleware import RequestContextMiddleware
from vbank.shared.api.router import api_v1_router
from vbank.shared.config import get_settings
from vbank.shared.telemetry import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.environment)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.environment,
        }

    return app
