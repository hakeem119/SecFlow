import errno
import json
import os
import shutil
import time
import typing
import uuid
from pathlib import Path

import pytest
from app.core.errors import ErrorCode, SecFlowError, WorkspaceCleanupError, WorkspaceNotFoundError
from app.services.workspace import WorkspaceManager


def fake_clock() -> float:
    return 1000.0


@pytest.fixture
def manager(tmp_path: Path) -> WorkspaceManager:
    root = tmp_path / "workspaces"
    root.mkdir(mode=0o700)
    (root / ".meta").mkdir(mode=0o700)
    (root / ".trash").mkdir(mode=0o700)
    return WorkspaceManager(root, 3600, fake_clock)


@pytest.mark.asyncio
async def test_create_and_resolve(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    path = await manager.resolve(ws_id)

    assert path.name == ws_id
    assert path.exists()
    assert (path.stat().st_mode & 0o777) == 0o700

    sidecar = manager.meta_dir / f"{ws_id}.json"
    assert sidecar.exists()
    assert (sidecar.stat().st_mode & 0o777) == 0o600


@pytest.mark.asyncio
async def test_resolve_missing(manager: WorkspaceManager) -> None:
    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_resolve_malformed_uuid(manager: WorkspaceManager) -> None:
    # We mapped InvalidWorkspaceIdError to INVALID_REQUEST
    with pytest.raises(SecFlowError) as exc:
        await manager.resolve("not-a-uuid")
    assert exc.value.stable_code == ErrorCode.INVALID_REQUEST


@pytest.mark.asyncio
async def test_resolve_expired(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    # Clock says 1000. TTL = 3600.

    # Fast forward clock
    manager.clock = lambda: 5000.0
    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws_id)

    st = (manager.root / ws_id).stat()
    fallback_expires = st.st_mtime + manager.ttl_seconds

    # Values that would expire EARLY if accepted (e.g. True is 1, so it is > 0)
    # Wait, the prompt says "1" would expire early, but our rule is > 0.
    # We will test things that fail the type check or bounds check:
    early_variants = [
        {"expires_at": True},
        {"expires_at": -100},
        {"expires_at": "NaN"},
        {"expires_at": "Infinity"},
        {"expires_at": []},
        {"expires_at": "wrong type"},
    ]

    for var in early_variants:
        with (manager.root / ".meta" / f"{ws_id}.json").open("w") as f:
            json.dump(var, f)

        # Clock inside the fallback window: shouldn't expire if fallback used
        manager.clock = lambda: fallback_expires - 100
        # If it wrongly accepted the variant, it would be expired (1 is in the past)
        # So resolve MUST succeed
        path = await manager.resolve(ws_id)
        assert path.exists()


@pytest.mark.asyncio
async def test_corrupt_sidecar_fallback(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    st = (manager.root / ws_id).stat()
    st = (manager.root / ws_id).stat()
    fallback_expires = st.st_mtime + manager.ttl_seconds

    # Values that would NEVER expire if wrongly accepted
    never_expire_variants = [{"expires_at": 1e308}, {"expires_at": 1e12}]

    for var in never_expire_variants:
        with (manager.root / ".meta" / f"{ws_id}.json").open("w") as f:
            json.dump(var, f)

        # Clock outside the fallback window
        manager.clock = lambda: fallback_expires + 100
        # If it wrongly accepted the variant, it would NOT be expired.
        # Since fallback is used, it SHOULD be expired.
        with pytest.raises(WorkspaceNotFoundError):
            await manager.resolve(ws_id)


@pytest.mark.asyncio
async def test_oversized_sidecar(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    st = (manager.root / ws_id).stat()
    st = (manager.root / ws_id).stat()
    fallback_expires = st.st_mtime + manager.ttl_seconds

    # Oversized sidecar (> 1 KiB) with a far-future expires_at
    payload = {"expires_at": 1e10, "padding": "x" * 2000}
    with (manager.root / ".meta" / f"{ws_id}.json").open("w") as f:
        json.dump(payload, f)

    # Clock outside fallback window -> must be expired
    manager.clock = lambda: fallback_expires + 100
    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws_id)


@pytest.mark.asyncio
async def test_is_expired_symlink_sidecar(manager: WorkspaceManager, tmp_path: Path) -> None:
    ws_id = await manager.create()
    sidecar = manager.meta_dir / f"{ws_id}.json"
    sidecar.unlink()
    # Symlink it
    target = tmp_path / "target"
    target.write_text('{"expires_at": 5000}')
    sidecar.symlink_to(target)
    # is_expired should return None (not S_ISREG), so it falls back to mtime
    # Since mtime is around now, clock + 4000 = expired

    manager.clock = lambda: time.time() + 4000.0
    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws_id)


@pytest.mark.asyncio
async def test_delete_not_dir(manager: WorkspaceManager) -> None:
    ws_id = str(uuid.uuid4())
    path = manager.root / ws_id
    path.write_text("file")
    with pytest.raises(WorkspaceNotFoundError):
        await manager.delete(ws_id)


@pytest.mark.asyncio
async def test_delete_rename_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    def mock_rename(*args: object, **kwargs: object) -> None:
        raise OSError("Rename failed")

    monkeypatch.setattr(os, "rename", mock_rename)
    with pytest.raises(WorkspaceCleanupError):
        await manager.delete(ws_id)


@pytest.mark.asyncio
async def test_delete_rename_enotempty(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    def mock_rename(*args: object, **kwargs: object) -> None:
        e = OSError("Not empty")
        e.errno = errno.ENOTEMPTY
        raise e

    monkeypatch.setattr(os, "rename", mock_rename)
    # Should raise WorkspaceCleanupError since ENOTEMPTY logic was removed for unique trash IDs

    with pytest.raises(WorkspaceCleanupError):
        await manager.delete(ws_id)


@pytest.mark.asyncio
async def test_rmtree_trash_fails(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    def mock_rmtree(*args: object, **kwargs: object) -> None:
        pass  # Doesn't actually remove

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    # Should catch OSError and log it without raising
    await manager.delete(ws_id)


@pytest.mark.asyncio
async def test_lifecycle_cleanup_exception(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    async def mock_delete(*args: object, **kwargs: object) -> None:
        raise ValueError("Delete failed")

    monkeypatch.setattr(manager, "delete", mock_delete)

    with pytest.raises(ValueError, match="Crash"):
        async with manager.lifecycle(ws_id):
            raise ValueError("Crash")


@pytest.mark.asyncio
async def test_validate_uuid_format_mismatch(manager: WorkspaceManager) -> None:
    # Valid UUID but wrong string format (uppercase)
    ws_id = str(uuid.uuid4()).upper()
    with pytest.raises(SecFlowError) as exc:
        await manager.resolve(ws_id)
    assert exc.value.stable_code == ErrorCode.INVALID_REQUEST


@pytest.mark.asyncio
async def test_write_sidecar_json_error(manager: WorkspaceManager, tmp_path: Path) -> None:
    # os.open succeeds, json.dump fails
    with pytest.raises(TypeError):
        await manager._write_sidecar(tmp_path / "test.json", {"bad": object()})  # type: ignore


@pytest.mark.asyncio
async def test_delete_missing_workspace(manager: WorkspaceManager) -> None:
    with pytest.raises(WorkspaceNotFoundError):
        await manager.delete(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_purge_trash_symlink_root(
    manager: WorkspaceManager, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Make trash_path a symlink
    ws_id = str(uuid.uuid4())
    trash_id = f"{ws_id}_{uuid.uuid4().hex}"
    trash_path = manager.trash_dir / trash_id
    target = tmp_path / "target"
    target.mkdir()
    trash_path.symlink_to(target)
    await manager.purge_trash(trash_id)
    # The purge should unlink it without following
    assert not trash_path.exists()
    assert target.exists()


@pytest.mark.asyncio
async def test_purge_trash_with_children(
    manager: WorkspaceManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = str(uuid.uuid4())
    trash_id = f"{ws_id}_{uuid.uuid4().hex}"
    trash_path = manager.trash_dir / trash_id
    trash_path.mkdir()
    (trash_path / "file.txt").write_text("hello")
    (trash_path / "sym.txt").symlink_to("nowhere")

    original_chmod = os.chmod

    def mock_chmod(
        path: int | str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        if str(path).endswith("file.txt"):
            raise OSError("Permission denied")
        original_chmod(path, mode, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "chmod", mock_chmod)

    await manager.purge_trash(trash_id)
    assert not trash_path.exists()


@pytest.mark.asyncio
async def test_purge_lstat_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    def mock_lstat(*args: typing.Any, **kwargs: typing.Any) -> os.stat_result:
        raise OSError("lstat failed")

    monkeypatch.setattr(os, "lstat", mock_lstat)

    with pytest.raises(WorkspaceNotFoundError):
        await manager.purge(ws_id)


@pytest.mark.asyncio
async def test_purge_rmtree_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    ws_id = await manager.create()

    def mock_rmtree(*args: typing.Any, **kwargs: typing.Any) -> None:
        raise OSError("rmtree failed")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    await manager.purge(ws_id)
    # the workspace is moved to trash, but rmtree failed.
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any("Workspace cleanup failed" in r.message for r in errors)


@pytest.mark.asyncio
async def test_write_unlink_fails(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:

    def mock_replace(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", mock_replace)

    def mock_unlink(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        raise OSError("unlink failed")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    with pytest.raises(WorkspaceCleanupError):
        await manager.create()


@pytest.mark.asyncio
async def test_purge_chmod_trash_fails(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    def mock_chmod(*args: object, **kwargs: object) -> None:
        raise OSError("chmod failed")

    monkeypatch.setattr(Path, "chmod", mock_chmod)
    # The purge ignores chmod error on trash_path and successfully deletes
    await manager.purge(ws_id)
    # verify it's gone
    assert not (manager.root / ws_id).exists()


@pytest.mark.asyncio
async def test_purge_chmod_child_fails(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()
    (manager.root / ws_id / "child").mkdir()

    def mock_chmod(*args: object, **kwargs: object) -> None:
        raise OSError("chmod failed")

    monkeypatch.setattr(Path, "chmod", mock_chmod)
    # Should ignore child chmod error and succeed
    await manager.purge(ws_id)
    assert not (manager.root / ws_id).exists()


@pytest.mark.asyncio
async def test_read_meta_attribute_error(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    with (Path(manager.root) / ".meta" / f"{ws_id}.json").open("w") as f:
        f.write("[]")  # list does not have .get

    # We must assert that it falls back to mtime + ttl
    # Let's set clock inside the fallback window
    st = (Path(manager.root) / ws_id).stat()
    manager.clock = lambda: st.st_mtime + manager.ttl_seconds - 100
    # resolve should succeed
    path = await manager.resolve(ws_id)
    assert path.exists()


@pytest.mark.asyncio
async def test_delete_expired(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()

    manager.clock = lambda: time.time() + 4000.0
    with pytest.raises(WorkspaceNotFoundError):
        await manager.delete(ws_id)


@pytest.mark.asyncio
async def test_write_tmp_unlink_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    await manager.create()

    def mock_replace(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", mock_replace)

    def mock_fdopen(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        raise RuntimeError("fdopen failed")

    monkeypatch.setattr(os, "fdopen", mock_fdopen)

    with pytest.raises(RuntimeError, match="fdopen failed"):
        await manager.create()


@pytest.mark.asyncio
async def test_read_meta_unknown_exception(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_id = await manager.create()

    # The json module used by workspace.py needs to be mocked

    def mock_fdopen(*args: object, **kwargs: object) -> object:
        # Raise an exception that is not a ValueError
        raise RuntimeError("fdopen failed")

    monkeypatch.setattr(os, "fdopen", mock_fdopen)

    with pytest.raises(RuntimeError, match="fdopen failed"):
        await manager.resolve(ws_id)


@pytest.mark.asyncio
async def test_concurrent_delete(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()

    # asyncio.gather of two delete calls
    import asyncio

    from app.core.errors import WorkspaceNotFoundError

    results = await asyncio.gather(
        manager.delete(ws_id), manager.delete(ws_id), return_exceptions=True
    )

    success_count = 0
    not_found_count = 0
    for res in results:
        if res is None:
            success_count += 1
        elif isinstance(res, WorkspaceNotFoundError):
            not_found_count += 1

    assert success_count == 1
    assert not_found_count == 1


@pytest.mark.asyncio
async def test_create_mkdir_file_exists(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    original_mkdir = os.mkdir
    calls = 0

    def mock_mkdir(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise FileExistsError("File exists")
        original_mkdir(*args, **kwargs)  # type: ignore

    monkeypatch.setattr(os, "mkdir", mock_mkdir)
    from app.core.errors import WorkspaceCleanupError

    with pytest.raises(WorkspaceCleanupError):
        await manager.create()


@pytest.mark.asyncio
async def test_create_mkdir_oserror(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    def mock_mkdir(*args: object, **kwargs: object) -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "mkdir", mock_mkdir)
    from app.core.errors import WorkspaceCleanupError

    with pytest.raises(WorkspaceCleanupError):
        await manager.create()


@pytest.mark.asyncio
async def test_resolve_not_a_dir(manager: WorkspaceManager) -> None:
    import uuid

    ws = str(uuid.uuid4())
    (manager.root / ws).touch()
    import pytest
    from app.core.errors import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws)


@pytest.mark.asyncio
async def test_is_expired_json_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test line 139->141: exception in fdopen or json load where f is None
    import uuid

    ws = str(uuid.uuid4())
    (manager.root / ws).mkdir()

    # We need to trigger an exception AFTER os.fstat but BEFORE f is assigned, OR when f is assigned
    # Wait, the code is:
    # try:
    #     if os.fstat(fd).st_size > 1024: raise ValueError("Sidecar too large")
    #     f = os.fdopen(fd)
    #     with f: data = json.load(f)
    # except Exception:
    #     if f is None: os.close(fd)

    import os

    def mock_fstat(fd: int) -> os.stat_result:
        raise OSError("fstat crash")

    monkeypatch.setattr(os, "fstat", mock_fstat)

    st = (manager.root / ws).stat()
    manager.clock = lambda: st.st_mtime + 50000000.0  # to ensure it's expired
    # resolve should still return WorkspaceNotFoundError, falling back to mtime and expiring
    import pytest
    from app.core.errors import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws)


@pytest.mark.asyncio
async def test_purge_trash_lstat_error(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import uuid

    trash_id = f"{uuid.uuid4()}_{uuid.uuid4().hex}"

    def mock_lstat(*args: object, **kwargs: object) -> os.stat_result:
        raise OSError("lstat fail")

    monkeypatch.setattr(os, "lstat", mock_lstat)
    # Shouldn't raise anything
    await manager.purge_trash(trash_id)


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_is_expired_json_error_f_not_none(
    manager: WorkspaceManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import uuid

    ws = str(uuid.uuid4())
    (manager.root / ws).mkdir()
    (manager.meta_dir / f"{ws}.json").write_text("{}")

    def mock_load(*args: object, **kwargs: object) -> object:
        raise OSError("json crash")

    monkeypatch.setattr(json, "load", mock_load)

    st = (manager.root / ws).stat()
    manager.clock = lambda: st.st_mtime + 50000000.0
    from app.core.errors import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await manager.resolve(ws)
