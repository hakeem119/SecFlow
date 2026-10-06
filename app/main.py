import asyncio
import os
import stat
import time
import typing
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from app.api.error_handlers import (
    http_exception_handler,
    secflow_error_handler,
    validation_exception_handler,
)
from app.api.middleware import SecurityMiddleware
from app.api.routes import router
from app.core.config import Settings
from app.core.errors import ErrorCode, SecFlowError
from app.services.reaper import WorkspaceReaper
from app.services.workspace import WorkspaceManager


class StartupError(SecFlowError):
    stable_code = ErrorCode.INTERNAL_ERROR
    message = "Service startup failed due to environment configuration."


def _validate_dir(path: os.PathLike[str], expected_dev: int | None = None) -> int:
    try:
        st = os.lstat(path)
    except OSError as e:
        raise StartupError() from e

    if not stat.S_ISDIR(st.st_mode):
        raise StartupError()
    if st.st_uid != os.getuid():
        raise StartupError()
    if (st.st_mode & 0o077) != 0:
        raise StartupError()
    if expected_dev is not None and st.st_dev != expected_dev:
        raise StartupError()
    return st.st_dev


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    root = settings.workspace_root

    if str(root) == "/" or len(root.parts) < 2:
        raise StartupError()

    try:
        # ASYNC240 requires blocking Path operations to be in a thread
        await asyncio.to_thread(Path(root).mkdir, mode=0o700, parents=True, exist_ok=True)
    except OSError as e:
        raise StartupError() from e

    root_dev = _validate_dir(root)

    meta_dir = root / ".meta"
    trash_dir = root / ".trash"

    for d in (meta_dir, trash_dir):
        try:
            await asyncio.to_thread(Path(d).mkdir, mode=0o700, parents=True, exist_ok=True)
        except OSError as e:
            raise StartupError() from e
        _validate_dir(d, expected_dev=root_dev)

    # Setup manager and reaper
    manager = WorkspaceManager(root, settings.ttl_hours * 3600, time.time)
    reaper = WorkspaceReaper(manager, settings.reaper_interval_seconds)

    app.state.workspace_manager = manager
    app.state.reaper_task = asyncio.create_task(reaper.start())

    try:
        yield
    finally:
        app.state.reaper_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.reaper_task


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="SecFlow Repository Analysis Service",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # Store settings on app state
    app.state.settings = settings

    # Add middleware
    app.add_middleware(SecurityMiddleware)

    # Add exception handlers
    # Starlette's handler signature typing

    app.add_exception_handler(SecFlowError, typing.cast(ExceptionHandler, secflow_error_handler))
    app.add_exception_handler(
        RequestValidationError, typing.cast(ExceptionHandler, validation_exception_handler)
    )
    app.add_exception_handler(
        StarletteHTTPException, typing.cast(ExceptionHandler, http_exception_handler)
    )

    # Add routes
    app.include_router(router)

    return app
