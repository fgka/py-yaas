# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import abc
import asyncio
from typing import Any, Iterable, List, Optional, Tuple, Union

from yaas.dto import request, scaling
from yaas import logger

_LOGGER = logger.get(__name__)


class Scaler(abc.ABC):
    """
    Generic class to define a scaler.
    """

    def __init__(self, definition: scaling.ScalingDefinition) -> None:
        expected_type = self.__class__._valid_definition_type()
        if not isinstance(definition, expected_type):
            raise TypeError(
                f"Definition must be an instance of {expected_type.__name__}. "
                f"Got <{definition}>({type(definition)})"
            )
        self._definition = definition
        super().__init__()

    @classmethod
    def _valid_definition_type(cls) -> type:
        return scaling.ScalingDefinition

    @property
    def definition(self) -> scaling.ScalingDefinition:
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


class ScalerPathBased(Scaler, abc.ABC):
    """
    Apply the given scaling definition based on X-Path like specification.
    """

    async def _safe_enact(self) -> None:
        await self.__class__._enact(  # pylint: disable=protected-access
            resource=self.definition.resource,
            field=self.definition.command.parameter,
            target=self.definition.command.target,
        )

    @classmethod
    async def _enact(cls, *, resource: str, field: str, target: Any) -> None:
        _LOGGER.info("Scaling <%s> to <%s> for resource <%s>", field, target, resource)
        try:
            path = cls._path_for_enact(resource, field, target)
        except Exception as err:
            raise RuntimeError(
                f"Could not parse path for resource={resource}, field={field}, and target={target}. Error: {err}"
            ) from err
        if not path:
            raise ValueError(f"Scaling {field} is not supported in {cls.__name__}")
        try:
            await cls._enact_by_path(
                resource=resource, field=field, target=target, path=path
            )
        except Exception as err:
            raise RuntimeError(
                f"Could not enact scaling for resource={resource}, field={field}, target={target}, and path={path}. Error: {err}"
            ) from err
        _LOGGER.info("Scaled <%s> to <%s> for resource <%s>", field, target, resource)

    @classmethod
    def _path_for_enact(cls, resource: str, field: str, target: Any) -> str:
        pass

    @classmethod
    async def _enact_by_path(
        cls, *, resource: str, field: str, target: Any, path: str
    ) -> None:
        pass


class CategoryScaleRequestParserError(Exception):
    """
    Wrapper for all errors creating a :py:class:`Scaler`
    for a given :py:class:`request.ScaleRequest`.
    """


class CategoryScaleRequestParser(abc.ABC):
    """
    For a given category process all :py:class:`request.ScaleRequest`.
    """

    def __init__(self, *, strict_mode: Optional[bool] = True):
        self._strict_mode = bool(strict_mode)

    async def enact(
        self,
        *value: request.ScaleRequest,
        singulate_if_only_one: Optional[bool] = True,
        raise_if_invalid_request: Optional[bool] = None,
    ) -> Union[List[Tuple[bool, Scaler]], Tuple[bool, Scaler]]:
        """
        Will create the corresponding :py:class:`Scaler`
            and call its :py:meth:`Scaler.enact` method.
        Args:
            value:
                Scaling request(s)
            singulate_if_only_one:
                if :py:obj:`True` will return the single :py:class:`Scaler`
                if ``value`` has a single item.
            raise_if_invalid_request:
                if :py:obj:`False` it will just log faulty requests.
        Returns:
            Used :py:class:`Scaler`
        """
        # validate input
        if raise_if_invalid_request is None:
            raise_if_invalid_request = self._strict_mode
        # logic
        item_lst = self.scaler(
            *value,
            singulate_if_only_one=False,
            raise_if_invalid_request=raise_if_invalid_request,
        )
        item_res_lst = await asyncio.gather(*[item.enact() for item in item_lst])
        result = list(zip(item_res_lst, item_lst))
        return result[0] if len(result) == 1 and singulate_if_only_one else result

    def scaler(
        self,
        *value: request.ScaleRequest,
        singulate_if_only_one: Optional[bool] = True,
        raise_if_invalid_request: Optional[bool] = None,
    ) -> Union[List[Scaler], Scaler]:
        """
        Returns the :py:cls:`Scaler` instance corresponding to the resource and command.

            singulate_if_only_one:
                if :py:obj:`True` will return the single :py:class:`Scaler`
                if ``value`` has a single item.
            value:
                Scaling request(s)
        Returns:
            Instance of :py:cls:`Scaler`.
        """
        # validate input
        self._validate_request(*value)
        if raise_if_invalid_request is None:
            raise_if_invalid_request = self._strict_mode
        # logic
        result = []
        scaling_def_lst: Iterable[scaling.ScalingDefinition] = self._filter_requests(
            self._to_scaling_definition(value, raise_if_error=self._strict_mode),
            raise_if_invalid_request=raise_if_invalid_request,
        )
        for ndx, val in enumerate(scaling_def_lst):
            try:
                item = self._scaler(
                    val, raise_if_invalid_request=raise_if_invalid_request
                )
            except Exception as err:
                raise CategoryScaleRequestParserError(
                    f"Could not create {Scaler.__name__} for request: {val}[{ndx}]. "
                    f"Error: {err}. "
                    f"Values: {scaling_def_lst}"
                ) from err
            if item is None:
                raise ValueError(
                    f"Resulting scaler for request: {val}[{ndx}] is None. "
                    f"Check implementation of {self._scaler.__name__} in {self.__class__.__name__}. "
                    f"Values: {scaling_def_lst}"
                )
            result.append(item)

        return result[0] if len(result) == 1 and singulate_if_only_one else result

    def _validate_request(self, *value: request.ScaleRequest) -> None:
        for ndx, val in enumerate(value):
            if not isinstance(val, request.ScaleRequest):
                raise TypeError(
                    f"The argument must be an instance of {request.ScaleRequest.__name__} "
                    f"Got: <{val}>[{ndx}]({type(val)}). "
                    f"Values: {value}"
                )
            if not self.is_supported(val.topic):
                raise ValueError(
                    f"The request topic {val.topic}[{ndx}] is not supported. "
                    f"Valid values are: {self.supported_categories()}. "
                    f"Values: {value}"
                )

    @abc.abstractmethod
    def _to_scaling_definition(
        self,
        value: Iterable[request.ScaleRequest],
        *,
        raise_if_error: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        """
        To convert the request into its proper, supported, scaling definition.
        Args:
            value:
            raise_if_error

        Returns:

        """

    def _filter_requests(  # pylint: disable=unused-argument
        self,
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        """
        Optional implementation to filter requests before creating :py:class:`Scaler`.
        """
        return value

    @abc.abstractmethod
    def _scaler(
        self,
        value: scaling.ScalingDefinition,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Scaler:
        """
        Only called with a pre-validated request.
        It should raise an exception if any specific is invalid.
        """

    @classmethod
    @abc.abstractmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
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
