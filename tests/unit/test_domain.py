import uuid

import pytest
from app.schemas.domain import WorkspaceId
from pydantic import BaseModel, ValidationError


class Dummy(BaseModel):
    ws_id: WorkspaceId


def test_workspace_id_valid() -> None:
    u = uuid.uuid4()
    d = Dummy(ws_id=u)  # type: ignore
    assert str(d.ws_id) == str(u)


def test_workspace_id_string_valid() -> None:
    u = str(uuid.uuid4())
    d = Dummy(ws_id=u)  # type: ignore
    assert str(d.ws_id) == u


def test_workspace_id_uppercase_string_valid() -> None:
    u = str(uuid.uuid4())
    d = Dummy(ws_id=u.upper())  # type: ignore
    # pydantic uuid schema handles lowercase formatting correctly
    assert str(d.ws_id).lower() == u.lower()


def test_workspace_id_rejects_uuid1() -> None:
    u = uuid.uuid1()
    with pytest.raises(ValidationError, match="UUID version 4 expected"):
        Dummy(ws_id=u)  # type: ignore


def test_workspace_id_rejects_malformed() -> None:
    with pytest.raises(ValidationError):
        Dummy(ws_id="not-a-uuid")  # type: ignore
