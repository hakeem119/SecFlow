import os
import sys
from pathlib import Path

import pytest
from app.core.safe_path import PathSecurityError, SafePath, open_nofollow


def test_safe_path_valid(tmp_path: Path) -> None:
    # A perfectly normal path should succeed
    child = tmp_path / "valid"
    child.mkdir()
    safe = SafePath.within(tmp_path, "valid")
    assert safe.path == child.resolve()


def test_safe_path_traversal_attempts(tmp_path: Path) -> None:
    # Cannot traverse out
    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "..")

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "a/../../x")

    # Cannot use absolute paths
    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "/etc/passwd")

    # Cannot use NUL bytes (caught by validate_posix_path)
    with pytest.raises((ValueError, PathSecurityError)):
        SafePath.within(tmp_path, "a\0b")


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_safe_path_symlink_inside_pointing_outside(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    sym = tmp_path / "sym"
    sym.symlink_to(outside)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "sym")


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_safe_path_intermediate_symlink(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    sym = tmp_path / "sym"
    sym.symlink_to(real_dir)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "sym/file.txt")


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_safe_path_root_is_symlink(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    sym_root = tmp_path / "sym_root"
    sym_root.symlink_to(real_dir)

    with pytest.raises(PathSecurityError):
        SafePath.within(sym_root, "some_file.txt")


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_safe_path_symlink_loop(tmp_path: Path) -> None:
    sym1 = tmp_path / "sym1"
    sym2 = tmp_path / "sym2"
    sym1.symlink_to(sym2)
    sym2.symlink_to(sym1)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "sym1")


@pytest.mark.skipif(sys.platform == "win32", reason="FIFO tests require Unix")
def test_open_nofollow_fifo(tmp_path: Path) -> None:
    fifo_path = tmp_path / "my_fifo"
    os.mkfifo(fifo_path)

    with pytest.raises(PathSecurityError):
        open_nofollow(fifo_path)


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_open_nofollow_symlink(tmp_path: Path) -> None:
    real_file = tmp_path / "real.txt"
    real_file.write_text("hello")
    sym = tmp_path / "sym.txt"
    sym.symlink_to(real_file)

    with pytest.raises(PathSecurityError):
        open_nofollow(sym)


def test_open_nofollow_valid(tmp_path: Path) -> None:
    real_file = tmp_path / "real.txt"
    real_file.write_text("hello")

    fd = open_nofollow(real_file)
    try:
        with os.fdopen(fd, "r") as f:
            assert f.read() == "hello"
    except Exception:
        os.close(fd)
        raise


def test_safe_path_not_found(tmp_path: Path) -> None:
    # A path that doesn't exist yet should still be safe
    safe = SafePath.within(tmp_path, "does_not_exist/file.txt")
    assert safe.path == (tmp_path / "does_not_exist/file.txt").resolve(strict=False)


def test_safe_path_lstat_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    def mock_lstat(self: Path) -> os.stat_result:
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "lstat", mock_lstat)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "valid")


def test_safe_path_resolve_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    def mock_resolve(self: Path, strict: bool = False) -> Path:
        raise RuntimeError("Symlink loop")

    monkeypatch.setattr(Path, "resolve", mock_resolve)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "valid")


def test_safe_path_not_relative_to(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    original_resolve = Path.resolve

    def mock_resolve(self: Path, strict: bool = False) -> Path:
        if self.name == "valid":
            return Path("/etc/passwd")
        return original_resolve(self, strict)

    monkeypatch.setattr(Path, "resolve", mock_resolve)

    with pytest.raises(PathSecurityError):
        SafePath.within(tmp_path, "valid")


def test_open_nofollow_fstat_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_file = tmp_path / "real.txt"
    real_file.write_text("hello")

    def mock_fstat(fd: int) -> os.stat_result:
        raise OSError("I/O error")

    monkeypatch.setattr(os, "fstat", mock_fstat)
    with pytest.raises(PathSecurityError):
        open_nofollow(real_file)


def test_safe_path_internal() -> None:
    with pytest.raises(RuntimeError):
        SafePath(Path("/invalid/path"))
