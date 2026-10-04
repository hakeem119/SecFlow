import os
from pathlib import Path

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_valid_and_defaults() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    try:
        settings = Settings()
        assert settings.workspace_root == Path("/opt/test/ws")
        assert settings.ttl_hours == 24
        assert settings.tool_timeout_scc == 60
        assert settings.max_output_items == 500
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]


def test_settings_env_override() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"] = "2000"
    try:
        settings = Settings()
        assert settings.max_file_size_bytes == 2000
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]
        del os.environ["SECFLOW_MAX_FILE_SIZE_BYTES"]


def test_settings_gt_0_rejection() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_TTL_HOURS"] = "0"
    try:
        with pytest.raises(ValidationError, match="Input should be greater than 0"):
            Settings()
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]
        del os.environ["SECFLOW_TTL_HOURS"]


def test_settings_relative_workspace_root_rejected() -> None:
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "relative/ws"
    try:
        with pytest.raises(ValidationError, match="workspace_root must be an absolute path"):
            Settings()
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]


def test_settings_le_upper_bound_rejection() -> None:
    """Upper bounds (le) must reject values above the limit."""
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    os.environ["SECFLOW_TTL_HOURS"] = "9999"
    try:
        with pytest.raises(ValidationError, match="Input should be less than or equal to"):
            Settings()
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]
        del os.environ["SECFLOW_TTL_HOURS"]


def test_settings_tool_timeout_seconds_default_removed() -> None:
    """tool_timeout_seconds_default was YAGNI; confirm it no longer exists."""
    assert "tool_timeout_seconds_default" not in Settings.model_fields
    os.environ["SECFLOW_WORKSPACE_ROOT"] = "/opt/test/ws"
    try:
        settings = Settings()
        assert not hasattr(settings, "tool_timeout_seconds_default")
    finally:
        del os.environ["SECFLOW_WORKSPACE_ROOT"]


def test_env_example_loads_without_error() -> None:
    """
    Every KEY=VALUE line in .env.example must load through Settings without
    error. This catches stale keys (field removed from Settings but left in
    the example) and missing required keys (required field added to Settings
    but forgotten in the example).
    """
    env_example = Path(__file__).parents[2] / ".env.example"
    env_vars: dict[str, str] = {}
    for line in env_example.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition("=")
        env_vars[key.strip()] = val.strip()

    saved = {k: os.environ.pop(k) for k in env_vars if k in os.environ}
    try:
        for k, v in env_vars.items():
            os.environ[k] = v
            # F1 requirement: verify the key belongs to Settings.
            if k.startswith("SECFLOW_"):
                field_name = k[len("SECFLOW_") :].lower()
                assert field_name in Settings.model_fields, (
                    f"Key {k} is not in Settings.model_fields"
                )

        settings = Settings()
        # Spot-check a few values to ensure parsing happened correctly.
        assert settings.workspace_root == Path("/var/lib/secflow/workspaces")
        assert settings.ttl_hours == 24
        assert settings.tool_timeout_git == 120
        assert settings.max_output_syft == 1000
    finally:
        for k in env_vars:
            os.environ.pop(k, None)
        for k, v in saved.items():
            os.environ[k] = v
