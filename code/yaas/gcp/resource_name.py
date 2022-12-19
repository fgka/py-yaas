# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Validates Google Cloud resource names that are, in general, in the format::
    "token[0]/value[0]/token[1]/value[1]/token[2]/value[2]"
"""
import re
from typing import List


# pylint: disable=anomalous-backslash-in-string
_TOKEN_REGEX: re.Pattern = re.compile("^[^/\s]+$")
_TOKEN_VALUE_REGEX_STR: str = "([^/\\s]+)"
# pylint: enable=anomalous-backslash-in-string


def validate_resource_name(
    *, value: str, tokens: List[str], raise_if_invalid: bool = True
) -> List[str]:
    """
    Validates the ``value`` against the pattern:
        "token[0]/value[0]/token[1]/value[1]/token[2]/value[2]".

    Args:
        value: Resource name to be validated.
        tokens: Which are the resource tokens,
            like: ``["projects", "locations", "services"]`` for Cloud Run.
        raise_if_invalid: if :py:obj:`True` will raise exception if ``value`` is not valid.

    Returns:
        If ``raise_if_invalid`` if :py:obj:`False` will contain all reasons
            why the validation failed.
    """
    result = []
    # validate input
    if not isinstance(value, str):
        result.append(
            f"Name <{value}>({type(str)}) must be an instance of {str.__name__}"
        )
    if not isinstance(tokens, list):
        result.append(
            f"Tokens <{tokens}>({type(str)}) must be an instance of {list.__name__}"
        )
    if not result:
        token_validation = []
        for tkn in tokens:
            token_validation.extend(_validate_token(tkn))
        if token_validation:
            result.append(
                f"Could not validate tokens <{tokens}>. Error(s): {token_validation}"
            )
        else:
            result.extend(_validate_resource_name(value, tokens))
    if result and raise_if_invalid:
        raise ValueError(
            f"Could not validate Secret name <{value}>. Error(s): {result}"
        )
    return result


def _validate_token(token: str) -> List[str]:
    result = []
    if not isinstance(token, str):
        result.append(
            f"Token <{token}>({type(token)}) must be an instance of {str.__name__}"
        )
    elif not _TOKEN_REGEX.match(token):
        result.append(
            f"Token must comply with regular expression: {_TOKEN_REGEX.pattern}. Got <{token}>"
        )
    return result


def _validate_resource_name(value: str, tokens: List[str]) -> List[str]:
    result = []
    resource_name_regex = _create_resource_name_regex(tokens)
    error_msg_pattern = _create_error_msg_pattern(tokens)
    matched = resource_name_regex.match(value)
    if matched is None:
        result.append(
            f"Name must obey the format: '{error_msg_pattern}'. " f"Got <{value}>"
        )
    else:
        # validate individual tokens
        token_values = list(matched.groups())
        if len(token_values) != len(tokens):
            result.append(
                f"The amount of values {len(token_values)} is not same as tokens {len(tokens)}. "
                f"Tokens: {tokens}. "
                f"Values: {token_values}"
            )
        for tkn, tkn_val in zip(tokens, token_values):
            if not tkn_val:
                result.append(
                    f"Could not find value for '{tkn}' in <{value}> "
                    f"assuming pattern {error_msg_pattern}"
                )
    return result


def _create_resource_name_regex(tokens: List[str]) -> re.Pattern:
    pattern_lst = []
    for tkn in tokens:
        pattern_lst.append(f"{tkn}/{_TOKEN_VALUE_REGEX_STR}")
    pattern_str = "/".join(pattern_lst)
    result = re.compile(f"^{pattern_str}$")
    return result


def _create_error_msg_pattern(tokens: List[str]) -> str:
    fmt_err_msg_lst = []
    for tkn in tokens:
        fmt_err_msg_lst.append(f"{tkn}/{{{{{_simple_plural_to_id(tkn)}}}}}")
    result = "/".join(fmt_err_msg_lst)
    return result


def _simple_plural_to_id(token: str) -> str:
    """
    It assumes the argument is an ``s`` terminated string, if plural,
        and adds ``_id`` to its singular form.
    Examples:
        * projects -> project_id
        * secrets -> secret_id
        * flies -> flie_id <<<< where it breaks
        * teeth -> teeth_id <<<< where it breaks
    """
    if token.endswith("s"):
        token = token[:-1]
    return f"{token}_id"
