# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,no-self-use,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any, Dict
import types

import pytest

from yaas import const
from yaas.gcp import cloud_run

_TEST_SERVICE_NAME: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)


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
