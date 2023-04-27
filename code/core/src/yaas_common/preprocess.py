# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Common value pre-processing and validation."""
from typing import Any, Optional

_DEFAULT_TYPE_VALUE: type = object
_DEFAULT_NAME_VALUE: str = "value"


def validate_type(
    value: Any,
    name: Optional[str] = _DEFAULT_NAME_VALUE,
    cls: Optional[type] = _DEFAULT_TYPE_VALUE,
    *,
    is_none_valid: Optional[bool] = False,
    default_value: Optional[Any] = None,
) -> Optional[Any]:
    """
    Verifies if a particular ``value`` is of the correct type.

    Args:
        value: what to test.
        name: name of the argument (for error reporting). Default: ``"value"``.
        cls: which :py:class:`type` to test against. Default: py:class:`object`
        is_none_valid: accept :py:obj:`None` as valid. Default: py:obj:`False`.
        default_value: what to return if the argument is :py:obj:`None`. Default: :py:obj:`None`.
    Returns:

    """
    result = value
    if result is None:
        result = default_value
    if not isinstance(result, cls):
        err = TypeError(
            f"Value of '{name}' must be a {cls.__name__}. Got: '{value}'({type(value)}) / '{result}'({type(result)})"
        )
        if result is None:
            if not is_none_valid:
                raise err
        else:
            raise err
    return result


def string(
    value: Any,
    name: Optional[str] = _DEFAULT_NAME_VALUE,
    *,
    strip_it: Optional[bool] = True,
    is_empty_valid: Optional[bool] = False,
    is_none_valid: Optional[bool] = False,
    default_value: Optional[Any] = None,
) -> Optional[str]:
    """
    Returns validated ``value`` argument. Behavior, in order:
    1. Check if is an instance of :py:class:`str`.
      * If it is not a :py:class:`str`, check if it is :py:obj:`None`
        and that it is acceptable (by default it does not).
    1. (By default) strip the content.
    1. Check if content is empty and if that is permitted (by default it is not).

    Args:
        value: what to test.
        name: name of the argument (for error reporting). Default: ``"value"``.
        strip_it: to strip input value. Default: py:obj:`True`.
        is_empty_valid: accept empty strings as valid. Default: py:obj:`False`.
        is_none_valid: accept :py:obj:`None` as valid. Default: py:obj:`False`.
        default_value: what to return if the argument is :py:obj:`None`. Default: :py:obj:`None`.

    Returns:
        Validated input ``value``.
    """
    # logic
    result = validate_type(value=value, name=name, cls=str, is_none_valid=is_none_valid, default_value=default_value)
    if isinstance(result, str):
        if strip_it:
            result = result.strip()
        if not result and not is_empty_valid:
            raise ValueError(
                f"Value of '{name}' must be a non-empty {str.__name__}. "
                f"Strip before checking = {strip_it}. "
                f"Got: '{value}'({type(value)}) / '{result}'({type(result)})"
            )
    return result


def integer(
    value: Any,
    name: Optional[str] = _DEFAULT_NAME_VALUE,
    *,
    lower_bound: Optional[int] = None,
    upper_bound: Optional[int] = None,
    is_none_valid: Optional[bool] = False,
    default_value: Optional[Any] = None,
) -> Optional[int]:
    """

    Args:
        value: what to test.
        name: name of the argument (for error reporting). Default: ``"value"``.
        lower_bound: minimum acceptable value. Default: py:obj:`None`.
        upper_bound: maximum acceptable value. Default: py:obj:`None`.
        is_none_valid: accept :py:obj:`None` as valid. Default: py:obj:`False`.
        default_value: what to return if the argument is :py:obj:`None`. Default: :py:obj:`None`.

    Returns:

    """
    # validate input
    if lower_bound is not None and upper_bound is not None and lower_bound > upper_bound:
        raise RuntimeError(
            f"Validation arguments for limits must obey 'lower_bound < upper_bound'. "
            f"Got: [{lower_bound}, {upper_bound}]"
        )
    result = validate_type(value=value, name=name, cls=int, is_none_valid=is_none_valid, default_value=default_value)
    if isinstance(result, int):
        if lower_bound is not None and result < lower_bound:
            raise ValueError(
                f"Argument '{name}' needs to be an {int.__name__} >= {lower_bound}. Got: '{result}'({type(result)})"
            )
        if upper_bound is not None and result > upper_bound:
            raise ValueError(
                f"Argument '{name}' needs to be an {int.__name__} <= {upper_bound}. Got: '{result}'({type(result)})"
            )
    return result
