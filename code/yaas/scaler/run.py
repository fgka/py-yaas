# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
`Cloud Run`_ scaler.

.. _Cloud Run: https://cloud.google.com/run
"""
import re
from typing import Any, Tuple

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


class CloudRunCommandTypes(dto_defaults.EnumWithFromStrIgnoreCase):
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

    def _is_parameter_valid(self, name: str, value: Any) -> None:
        if not CloudRunCommandTypes.from_str(value):
            raise TypeError(
                f"Attribute {name} cannot accept value <{value}>({type(value)})"
            )

    def _is_target_valid(self, name: str, value: Any) -> None:
        if not isinstance(value, int):
            raise TypeError(
                f"Attribute {name} must be an {int.__name__}. Got: <{value}>({type(value)})"
            )
        if value < 0:
            raise ValueError(
                f"Attribute {name} must be an {int.__name__} >= 0. Got <{value}>({type(value)})"
            )

    @staticmethod
    def from_command_str(value: str) -> scaling.ScalingCommand:
        """
        Parse the command :py:cls:`str` into an instance of :py:cls:`CloudRunScalingCommand`.

        Args:
            value:
        """
        match = _CLOUD_RUN_COMMAND_REGEX.match(value)
        if match:
            parameter, target = match.groups()
            target = int(target)
            result = CloudRunScalingCommand(parameter=parameter, target=target)
        else:
            raise ValueError(
                f"Command value must comply with {_CLOUD_RUN_COMMAND_REGEX}. "
                f"Got: <{value}>({type(value)})"
            )
        return result


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudRunScalingDefinition(  # pylint: disable=too-few-public-methods
    scaling.ScalingDefinition
):
    """
    DTO to Hold a Cloud Run scaling definition.
    """

    def _is_resource_valid(self, name: str, value: str) -> None:
        try:
            cloud_run.validate_cloud_run_resource_name(value, raise_if_invalid=True)
        except Exception as err:  # pylint: disable=broad-except
            raise ValueError(f"Attribute {name} is not a valid Cloud Run ID.") from err

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


class CloudRunScaler(base.Scaler):
    """
    Apply the given scaling definition to Cloud Run.
    """

    def __init__(self, definition: CloudRunScalingDefinition) -> None:
        if not isinstance(definition, CloudRunScalingDefinition):
            raise TypeError(
                f"Definition must be an instance of {CloudRunScalingDefinition.__name__}. "
                f"Got <{definition}>({type(definition)})"
            )
        super().__init__(definition)

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "CloudRunScaler":
        return CloudRunScaler(definition=CloudRunScalingDefinition.from_request(value))

    async def _safe_enact(self) -> None:
        await CloudRunScaler._enact(
            resource=self.definition.resource,
            field=self.definition.command.parameter,
            target=self.definition.command.target,
        )

    async def can_enact(self) -> Tuple[bool, str]:
        return await cloud_run.can_be_deployed(self.definition.resource)

    @classmethod
    async def _enact(cls, *, resource: str, field: str, target: int) -> None:
        _LOGGER.info("Scaling <%s> to <%d> for instance <%s>", field, target, resource)
        if CloudRunCommandTypes.MIN_INSTANCES.value == field:
            path = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM
        elif CloudRunCommandTypes.MAX_INSTANCES.value == field:
            path = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM
        elif CloudRunCommandTypes.CONCURRENCY.value == field:
            path = cloud_run_const.CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM
        else:
            raise ValueError(f"Scaling {field} is not supported in {cls.__name__}")
        await cloud_run.update_service(name=resource, path=path, value=target)
        _LOGGER.info("Scaled %s to %d for instance %s", field, target, resource)
