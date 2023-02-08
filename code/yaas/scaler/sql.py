# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
`Cloud SQL`_ scaler.

.. _Cloud SQL: https://cloud.google.com/sql
"""
import re
from typing import Any, Tuple

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


class CloudSqlCommandTypes(dto_defaults.EnumWithFromStrIgnoreCase):
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
        return CloudSqlCommandTypes.from_str(value) is not None

    def _is_target_type_valid(self, value: Any) -> bool:
        return isinstance(value, str)

    def _is_target_value_valid(self, value: Any) -> bool:
        return bool(value)

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
        return _CLOUD_SQL_COMMAND_REGEX


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
        return await cloud_sql.can_be_deployed(self.definition.resource)

    @classmethod
    def _valid_definition_type(cls) -> type:
        return CloudSqlScalingDefinition

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "CloudSqlScaler":
        return CloudSqlScaler(definition=CloudSqlScalingDefinition.from_request(value))

    @classmethod
    def _path_for_enact(cls, resource: str, field: str, target: Any) -> str:
        result = None
        if CloudSqlCommandTypes.INSTANCE_TYPE.value == field:
            result = cloud_sql_const.CLOUD_SQL_SERVICE_SCALING_INSTANCE_TYPE_PARAM
        return result

    @classmethod
    async def _enact_by_path(
        cls, *, resource: str, field: str, target: Any, path: str
    ) -> None:
        cloud_sql.update_instance(name=resource, path=path, value=target)
