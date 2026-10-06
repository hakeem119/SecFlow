"""
Safe path manipulation and containment checking.

Security Note (Check/Use Race Condition):
The `SafePath` class validates a path against symlink escapes and traversal
attacks by checking the filesystem state at a specific point in time (Time of Check).
However, an attacker could theoretically swap a directory for a symlink between
this check and the moment the file is actually opened (Time of Use).

To mitigate this TOCTOU race condition, consumers must STILL open files using
`open_nofollow` or similar safe access patterns that enforce `O_NOFOLLOW`
at the OS level. `SafePath` provides the strong guarantee that *at the time of
inspection*, the path was safely contained.
"""

import os
import stat
from pathlib import Path, PurePosixPath

from app.core.errors import ErrorCode, SecFlowError
from app.schemas.paths import validate_posix_path


class PathSecurityError(SecFlowError):
    stable_code = ErrorCode.INVALID_REQUEST
    message = "Path violates security constraints."


class SafePath:
    """
    A value object representing a validated, safely contained path.
    """

    def __init__(self, path: Path, _internal: bool = False) -> None:
        if not _internal:
            raise RuntimeError("Use SafePath.within() to construct a SafePath")
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @classmethod
    def within(cls, root: Path, relative: str | Path) -> "SafePath":
        """
        Validates that `relative` points to a path strictly contained within `root`.
        Rejects directory traversal, absolute paths, and any symlinks in the path hierarchy.
        """
        relative_str = str(relative)
        try:
            validate_posix_path(PurePosixPath(relative_str))
        except ValueError as e:
            raise PathSecurityError() from e

        # Combine paths without resolving yet
        target = root / relative_str

        current = target
        components_to_check: list[Path] = []
        # We only check components inside the workspace up to the root (inclusive), but not higher
        while current != root.parent and current != current.parent:
            components_to_check.append(current)
            current = current.parent
        components_to_check.reverse()

        for comp in components_to_check:
            try:
                st = comp.lstat()
            except FileNotFoundError:
                # If a component doesn't exist yet, we can't check it,
                # but it also can't be a symlink currently.
                continue
            except OSError as e:
                # Catch ELOOP or other OS errors
                raise PathSecurityError() from e

            if stat.S_ISLNK(st.st_mode):
                raise PathSecurityError()

        # Final containment cross-check
        try:
            resolved_target = target.resolve(strict=False)
            resolved_root = root.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            # RuntimeError can happen in Python's resolve() on symlink loops
            raise PathSecurityError() from e

        if not resolved_target.is_relative_to(resolved_root):
            raise PathSecurityError()

        return cls(resolved_target, _internal=True)


def open_nofollow(path: Path) -> int:
    """
    Safely opens a regular file, rejecting symlinks and special files (like FIFOs)
    at the OS level to avoid TOCTOU races and hanging processes.
    Returns the open file descriptor.
    """
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as e:
        raise PathSecurityError() from e

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise PathSecurityError()
    except OSError as e:
        os.close(fd)
        raise PathSecurityError() from e

    return fd
