# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,invalid-name
# type: ignore
import types
from typing import Any

import pytest

from yaas_common import xpath


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


def test_create_dict_based_on_path_value_lst_ok():
    # Given
    path_value_lst = [
        (
            "root.node_a",
            "value_a",
        ),
        (
            "root.node_b",
            "value_b",
        ),
    ]
    for ndx in range(10):
        path_value_lst.append(
            (
                f"root.node_c_{ndx}",
                f"value_c_{ndx}",
            )
        )
    # When
    result = xpath.create_dict_based_on_path_value_lst(path_value_lst)
    # Then: result
    assert isinstance(result, dict)
    # Then: path_value_lst
    for path, value in path_value_lst:
        node, key = xpath.get_parent_node_based_on_path(result, path)
        assert node.get(key) == value


@pytest.mark.parametrize(
    "value,path,expected_attr_val",
    [
        (
            _create_object_from_value(dict(root=dict(node=dict(value=123)))),
            "root.node.value",
            123,
        ),
        (
            _create_object_from_value(dict(root=dict(node_a=dict(value=123), node_b=dict(value=321)))),
            "root.node_a.value",
            123,
        ),
    ],
)
def test_get_parent_node_based_on_path_ok_object(value: Any, path: str, expected_attr_val: Any):
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
def test_get_parent_node_based_on_path_ok_dict(value: Any, path: str, expected_attr_val: Any):
    res_node, res_attr = xpath.get_parent_node_based_on_path(value, path)
    assert isinstance(res_node, dict)
    assert res_node.get(res_attr) == expected_attr_val
