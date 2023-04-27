# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Common input validation."""
from typing import Any, List, Optional, Tuple


def validate_path_value_lst(value: List[Tuple[str, Optional[Any]]]) -> None:
    """Checks if argument is a non-empty :py:class:`list` of
    :py:class:`tuple`s.

    Args:
        value:

    Returns:
    """
    if not isinstance(value, list) or not value:
        raise TypeError(
            f"Path and value list must be a non-empty instance of {list.__name__}. Got: <{value}>({type(value)}"
        )
    for ndx, path_value in enumerate(value):
        path, _ = path_value
        if not isinstance(path, str) or not path.strip():
            raise TypeError(
                f"Path argument must be a non-empty {str.__name__}. "
                f"Got: <{path}>[{ndx}]({type(path)}. "
                f"All items: <{value}>"
            )
