# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definitions for supporting scalers.
"""
import abc
import re
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
        if not self._is_parameter_value_valid(value):
            raise TypeError(
                f"Attribute {attribute.name} cannot accept value <{value}>({type(value)})"
            )

    @target.validator
    def _validate_target(self, attribute: attrs.Attribute, value: Any) -> None:
        self._is_target_valid(attribute.name, value)

    def _is_parameter_value_valid(self, value: Any) -> bool:
        """
        To be overwritten by child class
        """
        return value is not None

    def _is_target_valid(self, name: str, value: Any) -> None:
        expected_type = self._target_type()
        # pylint: disable=isinstance-second-argument-not-valid-type
        if expected_type is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"Attribute {name} must be an {expected_type.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        if not self._is_target_value_valid(value):
            raise ValueError(
                f"Attribute {name} value is not valid. Check implementation of "
                f"{self.__class__.__name__}.{ScalingCommand._is_target_valid.__name__}. "
                f"Got <{value}>({type(value)})"
            )

    @staticmethod
    def _target_type() -> type:
        """
        To be overwritten by child class. The default, :py:obj:`None` means any type.
        """
        return None

    def _is_target_value_valid(self, value: Any) -> bool:
        """
        To be overwritten by child class
        """
        return value is not None

    @classmethod
    def from_command_str(cls, value: str) -> "ScalingCommand":
        """
        Parse the command :py:cls:`str` into an instance of :py:cls:`ScalingCommand`.

        Args:
            value:
        """
        regex = cls._parameter_target_regex()
        match = regex.match(value)
        if match:
            parameter_target = match.groups()
            if len(parameter_target) > 1:
                parameter, target = parameter_target
            else:
                parameter = parameter_target[0]
                target = None
            try:
                target = cls._convert_target_value_string(target)
            except Exception as err:
                raise ValueError(
                    f"Could not convert target value string <{target}> to expected type using "
                    f"{cls.__name__}.{cls._convert_target_value_string.__name__}(). "
                    f"Error: {err}"
                ) from err
            result = cls(parameter=parameter, target=target)
        else:
            raise ValueError(
                f"Command value must comply with {regex}. "
                f"Got: <{value}>({type(value)})"
            )
        return result

    @classmethod
    def _convert_target_value_string(cls, value: str) -> Any:
        """
        To be overwritten by child classes to appropriate type
        """
        return value

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
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
        err_msg = (
            f"Attribute <{attribute.name}> "
            f"is not a valid resource ID for <{self.__class__.__name__}>. "
            f"Got: <{value}>({type(value)})"
        )
        try:
            result = self._is_resource_valid(value)
        except Exception as err:  # pylint: disable=broad-except
            raise ValueError(err_msg) from err
        if not result:
            raise ValueError(err_msg)

    def _is_resource_valid(self, value: str) -> bool:
        """
        To be overwritten by child class
        """
        return value is not None

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
