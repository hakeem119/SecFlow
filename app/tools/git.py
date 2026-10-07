import logging
import shutil
from pathlib import Path, PurePosixPath

from app.core.errors import AnalysisTimeoutError, CloneFailedError, ErrorContext
from app.core.safe_path import SafePath
from app.schemas.domain import GitHubRepoUrl
from app.schemas.fetch import FetchResult
from app.schemas.validators import validate_branch_name
from app.services.workspace_scan import ScanLimits, scan
from app.tools.runner import CommandRequest, CommandRunner

logger = logging.getLogger(__name__)


class GitAdapter:
    """Adapter for Git operations."""

    def __init__(self, runner: CommandRunner, timeout_seconds: int, limits: ScanLimits) -> None:
        self.runner = runner
        self.timeout_seconds = timeout_seconds
        self.limits = limits

    async def fetch(self, repo_url: GitHubRepoUrl, workspace_path: SafePath) -> FetchResult:
        workspace_id = workspace_path.path.name

        env = {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "PATH": "/usr/bin:/bin",
            "HOME": "/nonexistent",
        }

        # Safe run configuration
        cwd_tmp = SafePath(Path("/tmp"), _internal=True)  # noqa: S108

        # 1. Clone
        clone_args = (
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "-c",
            "http.followRedirects=false",
            "clone",
            "--depth=1",
            "--single-branch",
            "--no-tags",
            "--no-recurse-submodules",
            "--",
            str(repo_url),
            str(workspace_path.path),
        )

        clone_req = CommandRequest(
            executable="git",
            args=clone_args,
            cwd=cwd_tmp,
            timeout=self.timeout_seconds,
            max_stdout_bytes=1024 * 1024,
            max_stderr_bytes=1024 * 1024,
            env=env,
        )

        result = await self.runner.run(clone_req)
        if result.timed_out:
            logger.error("Git clone timed out for workspace %s", workspace_id)
            raise AnalysisTimeoutError(ErrorContext(tool_name="git"))
        if result.exit_code != 0:
            logger.error("Git clone failed for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="git", exit_code=result.exit_code))

        # 2. Read commit
        commit_req = CommandRequest(
            executable="git",
            args=(
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "core.fsmonitor=false",
                "rev-parse",
                "HEAD",
            ),
            cwd=workspace_path,
            timeout=self.timeout_seconds,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
            env=env,
        )
        commit_result = await self.runner.run(commit_req)
        if commit_result.exit_code != 0:
            logger.error("Git rev-parse failed for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="git", exit_code=commit_result.exit_code))
        commit = commit_result.stdout.decode("utf-8", errors="replace").strip()

        # 3. Read branch name
        branch_req = CommandRequest(
            executable="git",
            args=(
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "core.fsmonitor=false",
                "symbolic-ref",
                "--short",
                "HEAD",
            ),
            cwd=workspace_path,
            timeout=self.timeout_seconds,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
            env=env,
        )
        branch_result = await self.runner.run(branch_req)
        if branch_result.exit_code != 0:
            logger.error("Git symbolic-ref failed for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="git", exit_code=branch_result.exit_code))

        raw_branch = branch_result.stdout.decode("utf-8", errors="replace").strip()
        try:
            default_branch = validate_branch_name(raw_branch)
        except ValueError:
            logger.error("Invalid default branch name for workspace %s", workspace_id)  # noqa: TRY400
            raise CloneFailedError(ErrorContext(tool_name="git")) from None

        # 4. Read tracked files
        ls_req = CommandRequest(
            executable="git",
            args=("-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "ls-files", "-z"),
            cwd=workspace_path,
            timeout=self.timeout_seconds,
            max_stdout_bytes=50 * 1024 * 1024,
            max_stderr_bytes=1024 * 1024,
            env=env,
        )
        ls_result = await self.runner.run(ls_req)
        if ls_result.exit_code != 0:
            logger.error("Git ls-files failed for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="git", exit_code=ls_result.exit_code))

        if ls_result.truncated:
            logger.error("Git ls-files output truncated for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="git"))

        tracked_files: list[PurePosixPath] = []
        raw_paths = ls_result.stdout.split(b"\0")
        for raw_path in raw_paths:
            if not raw_path:
                continue

            try:
                # Decode safely, check for controls/NUL
                path_str = raw_path.decode("utf-8", errors="strict")
                if not path_str.isprintable():
                    raise ValueError("Path contains non-printable characters")  # noqa: TRY301
                if ".." in path_str.split("/"):
                    raise ValueError("Path contains ..")  # noqa: TRY301
                if path_str.startswith("/") or path_str.startswith("\\") or ":" in path_str:
                    raise ValueError("Path is absolute or contains drive letter")  # noqa: TRY301

                tracked_files.append(PurePosixPath(path_str))
            except (UnicodeDecodeError, ValueError):
                # We simply discard invalid files, or we could error out.
                # The requirement says "Validate every path... before PurePosixPath"
                # If we encounter invalid paths in the repo, we skip them.
                pass

        # 5. Remove .git
        # Deleting .git before scan ensures .git files don't count against scan limits
        # and hostile configs are purged early.
        git_dir = workspace_path.path / ".git"
        if git_dir.exists():
            try:
                shutil.rmtree(git_dir)
            except OSError:
                logger.error("Failed to remove .git directory for workspace %s", workspace_id)  # noqa: TRY400
                raise CloneFailedError(ErrorContext(tool_name="git")) from None

        # 6. Run workspace_scan
        scan_report = scan(workspace_path.path, self.limits)
        if scan_report.violations:
            logger.error("Workspace scan violations for workspace %s", workspace_id)
            raise CloneFailedError(ErrorContext(tool_name="workspace_scan"))

        return FetchResult(
            commit=commit,
            default_branch=default_branch,
            tracked_files=tracked_files,
        )
