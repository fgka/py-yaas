# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Produce Google Cloud supported resources' scalers.
"""
from typing import Iterable, List, Optional, Tuple

from yaas import logger
from yaas.dto import request, scaling
from yaas.scaler import base, run, resource_name_parser

_LOGGER = logger.get(__name__)


class StandardCategoryType(scaling.CategoryType):
    """
    Base type for encoding supported categories.
    """

    STANDARD = "standard"
    YAAS = "yaas"

    @classmethod
    def default(cls) -> "StandardCategoryType":
        """
        Default type.

        Returns:
        """
        return StandardCategoryType.STANDARD


class StandardScalingCommandParser(base.CategoryScaleRequestParser):
    """
    Standard category supported by YAAS.
    """

    def _to_scaling_definition(
        self, value: Iterable[request.ScaleRequest]
    ) -> Iterable[scaling.ScalingDefinition]:
        result = []
        for ndx, val in enumerate(value):
            res_type, _ = resource_name_parser.canonical_resource_type_and_name(
                val.resource
            )
            if res_type == resource_name_parser.ResourceType.CLOUD_RUN:
                result.append(run.CloudRunScalingDefinition.from_request(val))
            else:
                raise TypeError(
                    f"Request <{val}>[{ndx}]) of type {res_type} is not supported. "
                    f"Check implementation of {self._to_scaling_definition.__name__} "
                    f"in {self.__class__.__name__}. "
                    f"Values: {value}"
                )
        return result

    def _filter_requests(
        self,
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> List[scaling.ScalingDefinition]:
        result = {}
        for ndx, scaling_def in enumerate(
            sorted(value, key=lambda val: val.timestamp_utc, reverse=True)
        ):
            key = scaling_def.resource, scaling_def.command
            previous = result.get(key)
            if previous is not None:
                _LOGGER.warning(
                    "Discarding <%s>[%d] because there is an already a scaling definition "
                    "at the same, or later, timestamp (timestamp diff: %d): <%s>. "
                    "All elements: %s",
                    scaling_def,
                    ndx,
                    scaling_def.timestamp_utc - previous.timestamp_utc,
                    previous,
                    value,
                )
            else:
                result[key] = scaling_def
        return list(result.values())

    def _scaler(
        self,
        value: scaling.ScalingDefinition,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> base.Scaler:
        if isinstance(value, run.CloudRunScalingDefinition):
            result = run.CloudRunScaler(value)
        else:
            msg = (
                f"Scaler for definition <{value}> "
                f"is not supported by {self.__class__.__name__}. "
                f"Check implementation of {self._scaler.__name__} in {self.__class__.__name__}."
            )
            if raise_if_invalid_request:
                raise base.CategoryScaleRequestParserError(msg)
            _LOGGER.warning(msg)
        return result

    @staticmethod
    def _create_canonical_request(
        value: request.ScaleRequest,
    ) -> Tuple[resource_name_parser.ResourceType, request.ScaleRequest]:
        (
            resource_type,
            canonical_resource,
        ) = resource_name_parser.canonical_resource_type_and_name(value.resource)
        if canonical_resource:
            value_dict = value.as_dict()
            value_dict[request.ScaleRequest.resource.__name__] = canonical_resource
            canonical_req = request.ScaleRequest.from_dict(value_dict)
        else:
            resource_type = None
            canonical_req = None
            _LOGGER.warning(
                "Could not extract canonical resource name from request <%s>. Ignoring.",
                value,
            )
        return resource_type, canonical_req

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        return list(StandardCategoryType)
