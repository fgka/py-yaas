# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
DTOs to encode a command coming from the Cloud Function.
"""
from datetime import datetime
import enum
from typing import List, Optional

import attrs

from yaas import const
from yaas import logger

_LOGGER = logger.get(__name__)


class ScalingTargetType(enum.Enum):
    """
    Define the supported Google Cloud resources that can be scaled.
    """

    UNKNOWN = enum.auto()
    CLOUD_RUN = enum.auto()
    GCE = enum.auto()


@attrs.define(**const.ATTRS_DEFAULTS)
class BaseScalingTarget:  # pylint: disable=too-few-public-methods
    """
    Fully specified scaling target.
    """

    name: str = attrs.field(validator=attrs.validators.instance_of(str))
    start: datetime = attrs.field(validator=attrs.validators.instance_of(datetime))
    scaling_param: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    scaling_value: int = attrs.field(
        default=1, validator=[attrs.validators.instance_of(int), attrs.validators.ge(0)]
    )
    type: ScalingTargetType = attrs.field(
        default=ScalingTargetType.UNKNOWN,
        validator=attrs.validators.instance_of(ScalingTargetType),
    )


@attrs.define(**const.ATTRS_DEFAULTS)
class CloudRunScalingTarget(
    BaseScalingTarget
):  # pylint: disable=too-few-public-methods
    # pylint: disable=line-too-long
    """
    To understand the `scaling_param` value, it corresponds to the _path_ in the API:
        `UpdateServiceRequest`_.`Service`_.`RevisionTemplate`_.`RevisionScaling`_

    .. _UpdateServiceRequest: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.UpdateServiceRequest
    .. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    .. _RevisionTemplate: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionTemplate
    .. _RevisionScaling: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionScaling
    """
    # pylint: enable=line-too-long

    def __attrs_post_init__(self):
        # workaround for frozen objects
        object.__setattr__(
            self, "scaling_param", const.CLOUD_RUN_UPDATE_REQUEST_SCALING_TARGET_PARAM
        )
        object.__setattr__(self, "type", ScalingTargetType.CLOUD_RUN)
        # validate name
        _validate_cloud_run_resource_name(self.name, raise_if_invalid=True)


_CLOUD_RUN_NAME_REGEX_ERROR_MSG_ARG: str = (
    "projects/{{project}}/locations/{{location}}/services/{{service_id}}"
)


def _validate_cloud_run_resource_name(
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    result = []
    if not isinstance(value, str):
        result.append(
            f"Name <{value}>({type(str)}) must be an instance of {str.__name__}"
        )
    else:
        # validate format
        matched = const.CLOUD_RUN_NAME_REGEX.match(value)
        if matched is None:
            result.append(
                f"Name must obey the format: '{_CLOUD_RUN_NAME_REGEX_ERROR_MSG_ARG}'. Got <{value}>"
            )
        project, location, service_id = matched.groups()
        # validate individual tokens
        if not project:
            result.append(
                f"Could not find project ID in <{value}> "
                f"assuming pattern {_CLOUD_RUN_NAME_REGEX_ERROR_MSG_ARG}"
            )
        if not location:
            result.append(
                f"Could not find location in <{value}> "
                f"assuming pattern {_CLOUD_RUN_NAME_REGEX_ERROR_MSG_ARG}"
            )
        if not service_id:
            result.append(
                f"Could not find service ID in <{value}> "
                f"assuming pattern {_CLOUD_RUN_NAME_REGEX_ERROR_MSG_ARG}"
            )
    if result and raise_if_invalid:
        raise ValueError(
            f"Could not validate Cloud Run service name <{value}>. Error(s): {result}"
        )
    return result


def from_arguments(
    name: str, value: int, start: datetime
) -> Optional[BaseScalingTarget]:
    """

    Args:
        name:
        value:
        start:

    Returns:

    """
    if not _validate_cloud_run_resource_name(name, raise_if_invalid=False):
        # no errors
        result = CloudRunScalingTarget(name=name, scaling_value=value, start=start)
    else:
        raise ValueError(
            f"Could not parse resource <{name}>({type(name)} "
            f"into a valid {BaseScalingTarget.__name__}"
        )
    return result
