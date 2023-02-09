# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any, Dict, Optional

import pytest

from yaas.gcp import cloud_sql, cloud_sql_const
from yaas import xpath

_TEST_PROJECT: str = "my-project-123"
_TEST_INSTANCE_NAME: str = "my-instance-123"
_TEST_INSTANCE_RESOURCE_NAME: str = (
    f"{_TEST_PROJECT}:my-location-123:{_TEST_INSTANCE_NAME}"
)


class _StubCloudSqlRequest:
    def __init__(
        self,
        *,
        value: Optional[Dict[str, Any]] = None,
        raise_on_execute: Optional[bool] = False,
    ):
        self.called = {}
        self._raise_on_result = raise_on_execute
        self._result = value

    def execute(self) -> Dict[str, Any]:
        self.called[_StubCloudSqlRequest.execute.__name__] = True
        if self._raise_on_result:
            raise RuntimeError
        return self._result


class _StubSqlInstancesResource:
    def __init__(
        self,
        *,
        instance: Optional[Dict[str, Any]] = None,
        patch_result: Optional[Dict[str, Any]] = None,
        raise_on_get_execute: Optional[bool] = False,
        raise_on_patch_execute: Optional[bool] = False,
    ):
        self._instance = instance
        self._raise_on_get_execute = raise_on_get_execute
        self._patch_result = patch_result
        self._raise_on_patch_execute = raise_on_patch_execute
        self.called = {}

    def get(  # pylint: disable=unused-argument
        self, project: str, instance: str
    ) -> _StubCloudSqlRequest:
        result = _StubCloudSqlRequest(
            value=self._instance, raise_on_execute=self._raise_on_get_execute
        )
        self.called[_StubSqlInstancesResource.get.__name__] = locals()
        return result

    def patch(  # pylint: disable=unused-argument
        self, project: str, instance: str, body: Dict[str, Any]
    ) -> _StubCloudSqlRequest:
        result = _StubCloudSqlRequest(
            value=self._patch_result, raise_on_execute=self._raise_on_patch_execute
        )
        self.called[_StubSqlInstancesResource.patch.__name__] = locals()
        return result


@pytest.mark.asyncio
async def test_get_instance_nok_raises(monkeypatch):
    # Given
    client = _StubSqlInstancesResource(raise_on_get_execute=True)
    monkeypatch.setattr(cloud_sql, cloud_sql._sql_instances.__name__, lambda: client)
    # When/Then
    with pytest.raises(cloud_sql.CloudSqlServiceError):
        await cloud_sql.get_instance(_TEST_INSTANCE_RESOURCE_NAME)
    # Then:called
    called = client.called.get(_StubSqlInstancesResource.get.__name__)
    assert isinstance(called, dict)
    assert called.get("project") == _TEST_PROJECT
    assert called.get("instance") == _TEST_INSTANCE_NAME
    result = called.get("result")
    assert isinstance(result, _StubCloudSqlRequest)
    assert result.called.get("execute")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,raise_on_get_execute,expected",
    [
        (cloud_sql_const.CLOUD_SQL_STATUS_OK, False, True),  # all good
        (
            cloud_sql_const.CLOUD_SQL_STATUS_OK + "_NOT",
            False,
            False,
        ),  # status is not OK
        (
            cloud_sql_const.CLOUD_SQL_STATUS_OK,
            True,
            False,
        ),  # get_instance() raises exception
    ],
)
async def test_can_be_deployed_ok(
    monkeypatch, status: str, raise_on_get_execute: bool, expected: bool
):
    # Given
    instance = xpath.create_dict_based_on_path(
        cloud_sql_const.CLOUD_SQL_STATE_KEY, status
    )
    client = _StubSqlInstancesResource(
        instance=instance, raise_on_get_execute=raise_on_get_execute
    )
    monkeypatch.setattr(cloud_sql, cloud_sql._sql_instances.__name__, lambda: client)
    # When
    result, _ = await cloud_sql.can_be_deployed(_TEST_INSTANCE_RESOURCE_NAME)
    # Then
    assert result == expected


@pytest.mark.asyncio
async def test_update_instance_ok(monkeypatch):
    # Given
    path = "root.attr.sub_attr"
    value = "TEST_VALUE"
    instance = xpath.create_dict_based_on_path(
        "status", cloud_sql_const.CLOUD_SQL_STATUS_OK
    )
    client = _StubSqlInstancesResource(instance=instance, patch_result={})
    monkeypatch.setattr(cloud_sql, cloud_sql._sql_instances.__name__, lambda: client)
    # When
    result = await cloud_sql.update_instance(
        name=_TEST_INSTANCE_RESOURCE_NAME, path=path, value=value
    )
    # Then: result
    assert isinstance(result, dict)
    # Then: patch
    called_patch = client.called.get(_StubSqlInstancesResource.patch.__name__)
    assert isinstance(called_patch, dict)
    assert called_patch.get("project") == _TEST_PROJECT
    assert called_patch.get("instance") == _TEST_INSTANCE_NAME
    patch_body = called_patch.get("body")
    assert isinstance(patch_body, dict)
    node, key = xpath.get_parent_node_based_on_path(patch_body, path)
    assert node[key] == value


@pytest.mark.asyncio
async def test_update_service_nok_raises(monkeypatch):
    # Given
    path = "root.attr.sub_attr"
    value = "TEST_VALUE"
    client = _StubSqlInstancesResource(raise_on_patch_execute=True)
    monkeypatch.setattr(cloud_sql, cloud_sql._sql_instances.__name__, lambda: client)
    # When/Then
    with pytest.raises(cloud_sql.CloudSqlServiceError):
        await cloud_sql.update_instance(
            name=_TEST_INSTANCE_RESOURCE_NAME, path=path, value=value
        )


@pytest.mark.parametrize(
    "value,amount_errors",
    [
        (123, 1),
        (None, 1),
        ("", 1),
        ("projects/locations/my-location-123/instances/my-instance-123", 1),
        (_TEST_INSTANCE_RESOURCE_NAME + ":NOT", 1),
        ("my-project-123::my-instance-123", 1),
        (":my-location-123:my-instance-123", 1),
        (_TEST_INSTANCE_RESOURCE_NAME, 0),
    ],
)
def test_validate_cloud_run_resource_name_ok(value: str, amount_errors: int):
    # Given/When
    result = cloud_sql.validate_cloud_sql_resource_name(value, raise_if_invalid=False)
    # Then
    assert len(result) == amount_errors
