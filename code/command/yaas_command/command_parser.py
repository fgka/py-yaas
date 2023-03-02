# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Parses a dictionary into an instance of :py:class:`command: command.CommandBase`.
"""
from typing import Any, Dict

from yaas_common import command, logger

_LOGGER = logger.get(__name__)


def to_command(value: Dict[str, Any]) -> command.CommandBase:
    """
    Converts a dictionary to the corresponding
        :py:class:`command.CommandBase` subclass.

    Args:
        value:

    Returns:

    """
    _LOGGER.debug(
        "Converting value into a <%s> instance. Value: <%s>",
        command.CommandBase.__name__,
        value,
    )
    # validate input
    req_type = _validate_command_dict_and_get_request_type(value)
    if not req_type:
        raise ValueError(f"Could not parse request type from <{value}>({type(value)})")
    # logic
    if req_type == command.CommandType.UPDATE_CALENDAR_CREDENTIALS_SECRET:
        result = command.CommandUpdateCalendarCredentialsSecret.from_dict(value)
    elif req_type == command.CommandType.UPDATE_CALENDAR_CACHE:
        result = command.CommandUpdateCalendarCache.from_dict(value)
    elif req_type == command.CommandType.SEND_SCALING_REQUESTS:
        result = command.CommandSendScalingRequests.from_dict(value)
    else:
        raise ValueError(
            f"Command type <{req_type}> is not supported. Argument: <{value}>"
        )
    return result


def _validate_command_dict_and_get_request_type(
    value: Dict[str, Any]
) -> command.CommandType:
    if not isinstance(value, dict):
        raise TypeError(
            f"Expecting a {dict.__name__} as argument. Got: <{value}>({type(value)})"
        )
    return command.CommandType.from_str(value.get(command.CommandBase.type.__name__))
