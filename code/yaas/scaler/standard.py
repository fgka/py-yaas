# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Produce Google Cloud supported resources' scalers.
"""
from typing import Iterable, List, Optional, Tuple

from yaas import logger
from yaas.dto import request
from yaas.scaler import base, run, resource_name_parser

_LOGGER = logger.get(__name__)


class StandardCategoryType(base.CategoryType):
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

    def _filter_requests(
        self,
        value: Iterable[request.ScaleRequest],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> List[request.ScaleRequest]:
        result = {}
        for ndx, req in enumerate(
            sorted(value, key=lambda val: val.timestamp_utc, reverse=True)
        ):
            resource_type, canonical_request = self._create_canonical_request(req)
            if resource_type is not None and canonical_request is not None:
                previous = result.get(canonical_request.resource)
                if previous is not None:
                    _LOGGER.warning(
                        "Discarding <%s>[%d] because there is an already a request "
                        "at same, or later, timestamp (timestamp diff: %d): <%s>",
                        req,
                        ndx,
                        req.timestamp_utc - previous.timestamp_utc,
                        previous,
                    )
                else:
                    result[canonical_request.resource] = canonical_request
            else:
                msg = (
                    f"Could not extract type or canonical request from request <{req}>[{ndx}] "
                    f"in {value}. "
                    f"Request type: <{resource_type}>. "
                    f"Canonical request: <{canonical_request}>"
                )
                if raise_if_invalid_request:
                    raise base.CategoryScaleRequestParserError(msg)
                _LOGGER.warning(msg)
        return list(result.values())

    def _scaler(
        self,
        value: request.ScaleRequest,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> base.Scaler:
        resource_type, canonical_request = self._create_canonical_request(value)
        try:
            if resource_type == resource_name_parser.ResourceType.CLOUD_RUN:
                result = run.CloudRunScaler.from_request(canonical_request)
            else:
                msg = (
                    f"Scaler for resource type <{resource_type}> from request <{value}> "
                    f"is not supported by {self.__class__.__name__}."
                )
                if raise_if_invalid_request:
                    raise base.CategoryScaleRequestParserError(msg)
                _LOGGER.warning(msg)
        except Exception as err:
            raise RuntimeError(
                f"Could not create {base.Scaler.__name__} for type {resource_type.value}. "
                f"Got: {err}"
            ) from err
        if result is None:
            raise ValueError(
                f"Resource <{value.resource}> (canonical resource: <{canonical_request.resource}>)"
                f"in request {value} (canonical: {canonical_request}) "
                "cannot be parsed or is not supported"
            )
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
    def supported_categories(cls) -> List[base.CategoryType]:
        return list(StandardCategoryType)
