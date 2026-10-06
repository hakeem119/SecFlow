import asyncio
import logging
import re
from pathlib import Path

from app.core.errors import WorkspaceNotFoundError
from app.services.workspace import UUID_RE, WorkspaceManager

logger = logging.getLogger(__name__)


class WorkspaceReaper:
    """
    Background task to clean up expired workspaces and trash.
    """

    def __init__(self, manager: WorkspaceManager, interval_seconds: int) -> None:
        self.manager = manager
        self.interval_seconds = interval_seconds
        self._uuid_pattern = re.compile(UUID_RE)

    async def start(self) -> None:
        """Runs the periodic sweep loop indefinitely."""
        while True:
            try:
                await self.sweep()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - Reaper loop must never die
                # Deliberately catch everything and log class name only
                logger.error("Reaper loop encountered an error: %s", e.__class__.__name__)  # noqa: TRY400 - Intentionally hiding exc_info

            await asyncio.sleep(self.interval_seconds)

    async def sweep(self) -> None:
        """Sweeps root for expired workspaces and trash for pending deletions."""

        def _get_entries() -> list[str]:
            try:
                return [p.name for p in Path(self.manager.root).iterdir()]
            except OSError:
                return []

        def _unlink_stray(stray_entry: str) -> None:
            try:
                # Unlink WITHOUT following
                Path(self.manager.root, stray_entry).unlink(missing_ok=True)
            except OSError as e_unlink:
                logger.exception(
                    "Reaper cleanup failed: %s for %s", e_unlink.__class__.__name__, stray_entry
                )

        entries = await asyncio.to_thread(_get_entries)
        for entry in entries:
            # Ignore .meta, .trash, and anything not a UUID
            if not self._uuid_pattern.fullmatch(entry):
                continue

            try:
                # We attempt to resolve the workspace.
                # If it raises WorkspaceNotFoundError, it means it is expired or malformed.
                await self.manager.resolve(entry)
            except WorkspaceNotFoundError:
                # It's expired or corrupt, let's delete it
                try:
                    await self.manager.purge(entry)
                except WorkspaceNotFoundError:
                    # A7: stray non-directory entry in root named like a UUID
                    await asyncio.to_thread(_unlink_stray, entry)
                except Exception as e_del:
                    logger.exception(
                        "Reaper cleanup failed: %s for %s", e_del.__class__.__name__, entry
                    )
            except Exception as e:  # noqa: BLE001 - Sweep must continue
                logger.error("Reaper cleanup failed: %s for %s", e.__class__.__name__, entry)  # noqa: TRY400 - Intentionally hiding exc_info

        def _get_trash_entries() -> list[str]:
            try:
                return [p.name for p in Path(self.manager.trash_dir).iterdir()]
            except OSError:
                return []

        trash_entries = await asyncio.to_thread(_get_trash_entries)
        for entry in trash_entries:
            try:
                await self.manager.purge_trash(entry)
            except Exception as e_trash:
                logger.exception(
                    "Reaper trash cleanup failed: %s for %s", e_trash.__class__.__name__, entry
                )
