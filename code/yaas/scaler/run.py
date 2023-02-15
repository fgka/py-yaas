# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
`Cloud Run`_ scaler.

.. _Cloud Run: https://cloud.google.com/run
"""
import re
from typing import Any, List, Tuple, Type

import attrs

from yaas import const, logger
from yaas.dto import dto_defaults, request, scaling
from yaas.gcp import cloud_run, cloud_run_const
from yaas.scaler import base, resource_name_parser

_LOGGER = logger.get(__name__)

_CLOUD_RUN_COMMAND_REGEX: re.Pattern = re.compile(
    pattern=r"^\s*([^\s\.]+)\.?\s+\.?\s*([\d]+)\s*$", flags=re.IGNORECASE
)
"""
Example input::
    min_instances 10
Parses strings in the format::
    <COMMAND> <INT_VALUE>
"""


class CloudRunCommandType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    All supported scaling commands for Cloud Run.
    """

    MIN_INSTANCES = "min_instances"
    MAX_INSTANCES = "max_instances"
    CONCURRENCY = "concurrency"


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudRunScalingCommand(scaling.ScalingCommand):
    """
    Cloud Run scaling command definition.
    """

    def _is_parameter_value_valid(self, value: Any) -> bool:
        return CloudRunCommandType.from_str(value) is not None

    def _is_target_value_valid(self, value: Any) -> bool:
        return value >= 0

    @staticmethod
    def _target_type() -> Type[Any]:
        return int

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
        return _CLOUD_RUN_COMMAND_REGEX

    @classmethod
    def _convert_target_value_string(cls, value: str) -> Any:
        return int(value)


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudRunScalingDefinition(  # pylint: disable=too-few-public-methods
    scaling.ScalingDefinition
):
    """
    DTO to Hold a Cloud Run scaling definition.
    """

    def _is_resource_valid(self, value: str) -> bool:
        lst_errors = cloud_run.validate_cloud_run_resource_name(
            value, raise_if_invalid=True
        )
        return not lst_errors

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "CloudRunScalingDefinition":
        _, res_name = resource_name_parser.canonical_resource_type_and_name(
            value.resource
        )
        return CloudRunScalingDefinition(
            resource=res_name,
            command=CloudRunScalingCommand.from_command_str(value.command),
            timestamp_utc=value.timestamp_utc,
        )


class CloudRunScaler(base.ScalerPathBased):
    """
    Apply the given scaling definition to Cloud Run.
    """

    async def can_enact(self) -> Tuple[bool, str]:
        return await cloud_run.can_be_deployed(self.resource)

    @classmethod
    def _valid_definition_type(cls) -> Type[scaling.ScalingDefinition]:
        return CloudRunScalingDefinition

    @classmethod
    def from_request(
        cls, *value: Tuple[request.ScaleRequest], **kwargs
    ) -> "CloudRunScaler":
        return CloudRunScaler(
            *[CloudRunScalingDefinition.from_request(val) for val in value]
        )

    @classmethod
    def _get_enact_path_value(cls, *, resource: str, field: str, target: Any) -> str:
        result = None
        if CloudRunCommandType.MIN_INSTANCES.value == field:
            result = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM
        elif CloudRunCommandType.MAX_INSTANCES.value == field:
            result = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM
        elif CloudRunCommandType.CONCURRENCY.value == field:
            result = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM
        return result

    @classmethod
    async def _enact_by_path_value_lst(
        cls, *, resource: str, path_value_lst: List[Tuple[str, Any]]
    ) -> None:
        await cloud_run.update_service(name=resource, path_value_lst=path_value_lst)
