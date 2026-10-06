import typing

from fastapi import Request

from app.core.errors import WorkspaceNotFoundError
from app.services.workspace import WorkspaceManager


def get_workspace_manager(request: Request) -> WorkspaceManager:
    """Dependency injection for WorkspaceManager."""
    try:
        return typing.cast(WorkspaceManager, request.app.state.workspace_manager)
    except AttributeError:
        raise WorkspaceNotFoundError() from None
