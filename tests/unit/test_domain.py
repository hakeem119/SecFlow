import uuid

import pytest
from app.schemas.domain import WorkspaceId
from pydantic import BaseModel


class Dummy(BaseModel):
    ws_id: WorkspaceId


def test_workspace_id_valid() -> None:
    u = uuid.uuid4()
    d = Dummy(ws_id=u)  # type: ignore
    assert str(d.ws_id) == str(u)


def test_workspace_id_invalid() -> None:
    with pytest.raises(ValueError):
        Dummy(ws_id="not-a-uuid")  # type: ignore
