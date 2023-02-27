# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,invalid-name
# pylint: disable=attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
import re
from typing import List

import pytest

from yaas.gcp import resource_name


@pytest.mark.parametrize(
    "value,tokens,amount",
    [
        (None, None, 2),
        ("token", [], 1),
        ("", [], 0),
        (None, "tokens", 2),
        (None, ["tokens"], 1),
        ("tokens/my-token-123/", ["tokens"], 1),
        ("/tokens/my-token-123", ["tokens"], 1),
        ("tokens/my/token-123", ["tokens"], 1),
        ("tokens/my token-123", ["tokens"], 1),
        ("tokens/my-token-123", ["tokens"], 0),
        (  # Cloud Run
            "projects/my-project-123/locations/my-location-123/services/my-service-123",
            ["projects", "locations", "services"],
            0,
        ),
        (  # Secrets
            "projects/my-project-123/secrets/my-secret-123/versions/my-version-123",
            ["projects", "secrets", "versions"],
            0,
        ),
    ],
)
def test_validate_resource_name_ok(value: str, tokens: List[str], amount: int):
    # Given/When
    result = resource_name.validate_resource_name(
        value=value, tokens=tokens, raise_if_invalid=False
    )
    # Then
    assert isinstance(result, list)
    res_str = "@@".join(result)
    assert len(result) == amount, f"Got: {res_str}"


def test_validate_resource_name_nok_raise():
    with pytest.raises(ValueError):
        resource_name.validate_resource_name(
            value=None, tokens=[], raise_if_invalid=True
        )


@pytest.mark.parametrize(
    "token,amount",
    [
        (None, 1),
        ("", 1),
        ("token", 0),
        (" token", 1),
        ("token ", 1),
        ("token", 0),
        ("token-123", 0),
        ("token_123", 0),
        ("123_token", 0),
    ],
)
def test__validate_token_ok(token: str, amount: int):
    # Given/When
    result = resource_name._validate_token(token)
    # Then
    assert isinstance(result, list)
    assert len(result) == amount


@pytest.mark.parametrize(
    "value,tokens,amount",
    [
        ("my_token_values/my_token_value_id", ["my_token_values"], 0),
        (" my_token_values/my_token_value_id", ["my_token_values"], 1),
        ("my_token_values/my_token_value_id ", ["my_token_values"], 1),
        ("my_token_values/my_token_value id", ["my_token_values"], 1),
        ("my_token_values/my_token_value_id/", ["my_token_values"], 1),
        ("/my_token_values/my_token_value_id", ["my_token_values"], 1),
        ("my_token_values /my_token_value_id", ["my_token_values"], 1),
        (  # Cloud Run
            "projects/my-project-123/locations/my-location-123/services/my-service-123",
            ["projects", "locations", "services"],
            0,
        ),
        (  # Secrets
            "projects/my-project-123/secrets/my-secret-123/versions/my-version-123",
            ["projects", "secrets", "versions"],
            0,
        ),
    ],
)
def test__validate_resource_name_ok(value: str, tokens: List[str], amount: int):
    # Given/When
    result = resource_name._validate_resource_name(value, tokens)
    # Then
    assert isinstance(result, list)
    assert len(result) == amount


@pytest.mark.parametrize(
    "tokens,expected",
    [
        (
            ["projects", "locations", "services"],
            "^projects/([^/\\s]+)/locations/([^/\\s]+)/services/([^/\\s]+)$",
        ),
        (
            ["projects", "secrets", "versions"],
            "^projects/([^/\\s]+)/secrets/([^/\\s]+)/versions/([^/\\s]+)$",
        ),
    ],
)
def test__create_resource_name_regex_ok(tokens: List[str], expected: str):
    # Given/When
    result = resource_name._create_resource_name_regex(tokens)
    # Then
    assert isinstance(result, re.Pattern)
    assert result.pattern == expected


@pytest.mark.parametrize(
    "tokens,expected",
    [
        (
            ["projects", "locations", "services"],
            "projects/{{project_id}}/locations/{{location_id}}/services/{{service_id}}",
        ),
        (
            ["projects", "secrets", "versions"],
            "projects/{{project_id}}/secrets/{{secret_id}}/versions/{{version_id}}",
        ),
    ],
)
def test__create_error_msg_pattern_ok(tokens: List[str], expected: str):
    # Given/When
    result = resource_name._create_error_msg_pattern(tokens)
    # Then
    assert result == expected


@pytest.mark.parametrize(
    "root",
    [
        "project",
        "service",
        "location",
    ],
)
def test__simple_plural_to_id_ok_regular(root: str):
    # Given
    token = f"{root}s"
    # When
    result = resource_name._simple_plural_to_id(token)
    # Then
    assert result == f"{root}_id"


@pytest.mark.parametrize(
    "token",
    [
        "teeth",
        "feet",
        "something",
    ],
)
def test__simple_plural_to_id_ok_without_s_termination(token: str):
    # Given/When
    result = resource_name._simple_plural_to_id(token)
    # Then
    assert result == f"{token}_id"
