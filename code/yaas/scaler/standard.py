# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Produce Google Cloud supported resources' scalers.
"""
from typing import List

from yaas import logger
from yaas.dto import request
from yaas.scaler import base, run, resource_name_parser

_LOGGER = logger.get(__name__)


class StandardCategoryType(base.CategoryTypes):
    """
    Base type for encoding supported categories.
    """

    STANDARD = "standard"
    YAAS = "yaas"

    @classmethod
    def default(cls) -> "StandardCategoryType":
        return StandardCategoryType.STANDARD


class StandardScalingCommandParser(base.CategoryScalingCommandParser):
    """
    Standard category supported by YAAS.
    """

    def __init__(self, value: request.ScaleRequest) -> None:
        super().__init__(value)

    @classmethod
    def _create_scaler(cls, value: request.ScaleRequest) -> base.Scaler:
        if not cls.is_supported(value.topic):
            raise ValueError(
                f"The request topic {value.topic} is not supported by {cls.__name__}. "
                f"Check request: {value}"
            )
        res_type, res_name = resource_name_parser.canonical_resource_name_and_type(
            value.resource
        )
        if res_type == resource_name_parser.ResourceType.CLOUD_RUN:
            return run.CloudRunScaler.from_request(value)
        raise ValueError(
            f"Resource <{value.resource}> (parsed name: <{res_name}>)"
            f"in request {value} cannot be parsed or is not supported"
        )

    @classmethod
    def supported_categories(cls) -> List[base.CategoryTypes]:
        return list(StandardCategoryType)
