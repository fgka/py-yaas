# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Navigates objects or dictionaries using `x-path`_.

.. _x-path: https://en.wikipedia.org/wiki/XPath
"""
from typing import Any, Dict, List, Optional, Tuple

from yaas_common import validation

###########################
#  Update Request: paths  #
###########################

REQUEST_PATH_SEP: str = "."


def get_parent_node_based_on_path(value: Any, path: str) -> Tuple[Any, str]:
    """Returns the node and the last key in the path. Example with a
    :py:class:`dict`::

        value = {
            "root": {
                "node_a": 123,
                "node_b": "value_b",
            }
        }
        node, key = get_parent_node_based_on_path(value, "root.node_a")
        assert node == "node_a"
        assert node.get(key) == 123

    Example with an :py:class:`object`::

        node, key = get_parent_node_based_on_path(value, "root.node_a")
        assert node == "node_a"
        assert getattr(node, key) == 123

    Args:
        value: either an :py:class:`object` or a :py:class:`dict`.
        path: `x-path`_ like path.

    Returns: :py:class:`tuple` in the format:
        ``<node containing the last key in the path>, <last key in the path>``
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
        raise TypeError(f"Path argument must be a non-empty string. Got: <{value}>({type(value)})")


def _get_parent_node_attribute_based_on_path_object(  # pylint: disable=invalid-name
    value: Any, path: str
) -> Tuple[Any, str]:
    result = value
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = getattr(result, entry)
    return result, split_path[-1]


def _get_parent_node_attribute_based_on_path_dict(  # pylint: disable=invalid-name
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
    return create_dict_based_on_path_value_lst([(path, value)])


def create_dict_based_on_path_value_lst(  # pylint: disable=invalid-name
    path_value_lst: List[Tuple[str, Optional[Any]]]
) -> Dict[str, Any]:
    """
    Same as :py:func:`create_dict_based_on_path` but multiple times over the same :py:class:`dict`
    Args:
        path_value_lst: list of tuples ``[(<path>,<value>,)]``

    Returns:

    """
    # input validation
    validation.validate_path_value_lst(path_value_lst)
    # logic
    result = {}
    for path, value in path_value_lst:
        result = _create_dict_based_on_path(result, path, value)
    return result


def _create_dict_based_on_path(result: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
    node = result
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        if entry not in node:
            node[entry] = {}
        node = node[entry]
    node[split_path[-1]] = value
    return result
