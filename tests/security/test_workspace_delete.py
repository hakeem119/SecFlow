import os
import sys
from pathlib import Path

import pytest
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


@pytest.mark.skipif(sys.platform == "win32", reason="Hostile mode tests require Unix")
@pytest.mark.asyncio
async def test_delete_hostile_mode(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    ws_path = await manager.resolve(ws_id)

    # Create hostile directory
    hostile = ws_path / "hostile"
    hostile.mkdir()
    (hostile / "file.txt").write_bytes(b"bad")

    # Remove all permissions
    hostile.chmod(0o000)

    await manager.delete(ws_id)
    assert not ws_path.exists()
    assert not (manager.trash_dir / ws_id).exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
@pytest.mark.asyncio
async def test_delete_symlink_canary(manager: WorkspaceManager, tmp_path: Path) -> None:
    ws_id = await manager.create()
    ws_path = await manager.resolve(ws_id)

    # Create canary directory outside workspace
    canary_dir = tmp_path / "canary_dir"
    canary_dir.mkdir()
    canary_file = canary_dir / "canary.txt"
    canary_file.write_bytes(b"tweet")

    # Create symlink inside workspace pointing to canary dir
    sym = ws_path / "sym_dir"
    sym.symlink_to(canary_dir)

    # Create canary hardlink source
    canary_hl = tmp_path / "canary_hl.txt"
    canary_hl.write_bytes(b"tweet2")

    # Create hardlink inside workspace
    hl_inside = ws_path / "hl.txt"
    os.link(canary_hl, hl_inside)

    await manager.delete(ws_id)

    assert not ws_path.exists()
    assert not (manager.trash_dir / ws_id).exists()

    # Canaries survive!
    assert canary_dir.exists()
    assert canary_file.read_bytes() == b"tweet"
    assert canary_hl.exists()
    assert canary_hl.read_bytes() == b"tweet2"


@pytest.mark.asyncio
async def test_delete_already_in_trash(manager: WorkspaceManager) -> None:
    ws_id = await manager.create()
    ws_path = await manager.resolve(ws_id)

    # Fake that it's already in trash
    trash_path = manager.trash_dir / ws_id
    trash_path.mkdir()
    (trash_path / "f").write_bytes(b"foo")

    # Delete should not overwrite, but should remove sidecar
    await manager.delete(ws_id)

    # The sidecar should be gone
    assert not (manager.meta_dir / f"{ws_id}.json").exists()
    # Delete succeeds completely and original directory is now gone because trash ID is unique
    assert not ws_path.exists()
