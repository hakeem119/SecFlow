import os
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from app.schemas.paths import validate_posix_path


@dataclass(frozen=True)
class ScanLimits:
    max_file_count: int
    max_file_size_bytes: int
    max_total_size_bytes: int
    max_directory_depth: int


@dataclass(frozen=True)
class ScanReport:
    file_count: int
    total_bytes: int
    max_depth: int
    symlinks: list[str] = field(default_factory=list)
    special_files: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    truncated: bool = False


def scan(path: Path, limits: ScanLimits) -> ScanReport:
    """
    Scans a workspace path with bounded limits. Stops early if any limit is exceeded.
    Reports symlinks and special files without following them.
    """
    file_count = 0
    total_bytes = 0
    max_depth_found = 0
    symlinks: list[str] = []
    special_files: list[str] = []
    violations: list[str] = []
    truncated = False

    def _add_violation(msg: str) -> None:
        nonlocal truncated
        if len(violations) < 100:
            violations.append(msg)
        else:
            truncated = True

    def _walk(current_path: str, current_depth: int) -> bool:
        nonlocal file_count, total_bytes, max_depth_found, truncated

        if current_depth > max_depth_found:
            max_depth_found = current_depth

        if current_depth > limits.max_directory_depth:
            _add_violation("Directory depth exceeded maximum")
            return False

        try:
            it = os.scandir(current_path)
        except OSError:
            _add_violation("Directory could not be read")
            return True

        with it:
            for entry in it:
                file_count += 1
                if file_count > limits.max_file_count:
                    _add_violation("File count exceeded maximum")
                    return False

                rel_path = os.path.relpath(entry.path, str(path))
                posix_str = PurePosixPath(rel_path).as_posix()
                try:
                    validate_posix_path(PurePosixPath(posix_str))
                except ValueError:
                    posix_str = "<invalid_filename>"

                if entry.is_symlink():
                    if len(symlinks) < 100:
                        symlinks.append(posix_str)
                    else:
                        truncated = True
                    continue

                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    _add_violation("File stat failed")
                    continue

                if stat.S_ISDIR(st.st_mode):
                    if not _walk(entry.path, current_depth + 1):
                        return False
                elif stat.S_ISREG(st.st_mode):
                    size = st.st_size
                    if size > limits.max_file_size_bytes:
                        _add_violation("File size exceeded maximum")
                        return False

                    total_bytes += size
                    if total_bytes > limits.max_total_size_bytes:
                        _add_violation("Total size exceeded maximum")
                        return False
                else:
                    if len(special_files) < 100:
                        special_files.append(posix_str)
                    else:
                        truncated = True

        return True

    _walk(str(path), 0)

    return ScanReport(
        file_count=file_count,
        total_bytes=total_bytes,
        max_depth=max_depth_found,
        symlinks=symlinks,
        special_files=special_files,
        violations=violations,
        truncated=truncated,
    )
