import os
from pathlib import Path

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_valid_and_defaults() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    settings = Settings()
    assert settings.workspace_root == Path("/opt/test/ws")
    assert settings.ttl_hours == 24
    assert settings.tool_timeout_scc == 60
    assert settings.max_output_items == 500
    del os.environ["SECFLOW_WORKSPACE_ROOT"]


def test_settings_env_override() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"] = "2000"
    settings = Settings()
    assert settings.max_file_size_bytes == 2000
    del os.environ["SECFLOW_WORKSPACE_ROOT"]
    del os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"]


def test_settings_gt_0_rejection() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_TTL_HOURS"] = "0"
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        Settings()

    os.environ["SECFLOW_TTL_HOURS"] = "-5"
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        Settings()

    del os.environ["SECFLOW_WORKSPACE_ROOT"]
    del os.environ["SECFLOW_TTL_HOURS"]


def test_settings_relative_workspace_root_rejected() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "relative/ws"
    with pytest.raises(ValidationError, match="workspace_root must be an absolute path"):
        Settings()
    del os.environ["SECFLOW_WORKSPACE_ROOT"]
