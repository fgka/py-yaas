# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,protected-access,too-few-public-methods,invalid-name,missing-class-docstring
# type: ignore
from typing import Any

import pytest

from yaas_common import preprocess

_DEFAULT_VALUE_STR: str = "DEFAULT VALUE"
_DEFAULT_VALUE_INT: int = 123
_TEST_VALUE_STR: str = "test value"
_TEST_VALUE_INT: int = 11
_TEST_VALUE_DICT: dict = {"key": "value"}


@pytest.mark.parametrize(
    "value,cls,is_none_valid,default_value,exp_error,exp_value",
    [
        (None, str, True, None, None, None),  # is None, but should be str. None is acceptable
        (
            None,
            str,
            True,
            _DEFAULT_VALUE_STR,
            None,
            _DEFAULT_VALUE_STR,
        ),  # is None, but should be str. there is a default value
        (
            None,
            str,
            True,
            _DEFAULT_VALUE_INT,
            TypeError,
            None,
        ),  # is None, but should be str. there is a default value, of the wrong type
        (_TEST_VALUE_STR, str, False, None, None, _TEST_VALUE_STR),  # happy path
        (_TEST_VALUE_STR, str, False, _DEFAULT_VALUE_INT, None, _TEST_VALUE_STR),  # happy path
        (_TEST_VALUE_INT, int, False, None, None, _TEST_VALUE_INT),  # happy path
        (_TEST_VALUE_DICT, dict, False, None, None, _TEST_VALUE_DICT),  # happy path
        (_TEST_VALUE_INT, str, True, None, TypeError, None),  # is an int, but should be str
        (_TEST_VALUE_INT, str, False, None, TypeError, None),  # is an int, but should be str
    ],
)
def test_validate_type(value: Any, cls: type, is_none_valid: bool, default_value: Any, exp_error: type, exp_value: Any):
    try:
        result = preprocess.validate_type(
            value, "test_name", cls, is_none_valid=is_none_valid, default_value=default_value
        )
        assert result == exp_value
    except Exception as err:
        if not exp_error:
            raise err
        else:
            assert isinstance(err, exp_error)


@pytest.mark.parametrize(
    "value,strip_it,is_empty_valid,is_none_valid,default_value,exp_error,exp_value",
    [
        ("", False, True, False, None, None, ""),  # is empty and accept empty
        (" ", False, False, False, None, None, " "),  # not empty, but blank
        (None, True, False, True, None, None, None),  # None, but acceptable
        (None, False, False, False, _DEFAULT_VALUE_STR, None, _DEFAULT_VALUE_STR),  # None, but has default value
        ("", True, False, False, None, ValueError, None),  # empty and not acceptable
        (" ", True, False, False, None, ValueError, None),  # blank and not acceptable
        (None, True, True, False, None, TypeError, None),  # None and not acceptable
        (_TEST_VALUE_INT, True, True, True, _DEFAULT_VALUE_INT, TypeError, None),  # not a string and not acceptable
        (" to_strip ", True, False, False, _DEFAULT_VALUE_STR, None, "to_strip"),  # get stripped version
    ],
)
def test_string(
    value: str,
    strip_it: bool,
    is_empty_valid: bool,
    is_none_valid: bool,
    default_value: Any,
    exp_error: type,
    exp_value: Any,
):
    try:
        result = preprocess.string(
            value,
            "test_name",
            strip_it=strip_it,
            is_empty_valid=is_empty_valid,
            is_none_valid=is_none_valid,
            default_value=default_value,
        )
        assert result == exp_value
    except Exception as err:
        if not exp_error:
            raise err
        else:
            assert isinstance(err, exp_error)


@pytest.mark.parametrize(
    "value,lower_bound,upper_bound,is_none_valid,default_value,exp_error,exp_value",
    [
        (None, 2, 1, True, None, RuntimeError, None),  # lower > upper
        (None, None, None, True, None, None, None),  # is None but acceptable
        (None, None, None, False, _DEFAULT_VALUE_INT, None, _DEFAULT_VALUE_INT),  # is None but has default value
        (None, None, None, False, _DEFAULT_VALUE_STR, TypeError, None),  # is None and default value is wrong type
        (
            None,
            _DEFAULT_VALUE_INT + 1,
            _DEFAULT_VALUE_INT + 2,
            False,
            _DEFAULT_VALUE_INT,
            ValueError,
            None,
        ),  # is None and default value outside bounds
        (None, 1, 2, True, None, None, None),  # is None but acceptable
        (1, 1, 2, False, None, None, 1),  # happy path
        (2, 1, 2, False, None, None, 2),  # happy path
        (0, 1, 2, False, None, ValueError, None),  # value < lower_bound
        (3, 1, 2, False, None, ValueError, None),  # value > upper_bound
        ("1", 1, 2, False, None, TypeError, None),  # not an int
    ],
)
def test_integer(
    value: Any,
    lower_bound: int,
    upper_bound: int,
    is_none_valid: bool,
    default_value: Any,
    exp_error: type,
    exp_value: Any,
):
    try:
        result = preprocess.integer(
            value,
            "test_name",
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            is_none_valid=is_none_valid,
            default_value=default_value,
        )
        assert result == exp_value
    except Exception as err:
        if not exp_error:
            raise err
        else:
            assert isinstance(err, exp_error)
