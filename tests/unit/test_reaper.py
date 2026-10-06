import asyncio
import shutil
import typing
import uuid
from pathlib import Path

import pytest
from app.services.reaper import WorkspaceReaper
from app.services.workspace import WorkspaceManager
from pytest import LogCaptureFixture


def fake_clock() -> float:
    return 1000.0


@pytest.fixture
def manager(tmp_path: Path) -> WorkspaceManager:
    root = tmp_path / "workspaces"
    root.mkdir(mode=0o700)
    (root / ".meta").mkdir(mode=0o700)
    (root / ".trash").mkdir(mode=0o700)
    return WorkspaceManager(root, 3600, fake_clock)


@pytest.fixture
def reaper(manager: WorkspaceManager) -> WorkspaceReaper:
    return WorkspaceReaper(manager, 60)


@pytest.mark.asyncio
async def test_reaper_sweep_normal(manager: WorkspaceManager, reaper: WorkspaceReaper) -> None:
    # 1. Active workspace
    active_ws = await manager.create()

    # Fast forward clock slightly so next workspace has different creation time
    manager.clock = lambda: 5000.0

    # 2. Expired workspace
    expired_ws = await manager.create()

    # Now clock is 5000. active_ws expires at 1000 + 3600 = 4600.
    # expired_ws expires at 5000 + 3600 = 8600.

    # Set clock to 4700. active_ws is expired. expired_ws is NOT expired.
    manager.clock = lambda: 4700.0

    # Run sweep
    await reaper.sweep()

    # Check that active_ws is gone, expired_ws is still there.
    assert not (manager.root / active_ws).exists()
    assert (manager.root / expired_ws).exists()


@pytest.mark.asyncio
async def test_reaper_ignores_non_uuid(manager: WorkspaceManager, reaper: WorkspaceReaper) -> None:
    # Non-UUID and dotted entries
    (manager.root / "not-a-uuid").mkdir()
    (manager.root / ".hidden").mkdir()

    await reaper.sweep()

    assert (manager.root / "not-a-uuid").exists()
    assert (manager.root / ".hidden").exists()


@pytest.mark.asyncio
async def test_reaper_sweeps_orphan(manager: WorkspaceManager, reaper: WorkspaceReaper) -> None:

    orphan = str(uuid.uuid4())
    (manager.root / orphan).mkdir()

    # Clock is 1000. TTL is 3600.
    # Without sidecar, it will use mtime + 3600. So it expires at ~ mtime + 3600.
    # We fast forward clock to mtime + 4000.
    manager.clock = lambda: 9999999999.0

    await reaper.sweep()

    assert not (manager.root / orphan).exists()


@pytest.mark.asyncio
async def test_reaper_sweeps_trash(manager: WorkspaceManager, reaper: WorkspaceReaper) -> None:
    ws_id = str(uuid.uuid4())
    hex_id = uuid.uuid4().hex
    trashed = f"{ws_id}_{hex_id}"
    trash_path = manager.trash_dir / trashed
    trash_path.mkdir()
    (trash_path / "f").write_bytes(b"data")

    await reaper.sweep()
    assert not trash_path.exists()


@pytest.mark.asyncio
async def test_purge_rmtree_fails_once(
    manager: WorkspaceManager,
    reaper: WorkspaceReaper,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ws_id = await manager.create()
    original_rmtree = shutil.rmtree
    rmtree_calls = 0

    def mock_rmtree(*args: object, **kwargs: object) -> None:
        nonlocal rmtree_calls
        rmtree_calls += 1
        if rmtree_calls == 1:
            raise OSError("First time fail")
        original_rmtree(*args, **kwargs)  # type: ignore

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    # trigger purge directly
    await manager.purge(ws_id)

    # verify it's in trash but not fully deleted
    trash_entries = list(manager.trash_dir.iterdir())
    assert len(trash_entries) == 1

    # now run sweep
    await reaper.sweep()
    # verify trash is empty
    trash_entries2 = list(manager.trash_dir.iterdir())
    assert len(trash_entries2) == 0


@pytest.mark.asyncio
async def test_reaper_loop_exception_resilience(
    manager: WorkspaceManager,
    reaper: WorkspaceReaper,
    caplog: LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force sweep to crash
    async def crash(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Crash")

    monkeypatch.setattr(reaper, "sweep", crash)

    # Start reaper loop but cancel it almost immediately
    task = asyncio.create_task(reaper.start())
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) >= 1
    assert "Reaper loop encountered an error: RuntimeError" in errors[0].getMessage()


@pytest.mark.asyncio
async def test_reaper_listdir_oserror(
    manager: WorkspaceManager, reaper: WorkspaceReaper, monkeypatch: pytest.MonkeyPatch
) -> None:

    def mock_iterdir(*args: object, **kwargs: object) -> typing.Any:
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "iterdir", mock_iterdir)
    await reaper.sweep()  # Should not raise and removes nothing
    assert True


@pytest.mark.asyncio
async def test_reaper_resolve_unexpected_error(
    manager: WorkspaceManager, reaper: WorkspaceReaper, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 59->47: resolve raises exception OTHER than WorkspaceNotFoundError

    ws = str(uuid.uuid4())
    (manager.root / ws).mkdir()

    async def mock_resolve(workspace_id: str) -> Path:
        raise ValueError("Something else")

    monkeypatch.setattr(manager, "resolve", mock_resolve)
    await reaper.sweep()
    # It just continues, so workspace should still exist
    assert (manager.root / ws).exists()


@pytest.mark.asyncio
async def test_reaper_delete_exception(
    manager: WorkspaceManager,
    reaper: WorkspaceReaper,
    caplog: LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    # Create an expired workspace
    ws = str(uuid.uuid4())
    (manager.root / ws).mkdir()
    manager.clock = lambda: 9999999999.0

    async def mock_purge(workspace_id: str) -> None:
        raise ValueError("Delete failed")

    monkeypatch.setattr(manager, "purge", mock_purge)
    await reaper.sweep()

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any("Reaper cleanup failed: ValueError" in r.getMessage() for r in errors)


@pytest.mark.asyncio
async def test_reaper_trash_ignores_non_uuid(
    manager: WorkspaceManager, reaper: WorkspaceReaper
) -> None:
    (manager.trash_dir / "not-a-uuid").mkdir()
    await reaper.sweep()
    assert (manager.trash_dir / "not-a-uuid").exists()


@pytest.mark.asyncio
async def test_reaper_cancelled_during_sweep(
    manager: WorkspaceManager, reaper: WorkspaceReaper, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_sweep() -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(reaper, "sweep", mock_sweep)

    with pytest.raises(asyncio.CancelledError):
        await reaper.start()


@pytest.mark.asyncio
async def test_reaper_stray_non_directory(
    manager: WorkspaceManager,
    reaper: WorkspaceReaper,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import uuid

    ws = str(uuid.uuid4())
    (manager.root / ws).touch()

    await reaper.sweep()
    assert not (manager.root / ws).exists()

    # Test unlink failure
    ws2 = str(uuid.uuid4())
    (manager.root / ws2).touch()

    def mock_unlink(*args: object, **kwargs: object) -> None:
        raise OSError("Unlink failed")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    await reaper.sweep()
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any(
        "Reaper cleanup failed: OSError" in r.getMessage() and ws2 in r.getMessage() for r in errors
    )


@pytest.mark.asyncio
async def test_reaper_sweep_trash_failure_continues(
    manager: WorkspaceManager,
    reaper: WorkspaceReaper,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import os
    import uuid

    t1 = f"11111111-1111-4111-8111-111111111111_{uuid.uuid4().hex}"
    t2 = f"22222222-2222-4222-8222-222222222222_{uuid.uuid4().hex}"

    (manager.trash_dir / t1).mkdir()
    (manager.trash_dir / t2).mkdir()

    original_lstat = os.lstat

    def mock_lstat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes], *args: object, **kwargs: object
    ) -> os.stat_result:
        if "11111111" in str(path):
            raise ValueError("Intentional crash")
        return original_lstat(path, *args, **kwargs)  # type: ignore

    monkeypatch.setattr(os, "lstat", mock_lstat)

    await reaper.sweep()

    assert (manager.trash_dir / t1).exists()
    assert not (manager.trash_dir / t2).exists()
