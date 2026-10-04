import os
from pathlib import Path

from app.core.config import Settings


def test_settings_valid() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"] = "2000"

    settings = Settings()
    assert settings.workspace_root == Path("/opt/test/ws")
    assert settings.max_file_size_bytes == 2000
    assert settings.ttl_hours == 24
    assert settings.tool_timeout_git == 120

    del os.environ["SECFLOW_WORKSPACE_ROOT"]
    del os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"]
