# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import attrs

from yaas.dto import dto_defaults
from yaas import const


@attrs.define(**const.ATTRS_DEFAULTS)
class ScaleRequest(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    To be sent as a scale request to a particular topic.
    """

    topic: str = attrs.field(validator=attrs.validators.instance_of(str))
    resource: str = attrs.field(validator=attrs.validators.instance_of(str))
    command: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    timestamp_utc: int = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.and_(
                attrs.validators.instance_of(int),
                attrs.validators.gt(0),
            )
        ),
    )
    original_json_event: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
