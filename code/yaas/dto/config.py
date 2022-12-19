# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import attrs

from yaas.dto import dto_defaults
from yaas import const


@attrs.define(**const.ATTRS_DEFAULTS)
class GoogleCalendarConfig(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    To specify which Google Calendar to use.
    """

    calendar_id: str = attrs.field(validator=attrs.validators.instance_of(str))
    secret_fqn: str = attrs.field(validator=attrs.validators.instance_of(str))
