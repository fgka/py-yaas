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


class CategoryType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    Base type for encoding supported categories.
    """


class CategoryScaleRequestProcessorError(Exception):
    """
    Wrapper for all errors creating a :py:class:`Scaler`
    for a given :py:class:`request.ScaleRequest`.
    """


class CategoryScaleRequestProcessor(abc.ABC):
    """
    For a given category process all :py:class:`request.ScaleRequest`.
    """

    def scaler(self, value: request.ScaleRequest) -> Scaler:
        """
        Returns the :py:cls:`Scaler` instance corresponding to the resource and command.

        Returns:
            Instance of :py:cls:`Scaler`.
        """
        # validate input
        if not isinstance(value, request.ScaleRequest):
            raise TypeError(
                f"The argument must be an instance of {request.ScaleRequest.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        if not self.is_supported(value.topic):
            raise ValueError(
                f"The request topic {value.topic} is not supported. "
                f"Valid values are: {self.supported_categories()}"
            )
        # logic
        try:
            result = self._scaler(value)
        except Exception as err:
            raise CategoryScaleRequestProcessorError(
                f"Could not create {Scaler.__name__} for request: {value}. Error: {err}"
            ) from err
        if result is None:
            raise ValueError(
                f"Resulting scaler for request: {value} is None. "
                f"Check implementation of {self._scaler.__name__} in {self.__class__.__name__}"
            )
        return result

    @abc.abstractmethod
    def _scaler(self, value: request.ScaleRequest) -> Scaler:
        """
        Only called with a pre-validated request.
        It should raise an exception if any specific is invalid.
        """

    @classmethod
    @abc.abstractmethod
    def supported_categories(cls) -> List[CategoryType]:
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
