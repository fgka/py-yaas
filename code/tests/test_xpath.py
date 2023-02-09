# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any
import types

import pytest

from yaas import xpath


def _create_object_from_value(value: Any) -> Any:
    result = value
    if isinstance(value, dict):
        result = types.SimpleNamespace()
        for k, v in value.items():
            setattr(result, k, _create_object_from_value(v))
    return result


@pytest.mark.parametrize(
    "path,value",
    [
        (
            "root.node.subnode",
            [1, 2, 3],
        ),
        (
            "root.node.value",
            123,
        ),
        (
            "root.node_a.value",
            "value",
        ),
    ],
)
def test_create_dict_based_on_path_ok(path: str, value: Any):
    # Given/When
    result = xpath.create_dict_based_on_path(path, value)
    # Then
    assert isinstance(result, dict)
    node = result
    for key in path.split(xpath.REQUEST_PATH_SEP)[:-1]:
        node = node[key]
        assert isinstance(node, dict)
    assert node[path.split(xpath.REQUEST_PATH_SEP)[-1]] == value


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
def test_get_parent_node_based_on_path_ok_object(
    value: Any, path: str, expected_attr_val: Any
):
    res_node, res_attr = xpath.get_parent_node_based_on_path(value, path)
    assert isinstance(res_node, object)
    assert getattr(res_node, res_attr) == expected_attr_val


@pytest.mark.parametrize(
    "value,path,expected_attr_val",
    [
        (
            dict(root=dict(node=dict(value=123))),
            "root.node.value",
            123,
        ),
        (
            dict(root=dict(node_a=dict(value=123), node_b=dict(value=321))),
            "root.node_a.value",
            123,
        ),
    ],
)
def test_get_parent_node_based_on_path_ok_dict(
    value: Any, path: str, expected_attr_val: Any
):
    res_node, res_attr = xpath.get_parent_node_based_on_path(value, path)
    assert isinstance(res_node, dict)
    assert res_node.get(res_attr) == expected_attr_val
