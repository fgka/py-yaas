# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Navigates objects or dictionaries using `x-path`_.

.. _x-path: https://en.wikipedia.org/wiki/XPath
"""
from typing import Any, Dict, Tuple

###########################
#  Update Request: paths  #
###########################

REQUEST_PATH_SEP: str = "."


def get_parent_node_based_on_path(value: Any, path: str) -> Tuple[Any, str]:
    """

    Args:
        value: either an py:class:`object` or a py:class:`dict`.
        path: `x-path`_ like path.

    Returns:

    """
    # input validation
    _validate_path(path)
    # logic
    path = path.strip()
    if isinstance(value, dict):
        result = _get_parent_node_attribute_based_on_path_dict(value, path)
    else:
        result = _get_parent_node_attribute_based_on_path_object(value, path)
    return result


def _validate_path(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(
            f"Path argument must be a non-empty string. Got: <{value}>({type(value)})"
        )


def _get_parent_node_attribute_based_on_path_object(
    value: Any, path: str
) -> Tuple[Any, str]:
    result = value
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = getattr(result, entry)
    return result, split_path[-1]


def _get_parent_node_attribute_based_on_path_dict(
    value: Dict[str, Any], path: str
) -> Tuple[Any, str]:
    result = value
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = result.get(entry, {})
    return result, split_path[-1]


def create_dict_based_on_path(path: str, value: Any) -> Dict[str, Any]:
    """
    Will create a :py:class:`dict` based on the `path` and `value`.
    Example::
        path = "root.node.subnode"
        value = [1, 2, 3]
        result = create_dict_based_on_path(path, value)
        result = {
            "root": {
                "node": {
                    "subnode": [1, 2, 3]
                }
            }
        }
    Args:
        path:
        value:

    Returns:

    """
    # input validation
    _validate_path(path)
    # logic
    result = {}
    node = result
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        node[entry] = {}
        node = node[entry]
    node[split_path[-1]] = value
    return result
