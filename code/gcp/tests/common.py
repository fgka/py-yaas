# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import base64
import json
import pathlib
from typing import Any, Dict, Optional, Union

import flask

from yaas_common import const, request
from yaas_gcp import pubsub

#############
# Test Data #
#############

_TEST_DATA_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.joinpath(
    "test_data"
)
TEST_DATA_CONFIG_JSON: pathlib.Path = _TEST_DATA_DIR / "config.json"

################
# ScaleRequest #
################


_TEST_SCALE_REQUEST_KWARGS: Dict[str, Any] = dict(
    topic="TEST_TOPIC",
    resource="TEST_RESOURCE",
    command="TEST_COMMAND 123",
    timestamp_utc=123,
    original_json_event="TEST_ORIGINAL_JSON_EVENT",
)


def create_scale_request(**kwargs) -> request.ScaleRequest:
    """
    Create a default :py:class:`request.ScaleRequest` using ``kwargs`` to overwrite defaults.

    Args:
        **kwargs:

    Returns:

    """
    scale_kwargs = {
        **_TEST_SCALE_REQUEST_KWARGS,
        **kwargs,
    }
    return request.ScaleRequest(**scale_kwargs)


##########
# PubSub #
##########


class _MyRequest(flask.Request):
    def __init__(  # pylint: disable=super-init-not-called
        self, json_payload: Optional[Any] = None
    ):
        self.called = {}
        self._json_payload = json_payload

    def get_json(self) -> str:  # pylint: disable=arguments-differ
        self.called[_MyRequest.get_json.__name__] = True
        return self._json_payload

    def __repr__(self) -> str:
        return _MyRequest.__name__


_TEST_ISO_DATE_STR_PREFIX: str = "2022-01-31T11:01:38"


def create_event(
    obj_dict: Dict[str, Any],
    as_request: bool,
    publish_date_str: Optional[str] = _TEST_ISO_DATE_STR_PREFIX,
):
    data = create_event_str(obj_dict, as_bytes=not as_request)
    if as_request:
        payload = {
            pubsub._EVENT_MESSAGE_KEY: {
                pubsub._EVENT_MESSAGE_DATA_KEY: data,
                pubsub._MESSAGE_PUBLISH_TIME_KEY: publish_date_str,
            }
        }
        result = _MyRequest(payload)
    else:
        result = {pubsub._EVENT_MESSAGE_DATA_KEY: data}
    return result


def create_event_str(data: Any, as_bytes: Optional[bool] = True) -> Union[str, bytes]:
    result = base64.b64encode(bytes(json.dumps(data).encode(const.ENCODING_UTF8)))
    if not as_bytes:
        result = result.decode(encoding=const.ENCODING_UTF8)
    return result
