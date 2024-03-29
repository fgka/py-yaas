# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""DTOs to encode a command coming from the Cloud Function."""
from typing import Any

import attrs

from yaas_common import const, dto_defaults, request


class CommandType(dto_defaults.EnumWithFromStrIgnoreCase):
    """Available command types."""

    UPDATE_CALENDAR_CREDENTIALS_SECRET = const.CMD_TYPE_UPDATE_CALENDAR_CREDENTIALS_SECRET
    UPDATE_CALENDAR_CACHE = const.CMD_TYPE_UPDATE_CALENDAR_CACHE
    SEND_SCALING_REQUESTS = const.CMD_TYPE_SEND_SCALING_REQUESTS


@attrs.define(**const.ATTRS_DEFAULTS)
class CommandBase(dto_defaults.HasFromDict):
    """Common command DTO with mandatory fields."""

    type: str = attrs.field(validator=attrs.validators.instance_of(str))

    @type.validator
    def _is_type_valid(self, attribute: attrs.Attribute, value: Any) -> None:
        if not CommandType.from_str(value):
            raise ValueError(
                f"Attribute '{attribute.name}' must be one of {[d.value for d in CommandType]}," f" got: '{value}'"
            )


@attrs.define(**const.ATTRS_DEFAULTS)
class CommandUpdateCalendarCredentialsSecret(CommandBase):
    """To request a calendar credentials update."""


@attrs.define(**const.ATTRS_DEFAULTS)
class CommandBaseWithRange(CommandBase):
    """Same as base but with range object."""

    range: request.Range = attrs.field(validator=attrs.validators.instance_of(request.Range))


@attrs.define(**const.ATTRS_DEFAULTS)
class CommandUpdateCalendarCache(CommandBaseWithRange):
    """To update calendar snapshot."""


@attrs.define(**const.ATTRS_DEFAULTS)
class CommandSendScalingRequests(CommandBaseWithRange):
    """To send upcoming scaling requests out."""
