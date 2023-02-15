# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
`Cloud SQL`_ scaler.

.. _Cloud SQL: https://cloud.google.com/sql
"""
import re
from typing import Any, List, Tuple, Type

import attrs

from yaas import const, logger
from yaas.dto import dto_defaults, request, scaling
from yaas.gcp import cloud_sql, cloud_sql_const
from yaas.scaler import base, resource_name_parser

_LOGGER = logger.get(__name__)

_CLOUD_SQL_COMMAND_REGEX: re.Pattern = re.compile(
    pattern=r"^\s*([^\s\.]+)\.?\s+\.?\s*([^\s\.]+)\s*$", flags=re.IGNORECASE
)
"""
Example input::
    instance_type db-f1-micro
Parses strings in the format::
    <COMMAND> <STRING_VALUE>
"""


class CloudSqlCommandType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    All supported scaling commands for Cloud SQL.
    """

    INSTANCE_TYPE = "instance_type"


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudSqlScalingCommand(scaling.ScalingCommand):
    """
    Cloud SQL scaling command definition.
    """

    def _is_parameter_value_valid(self, value: Any) -> bool:
        return CloudSqlCommandType.from_str(value) is not None

    def _is_target_value_valid(self, value: Any) -> bool:
        return bool(value)

    @staticmethod
    def _target_type() -> Type[Any]:
        return str

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
        return _CLOUD_SQL_COMMAND_REGEX

    @classmethod
    def _convert_target_value_string(cls, value: str) -> Any:
        return value.strip()


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudSqlScalingDefinition(  # pylint: disable=too-few-public-methods
    scaling.ScalingDefinition
):
    """
    DTO to Hold a Cloud SQL scaling definition.
    """

    def _is_resource_valid(self, value: str) -> bool:
        lst_errors = cloud_sql.validate_cloud_sql_resource_name(
            value, raise_if_invalid=True
        )
        return not lst_errors

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "CloudSqlScalingDefinition":
        _, res_name = resource_name_parser.canonical_resource_type_and_name(
            value.resource
        )
        return CloudSqlScalingDefinition(
            resource=res_name,
            command=CloudSqlScalingCommand.from_command_str(value.command),
            timestamp_utc=value.timestamp_utc,
        )


class CloudSqlScaler(base.ScalerPathBased):
    """
    Apply the given scaling definition to Cloud SQL.
    """

    async def can_enact(self) -> Tuple[bool, str]:
        return await cloud_sql.can_be_deployed(self.resource)

    @classmethod
    def _valid_definition_type(cls) -> Type[scaling.ScalingDefinition]:
        return CloudSqlScalingDefinition

    @classmethod
    def from_request(
        cls, *value: Tuple[request.ScaleRequest], **kwargs
    ) -> "CloudSqlScaler":
        return CloudSqlScaler(
            *[CloudSqlScalingDefinition.from_request(val) for val in value]
        )

    @classmethod
    def _get_enact_path_value(cls, *, resource: str, field: str, target: Any) -> str:
        result = None
        if CloudSqlCommandType.INSTANCE_TYPE.value == field:
            result = cloud_sql_const.CLOUD_SQL_SERVICE_SCALING_INSTANCE_TYPE_PARAM
        return result

    @classmethod
    async def _enact_by_path_value_lst(
        cls, *, resource: str, path_value_lst: List[Tuple[str, Any]]
    ) -> None:
        await cloud_sql.update_instance(name=resource, path_value_lst=path_value_lst)
