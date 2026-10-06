import asyncio
import json
import logging
import math
import os
import re
import shutil
import stat
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import UUID

from app.core.errors import InvalidWorkspaceIdError, WorkspaceCleanupError, WorkspaceNotFoundError
from app.core.safe_path import PathSecurityError, open_nofollow

logger = logging.getLogger(__name__)

UUID_RE = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
TRASH_RE = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}_[0-9a-f]{32}$"


class WorkspaceManager:
    """
    Manages secure lifecycle of workspaces on disk.
    Repositories are hostile; so are workspace contents.
    """

    def __init__(self, root: Path, ttl_seconds: int, clock: Callable[[], float]) -> None:
        self.root = root
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.meta_dir = self.root / ".meta"
        self.trash_dir = self.root / ".trash"

    def _validate_uuid(self, workspace_id: str) -> None:
        val_str = ""
        try:
            val_str = str(UUID(workspace_id, version=4))
        except ValueError as e:
            raise InvalidWorkspaceIdError() from e

        if val_str != workspace_id:
            raise InvalidWorkspaceIdError()

    async def create(self) -> str:
        """
        Creates a new workspace directory (mode 0700) and its sidecar metadata.
        Returns the generated UUID4 string.
        """
        ws_id = str(uuid.uuid4())
        ws_path = self.root / ws_id
        sidecar_path = self.meta_dir / f"{ws_id}.json"

        # 1. Create workspace dir
        try:
            await asyncio.to_thread(os.mkdir, ws_path, 0o700)
        except FileExistsError:
            # UUID collision should be impossible, but if it happens, bubble up an error.
            raise WorkspaceCleanupError() from None
        except OSError as e:
            raise WorkspaceCleanupError() from e

        # 2. Write sidecar metadata
        created_at = self.clock()
        expires_at = created_at + self.ttl_seconds
        meta_data = {"expires_at": expires_at}

        try:
            await self._write_sidecar(sidecar_path, meta_data)
        except OSError:
            # If sidecar fails, remove the newly created empty dir to avoid orphans
            with suppress(OSError):
                await asyncio.to_thread(os.rmdir, ws_path)
            raise WorkspaceCleanupError() from None

        return ws_id

    async def _write_sidecar(self, path: Path, data: dict[str, float]) -> None:
        tmp_path = path.with_suffix(".tmp")

        def _write() -> None:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
            fd = os.open(tmp_path, flags, 0o600)
            f = None
            try:
                f = os.fdopen(fd, "w")
                with f:
                    json.dump(data, f)
                    f.flush()
                    os.fsync(f.fileno())
                Path(tmp_path).replace(path)
            except Exception:
                if f is None:
                    os.close(fd)
                with suppress(OSError):
                    Path(tmp_path).unlink()
                raise

        await asyncio.to_thread(_write)

    async def resolve(self, workspace_id: str) -> Path:
        """
        Resolves an ID to a path. Raises WorkspaceNotFoundError if missing or expired.
        """
        self._validate_uuid(workspace_id)
        ws_path = self.root / workspace_id

        try:
            st = await asyncio.to_thread(os.lstat, ws_path)
        except OSError as e:
            raise WorkspaceNotFoundError() from e

        if not stat.S_ISDIR(st.st_mode):
            raise WorkspaceNotFoundError()

        if await self._is_expired(workspace_id, st):
            raise WorkspaceNotFoundError()

        return ws_path

    async def _is_expired(self, workspace_id: str, ws_stat: os.stat_result) -> bool:
        sidecar_path = self.meta_dir / f"{workspace_id}.json"

        def _read_meta() -> float | None:
            def _check_size(fd_val: int) -> None:
                if os.fstat(fd_val).st_size > 1024:
                    raise ValueError("Sidecar too large")

            try:
                fd = open_nofollow(sidecar_path)
                try:
                    _check_size(fd)
                except ValueError:
                    os.close(fd)
                    raise
                f = None
                try:
                    f = os.fdopen(fd)
                    with f:
                        data = json.load(f)
                except Exception:
                    if f is None:
                        os.close(fd)
                    raise

                expires_at = data.get("expires_at")
                if (
                    type(expires_at) in (int, float)
                    and math.isfinite(expires_at)
                    and 0 < expires_at < 1e12
                ):
                    return float(expires_at)
            except (ValueError, TypeError, OSError, AttributeError):
                pass
            except PathSecurityError:
                pass
            return None

        expires_at = await asyncio.to_thread(_read_meta)
        if expires_at is None:
            expires_at = ws_stat.st_mtime + self.ttl_seconds

        return self.clock() >= expires_at

    async def purge(self, workspace_id: str) -> None:
        """
        Force deletes the workspace (used by the reaper). Does not check expiry.
        """
        self._validate_uuid(workspace_id)
        ws_path = self.root / workspace_id

        trash_id = f"{workspace_id}_{uuid.uuid4().hex}"
        trash_path = self.trash_dir / trash_id
        sidecar_path = self.meta_dir / f"{workspace_id}.json"

        try:
            st = await asyncio.to_thread(os.lstat, ws_path)
        except OSError as e:
            raise WorkspaceNotFoundError() from e

        if not stat.S_ISDIR(st.st_mode):
            raise WorkspaceNotFoundError()

        def _rename() -> bool:
            Path(ws_path).rename(trash_path)
            return True

        try:
            await asyncio.to_thread(_rename)
        except FileNotFoundError as e:
            raise WorkspaceNotFoundError() from e
        except OSError as e:
            raise WorkspaceCleanupError() from e

        await self.purge_trash(trash_id)

        def _remove_sidecar() -> None:
            with suppress(OSError):
                Path(sidecar_path).unlink(missing_ok=True)

        await asyncio.to_thread(_remove_sidecar)

    async def delete(self, workspace_id: str) -> None:
        """
        Deletes the workspace atomically by renaming to .trash and then using rmtree.
        Raises 404 if missing or expired.
        """
        self._validate_uuid(workspace_id)
        ws_path = self.root / workspace_id
        try:
            st = await asyncio.to_thread(os.lstat, ws_path)
        except OSError as e:
            raise WorkspaceNotFoundError() from e

        if await self._is_expired(workspace_id, st):
            raise WorkspaceNotFoundError()

        await self.purge(workspace_id)

    async def purge_trash(self, entry_name: str) -> None:
        if not re.fullmatch(TRASH_RE, entry_name):
            return

        trash_path = self.trash_dir / entry_name

        def _do_purge() -> None:
            try:
                st = os.lstat(trash_path)
            except OSError:
                return
            if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
                with suppress(OSError):
                    Path(trash_path).unlink()
                return

            with suppress(OSError):
                Path(trash_path).chmod(st.st_mode | stat.S_IRWXU)

            for root, dirs, _files in os.walk(trash_path):
                for name in dirs:
                    p = Path(root) / name
                    try:
                        st_child = p.lstat()
                        if stat.S_ISDIR(st_child.st_mode) and not stat.S_ISLNK(st_child.st_mode):
                            p.chmod(st_child.st_mode | stat.S_IRWXU)
                    except OSError:
                        pass

            shutil.rmtree(trash_path)
            if trash_path.exists():
                raise OSError("rmtree failed to completely remove directory")

        try:
            await asyncio.to_thread(_do_purge)
        except OSError as e:
            logger.error("Workspace cleanup failed: %s for %s", e.__class__.__name__, entry_name)  # noqa: TRY400 - Intentionally hiding exc_info

    @asynccontextmanager
    async def lifecycle(self, workspace_id: str) -> AsyncGenerator[Path, None]:
        """
        Yields the workspace path. If the body raises an exception, the workspace is deleted.
        """
        path = await self.resolve(workspace_id)
        try:
            yield path
        except Exception:
            try:
                await self.delete(workspace_id)
            except Exception as e:
                logger.exception(
                    "Lifecycle cleanup failed: %s for %s", e.__class__.__name__, workspace_id
                )
            raise
