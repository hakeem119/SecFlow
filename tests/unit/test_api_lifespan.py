import os
import uuid
from pathlib import Path

import pytest
from app.core.config import Settings
from app.main import StartupError, create_app
from fastapi.testclient import TestClient


def test_lifespan_starts_and_stops_reaper(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    settings = Settings(workspace_root=root)
    app = create_app(settings)

    with TestClient(app):
        # Check reaper task is started
        assert app.state.reaper_task is not None
        assert not app.state.reaper_task.done()

        # Check root and subdirs are created
        assert root.exists()
        assert (root / ".meta").exists()
        assert (root / ".trash").exists()

        # Roots and subdirs created correctly in lifespan
        manager = app.state.workspace_manager
        import asyncio

        asyncio.run(manager.create())
    # After exit, reaper task should be cancelled
    assert app.state.reaper_task.cancelled()


def test_lifespan_fails_on_root_file(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.write_bytes(b"not a dir")

    settings = Settings(workspace_root=root)
    app = create_app(settings)

    with pytest.raises(StartupError):  # noqa: SIM117
        with TestClient(app):
            pass


def test_delete_workspace_via_api(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    settings = Settings(workspace_root=root)
    app = create_app(settings)

    with TestClient(app) as client:
        # It's missing
        ws_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/workspaces/{ws_id}")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "workspace_not_found"


def test_create_app_no_disk_touch(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    settings = Settings(workspace_root=root)
    # create_app should not touch disk
    create_app(settings)
    assert not root.exists()


def test_lifespan_symlink_meta_trash(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.mkdir()
    meta = root / ".meta"
    trash = root / ".trash"
    meta.symlink_to(tmp_path)  # symlink!
    trash.mkdir()

    settings = Settings(workspace_root=root)
    app = create_app(settings)
    with pytest.raises(StartupError) as exc:  # noqa: SIM117
        with TestClient(app):
            pass
    assert "paths" not in str(exc.value).lower()
    assert "/" not in str(exc.value)


def test_lifespan_root_permissions(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.mkdir(mode=0o777)  # World accessible

    settings = Settings(workspace_root=root)
    app = create_app(settings)
    with pytest.raises(StartupError):  # noqa: SIM117
        with TestClient(app):
            pass


def test_lifespan_root_slash() -> None:
    import asyncio

    from app.main import lifespan
    from fastapi import FastAPI

    app = FastAPI()
    app.state.settings = Settings(workspace_root=Path("/"))

    with pytest.raises(StartupError):
        asyncio.run(lifespan(app).__aenter__())


def test_validate_dir_missing(tmp_path: Path) -> None:
    from app.main import _validate_dir

    with pytest.raises(StartupError):
        _validate_dir(tmp_path / "nonexistent")


def test_lifespan_mkdir_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from app.main import lifespan
    from fastapi import FastAPI

    app = FastAPI()
    app.state.settings = Settings(workspace_root=tmp_path / "workspaces")

    original_mkdir = Path.mkdir
    call_count = 0

    def mock_mkdir(
        self: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("Permission denied")
        original_mkdir(self, mode, parents, exist_ok)

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)
    with pytest.raises(StartupError):
        asyncio.run(lifespan(app).__aenter__())


def test_validate_dir_wrong_dev(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.mkdir(mode=0o700)

    from app.main import _validate_dir

    with pytest.raises(StartupError):
        _validate_dir(root, expected_dev=123456789)


def test_validate_dir_wrong_uid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "workspaces"
    root.mkdir(mode=0o700)

    monkeypatch.setattr(os, "getuid", lambda: 999999)
    from app.main import _validate_dir

    with pytest.raises(StartupError):
        _validate_dir(root)


def test_validate_dir_not_dir(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.write_bytes(b"not a dir")
    from app.main import _validate_dir

    with pytest.raises(StartupError):
        _validate_dir(root)


def test_validate_dir_symlink(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.symlink_to(tmp_path)
    from app.main import _validate_dir

    with pytest.raises(StartupError):
        _validate_dir(root)
