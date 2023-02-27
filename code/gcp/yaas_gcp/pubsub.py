# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Manages PubSub boilerplate. How to parse the data and publish it.
* https://cloud.google.com/pubsub/docs/push
* https://cloud.google.com/pubsub/docs/publisher

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364
"""
# pylint: enable=line-too-long
import asyncio
import base64
import calendar
from concurrent import futures
from datetime import datetime
import json
from typing import Any, Callable, Dict, List, Optional, Union

import cachetools
import flask

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from yaas_common import const, logger
from yaas_gcp import resource_name

_PUBSUB_NAME_TOKENS: List[str] = ["projects", "topics"]
_EVENT_MESSAGE_KEY: str = "message"
_EVENT_MESSAGE_DATA_KEY: str = "data"
_MESSAGE_PUBLISH_TIME_KEY: str = "publish_time"
_LOGGER = logger.get(__name__)


def validate_topic_id(value: str) -> None:
    """
    Verify that the value comply with the pattern: ``projects/my-new-project/topics/my-topic``.
    Args:
        value:

    Returns:

    """
    resource_name.validate_resource_name(
        value=value, tokens=_PUBSUB_NAME_TOKENS, raise_if_invalid=True
    )


def parse_pubsub(
    *,
    event: Union[flask.Request, Dict[str, Any]],
    dict_to_obj_fn: Callable[[Dict[str, Any], int], Any],
    iso_str_timestamp: Optional[str] = None,
) -> Any:
    """
    This will parse either Cloud Run (wrapped in a :py:class:`flask.Request`)
        or Cloud Function (wrapped in a py:class:`dict`) Pub/Sub messages.

    Example that works with Cloud Run and Cloud Function::
        def dict_to_obj_fn(value: Dict[str, Any], timestamp: int) -> Any:
            kwargs = {
                **value,
                **dict(timestamp=timestamp),
            }
            return MyClass(**kwargs)

        def handler(
            event: Optional[Union[flask.Request, Dict[str, Any]]] = None,
            context: Optional[Any] = None
        ) -> None:
            iso_str_timestamp = None
            if context is not None:
                iso_str_timestamp = context.timestamp
            my_obj = parse_pubsub(
                event=event, dict_to_obj_fn=dict_to_obj_fn, iso_str_timestamp=iso_str_timestamp
            )

    Args:
        event:
            A Pub/Sub message wrapping.
        dict_to_obj_fn:
            After extracting the payload, will be called to create the corresponding object.
        iso_str_timestamp:
            To allow for a Cloud Function trigger,
            where the timestamp (a ISO formatted string) is in the context object.

    Returns:

    """
    # if it is flask wrapped
    actual_event = event
    if isinstance(event, flask.Request):
        _LOGGER.debug("Event is of type %s. Extracting JSON payload.", type(event))
        actual_event = event.get_json()
    # validate input
    if not isinstance(actual_event, dict):
        raise TypeError(
            f"Actual event <{actual_event}>({type(actual_event)}) must be a {dict.__name__} "
            f"(from <{event}>({type(event)})"
        )
    if not callable(dict_to_obj_fn):
        raise TypeError(
            f"The conversion function argument is not callable. "
            f"Got: <{dict_to_obj_fn}>({type(dict_to_obj_fn)})"
        )
    # logic
    message = actual_event.get(_EVENT_MESSAGE_KEY)
    timestamp = datetime.utcnow().timestamp()
    # is it an HTTP triggered function?
    if isinstance(message, dict):
        data = message.get(_EVENT_MESSAGE_DATA_KEY)
        timestamp = _extract_timestamp_from_iso_str(
            message.get(_MESSAGE_PUBLISH_TIME_KEY)
        )
    else:
        data = actual_event.get(_EVENT_MESSAGE_DATA_KEY)
        if iso_str_timestamp is not None:
            timestamp = _extract_timestamp_from_iso_str(iso_str_timestamp)
    obj_dict = _parse_json_data(data)
    try:
        result = dict_to_obj_fn(obj_dict, timestamp)
    except Exception as err:
        raise RuntimeError(
            f"Could not call converter function <{dict_to_obj_fn.__name__}> "
            f"with: <{obj_dict}> and <{timestamp}>. "
            f"Error: {err}"
        ) from err
    return result


def _extract_timestamp_from_iso_str(value: str) -> int:
    # Zulu timezone = UTC
    # https://en.wikipedia.org/wiki/List_of_military_time_zones
    plain_iso_dateime = value.removesuffix("Z").split(".")[0] + "+00:00"
    try:
        result: int = calendar.timegm(
            datetime.fromisoformat(plain_iso_dateime).utctimetuple()
        )
    except Exception as err:  # pylint: disable=broad-except
        raise RuntimeError(
            f"Could not extract timestamp from <{value}>({type(value)}). Error: {err}"
        ) from err
    return result


def _parse_json_data(value: Union[str, bytes]) -> Any:
    """
    Parses a Pub/Sub base64 JSON coded :py:class:`str`.

    Args:
        value:
            The raw payload from Pub/Sub.

    Returns:

    """
    # parse PubSub payload
    str_data = None
    try:
        str_data = _parse_str_data(value)
        if isinstance(str_data, str):
            result = json.loads(str_data)
        else:
            raise RuntimeError(f"Could not parse input value <{value}>")
    except Exception as err:
        raise RuntimeError(
            f"Could not parse PubSub JSON data. Raw data: <{value}>, string data: <{str_data}>. "
            f"Error: {err}"
        ) from err
    return result


def _parse_str_data(value: Union[str, bytes]) -> str:
    """
    Parses a Pub/Sub base64 coded :py:class:`str`.

    Args:
        value:
            The raw payload from Pub/Sub.

    Returns:
        JSON encoded string.
    """
    # parse PubSub payload
    if not isinstance(value, (bytes, str)):
        raise TypeError(
            f"Event data is not a {str.__name__} or {bytes.__name__}. "
            f"Got: <{value}>({type(value)})"
        )
    try:
        result = base64.b64decode(value).decode(const.ENCODING_UTF8)
    except Exception as err:
        raise RuntimeError(
            f"Could not parse PubSub string data. Raw data: <{value}>. Error: {err}"
        ) from err
    return result


async def publish(value: Dict[str, Any], topic_id: str) -> None:
    """
    Converts argument to a string to be published to a Pub/Sub topic.

    Args:
        value:
        topic_id:

    Returns:

    """
    # validate input
    if not isinstance(value, dict):
        raise TypeError(
            f"Value must be a {dict.__name__}. Got <{value}>({type(value)})"
        )
    validate_topic_id(topic_id)
    # logic
    _LOGGER.debug("Publishing data <%s> into topic <%s>", value, topic_id)
    json_str = json.dumps(value)
    data = json_str.encode(const.ENCODING_UTF8)
    publish_future = _client().publish(topic_id, data)
    await asyncio.sleep(0)
    futures.wait([publish_future], return_when=futures.ALL_COMPLETED)
    _LOGGER.debug("Published data <%s> into topic <%s>", value, topic_id)


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _client() -> pubsub_v1.PublisherClient:
    flow_control = types.PublishFlowControl(
        limit_exceeded_behavior=types.LimitExceededBehavior.BLOCK
    )
    return pubsub_v1.PublisherClient(
        publisher_options=types.PublisherOptions(flow_control=flow_control)
    )
