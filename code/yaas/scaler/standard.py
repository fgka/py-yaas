# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Produce Google Cloud supported resources' scalers.
"""
from typing import List, Tuple

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


class StandardScalingCommandParser(base.CategoryScaleRequestProcessor):
    """
    Standard category supported by YAAS.
    """

    def _scaler(self, value: request.ScaleRequest) -> base.Scaler:
        resource_type, canonical_request = self._create_canonical_request(value)
        try:
            if resource_type == resource_name_parser.ResourceType.CLOUD_RUN:
                result = run.CloudRunScaler.from_request(canonical_request)
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
        ) = resource_name_parser.canonical_resource_name_and_type(value.resource)
        value_dict = value.as_dict()
        value_dict[request.ScaleRequest.resource.__name__] = canonical_resource
        return resource_type, request.ScaleRequest.from_dict(value_dict)

    @classmethod
    def supported_categories(cls) -> List[base.CategoryType]:
        return list(StandardCategoryType)
