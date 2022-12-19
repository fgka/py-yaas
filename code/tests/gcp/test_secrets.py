# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any, Dict, Optional

import pytest

from yaas import const
from yaas.gcp import secrets


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            dict(
                project_id="test_project_id",
                secret_id="test_secret_id",
                version="test_version",
            ),
            "projects/test_project_id/secrets/test_secret_id/versions/test_version",
        ),
        (
            dict(
                project_id="test_project_id",
                secret_id="test_secret_id",
            ),
            "projects/test_project_id/secrets/test_secret_id/versions/latest",
        ),
    ],
)
def test_name_ok(kwargs, expected):
    # Given/When
    result = secrets.name(**kwargs)
    # Then
    assert result == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(
            project_id="",
            secret_id="test_secret_id",
            version="test_version",
        ),
        dict(
            project_id=None,
            secret_id="test_secret_id",
            version="test_version",
        ),
        dict(
            project_id="test_project_id",
            secret_id="",
            version="test_version",
        ),
        dict(
            project_id="test_project_id",
            secret_id=None,
            version="test_version",
        ),
    ],
)
def test_name_nok(kwargs):
    # Given/When/Then
    with pytest.raises(TypeError):
        secrets.name(**kwargs)


class _StubResponse:
    class _StubPayload:
        def __init__(self, data: Any):
            self.data = data

    def __init__(self, data: Any):
        self.payload = _StubResponse._StubPayload(data)


class _StubSecretClient:
    def __init__(
        self,
        *,
        data: Optional[str] = "TEST_DATA",
        raise_on_access: Optional[bool] = False,
    ):
        self._response = _StubResponse(bytes(data.encode(const.ENCODING_UTF8)))
        self._raise_on_access = raise_on_access
        self._request = None

    def access_secret_version(self, *, request: Dict[str, Any]) -> _StubResponse:
        self._request = request
        if self._raise_on_access:
            raise RuntimeError
        return self._response


def test_get_ok(monkeypatch):
    # Given
    expected = "EXPECTED"
    secret_name = "TEST_SECRET"
    client = _StubSecretClient(data=expected)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When
    result = secrets.get(secret_name)
    # Then
    assert result == expected
    assert client._request.get("name") == secret_name


def test_get_nok(monkeypatch):
    # Given
    client = _StubSecretClient(raise_on_access=True)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When/Then
    with pytest.raises(secrets.SecretManagerAccessError):
        secrets.get("TEST_SECRET")


@pytest.mark.parametrize(
    "value,amount_errors",
    [
        (123, 1),
        (None, 1),
        ("", 1),
        ("projects/ /secrets/my-secret-123/versions/my-version-123", 1),
        ("projects/my-project-123/secrets/ /versions/my-version-123", 1),
        ("projects/my-project-123/secrets/my-secret-123/versions/ ", 1),
        (
            " projects/my-project-123/secrets/my-secret-123/versions/my-version-123",
            1,
        ),
        (
            "projects/my project 123/secrets/my secret 123/versions/my version 123",
            1,
        ),
        (
            "projects/my-project-123/secrets/my-secret-123/versions/my-version-123",
            0,
        ),
    ],
)
def test_validate_secret_resource_name_ok(value: str, amount_errors: int):
    # Given/When
    result = secrets.validate_secret_resource_name(value, raise_if_invalid=False)
    # Then
    assert len(result) == amount_errors
