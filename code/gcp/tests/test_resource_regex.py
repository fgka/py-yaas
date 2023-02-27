# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, List

import pytest

from yaas_gcp import resource_regex, resource_regex_const

_TEST_INVALID_VALUE_TYPES: List[Any] = [None, 123, {}, []]

_TEST_PROJECT: str = "my_project"
_TEST_LOCATION: str = "my_location"
# Cloud Run
_TEST_CLOUD_RUN_SERVICE: str = "my_service"
_TEST_CLOUD_RUN_CANONICAL: str = (
    resource_regex_const.CLOUD_RUN_RESOURCE_NAME_TMPL.format(
        _TEST_PROJECT, _TEST_LOCATION, _TEST_CLOUD_RUN_SERVICE
    )
)
_TEST_CLOUD_RUN_TERRAFORM_TMPL: str = "locations/{1:}/namespaces/{0:}/services/{2:}"
_TEST_CLOUD_RUN_TERRAFORM: str = _TEST_CLOUD_RUN_TERRAFORM_TMPL.format(
    _TEST_PROJECT, _TEST_LOCATION, _TEST_CLOUD_RUN_SERVICE
)
_TEST_CLOUD_RUN_SIMPLE_TMPL: str = "CloudRun {2:} @ {0:} {1:}"
_TEST_CLOUD_RUN_SIMPLE: str = _TEST_CLOUD_RUN_SIMPLE_TMPL.format(
    _TEST_PROJECT, _TEST_LOCATION, _TEST_CLOUD_RUN_SERVICE
)
# Cloud SQL
_TEST_CLOUD_SQL_INSTANCE: str = "my_instance"
_TEST_CLOUD_SQL_CANONICAL: str = (
    resource_regex_const.CLOUD_SQL_RESOURCE_NAME_TMPL.format(
        _TEST_PROJECT, _TEST_LOCATION, _TEST_CLOUD_SQL_INSTANCE
    )
)
_TEST_CLOUD_SQL_SIMPLE_TMPL: str = "CloudSql {2:} @ {0:} {1:}"
_TEST_CLOUD_SQL_SIMPLE: str = _TEST_CLOUD_SQL_SIMPLE_TMPL.format(
    _TEST_PROJECT, _TEST_LOCATION, _TEST_CLOUD_SQL_INSTANCE
)


@pytest.mark.parametrize("value", _TEST_INVALID_VALUE_TYPES)
def test_parse_cloud_run_nok(value: str):
    # Given/When/Then
    with pytest.raises(TypeError):
        resource_regex.CLOUD_RUN_PARSER.canonical(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", None),
        # Cloud Run strings
        (_TEST_CLOUD_RUN_CANONICAL, _TEST_CLOUD_RUN_CANONICAL),
        (_TEST_CLOUD_RUN_TERRAFORM, _TEST_CLOUD_RUN_CANONICAL),
        (_TEST_CLOUD_RUN_SIMPLE, _TEST_CLOUD_RUN_CANONICAL),
        # Cloud SQL strings
        (_TEST_CLOUD_SQL_CANONICAL, None),
        (_TEST_CLOUD_SQL_SIMPLE, None),
    ],
)
def test_parse_cloud_run_ok(value: str, expected: str):
    # Given/When
    result = resource_regex.CLOUD_RUN_PARSER.canonical(value)
    # Then
    assert result == expected


@pytest.mark.parametrize("value", _TEST_INVALID_VALUE_TYPES)
def test_parse_cloud_sql_nok(value: str):
    # Given/When/Then
    with pytest.raises(TypeError):
        resource_regex.CLOUD_SQL_PARSER.canonical(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", None),
        # Cloud Run strings
        (_TEST_CLOUD_RUN_CANONICAL, None),
        (_TEST_CLOUD_RUN_TERRAFORM, None),
        (_TEST_CLOUD_RUN_SIMPLE, None),
        # Cloud SQL strings
        (_TEST_CLOUD_SQL_CANONICAL, _TEST_CLOUD_SQL_CANONICAL),
        (_TEST_CLOUD_SQL_SIMPLE, _TEST_CLOUD_SQL_CANONICAL),
    ],
)
def test_parse_cloud_sql_ok(value: str, expected: str):
    # Given/When
    result = resource_regex.CLOUD_SQL_PARSER.canonical(value)
    # Then
    assert result == expected
