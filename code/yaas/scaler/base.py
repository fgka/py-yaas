# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import abc
import asyncio
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from yaas.dto import request, scaling
from yaas import logger

_LOGGER = logger.get(__name__)


class Scaler(abc.ABC):
    """
    Generic class to define a scaler.
    """

    def __init__(
        self,
        *definition: Tuple[scaling.ScalingDefinition],
        sort_definitions_by_increasing_timestamp: bool = True,
        allow_partial_enact: bool = False,
    ) -> None:
        """
        It will convert the `definition` argument into a list sorted by `timestamp_utc`.
        Example::
            # just the timestamp_utc field for simplicity
            definition = [10, 9, 11, 2]
            self.definitions = [2, 9, 10, 11]
        Args:
            *definition:
            sort_definitions_by_increasing_timestamp: if :py:obj:`True` the latest definition,
                by timestamp, is the last entry, otherwise the reversed order.
            allow_partial_enact: if :py:obj:`True` will enact as much as possible
                from the definitions. This can lead to inconsistencies, please be aware.
        """
        definitions, self._resource = self._validate_definitions(list(definition))
        # The latest, based on timestamp_utc, last
        self._definitions = sorted(
            definitions,
            key=lambda scale_def: scale_def.timestamp_utc,
            reverse=not sort_definitions_by_increasing_timestamp,
        )
        self._allow_partial_enact = allow_partial_enact
        super().__init__()

    @classmethod
    def _validate_definitions(
        cls, definitions: List[scaling.ScalingDefinition]
    ) -> Tuple[List[scaling.ScalingDefinition], str]:
        expected_type = cls._valid_definition_type()
        resource = None
        for ndx, item in enumerate(definitions):
            if not isinstance(item, expected_type):
                raise TypeError(
                    f"Definition must be an instance of {expected_type.__name__}. "
                    f"Got<{item}>[{ndx}]({type(item)}). "
                    f"All definitions: <{definitions}>"
                )
            if resource is None:
                resource = item.resource
            elif item.resource != resource:
                raise ValueError(
                    f"All definitions must have the same resource <{resource}>."
                    f"Got<{item}>[{ndx}]({type(item)}). "
                    f"All definitions: <{definitions}>"
                )
        return definitions, resource

    @classmethod
    def _valid_definition_type(cls) -> type:
        return scaling.ScalingDefinition

    @property
    def definitions(self) -> List[scaling.ScalingDefinition]:
        """
        Scaling definition.

        Returns:
            Scaling definition.
        """
        return self._definitions

    @property
    def resource(self) -> str:
        """
        Which resource will be scaled.
        """
        return self._resource

    @property
    def allow_partial_enact(self) -> bool:
        """
        If :py:obj:`True`, indicates that enactment should try to ignore faulty requests
        instead of failing all.
        """
        return self._allow_partial_enact

    @classmethod
    @abc.abstractmethod
    def from_request(cls, *value: Tuple[request.ScaleRequest]) -> "Scaler":
        """
        Return an instance corresponding to the :py:cls:`scale_request.ScaleRequest`.

        Args:
            value: scaling requests.

        Returns:
            ``value`` converted to a py:cls:`Scaler`.
        """

    async def enact(self) -> bool:
        """
        Apply the required scaling command onto the given resource.

        Returns:
            :py:obj:`True` if successfully enacted.
        """
        _LOGGER.debug(
            "Enacting definitions for resource <%s>. Definitions: <%s>",
            self.resource,
            self.definitions,
        )
        result = False
        can_enact, reason = await self.can_enact()
        if can_enact:
            await self._safe_enact()
            result = True
        else:
            _LOGGER.warning(
                "[%s] Resource is not ready to enact scaling specified in <%s>. "
                "Reason: <%s>. "
                "Check logs for details.",
                self.__class__.__name__,
                self._definitions,
                reason,
            )
        _LOGGER.info(
            "Enacted definitions for resource <%s>. Definitions: <%s>",
            self.resource,
            self.definitions,
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
        # Build path_value_lst
        path_value_lst = []
        for ndx, scale_def in enumerate(self.definitions):
            field = scale_def.command.parameter
            target = scale_def.command.target
            try:
                path = self._get_enact_path_value(
                    resource=scale_def.resource, field=field, target=target
                )
                path_value_lst.append(
                    (
                        path,
                        target,
                    )
                )
            except Exception as err:
                msg = (
                    f"Could not parse path for resource={scale_def.resource}, "
                    f"field={field}, and target={target}. "
                    f"Item {ndx} in {self.definitions}"
                    f"Error: {err}"
                )
                if not self.allow_partial_enact:
                    raise RuntimeError(msg) from err
                _LOGGER.warning("%s. Ignoring", msg)
        # Scale path_value_lst
        _LOGGER.debug("Scaling resource <%s> with <%s>", self.resource, path_value_lst)
        try:
            await self._enact_by_path_value_lst(
                resource=self.resource, path_value_lst=path_value_lst
            )
        except Exception as err:
            raise RuntimeError(
                f"Could not enact scaling for resource={self.resource}, "
                f"path_value_lst={path_value_lst}. "
                f"Error: {err}"
            ) from err
        _LOGGER.info("Scaled resource <%s> with <%s>", self.resource, path_value_lst)

    @classmethod
    def _get_enact_path_value(cls, *, resource: str, field: str, target: Any) -> str:
        pass

    @classmethod
    async def _enact_by_path_value_lst(
        cls, *, resource: str, path_value_lst: List[Tuple[str, Any]]
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
        _LOGGER.debug("Enacting requests: <%s>", list(value))
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
        _LOGGER.info("Enacted requests: <%s>", list(value))
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
        _LOGGER.debug("Creating scaler(s) for requests: <%s>", list(value))
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
        resource_to_requests = self._request_by_resource(scaling_def_lst)
        for resource, scale_def_lst in resource_to_requests.items():
            try:
                items = self._scaler(
                    scale_def_lst, raise_if_invalid_request=raise_if_invalid_request
                )
                _LOGGER.info(
                    "Created <%d> scaler(s) for definitions: <%s>",
                    len(items),
                    scale_def_lst,
                )
            except Exception as err:
                raise CategoryScaleRequestParserError(
                    f"Could not create {Scaler.__name__} "
                    f"for resource: {resource}[{scale_def_lst}]. "
                    f"Error: {err}. "
                    f"Values: {scaling_def_lst}"
                ) from err
            if not items:
                msg = (
                    f"Resulting scaler for resource: {resource}[{scale_def_lst}] is None. "
                    f"Check implementation of {self.__class__.__name__}.{self._scaler.__name__} "
                    f"Values: {scaling_def_lst}"
                )
                if raise_if_invalid_request:
                    raise ValueError(msg)
                _LOGGER.warning(msg)
                continue
            result.extend(items)
        return result[0] if len(result) == 1 and singulate_if_only_one else result

    @staticmethod
    def _request_by_resource(
        values: Iterable[scaling.ScalingDefinition],
    ) -> Dict[str, List[scaling.ScalingDefinition]]:
        # pylint: disable=line-too-long
        """
        It will go through all requests in the batch and put them into "buckets"
        by resource ID. E.g.:

        Input:
            - ``standard | locations/my-location/namespaces/my-project/services/my-service | min_instances 0``
            - ``standard | locations/my-location/namespaces/my-project/services/my-service | max_instances 100``
            - ``standard | locations/my-location/namespaces/my-project/services/my-service | concurrency 80``
            - ``standard | my-project:my-location:my-instance | instance_type db-f1-micro``

        Output::

            {
                "locations/my-location/namespaces/my-project/services/my-service": [
                    "standard | locations/my-location/namespaces/my-project/services/my-service | min_instances 0",
                    "standard | locations/my-location/namespaces/my-project/services/my-service | max_instances 100",
                    "standard | locations/my-location/namespaces/my-project/services/my-service | concurrency 80"
                ],
                "my-project:my-location:my-instance" : [
                    "standard | my-project:my-location:my-instance | instance_type db-f1-micro"
                ]
            }
        """
        # pylint: enable=line-too-long
        result = {}
        for val in values:
            if val.resource not in result:
                result[val.resource] = []
            result[val.resource].append(val)
        return result

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
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Iterable[Scaler]:
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
