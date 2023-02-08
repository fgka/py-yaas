# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Navigates objects or dictionaries using `x-path`_.

.. _x-path: https://en.wikipedia.org/wiki/XPath
"""
from typing import Any, Tuple

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
    if value is None:
        raise TypeError(f"Value argument must be an object or dictionary. Got: <{value}>({type(value)})")
    if not isinstance(path, str) or not path:
        raise TypeError(f"Path argument must be a non-empty string. Got: <{path}>({type(path)})")
    # logic
    if isinstance(value, dict):
        result = _get_parent_node_attribute_based_on_path_dict(value, path)
    else:
        result = _get_parent_node_attribute_based_on_path_dict(value, path)
    return result


def _get_parent_node_attribute_based_on_path_object(value: Any, path: str) -> Tuple[Any, str]:
    result = value
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = getattr(result, entry)
    return result, split_path[-1]


def _get_parent_node_attribute_based_on_path_dict(value: Any, path: str) -> Tuple[Any, str]:
    result = value
    split_path = path.split(REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = result.get(entry, {})
    return result, split_path[-1]
