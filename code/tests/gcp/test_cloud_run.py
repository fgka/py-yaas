# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,no-self-use,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from typing import Any

import pytest

from yaas import const
from yaas.gcp import cloud_run

_TEST_SERVICE_NAME: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)


@pytest.mark.parametrize(
    "path,value",
    [
        ("root", "value"),
        ("root.node", None),
        ("root.node_a.node_b", []),
        ("root.node_a.node_b.node_a", 123),
    ],
)
def test__dict_from_path_ok(path: str, value: Any):
    # Given/When
    result = cloud_run._dict_from_path(path, value)
    # Then
    assert isinstance(result, dict)
    # Then: deep check
    node = result
    split_path = path.split(const.REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        assert isinstance(node.get(entry), dict)
        node = node[entry]
    assert node.get(split_path[-1]) == value
