# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any
import types

import pytest

from yaas.gcp import cloud_run, cloud_run_const

_TEST_SERVICE_NAME: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)


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


class _StubCloudRunService:
    class _StubAttr:
        pass

    def __init__(self, path: str, value: Any):
        self.name = self.__class__.__name__
        parent = self
        paths = path.split(cloud_run_const.REQUEST_PATH_SEP)
        for attr in paths[:-1]:
            setattr(parent, attr, _StubCloudRunService._StubAttr())
            parent = getattr(parent, attr)
        setattr(parent, path[-1], value)


def test__set_service_value_by_path_ok():
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
    result = cloud_run._update_service_revision(service)
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
