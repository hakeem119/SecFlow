from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.dependencies import get_workspace_manager
from app.core.errors import NotImplementedYetError
from app.schemas.api import AnalyzeRequest, AnalyzeResponse, ErrorResponse, HealthResponse
from app.schemas.domain import WorkspaceId
from app.services.workspace import WorkspaceManager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(status="ok")


@router.post(
    "/api/v1/repositories/analyze",
    response_model=AnalyzeResponse,
    responses={
        422: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        501: {"model": ErrorResponse},
    },
)
async def analyze_repository(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a repository."""
    raise NotImplementedYetError()


@router.delete(
    "/api/v1/workspaces/{workspace_id}",
    status_code=204,
    responses={
        422: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def delete_workspace(
    workspace_id: Annotated[
        WorkspaceId, Path(..., description="The ID of the workspace to delete")
    ],
    manager: Annotated[WorkspaceManager, Depends(get_workspace_manager)],
) -> None:
    """Delete a workspace."""
    await manager.delete(str(workspace_id))
