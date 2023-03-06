# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Common input validation."""
from typing import Any, List, Optional, Tuple


def validate_path_value_lst(path_value_lst: List[Tuple[str, Optional[Any]]]) -> None:
    """Checks if argument is a non-empty :py:class:`list` of
    :py:class:`tuple`s.

    Args:
        path_value_lst:

    Returns:
    """
    if not isinstance(path_value_lst, list) or not path_value_lst:
        raise TypeError(
            f"Path and value list must be a non-empty instance of {list.__name__}. "
            f"Got: <{path_value_lst}>({type(path_value_lst)}"
        )
    for ndx, path_value in enumerate(path_value_lst):
        path, _ = path_value
        if not isinstance(path, str) or not path.strip():
            raise TypeError(
                f"Path argument must be a non-empty {str.__name__}. "
                f"Got: <{path}>[{ndx}]({type(path)}. "
                f"All items: <{path_value_lst}>"
            )
