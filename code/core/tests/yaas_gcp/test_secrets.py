# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,invalid-name,protected-access,missing-class-docstring,too-few-public-methods
# type: ignore
from typing import Any, Dict, List, Optional

import pytest

from yaas_common import const
from yaas_gcp import secrets


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

    def __init__(self, data: Any = None, name: str = None):
        self.payload = _StubResponse._StubPayload(data)
        self.name = name


class _StubSecretClient:
    def __init__(
        self,
        *,
        data: Optional[str] = "TEST_DATA",
        name: Optional[str] = "TEST_SECRET",
        list_response: Optional[List[str]] = None,
        raise_on_access: Optional[bool] = False,
        raise_on_add: Optional[bool] = False,
        raise_on_list: Optional[bool] = False,
        raise_on_disable: Optional[bool] = False,
        raise_on_destroy: Optional[bool] = False,
    ):
        self._response = _StubResponse(data=bytes(data.encode(const.ENCODING_UTF8)), name=name)
        self._list_response = list_response
        self._raise_on_access = raise_on_access
        self._raise_on_add = raise_on_add
        self._raise_on_list = raise_on_list
        self._raise_on_disable = raise_on_disable
        self._raise_on_destroy = raise_on_destroy
        self._request = None
        self._requests = []

    def access_secret_version(self, *, request: Dict[str, Any]) -> _StubResponse:
        self._request = request
        if self._raise_on_access:
            raise RuntimeError
        return self._response

    def add_secret_version(self, *, request: Dict[str, Any]) -> _StubResponse:
        self._request = request
        if self._raise_on_add:
            raise RuntimeError
        return self._response

    def list_secret_versions(self, *, request: Dict[str, Any]) -> List[str]:
        self._request = request
        if self._raise_on_list:
            raise RuntimeError
        return self._list_response

    def disable_secret_version(self, *, request: Dict[str, Any]) -> _StubResponse:
        self._requests.append(
            (
                "disable",
                request,
            )
        )
        if self._raise_on_disable:
            raise RuntimeError
        return self._response

    def destroy_secret_version(self, *, request: Dict[str, Any]) -> _StubResponse:
        self._requests.append(
            (
                "destroy",
                request,
            )
        )
        if self._raise_on_destroy:
            raise RuntimeError
        return self._response


@pytest.mark.asyncio
async def test_list_versions_ok(monkeypatch):
    # Given
    secret_name = "TEST_SECRET"
    versions = range(1, 6)
    version_numbers = sorted(versions, reverse=True)
    client = _mock_list(monkeypatch, secret_name, version_numbers)
    # When
    result = await secrets.list_versions(secret_name=secret_name + "/versions/123")
    # Then
    assert isinstance(result, list)
    assert len(result) == len(versions)
    assert client._request.get("parent") == secret_name


def _mock_list(monkeypatch, secret_name: str, version_numbers: List[int]):
    client = _StubSecretClient(
        list_response=[_StubResponse(name=f"{secret_name}/versions/{v_num}") for v_num in version_numbers]
    )
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    return client


@pytest.mark.asyncio
async def test_exists_ok(monkeypatch):
    # Given
    secret_name = "TEST_SECRET"
    versions = range(1, 6)
    version_numbers = sorted(versions, reverse=True)
    _mock_list(monkeypatch, secret_name, version_numbers)
    # When/Then
    for num in versions:
        assert await secrets.exists(secret_name=f"{secret_name}/versions/{num}")
    # Then: latest
    assert await secrets.exists(secret_name=f"{secret_name}/versions/latest")


@pytest.mark.asyncio
async def test_exists_ok_empty(monkeypatch):
    # Given
    secret_name = "TEST_SECRET"
    _mock_list(monkeypatch, secret_name, [])
    # When/Then
    assert not await secrets.exists(secret_name=f"{secret_name}/versions/latest")


@pytest.mark.asyncio
async def test_get_ok(monkeypatch):
    # Given
    expected = "EXPECTED"
    secret_name = "TEST_SECRET/versions/latest"
    client = _StubSecretClient(data=expected)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When
    result = await secrets.get(secret_name)
    # Then
    assert result == expected
    assert client._request.get("name") == secret_name


@pytest.mark.asyncio
async def test_get_nok(monkeypatch):
    # Given
    client = _StubSecretClient(raise_on_access=True)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When/Then
    with pytest.raises(secrets.SecretManagerAccessError):
        await secrets.get("TEST_SECRET")


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


@pytest.mark.asyncio
async def test_put_ok(monkeypatch):
    # Given
    content = "EXPECTED"
    secret_name = "TEST_SECRET"
    client = _StubSecretClient(name=secret_name)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When
    result = await secrets.put(secret_name=secret_name, content=content)
    # Then
    assert result == secret_name
    assert client._request.get("parent") == secret_name
    assert client._request.get("payload", {}).get("data") == content.encode(const.ENCODING_UTF8)


@pytest.mark.asyncio
async def test_put_nok(monkeypatch):
    # Given
    content = "EXPECTED"
    secret_name = "TEST_SECRET"
    client = _StubSecretClient(raise_on_add=True)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When/Then
    with pytest.raises(secrets.SecretManagerAccessError):
        await secrets.put(secret_name=secret_name, content=content)


@pytest.mark.asyncio
async def test_clean_up_ok(monkeypatch):
    # Given
    called = {}
    secret_name = "TEST_SECRET"
    amount_to_keep = 3
    versions = range(1, 6)
    version_numbers = sorted(versions, reverse=True)
    client = _mock_list(monkeypatch, secret_name, version_numbers)

    async def mocked_disable_versions(secret_name: str, version_numbers: List[int]) -> None:
        nonlocal called
        called[secrets._disable_versions.__name__] = (secret_name, version_numbers)

    monkeypatch.setattr(secrets, secrets._disable_versions.__name__, mocked_disable_versions)

    async def mocked_remove_versions(secret_name: str, version_numbers: List[int]) -> None:
        nonlocal called
        called[secrets._remove_versions.__name__] = (secret_name, version_numbers)

    monkeypatch.setattr(secrets, secrets._remove_versions.__name__, mocked_remove_versions)

    # When
    await secrets.clean_up(secret_name=secret_name, amount_to_keep=amount_to_keep)
    # Then
    assert client._request.get("parent") == secret_name
    # Then: disabled
    dis_name, dis_numbers = called.get(secrets._disable_versions.__name__, (None, None))
    assert dis_name == secret_name
    assert set(dis_numbers) == set(version_numbers[1 : amount_to_keep + 1])
    # Then: disabled
    rem_name, rem_numbers = called.get(secrets._remove_versions.__name__, (None, None))
    assert rem_name == secret_name
    assert set(rem_numbers) == set(version_numbers[amount_to_keep + 1 :])


@pytest.mark.asyncio
async def test_clean_up_nok(monkeypatch):
    # Given
    secret_name = "TEST_SECRET"
    amount_to_keep = 3
    client = _StubSecretClient(raise_on_list=True)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    # When/Then
    with pytest.raises(secrets.SecretManagerAccessError):
        await secrets.clean_up(secret_name=secret_name, amount_to_keep=amount_to_keep)
    # Then
    assert client._request.get("parent") == secret_name


@pytest.mark.asyncio
@pytest.mark.parametrize("to_raise", [True, False])
async def test__disable_versions_ok(monkeypatch, to_raise: bool):
    # Given
    secret_name = "TEST_SECRET"
    version_numbers = [1, 2, 3, 4, 5]
    client = _StubSecretClient(raise_on_disable=to_raise)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    exception = None
    # When
    try:
        await secrets._disable_versions(secret_name=secret_name, version_numbers=version_numbers)
    except secrets.SecretManagerAccessError as err:
        exception = err
    # Then: error?
    assert to_raise == bool(exception)
    # Then
    assert client._request is None
    # Then: requests
    await _assert_requests(client, secret_name, "disable", version_numbers)


async def _assert_requests(client: _StubSecretClient, secret_name: str, what: str, version_numbers: List[int]) -> None:
    # Then requests
    assert len(client._requests) == len(version_numbers)
    req_numbers = []
    for r_what, req in client._requests:
        assert r_what == what
        req_name = req.get("name")
        assert req_name.startswith(secret_name)
        v_number = int(req_name.split("/versions/")[-1])
        req_numbers.append(v_number)
    # Then: versions
    assert set(version_numbers) == set(req_numbers)


@pytest.mark.asyncio
@pytest.mark.parametrize("to_raise", [True, False])
async def test__remove_versions_ok(monkeypatch, to_raise: bool):
    # Given
    secret_name = "TEST_SECRET"
    version_numbers = [1, 2, 3, 4, 5]
    client = _StubSecretClient(raise_on_destroy=to_raise)
    monkeypatch.setattr(secrets, secrets._secret_client.__name__, lambda: client)
    exception = None
    # When
    try:
        await secrets._remove_versions(secret_name=secret_name, version_numbers=version_numbers)
    except secrets.SecretManagerAccessError as err:
        exception = err
    # Then: error?
    assert to_raise == bool(exception)
    # Then
    assert client._request is None
    # Then: requests
    await _assert_requests(client, secret_name, "destroy", version_numbers)
