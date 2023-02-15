# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Produce Google Cloud supported resources' scalers.
"""
from typing import Iterable, List, Optional, Type

from yaas import logger
from yaas.dto import request, resource_regex, scaling
from yaas.scaler import base, resource_name_parser, run, sql

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


class StandardScalingCommandParser(base.CategoryScaleRequestParserWithScaler):
    """
    Standard category supported by YAAS.
    """

    def _to_scaling_definition(
        self,
        value: Iterable[request.ScaleRequest],
        *,
        raise_if_error: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        result = []
        for ndx, val in enumerate(value):
            res_type, _ = resource_name_parser.canonical_resource_type_and_name(
                val.resource
            )
            if res_type == resource_regex.ResourceType.CLOUD_RUN:
                result.append(run.CloudRunScalingDefinition.from_request(val))
            elif res_type == resource_regex.ResourceType.CLOUD_SQL:
                result.append(sql.CloudSqlScalingDefinition.from_request(val))
            else:
                msg = (
                    f"Request <{val}>[{ndx}]) of type {res_type} is not supported. "
                    f"Check implementation of {self._to_scaling_definition.__name__} "
                    f"in {self.__class__.__name__}. "
                    f"Values: {value}"
                )
                if raise_if_error:
                    raise TypeError(msg)
                _LOGGER.warning(msg)
        return result

    @classmethod
    def _supported_scaling_definition_classes(cls) -> List[type]:
        return [run.CloudRunScalingDefinition, sql.CloudSqlScalingDefinition]

    @classmethod
    def _scaler_class_for_definition_class(
        cls, definition_type: Type[scaling.ScalingDefinition]
    ) -> Type[base.Scaler]:
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
