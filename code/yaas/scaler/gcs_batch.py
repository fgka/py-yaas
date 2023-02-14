# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCS file based batch scaling.
"""
import re
from typing import Any, Dict, List, Tuple

import attrs

from yaas import const, logger
from yaas.dto import request, scaling
from yaas.entry_point import pubsub_dispatcher
from yaas.gcp import gcs
from yaas.scaler import base

_LOGGER = logger.get(__name__)

_GCS_BATCH_COMMAND_REGEX: re.Pattern = re.compile(
    pattern=r"^\s*([^/\.][^\s]+[^/\.])\.*\s*$", flags=re.IGNORECASE
)
"""
Example input::
    path/to/object
Parses strings in the format::
    <path to gcs object>
"""


@attrs.define(**const.ATTRS_DEFAULTS)
class GcsBatchScalingCommand(scaling.ScalingCommand):
    """
    GCS based batch scaling command definition.
    """

    def _is_parameter_value_valid(self, value: Any) -> bool:
        result = False
        if isinstance(value, str):
            match = self._parameter_target_regex().match(value)
            if match:
                result = bool(match.groups())
        return result

    def _is_target_valid(self, name: str, value: Any) -> None:
        if value is not None:
            raise ValueError(
                f"Attribute {name} should not be given (aka None) for {GcsBatchScalingCommand.__name__}. Got: <{value}>({type(value)})"
            )

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
        return _GCS_BATCH_COMMAND_REGEX


@attrs.define(**const.ATTRS_DEFAULTS)
class GcsBatchScalingDefinition(  # pylint: disable=too-few-public-methods
    scaling.ScalingDefinition
):
    """
    DTO to Hold a GCS based batch scaling definition.
    """

    def _is_resource_valid(self, value: str) -> bool:
        result = False
        try:
            cleaned_value = gcs.validate_and_clean_bucket_name(value)
            result = cleaned_value == value
        except Exception as err:
            _LOGGER.warning(
                f"Could not validate resource value for {self.__class__.__name__} <{value}>. Error: {err}"
            )
        return result

    def _is_target_value_valid(self, value: Any) -> bool:
        return value is None

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "GcsBatchScalingDefinition":
        return GcsBatchScalingDefinition(
            resource=value.resource,
            command=GcsBatchScalingCommand.from_command_str(value.command),
            timestamp_utc=value.timestamp_utc,
        )


class GcsBatchScaler(base.Scaler):
    """
    Apply the given GCS batched scaling definitions.
    """

    def __init__(
        self,
        *definition: Tuple[scaling.ScalingDefinition],
        topic_to_pubsub: Dict[str, str],
    ) -> None:
        super().__init__(*definition)
        if not isinstance(topic_to_pubsub, dict):
            raise TypeError(
                f"Topic to pubsub argument must be an instance of {dict.__name__}. "
                f"Got: <{topic_to_pubsub}>({type(topic_to_pubsub)})"
            )
        self._topic_to_pubsub = topic_to_pubsub

    @property
    def topic_to_pubsub(self) -> Dict[str, str]:
        """
        Topic to PubSub mapping
        """
        return self._topic_to_pubsub

    async def can_enact(self) -> Tuple[bool, str]:
        return True, ""

    async def _safe_enact(self) -> None:
        """
        Algorithm:
            1. Reads from bucket;
            2. Parses the requests;
            3. Calls pubsub_dispatcher.
        """
        # TODO: read bucket objects
        # TODO: parse content into ScaleRequests
        requests: List[request.ScaleRequest] = []
        await pubsub_dispatcher.dispatch(
            self._configuration.topic_to_pubsub,
            *requests,
            raise_if_invalid_request=False,
        )

    @classmethod
    def _valid_definition_type(cls) -> type:
        return GcsBatchScalingDefinition

    @classmethod
    def from_request(cls, *value: Tuple[request.ScaleRequest], topic_to_pubsub: Dict[str, str]) -> "GcsBatchScaler":
        return GcsBatchScaler(
            *[GcsBatchScalingDefinition.from_request(val) for val in value],
            topic_to_pubsub=topic_to_pubsub
        )
