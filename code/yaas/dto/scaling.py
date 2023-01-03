# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definitions for supporting scalers.
"""
import abc
from typing import Any

import attrs

from yaas.dto import dto_defaults, request
from yaas import const, logger

_LOGGER = logger.get(__name__)


@attrs.define(**const.ATTRS_DEFAULTS)
class ScalingCommand(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Defines the type for a scaling command.
    """

    parameter: str = attrs.field(validator=attrs.validators.instance_of(str))
    target: Any = attrs.field(default=None)

    @parameter.validator
    def _validate_attribute(self, attribute: attrs.Attribute, value: Any) -> None:
        self._is_parameter_valid(attribute.name, value)

    @target.validator
    def _validate_target(self, attribute: attrs.Attribute, value: Any) -> None:
        self._is_target_valid(attribute.name, value)

    def _is_parameter_valid(self, name: str, value: Any) -> None:
        pass

    def _is_target_valid(self, name: str, value: Any) -> None:
        pass


@attrs.define(**const.ATTRS_DEFAULTS)
class ScalingDefinition(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Defines a DTO to hold the scaling definition.
    """

    resource: str = attrs.field(validator=attrs.validators.instance_of(str))
    command: ScalingCommand = attrs.field(
        validator=attrs.validators.instance_of(ScalingCommand)
    )
    timestamp_utc: int = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.and_(
                attrs.validators.instance_of(int), attrs.validators.gt(0)
            )
        ),
    )

    @resource.validator
    def _is_resource_valid_call(self, attribute: attrs.Attribute, value: str) -> None:
        self._is_resource_valid(attribute.name, value)

    def _is_resource_valid(self, name: str, value: str) -> None:
        pass

    @classmethod
    @abc.abstractmethod
    def from_request(cls, value: request.ScaleRequest) -> "ScalingDefinition":
        """
        Return an instance corresponding to the :py:cls:`scale_request.ScaleRequest`.

        Args:
            value: the request

        Returns:

        """


class CategoryType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    Base type for encoding supported categories.
    """
