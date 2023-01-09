# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any, Dict, Optional
import types

import pytest

from yaas.gcp import cloud_run, cloud_run_const

_TEST_SERVICE_NAME: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)
_TEST_REVISION: str = "TEST_REVISION"


class _StubCloudRunService:
    class _StubAttr:
        pass

    def __init__(self, path: str, value: Any, revision: Optional[str] = _TEST_REVISION):
        self.name = self.__class__.__name__
        self._set_path_value(path, value)
        self._set_path_value(cloud_run_const.CLOUD_RUN_SERVICE_REVISION_PATH, revision)

    def _set_path_value(self, path: str, value: Any) -> None:
        parent = self
        if cloud_run_const.REQUEST_PATH_SEP in path:
            path_lst = path.split(cloud_run_const.REQUEST_PATH_SEP)
        else:
            path_lst = [path]
        for attr in path_lst[:-1]:
            setattr(parent, attr, _StubCloudRunService._StubAttr())
            parent = getattr(parent, attr)
        setattr(parent, path_lst[-1], value)


class _StubCloudRunAsyncOperation:
    def __init__(
        self, *, value: Optional[Any] = None, raise_on_result: Optional[bool] = False
    ):
        self.called = {}
        self._raise_on_result = raise_on_result
        self._result = value

    async def result(self) -> Any:
        self.called[_StubCloudRunAsyncOperation.result.__name__] = True
        if self._raise_on_result:
            raise RuntimeError
        return self._result


class _StubCloudRunAsyncClient:
    def __init__(
        self,
        *,
        service: Optional[_StubCloudRunService] = None,
        update_operation: Optional[_StubCloudRunAsyncOperation] = None,
        raise_on_get: Optional[bool] = False,
        raise_on_update: Optional[bool] = False,
    ):
        self._service = service
        self._update_operation = update_operation
        self._raise_on_get = raise_on_get
        self._raise_on_update = raise_on_update
        self.called = {}

    async def get_service(self, request: Dict[str, Any]) -> _StubCloudRunService:
        self.called[_StubCloudRunAsyncClient.get_service.__name__] = request
        if self._raise_on_get:
            raise ValueError
        return self._service

    async def update_service(self, request: Dict[str, Any]) -> Any:
        self.called[_StubCloudRunAsyncClient.update_service.__name__] = request
        if self._raise_on_update:
            raise ValueError
        return self._update_operation


@pytest.mark.asyncio
async def test_get_service_nok_raises(monkeypatch):
    # Given
    client = _StubCloudRunAsyncClient(raise_on_get=True)
    monkeypatch.setattr(cloud_run, cloud_run._run_client.__name__, lambda: client)
    # When/Then
    with pytest.raises(cloud_run.CloudRunServiceError):
        await cloud_run.get_service(_TEST_SERVICE_NAME)
    # Then:called
    request = client.called.get(_StubCloudRunAsyncClient.get_service.__name__)
    assert isinstance(request, dict)
    assert request.get("name") == _TEST_SERVICE_NAME


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reconciling,raise_on_get,expected",
    [
        (False, False, True),  # all good
        (True, False, False),  # reconciling is True
        (False, True, False),  # get_service() raises exception
    ],
)
async def test_can_be_deployed_ok(
    monkeypatch, reconciling: bool, raise_on_get: bool, expected: bool
):
    # Given
    client = _StubCloudRunAsyncClient(
        service=_StubCloudRunService(path="reconciling", value=reconciling),
        raise_on_get=raise_on_get,
    )
    monkeypatch.setattr(cloud_run, cloud_run._run_client.__name__, lambda: client)
    # When
    result, _ = await cloud_run.can_be_deployed(_TEST_SERVICE_NAME)
    # Then
    assert result == expected


@pytest.mark.asyncio
async def test_update_service_ok(monkeypatch):
    # Given
    path = "root.attr.sub_attr"
    value = "TEST_VALUE"
    service = _StubCloudRunService(path=path, value=f"NOT_{value}")
    update_operation = _StubCloudRunAsyncOperation(value=service)
    client = _StubCloudRunAsyncClient(
        service=service,
        update_operation=update_operation,
    )
    monkeypatch.setattr(cloud_run, cloud_run._run_client.__name__, lambda: client)
    monkeypatch.setattr(
        cloud_run, cloud_run._create_update_request.__name__, lambda x: {"service": x}
    )
    # When
    result = await cloud_run.update_service(
        name=_TEST_SERVICE_NAME, path=path, value=value
    )
    # Then
    assert result.root.attr.sub_attr == value
    assert client.called.get(_StubCloudRunAsyncClient.get_service.__name__)
    assert update_operation.called.get(_StubCloudRunAsyncOperation.result.__name__)
    request = client.called.get(_StubCloudRunAsyncClient.update_service.__name__)
    assert request.get("service") == service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raise_on_get,raise_on_update,raise_on_result",
    [
        (True, False, False),  # raise on get
        (False, True, False),  # raise on update
        (False, False, True),  # raise on result
    ],
)
async def test_update_service_nok_raises(
    monkeypatch, raise_on_get: bool, raise_on_update: bool, raise_on_result: bool
):
    # Given
    path = "root.attr.sub_attr"
    value = "TEST_VALUE"
    service = _StubCloudRunService(path=path, value=f"NOT_{value}")
    update_operation = _StubCloudRunAsyncOperation(
        value=service, raise_on_result=raise_on_result
    )
    client = _StubCloudRunAsyncClient(
        service=service,
        update_operation=update_operation,
        raise_on_get=raise_on_get,
        raise_on_update=raise_on_update,
    )
    monkeypatch.setattr(cloud_run, cloud_run._run_client.__name__, lambda: client)
    monkeypatch.setattr(
        cloud_run, cloud_run._create_update_request.__name__, lambda x: {"service": x}
    )
    # When/Then
    with pytest.raises(cloud_run.CloudRunServiceError):
        await cloud_run.update_service(name=_TEST_SERVICE_NAME, path=path, value=value)


@pytest.mark.parametrize(
    "value,amount_errors",
    [
        (123, 1),
        (None, 1),
        ("", 1),
        ("projects/ /locations/my-location-123/services/my-service-123", 1),
        ("projects/my-project-123/locations/ /services/my-service-123", 1),
        ("projects/my-project-123/locations/my-location-123/services/ ", 1),
        (
            " projects/my-project-123/locations/my-location-123/services/my-service-123",
            1,
        ),
        (
            "projects/my project 123/locations/my location 123/services/my service 123",
            1,
        ),
        (
            "projects/my-project-123/locations/my-location-123/services/my-service-123",
            0,
        ),
    ],
)
def test_validate_cloud_run_resource_name_ok(value: str, amount_errors: int):
    # Given/When
    result = cloud_run.validate_cloud_run_resource_name(value, raise_if_invalid=False)
    # Then
    assert len(result) == amount_errors


def _create_object_from_value(value: Any) -> Any:
    result = value
    if isinstance(value, dict):
        result = types.SimpleNamespace()
        for k, v in value.items():
            setattr(result, k, _create_object_from_value(v))
    return result


@pytest.mark.parametrize(
    "value,path,expected_attr_val",
    [
        (
            _create_object_from_value(dict(root=dict(node=dict(value=123)))),
            "root.node.value",
            123,
        ),
        (
            _create_object_from_value(
                dict(root=dict(node_a=dict(value=123), node_b=dict(value=321)))
            ),
            "root.node_a.value",
            123,
        ),
    ],
)
def test__get_parent_node_attribute_based_on_path_ok(
    value: Any, path: str, expected_attr_val: Any
):
    res_node, res_attr = cloud_run._get_parent_node_attribute_based_on_path(value, path)
    assert isinstance(res_node, object)
    assert getattr(res_node, res_attr) == expected_attr_val


def test__set_service_value_by_path_ok():
    # pylint: disable=no-member
    # Given
    expected = "TEST_VALUE"
    service = _StubCloudRunService("a.b", f"NOT_{expected}")
    # When
    result = cloud_run._set_service_value_by_path(service, "a.b", expected)
    # Then
    assert result.a.b == expected


def test__clean_service_for_update_request_ok():
    # Given
    service = _StubCloudRunService("a", "value_a")
    # When
    result = cloud_run._clean_service_for_update_request(service)
    # Then
    for attr in cloud_run_const.CLOUD_RUN_UPDATE_REQUEST_SERVICE_PATHS_TO_REMOVE:
        assert getattr(result, attr, "TEST") is None


def test__update_service_revision_ok():
    # Given
    curr_revision = "current_revision"
    service = _StubCloudRunService(
        cloud_run_const.CLOUD_RUN_SERVICE_REVISION_PATH, curr_revision
    )
    # When
    cloud_run._update_service_revision(service)
    # Then
    node, attr_name = cloud_run._get_parent_node_attribute_based_on_path(
        service, cloud_run_const.CLOUD_RUN_SERVICE_REVISION_PATH
    )
    assert getattr(node, attr_name) != curr_revision


def test__create_revision_ok():
    # Given
    simple_name = "simple_name"
    name = f"projects/project/location/location/services/{simple_name}"
    # When
    result = cloud_run._create_revision(name)
    # Then
    assert result.startswith(cloud_run._CLOUD_RUN_REVISION_TMPL.format(simple_name, ""))


def test__validate_service_ok():
    path = "a.b.c"
    value = 123
    service = _StubCloudRunService(path, value)
    # When
    result = cloud_run._validate_service(service, path, value, raise_if_invalid=True)
    # Then
    assert result == service


def test__validate_service_nok():
    path = "a.b.c"
    value = 123
    service = _StubCloudRunService(path, f"NOT_{value}")
    # When/Then
    with pytest.raises(RuntimeError):
        cloud_run._validate_service(service, path, value, raise_if_invalid=True)
