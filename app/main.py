from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_handlers import (
    http_exception_handler,
    secflow_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.middleware import SecurityMiddleware
from app.api.routes import router
from app.core.config import Settings
from app.core.errors import SecFlowError


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="SecFlow Repository Analysis Service",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    # Store settings on app state
    app.state.settings = settings

    # Add middleware
    app.add_middleware(SecurityMiddleware)

    # Add exception handlers
    # FastAPI signature mismatches for exception handlers require type ignores
    app.add_exception_handler(SecFlowError, secflow_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Add routes
    app.include_router(router)

    return app
