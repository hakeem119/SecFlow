import typing

from fastapi import Request

from app.core.errors import NotImplementedYetError, WorkspaceNotFoundError
from app.services.repository_service import RepositoryAnalysisService
from app.services.workspace import WorkspaceManager


def get_workspace_manager(request: Request) -> WorkspaceManager:
    """Dependency injection for WorkspaceManager."""
    try:
        return typing.cast(WorkspaceManager, request.app.state.workspace_manager)
    except AttributeError:
        raise WorkspaceNotFoundError() from None


from app.services.repository_service import RepositoryAnalysisService, AnalysisTool
from app.services.snapshot_adapter import SnapshotPortAdapter
from app.services.snapshot_builder import SnapshotPipeline
from app.services.workspace import WorkspaceManager
from app.services.workspace_scan import ScanLimits
from app.tools.git import GitAdapter
from app.tools.runner import ToolRunner
from app.tools.scc import SccAdapter
from app.tools.secrets import DetectSecretsAdapter
from app.tools.semgrep import SemgrepAdapter
from app.tools.syft import SyftAdapter
from app.tools.tree_sitter import TreeSitterAdapter
from app.core.config import Settings


def get_analysis_service(request: Request) -> RepositoryAnalysisService:
    """Dependency injection for RepositoryAnalysisService. (Phase 10)"""
    workspace_manager = get_workspace_manager(request)
    settings: Settings = request.app.state.settings
    
    runner = ToolRunner()
    
    limits = ScanLimits(
        max_file_count=settings.max_file_count,
        max_file_size_bytes=settings.max_file_size_bytes,
        max_total_size_bytes=settings.max_total_size_bytes,
        max_directory_depth=settings.max_directory_depth,
    )
    
    git_adapter = GitAdapter(runner=runner, timeout_seconds=settings.tool_timeout_git, limits=limits)
    
    tools: list[AnalysisTool] = [
        SccAdapter(runner=runner),
        TreeSitterAdapter(runner=runner),
        SyftAdapter(runner=runner),
        SemgrepAdapter(runner=runner),
        DetectSecretsAdapter(runner=runner),
    ]
    
    pipeline = SnapshotPipeline()
    snapshot_adapter = SnapshotPortAdapter(
        pipeline=pipeline, 
        workspace_root=settings.workspace_root,
        limits=limits
    )
    
    return RepositoryAnalysisService(
        workspace_manager=workspace_manager,
        git_port=git_adapter,
        tools=tools,
        snapshot_port=snapshot_adapter,
        timeout_seconds=max([
            settings.tool_timeout_scc,
            settings.tool_timeout_syft,
            settings.tool_timeout_semgrep,
            settings.tool_timeout_tree_sitter,
            settings.tool_timeout_detect_secrets,
        ]),
        max_output_items=settings.max_output_items
    )
