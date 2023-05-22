# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Basic definition for resource parsers using regular expressions."""
import re
from typing import Any, List, Optional, Tuple

import attrs

from yaas_common import const, dto_defaults
from yaas_gcp import resource_regex_const


class ResourceType(dto_defaults.EnumWithFromStrIgnoreCase):
    """Supported Google Cloud resource type."""

    CLOUD_RUN = "run"
    CLOUD_SQL = "sql"


@attrs.define(**const.ATTRS_DEFAULTS)
class ResourceRegex(dto_defaults.HasFromJsonString):
    """A specific regex parser to a specific resource type."""

    regex: re.Pattern = attrs.field(validator=attrs.validators.instance_of(re.Pattern))
    prj_loc_name_order: Tuple[int] = attrs.field(validator=attrs.validators.instance_of(tuple))

    @prj_loc_name_order.validator
    def _validate_prj_loc_name_order(self, attribute: attrs.Attribute, value: Any) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"Attribute {attribute.name} must be a {tuple.__name__}. Got: '{value}'({type(value)})")
        if len(value) != 3:
            raise ValueError(
                f"Attribute {attribute.name} must be a {tuple.__name__} with exactly 3 items. "
                f"Got: '{value}'[{len(value)}]"
            )
        for ndx, val in enumerate(value):
            if val < 0 or val > 2:
                raise ValueError(
                    f"Values for attribute {attribute.name} must be a be in the range of [0, 2]. "
                    f"Got: '{val}'[{ndx}] in '{value}'"
                )

    def prj_loc_name(self, value: str) -> Optional[Tuple[str, str, str]]:
        """
        Returns a tuple in the format::
            project, location, name = resource_regex.prj_loc_name("some string")
        Args:
            value: string to be parsed by the underlying regex.

        Returns:
            :py:obj:`None` if cannot be parsed.
        """
        # validate input
        if not isinstance(value, str):
            raise TypeError(f"Argument must be a {str.__name__} instance. Got: '{value}'({type(value)})")
        # logic
        result = None
        match = self.regex.match(value)
        if match:
            tokens = list(match.groups())
            result = (
                tokens[self.prj_loc_name_order[0]],
                tokens[self.prj_loc_name_order[1]],
                tokens[self.prj_loc_name_order[2]],
            )
        return result


@attrs.define(**const.ATTRS_DEFAULTS)
class ResourceRegexParser(dto_defaults.HasFromJsonString):
    """Aggregate multiple regexes to parse the same type of resource."""

    regex_lst: List[ResourceRegex] = attrs.field(
        validator=attrs.validators.deep_iterable(member_validator=attrs.validators.instance_of(ResourceRegex)),
    )
    canonical_form_tmpl: str = attrs.field(validator=attrs.validators.instance_of(str))
    type: ResourceType = attrs.field(validator=attrs.validators.instance_of(ResourceType))

    def prj_loc_name(self, value: str) -> Optional[Tuple[str, str, str]]:
        """
        Returns a tuple in the format::
            project, location, name = resource_regex_parser.prj_loc_name("some string")
        Args:
            value: string to be parsed by any of the underlying regex.

        Returns:
            :py:obj:`None` if cannot be parsed.
        """
        result = None
        for regex in self.regex_lst:
            result = regex.prj_loc_name(value)
            if result is not None:
                break
        return result

    def canonical(self, value: str) -> Optional[str]:
        """If the value is valid, will return the canonical string representing
        the resource.

        Args:
            value:

        Returns:
        """
        result = None
        parsed = self.prj_loc_name(value)
        if parsed is not None:
            result = self.canonical_form_tmpl.format(*parsed)
        return result


CLOUD_RUN_CANONICAL_REGEX: ResourceRegex = ResourceRegex(
    regex=resource_regex_const.FQN_CLOUD_RUN_RESOURCE_REGEX,
    prj_loc_name_order=resource_regex_const.FQN_CLOUD_RUN_RESOURCE_REGEX_ORDER,
)
CLOUD_RUN_PARSER: ResourceRegexParser = ResourceRegexParser(
    regex_lst=[
        CLOUD_RUN_CANONICAL_REGEX,
        ResourceRegex(
            regex=resource_regex_const.FQN_CLOUD_RUN_TERRAFORM_RESOURCE_REGEX,
            prj_loc_name_order=resource_regex_const.FQN_CLOUD_RUN_TERRAFORM_RESOURCE_REGEX_ORDER,
        ),
        ResourceRegex(
            regex=resource_regex_const.SIMPLE_CLOUD_RUN_RESOURCE_REGEX,
            prj_loc_name_order=resource_regex_const.SIMPLE_CLOUD_RUN_RESOURCE_REGEX_ORDER,
        ),
    ],
    type=ResourceType.CLOUD_RUN,
    canonical_form_tmpl=resource_regex_const.CLOUD_RUN_RESOURCE_NAME_TMPL,
)

CLOUD_SQL_CANONICAL_REGEX: ResourceRegex = ResourceRegex(
    regex=resource_regex_const.FQN_CLOUD_SQL_RESOURCE_REGEX,
    prj_loc_name_order=resource_regex_const.FQN_CLOUD_SQL_RESOURCE_REGEX_ORDER,
)
CLOUD_SQL_PARSER: ResourceRegexParser = ResourceRegexParser(
    regex_lst=[
        CLOUD_SQL_CANONICAL_REGEX,
        ResourceRegex(
            regex=resource_regex_const.SIMPLE_CLOUD_SQL_RESOURCE_REGEX,
            prj_loc_name_order=resource_regex_const.SIMPLE_CLOUD_SQL_RESOURCE_REGEX_ORDER,
        ),
    ],
    type=ResourceType.CLOUD_SQL,
    canonical_form_tmpl=resource_regex_const.CLOUD_SQL_RESOURCE_NAME_TMPL,
)
