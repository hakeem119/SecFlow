import os
import sys
import typing
from pathlib import Path

import pytest
from app.services.workspace_scan import ScanLimits, scan


@pytest.fixture
def base_limits() -> ScanLimits:
    return ScanLimits(
        max_file_count=100,
        max_file_size_bytes=1000,
        max_total_size_bytes=10000,
        max_directory_depth=5,
    )


def test_scan_normal_tree(tmp_path: Path, base_limits: ScanLimits) -> None:
    f1 = tmp_path / "f1.txt"
    f1.write_bytes(b"a" * 10)

    d1 = tmp_path / "d1"
    d1.mkdir()
    f2 = d1 / "f2.txt"
    f2.write_bytes(b"b" * 20)

    report = scan(tmp_path, base_limits)

    assert report.file_count == 3
    assert report.total_bytes == 30
    assert report.max_depth == 1
    assert not report.violations
    assert not report.symlinks
    assert not report.special_files


def test_scan_exceeds_max_file_count(tmp_path: Path, base_limits: ScanLimits) -> None:
    limits = ScanLimits(
        max_file_count=2,
        max_file_size_bytes=100,
        max_total_size_bytes=1000,
        max_directory_depth=5,
    )

    for i in range(5):
        (tmp_path / f"f{i}.txt").write_bytes(b"a")

    report = scan(tmp_path, limits)

    assert report.file_count == 3
    assert len(report.violations) == 1
    assert "File count exceeded" in report.violations[0]


def test_scan_exceeds_max_file_size(tmp_path: Path, base_limits: ScanLimits) -> None:
    limits = ScanLimits(
        max_file_count=10,
        max_file_size_bytes=10,
        max_total_size_bytes=1000,
        max_directory_depth=5,
    )

    (tmp_path / "f1.txt").write_bytes(b"a" * 5)
    (tmp_path / "f2.txt").write_bytes(b"b" * 15)  # exceeds limit

    report = scan(tmp_path, limits)

    assert len(report.violations) == 1
    assert "File size exceeded" in report.violations[0]


def test_scan_exceeds_max_total_size(tmp_path: Path, base_limits: ScanLimits) -> None:
    limits = ScanLimits(
        max_file_count=10,
        max_file_size_bytes=100,
        max_total_size_bytes=15,
        max_directory_depth=5,
    )

    (tmp_path / "f1.txt").write_bytes(b"a" * 10)
    (tmp_path / "f2.txt").write_bytes(b"b" * 10)

    report = scan(tmp_path, limits)

    # 20 > 15
    assert len(report.violations) == 1
    assert "Total size exceeded" in report.violations[0]


def test_scan_exceeds_max_depth(tmp_path: Path, base_limits: ScanLimits) -> None:
    limits = ScanLimits(
        max_file_count=10,
        max_file_size_bytes=100,
        max_total_size_bytes=1000,
        max_directory_depth=1,
    )

    d1 = tmp_path / "d1"
    d1.mkdir()
    d2 = d1 / "d2"
    d2.mkdir()
    d3 = d2 / "d3"
    d3.mkdir()

    report = scan(tmp_path, limits)

    assert len(report.violations) == 1
    assert "Directory depth exceeded" in report.violations[0]
    assert report.max_depth == 2


@pytest.mark.skipif(sys.platform == "win32", reason="Symlink tests require Unix")
def test_scan_symlinks_and_fifo(tmp_path: Path, base_limits: ScanLimits) -> None:
    real_file = tmp_path / "real.txt"
    real_file.write_bytes(b"hello")

    sym = tmp_path / "sym.txt"
    sym.symlink_to(real_file)

    fifo_path = tmp_path / "my_fifo"
    os.mkfifo(fifo_path)

    report = scan(tmp_path, base_limits)

    assert report.file_count == 3
    assert len(report.symlinks) == 1
    assert "sym.txt" in report.symlinks
    assert len(report.special_files) == 1
    assert "my_fifo" in report.special_files
    assert not report.violations


def test_scan_workspace_stat_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    from app.services.workspace_scan import ScanLimits, scan

    # Create a file
    (tmp_path / "test.txt").write_text("hello")

    # Mock os.DirEntry.stat to raise OSError
    original_scandir = os.scandir

    class MockEntry:
        def __init__(self, path: str):
            self.path = path

        def is_symlink(self) -> bool:
            return False

        def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
            raise OSError("Permission denied")

    class MockScandir:
        def __init__(self, items: list[MockEntry]):
            self.items = items

        def __enter__(self) -> "MockScandir":
            return self

        def __exit__(self, exc_type: typing.Any, exc_val: typing.Any, exc_tb: typing.Any) -> None:
            pass

        def __iter__(self) -> typing.Iterator[MockEntry]:
            return iter(self.items)

    def mock_scandir(path: str | os.PathLike[str] | None = None) -> typing.Any:
        if path == str(tmp_path):
            return MockScandir([MockEntry(str(Path(str(path)) / "test.txt"))])
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", mock_scandir)
    report = scan(
        tmp_path,
        ScanLimits(
            max_file_count=100,
            max_file_size_bytes=1000,
            max_total_size_bytes=10000,
            max_directory_depth=5,
        ),
    )
    assert report.file_count == 1
    assert len(report.violations) == 1
    assert "File stat failed" in report.violations[0]


def test_scan_workspace_scandir_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    from app.services.workspace_scan import ScanLimits, scan

    # Mock scandir to fail
    def mock_scandir(path: str | os.PathLike[str] | None = None) -> typing.Any:
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "scandir", mock_scandir)
    report = scan(
        tmp_path,
        ScanLimits(
            max_file_count=100,
            max_file_size_bytes=1000,
            max_total_size_bytes=10000,
            max_directory_depth=5,
        ),
    )
    assert report.file_count == 0
    assert len(report.violations) == 1
    assert "Directory could not be read" in report.violations[0]


def test_scan_max_file_count_dirs(tmp_path: Path) -> None:
    limits = ScanLimits(
        max_file_count=2, max_file_size_bytes=100, max_total_size_bytes=1000, max_directory_depth=5
    )
    (tmp_path / "d1").mkdir()
    (tmp_path / "d2").mkdir()
    (tmp_path / "d3").mkdir()
    report = scan(tmp_path, limits)
    assert len(report.violations) == 1
    assert "File count exceeded" in report.violations[0]


def test_scan_truncated(tmp_path: Path, base_limits: ScanLimits) -> None:
    from dataclasses import replace

    higher_limits = replace(base_limits, max_file_count=200)
    for i in range(101):
        (tmp_path / f"sym{i}").symlink_to("target")
    report = scan(tmp_path, higher_limits)
    assert len(report.symlinks) == 100
    assert report.truncated is True


def test_scan_hostile_filename(tmp_path: Path, base_limits: ScanLimits) -> None:
    hostile = tmp_path / "bad\nname"
    hostile.write_bytes(b"bad")
    report = scan(tmp_path, base_limits)
    assert report.file_count == 1
    assert "bad\nname" not in report.violations
    assert "bad\nname" not in report.symlinks
    assert "bad\nname" not in report.special_files
    # mapped to <invalid_filename>
    # let's make a hostile symlink to be sure
    hostile_sym = tmp_path / "bad\x00sym"
    import contextlib

    with contextlib.suppress(ValueError):
        hostile_sym.symlink_to("target")
    hostile_sym2 = tmp_path / "bad\nsym"
    hostile_sym2.symlink_to("target")
    report2 = scan(tmp_path, base_limits)
    assert "<invalid_filename>" in report2.symlinks
    assert "bad\nsym" not in report2.symlinks


def test_scan_violations_truncation(tmp_path: Path) -> None:
    from app.services.workspace_scan import ScanLimits, scan

    limits = ScanLimits(
        max_file_count=200,
        max_file_size_bytes=1000,
        max_total_size_bytes=100000,
        max_directory_depth=5,
    )
    for i in range(105):
        (tmp_path / f"dir_{i}").mkdir()
        (tmp_path / f"dir_{i}").chmod(0o000)
    report = scan(tmp_path, limits)
    assert report.truncated is True
    assert len(report.violations) == 100
    for i in range(105):
        (tmp_path / f"dir_{i}").chmod(0o700)


def test_scan_special_files_truncation(tmp_path: Path) -> None:
    from app.services.workspace_scan import ScanLimits, scan

    limits = ScanLimits(
        max_file_count=200,
        max_file_size_bytes=1000,
        max_total_size_bytes=100000,
        max_directory_depth=5,
    )
    import os

    for i in range(105):
        os.mkfifo(tmp_path / f"fifo_{i}")
    report = scan(tmp_path, limits)
    assert report.truncated is True
    assert len(report.special_files) == 100
