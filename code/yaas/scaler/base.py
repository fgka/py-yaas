# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import abc
from typing import Any, List, Tuple

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


class Scaler(abc.ABC):
    """
    Generic class to define a scaler.
    """

    def __init__(self, definition: ScalingDefinition) -> None:
        if not isinstance(definition, ScalingDefinition):
            raise TypeError(
                f"The argument definition must be of type {ScalingDefinition.__name__}"
            )
        self._definition = definition
        super().__init__()

    @property
    def definition(self) -> ScalingDefinition:
        """
        Scaling definition.

        Returns:
            Scaling definition.
        """
        return self._definition

    @classmethod
    @abc.abstractmethod
    def from_request(cls, value: request.ScaleRequest) -> "Scaler":
        """
        Return an instance corresponding to the :py:cls:`scale_request.ScaleRequest`.

        Args:
            value: scaling request.

        Returns:
            ``value`` converted to a py:cls:`Scaler`.
        """

    async def enact(self) -> bool:
        """
        Apply the required scaling command onto the given resource.

        Returns:
            :py:obj:`True` if successfully enacted.
        """
        result = False
        can_enact, reason = await self.can_enact()
        if can_enact:
            await self._safe_enact()
            result = True
        else:
            _LOGGER.warning(
                "Resource is not ready to enact scaling specified in <%s>. "
                "Reason: <%s>. "
                "Check logs for details.",
                self._definition,
                reason,
            )
        return result

    @abc.abstractmethod
    async def _safe_enact(self) -> None:
        """
        When this is call, :py:meth:`can_enact` has been called.
        """

    @abc.abstractmethod
    async def can_enact(self) -> Tuple[bool, str]:
        """
        Informs if the resource is ready for enacting the scaling.
        Reasons for returning :py:obj:`False` are:
        - It does not exist (has not been deployed yet or no longer exists);
        - It is in a non-ready or non-healthy state (currently being deployed or destroyed).

        Returns:
            A tuple in the form ``(<can_enact: bool>, <reason for False: str>)``.
        """


class CategoryTypes(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    Base type for encoding supported categories.
    """


class CategoryScalingCommandParser(abc.ABC):
    """
    For a given category provide the corresponding scaler.
    """

    def __init__(self, value: request.ScaleRequest) -> None:
        if not isinstance(value, request.ScaleRequest):
            raise TypeError(
                f"Request argument must be an instance of {request.ScaleRequest.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        self._request = value
        self._scaler = self.__class__._create_scaler(value)
        super().__init__()

    @classmethod
    @abc.abstractmethod
    def _create_scaler(cls, value: request.ScaleRequest) -> Scaler:
        """
        To be overwritten to add ctor arguments' validation.
        It should raise an exception if invalid.

        Args:
            value: scale request
        """

    @property
    def request(self) -> str:
        """
        Resource original :py:cls:`str`.

        Returns:
            Resource definition.
        """
        return self._request

    @property
    def scaler(self) -> Scaler:
        """
        Returns the :py:cls:`Scaler` instance corresponding to the resource and command.

        Returns:
            Instance of :py:cls:`Scaler`.
        """
        return self._scaler

    @classmethod
    @abc.abstractmethod
    def supported_categories(cls) -> List[CategoryTypes]:
        """
        Returns the :py:cls:`list` of :py:cls:`str` that this class supports for scaling.

        Returns:
            :py:cls:`list` of supported categories.
        """

    @classmethod
    def is_supported(cls, value: str) -> bool:
        """
        Returns :py:obj:`True` if the category in ``value`` is supported by this class.

        Args:
            value: category to be checked.

        Returns:
            :py:obj:`True` if it is supported.
        """
        result = False
        for cat in cls.supported_categories():
            if cat.name_equal_str(value):
                result = True
                break
        return result
