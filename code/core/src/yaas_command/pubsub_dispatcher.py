# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
On receiving a scaling request(s) route it properly through `PubSub`_.

.. _PubSub: https://cloud.google.com/pubsub/
"""
from typing import Any, Dict, Iterable, List, Optional, Type, Union

import flask

from yaas_command import command_parser
from yaas_common import command, dto_defaults, logger, request
from yaas_gcp import pubsub

_LOGGER = logger.get(__name__)


class DispatchError(Exception):
    """
    To encode logical errors in routing the request(s).
    """


async def dispatch(
    topic_to_pubsub: Dict[str, str],
    *value: request.ScaleRequest,
    raise_if_invalid_request: Optional[bool] = True,
) -> None:
    """
    Will read the request(s) and route them according to the mapping in ``topic_to_pubsub``.
    Args:
        topic_to_pubsub:
            Maps request topic to proper PubSub topic.
        raise_if_invalid_request:
            Will raise py:class:`DispatchError` if:
              * ``value`` is not :py:class:`request.ScaleRequest`,
                otherwise logged and ignored.
              * ``value`` has a topic not contained in ``topic_to_pubsub``,
                otherwise logged and ignored.
        *value: what to process
    Returns:
    """
    # validate input
    if not isinstance(topic_to_pubsub, dict):
        raise TypeError(
            f"The mapping from topic to pubsub must be a {dict.__name__}. "
            f"Got: '{topic_to_pubsub}'({type(topic_to_pubsub)})"
        )
    # routing
    topic_to_request_lst = _topic_to_request_lst(topic_to_pubsub, value, raise_if_invalid_request)
    # route
    await _publish_requests(topic_to_pubsub, topic_to_request_lst)


def _topic_to_request_lst(
    topic_to_pubsub: Dict[str, str],
    value: Iterable[request.ScaleRequest],
    raise_if_invalid_request: Optional[bool] = True,
) -> Dict[str, List[request.ScaleRequest]]:
    result = {key: [] for key in topic_to_pubsub}
    for ndx, val in enumerate(value):
        # validate value
        if not isinstance(val, request.ScaleRequest):
            msg = f"Value '{val}'({type(val)})[{ndx}] is not a {request.ScaleRequest.__name__}"
            if raise_if_invalid_request:
                raise DispatchError(msg)
            _LOGGER.warning(msg)
            continue
        if val.topic not in topic_to_pubsub:
            msg = f"Value '{val}'[{ndx}] has a topic {val.topic} that is not present in {topic_to_pubsub}"
            if raise_if_invalid_request:
                raise DispatchError(msg)
            _LOGGER.warning(msg)
            continue
        # accumulate for routing
        result[val.topic].append(val)
    return result


async def _publish_requests(
    topic_to_pubsub: Dict[str, str],
    topic_to_request_lst: Dict[str, List[request.ScaleRequest]],
) -> None:
    for topic, req_lst in topic_to_request_lst.items():
        if req_lst:
            _LOGGER.debug(
                "Sending '%s' with '%d' request into topic '%s'",
                request.ScaleRequestCollection.__name__,
                len(req_lst),
                topic,
            )
            payload = request.ScaleRequestCollection.from_lst(req_lst)
            await pubsub.publish(payload.as_dict(), topic_to_pubsub.get(topic))
        else:
            _LOGGER.debug("There are no requests for topic '%s' to be sent out", topic)


def from_event(
    *,
    event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
) -> List[request.ScaleRequest]:
    """
    Just a convenient wrapper around :py:func:`pubsub.parse_pubsub`.

    Args:
        event:
        iso_str_timestamp:

    Returns:

    """
    result = _dto_from_event(
        event=event,
        iso_str_timestamp=iso_str_timestamp,
        result_type=request.ScaleRequestCollection,
    )
    return result.collection


def _dto_from_event(
    *,
    event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
    result_type: Type[dto_defaults.HasFromDict],
) -> Type[Any]:
    # validate input
    if not issubclass(result_type, dto_defaults.HasFromDict):
        raise TypeError(
            f"Type '{result_type.__name__}'({type(result_type)}) "
            f"must be a sub-class of '{dto_defaults.HasFromDict.__name__}'"
        )
    # logic

    def dict_to_obj_fn(  # pylint: disable=unused-argument
        value: Dict[str, Any], *args, **kwargs
    ) -> dto_defaults.HasFromDict:
        try:
            result = result_type.from_dict(value)
        except Exception as err_fn:
            raise RuntimeError(
                f"Could not extract '{result_type.__name__}' from dict '{value}'. Error: {err_fn}"
            ) from err_fn
        return result

    try:
        result = pubsub.parse_pubsub(
            event=event,
            dict_to_obj_fn=dict_to_obj_fn,
            iso_str_timestamp=iso_str_timestamp,
        )
    except Exception as err:
        raise RuntimeError(f"Could extract {result_type.__name__} from event '{event}'. Error: {err}") from err
    if not isinstance(result, result_type):
        raise ValueError(f"Parsed value is not an instance of {result_type.__name__}. Got: '{result}'({type(result)})")
    return result


def range_from_event(
    *,
    event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
) -> request.Range:
    """
    Extracts a range embedded into a Pub/Sub payload.

    Args:
        event:
        iso_str_timestamp:

    Returns:

    """
    return _dto_from_event(
        event=event,
        iso_str_timestamp=iso_str_timestamp,
        result_type=request.Range,
    )


def command_from_event(
    *,
    event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
) -> command.CommandBase:
    """
    Extracts a command embedded into a Pub/Sub payload.

    Args:
        event:
        iso_str_timestamp:

    Returns:

    """

    def dict_to_obj_fn(  # pylint: disable=unused-argument
        value: Dict[str, Any], *args, **kwargs
    ) -> command.CommandBase:
        try:
            result = command_parser.to_command(value)
        except Exception as err_fn:
            raise RuntimeError(
                f"Could not convert dict '{value}' to {command.CommandBase.__name__}. "
                f"Check {command_parser.__name__}.{command_parser.to_command.__name__}. "
                f"Error: {err_fn}"
            ) from err_fn
        return result

    try:
        result = pubsub.parse_pubsub(
            event=event,
            dict_to_obj_fn=dict_to_obj_fn,
            iso_str_timestamp=iso_str_timestamp,
        )
    except Exception as err:
        raise RuntimeError(f"Could extract {command.CommandBase.__name__} from event '{event}'. Error: {err}") from err
    if not isinstance(result, command.CommandBase):
        raise ValueError(
            f"Parsed value is not an instance of {command.CommandBase.__name__}. Got: '{result}'({type(result)})"
        )
    return result
