# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCS file based batch scaling."""
import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple, Type

import attrs

from yaas_calendar import parser
from yaas_command import pubsub_dispatcher
from yaas_common import const, logger, request
from yaas_gcp import gcs
from yaas_scaler import base, scaling

_LOGGER = logger.get(__name__)

_GCS_BATCH_COMMAND_REGEX: re.Pattern = re.compile(pattern=r"^\s*([^/\.][^\s]+[^/\.])\.*\s*$", flags=re.IGNORECASE)
"""
Example input::
    path/to/object
Parses strings in the format::
    <path to gcs object>
"""


@attrs.define(**const.ATTRS_DEFAULTS)
class GcsBatchScalingCommand(scaling.ScalingCommand):
    """GCS based batch scaling command definition."""

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
                f"Attribute {name} should not be given (aka None) for "
                f"{GcsBatchScalingCommand.__name__}. "
                f"Got: '{value}'({type(value)})"
            )

    @classmethod
    def _parameter_target_regex(cls) -> re.Pattern:
        return _GCS_BATCH_COMMAND_REGEX


@attrs.define(**const.ATTRS_DEFAULTS)
class GcsBatchScalingDefinition(scaling.ScalingDefinition):
    """DTO to Hold a GCS based batch scaling definition."""

    def _is_resource_valid(self, value: str) -> bool:
        result = False
        try:
            cleaned_value = gcs.validate_and_clean_bucket_name(value)
            result = cleaned_value == value
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not validate resource value for %s '%s', Error: %s",
                self.__class__.__name__,
                value,
                err,
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

    def as_gcs_uri(self) -> str:
        """Returns a GCS URI in the format::
        gs://<resource>/<command.parameter>
        """
        return f"gs://{self.resource}/{self.command.parameter}"


class GcsBatchCategoryType(scaling.CategoryType):
    """GCS Batch supported categories."""

    GCS = "gcs"
    GCS_BATCH = "gcs_batch"

    @classmethod
    def default(cls) -> "GcsBatchCategoryType":
        """Default type.

        Returns:
        """
        return GcsBatchCategoryType.GCS


class GcsBatchScaler(base.Scaler):
    """Apply the given GCS batched scaling definitions."""

    def __init__(
        self,
        *definition: Tuple[scaling.ScalingDefinition],
        topic_to_pubsub: Dict[str, str],
    ) -> None:
        super().__init__(*definition, sort_definitions_by_increasing_timestamp=False)
        if not isinstance(topic_to_pubsub, dict):
            raise TypeError(
                f"Topic to pubsub argument must be an instance of {dict.__name__}. "
                f"Got: '{topic_to_pubsub}'({type(topic_to_pubsub)})"
            )
        self._topic_to_pubsub = topic_to_pubsub

    @property
    def topic_to_pubsub(self) -> Dict[str, str]:
        """Topic to PubSub mapping."""
        return self._topic_to_pubsub

    async def can_enact(self) -> Tuple[bool, str]:
        return True, ""

    async def _safe_enact(self) -> None:
        """
        Algorithm:
            1. Reads from bucket.
            2. Parses the requests.
            3. Calls pubsub_dispatcher.
        """
        # get unique
        processed = set()
        for ndx, scale_def in enumerate(self.definitions):
            obj_path = scale_def.command.parameter
            # ignored already read objects
            if obj_path in processed:
                _LOGGER.warning(
                    "Path '%s' already read. Ignoring. Full list: %s",
                    obj_path,
                    self.definitions,
                )
                continue
            # logic
            try:
                await self._process_definition(scale_def)
            except Exception as err:  # pylint: disable=broad-except
                msg = f"Cloud not process definition in '{scale_def}'[{ndx}]. Error: {err}"
                if not self.allow_partial_enact:
                    raise RuntimeError(msg) from err
                _LOGGER.warning("%s. Ignoring", msg)
            # mark as processed
            processed.add(obj_path)

    async def _process_definition(self, definition: GcsBatchScalingDefinition) -> None:
        await asyncio.sleep(0)
        content = gcs.read_object(bucket_name=self.resource, object_path=definition.command.parameter)
        await asyncio.sleep(0)
        if content is not None:
            request_str_lst = content.decode(encoding=const.ENCODING_UTF8).split("\n")
            request_lst = parser.parse_lines(
                lines=request_str_lst,
                timestamp_utc=definition.timestamp_utc,
                json_event=definition.as_json(),
            )
            if request_lst:
                valid_request_lst = self._filter_requests(request_lst)
                await pubsub_dispatcher.dispatch(
                    self.topic_to_pubsub,
                    *valid_request_lst,
                    raise_if_invalid_request=False,
                )
        else:
            _LOGGER.warning(
                "The content of '%s' from definition '%s' is empty. Ignoring.",
                definition.as_gcs_uri(),
                definition,
            )

    @classmethod
    def _filter_requests(cls, value: List[request.ScaleRequest]) -> List[request.ScaleRequest]:
        result = []
        for ndx, item in enumerate(value):
            if GcsBatchCategoryType.from_str(item.topic) is not None:
                _LOGGER.warning(
                    "%s does not support recursive requests. "
                    "Meaning: you cannot specify any of the topics '%s' in your content. "
                    "Ignoring item: '%s'[%d](%s). "
                    "All items: %s",
                    cls.__name__,
                    list(GcsBatchCategoryType),
                    item,
                    ndx,
                    type(item),
                    value,
                )
            else:
                result.append(item)
        return result

    @classmethod
    def _valid_definition_type(cls) -> Type[scaling.ScalingDefinition]:
        return GcsBatchScalingDefinition

    # pylint: disable=arguments-differ
    @classmethod
    def from_request(cls, *value: Tuple[request.ScaleRequest], topic_to_pubsub: Dict[str, str]) -> "GcsBatchScaler":
        return GcsBatchScaler(
            *[GcsBatchScalingDefinition.from_request(val) for val in value],
            topic_to_pubsub=topic_to_pubsub,
        )

    # pylint: enable=arguments-differ


class GcsBatchCommandParser(base.CategoryScaleRequestParserWithScaler):
    """GCS Batch category supported by YAAS."""

    def __init__(
        self,
        *,
        strict_mode: Optional[bool] = True,
        topic_to_pubsub: Dict[str, str],
    ):
        super().__init__(strict_mode=strict_mode)
        if not isinstance(topic_to_pubsub, dict):
            raise TypeError(
                f"Topic to pubsub argument must be an instance of {dict.__name__}. "
                f"Got: '{topic_to_pubsub}'({type(topic_to_pubsub)})"
            )
        self._topic_to_pubsub = topic_to_pubsub

    @property
    def topic_to_pubsub(self) -> Dict[str, str]:
        """Topic to PubSub mapping."""
        return self._topic_to_pubsub

    def _scaling_definition_from_request(self, value: request.ScaleRequest) -> scaling.ScalingDefinition:
        return GcsBatchScalingDefinition.from_request(value)

    def _instantiate_scaler(
        self,
        scaler_type: Type[base.Scaler],
        definitions: List[scaling.ScalingDefinition],
    ) -> base.Scaler:
        """
        Check that implementation below is correct for your scaler. If not, overwrite it.
        Args:
            scaler_type:
            definitions:

        Returns:

        """
        return scaler_type(*definitions, topic_to_pubsub=self.topic_to_pubsub)

    @classmethod
    def _supported_scaling_definition_classes(
        cls,
    ) -> List[Type[scaling.ScalingDefinition]]:
        return [GcsBatchScalingDefinition]

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
        if definition_type is GcsBatchScalingDefinition:
            result = GcsBatchScaler
        return result

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        return list(GcsBatchCategoryType)
