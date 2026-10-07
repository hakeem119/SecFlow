import uuid
from typing import Any
from pathlib import PurePosixPath, Path

from app.core.safe_path import SafePath
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.fetch import FetchResult
from app.schemas.tool import ToolResult
from app.services.snapshot_builder import SnapshotPipeline, PipelineInput
from app.services.repository_service import SnapshotPort
from app.services.workspace_scan import scan, ScanLimits


class SnapshotPortAdapter(SnapshotPort):
    """
    Adapter bridging the SnapshotPort protocol to the SnapshotPipeline.
    This solves the impedance mismatch between the service layer's SnapshotPort contract
    and the M3 SnapshotPipeline's PipelineInput requirements by scanning the workspace
    and preparing the pipeline input.
    """

    def __init__(self, pipeline: SnapshotPipeline, workspace_root: Path, limits: ScanLimits):
        self.pipeline = pipeline
        self.workspace_root = workspace_root
        self.limits = limits

    async def write(
        self,
        repo_url: GitHubRepoUrl,
        fetch_result: FetchResult,
        tool_results: list[ToolResult[Any]],
        workspace_id: WorkspaceId,
    ) -> str:
        workspace_path = self.workspace_root / str(workspace_id)
        
        # We need scanned_files and scanned_directories for the pipeline.
        # Although git returned tracked_files, we can use workspace_scan to get actual sizes.
        # But wait, workspace_scan doesn't return file paths, it just returns a ScanReport with counts.
        # So we have to build the scanned_files from fetch_result.tracked_files.
        
        scanned_files = []
        scanned_directories_set = set()

        for rel_path in fetch_result.tracked_files:
            abs_path = workspace_path / rel_path
            try:
                st = abs_path.stat()
                size = st.st_size
            except OSError:
                continue

            scanned_files.append({
                "path": str(rel_path),
                "size": size,
                "language": "Unknown"  # SCC will provide aggregated metrics, tree-sitter will parse Python
            })

            # Add parent directories
            parent = rel_path.parent
            while parent and str(parent) != ".":
                scanned_directories_set.add(str(parent))
                parent = parent.parent

        pipeline_input = PipelineInput(
            workspace_id=str(workspace_id),
            repo_name=repo_url.repo,
            repo_url=str(repo_url),
            commit=fetch_result.commit,
            default_branch=fetch_result.default_branch,
            scanned_files=scanned_files,
            scanned_directories=sorted(list(scanned_directories_set)),
            tool_results=tool_results,
            files_truncated=False,  # If git ls-files was truncated it would have raised CloneFailedError
        )

        output_filename = "repository_snapshot.yaml"
        output_path = PurePosixPath(output_filename)
        
        # Write to the workspace path temporarily
        abs_output_path = workspace_path / output_filename
        
        self.pipeline.build(pipeline_input, output_path=PurePosixPath(abs_output_path))
        
        # Return the relative path for the API response
        return f"{workspace_id}/{output_filename}"
