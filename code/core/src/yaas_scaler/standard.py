# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Produce Google Cloud supported resources' scalers."""
from typing import List, Type

from yaas_common import logger, request
from yaas_gcp import resource_regex
from yaas_scaler import base, resource_name_parser, run, scaling, sql

_LOGGER = logger.get(__name__)


class StandardCategoryType(scaling.CategoryType):
    """Standard supported categories."""

    STANDARD = "standard"
    YAAS = "yaas"

    @classmethod
    def default(cls) -> "StandardCategoryType":
        """Default type.

        Returns:
        """
        return StandardCategoryType.STANDARD


class StandardScalingCommandParser(base.CategoryScaleRequestParserWithScaler):
    """Standard category supported by YAAS."""

    def _scaling_definition_from_request(self, value: request.ScaleRequest) -> scaling.ScalingDefinition:
        res_type, _ = resource_name_parser.canonical_resource_type_and_name(value.resource)
        if res_type == resource_regex.ResourceType.CLOUD_RUN:
            result = run.CloudRunScalingDefinition.from_request(value)
        elif res_type == resource_regex.ResourceType.CLOUD_SQL:
            result = sql.CloudSqlScalingDefinition.from_request(value)
        else:
            raise TypeError(
                f"Request '{value}' of type {res_type} is not supported. "
                f"Check implementation of {self.__class__.__name__}.{self._scaling_definition_from_request.__name__}"
            )
        return result

    @classmethod
    def _supported_scaling_definition_classes(cls) -> List[type]:
        return [run.CloudRunScalingDefinition, sql.CloudSqlScalingDefinition]

    @classmethod
    def _scaler_class_for_definition_class(cls, definition_type: Type[scaling.ScalingDefinition]) -> Type[base.Scaler]:
        """
        For a subclass of :py:class:`scaling.ScalingDefinition`
        returns the corresponding :py:class:`Scaler` subclass.
        Args:
            definition_type:

        Returns:
        """
        result = None
        if definition_type is run.CloudRunScalingDefinition:
            result = run.CloudRunScaler
        elif definition_type is sql.CloudSqlScalingDefinition:
            result = sql.CloudSqlScaler
        return result

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        return list(StandardCategoryType)
