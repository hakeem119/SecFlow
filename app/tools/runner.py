"""
FROZEN-AFTER-REVIEW

Contracts for external tool execution.
"""

import asyncio
import contextlib
import os
import resource
import signal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.safe_path import SafePath

ExecutableKey = Literal["scc", "syft", "semgrep", "git", "tree-sitter", "detect-secrets"]

BINARIES: dict[ExecutableKey, str] = {
    "scc": "/usr/local/bin/scc",
    "syft": "/usr/local/bin/syft",
    "semgrep": "/usr/local/bin/semgrep",
    "git": "/usr/bin/git",
    "tree-sitter": "/usr/local/bin/tree-sitter",
    "detect-secrets": "/usr/local/bin/detect-secrets",
}


class CommandRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    executable: ExecutableKey
    args: tuple[str, ...]
    cwd: SafePath
    timeout: int = Field(gt=0, description="Timeout in seconds")
    max_stdout_bytes: int = Field(gt=0)
    max_stderr_bytes: int = Field(gt=0)
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment overrides. Must be from an allowlist in the actual runner.",
    )


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    truncated: bool


class CommandRunner(Protocol):
    async def run(self, request: CommandRequest) -> CommandResult:
        """Execute a command request and return the result."""
        ...


class FakeCommandRunner:
    """
    Fake CommandRunner for tests. Scripted results, records requests.
    """

    def __init__(
        self, scripted_results: dict[tuple[str, ...], CommandResult] | None = None
    ) -> None:
        self.results = scripted_results or {}
        self.requests: list[CommandRequest] = []

    async def run(self, request: CommandRequest) -> CommandResult:
        self.requests.append(request)
        key = (request.executable, *request.args)
        if key in self.results:
            return self.results[key]
        return CommandResult(
            exit_code=0,
            stdout=b"",
            stderr=b"",
            timed_out=False,
            truncated=False,
        )


class ToolRunner:
    """
    Real CommandRunner using asyncio subprocess.
    """

    def __init__(self) -> None:
        self._base_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",  # noqa: S108 # nosec B108
            "LANG": "C.UTF-8",
        }

    async def run(self, request: CommandRequest) -> CommandResult:
        bin_path = BINARIES[request.executable]
        env = self._base_env.copy()
        env.update(request.env)

        def preexec() -> None:
            os.setsid()
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path,
                *request.args,
                cwd=str(request.cwd.path),
                env=env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec,
            )
        except OSError:
            return CommandResult(
                exit_code=127, stdout=b"", stderr=b"", timed_out=False, truncated=False
            )

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        stdout_size = 0
        stderr_size = 0
        truncated = False

        async def read_stream(
            stream: asyncio.StreamReader | None, max_bytes: int, is_stdout: bool
        ) -> None:
            nonlocal stdout_size, stderr_size, truncated
            if stream is None:
                return
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break

                size = stdout_size if is_stdout else stderr_size
                chunks = stdout_chunks if is_stdout else stderr_chunks

                if size + len(chunk) > max_bytes:
                    allowed = max_bytes - size
                    if allowed > 0:
                        chunks.append(chunk[:allowed])
                    truncated = True
                    break
                else:
                    chunks.append(chunk)
                    if is_stdout:
                        stdout_size += len(chunk)
                    else:
                        stderr_size += len(chunk)

        stdout_task = asyncio.create_task(read_stream(proc.stdout, request.max_stdout_bytes, True))
        stderr_task = asyncio.create_task(read_stream(proc.stderr, request.max_stderr_bytes, False))

        timed_out = False
        try:
            await asyncio.wait_for(proc.wait(), timeout=request.timeout)
        except TimeoutError:
            timed_out = True
            with contextlib.suppress(OSError):
                os.killpg(proc.pid, signal.SIGKILL)

        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        if not timed_out and truncated and proc.returncode is None:
            with contextlib.suppress(OSError):
                os.killpg(proc.pid, signal.SIGKILL)

        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(proc.wait(), timeout=2.0)

        return CommandResult(
            exit_code=proc.returncode if not timed_out else None,
            stdout=b"".join(stdout_chunks),
            stderr=b"".join(stderr_chunks),
            timed_out=timed_out,
            truncated=truncated,
        )
