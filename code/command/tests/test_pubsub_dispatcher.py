# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Callable, Dict, Optional, Union

import flask
import pytest

from yaas_common import dto_defaults, request
from yaas_command import pubsub_dispatcher

from tests import common
from tests import command_test_data

_TEST_REQUEST: request.ScaleRequest = common.create_scale_request()
_TEST_TOPIC_TO_PUBSUB: Dict[str, str] = {_TEST_REQUEST.topic: "test_pubsub_topic"}


class _MyPubSub:
    def __init__(self):
        self.messages = {}
        self.called = {}

    async def publish(self, value: Dict[str, Any], topic_path: str) -> None:
        self.called[_MyPubSub.publish.__name__] = locals()
        if topic_path not in self.messages:
            self.messages[topic_path] = []
        self.messages[topic_path].append(value)

    def parse_pubsub(
        self,
        *,
        event: Union[flask.Request, Dict[str, Any]],
        dict_to_obj_fn: Callable[[Dict[str, Any], int], Any],
        iso_str_timestamp: Optional[str] = None,
    ) -> Any:
        self.called[_MyPubSub.parse_pubsub.__name__] = locals()
        return dict_to_obj_fn(event, iso_str_timestamp)


@pytest.mark.asyncio
async def test_dispatch_ok(monkeypatch):
    # Given
    pubsub = _MyPubSub()
    topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
    req = _TEST_REQUEST

    async def mocked_publish(value: Dict[str, Any], topic_path: str) -> None:
        nonlocal pubsub
        await pubsub.publish(value, topic_path)

    monkeypatch.setattr(
        pubsub_dispatcher.pubsub,
        pubsub_dispatcher.pubsub.publish.__name__,
        mocked_publish,
    )
    # When
    await pubsub_dispatcher.dispatch(
        topic_to_pubsub, req, raise_if_invalid_request=True
    )
    # Then
    messages = pubsub.messages.get(topic_to_pubsub.get(req.topic))
    assert len(messages) == 1
    obj = request.ScaleRequestCollection.from_dict(messages[0])
    assert len(obj.collection) == 1
    assert obj.collection[0] == req.clone(original_json_event=None)


@pytest.mark.asyncio
async def test_dispatch_nok_no_mapping():
    with pytest.raises(TypeError):
        await pubsub_dispatcher.dispatch(None, _TEST_REQUEST)


@pytest.mark.asyncio
async def test_dispatch_nok_value_wrong_type():
    with pytest.raises(pubsub_dispatcher.DispatchError):
        await pubsub_dispatcher.dispatch(
            _TEST_TOPIC_TO_PUBSUB,
            _TEST_REQUEST,
            None,
            _TEST_REQUEST,
            raise_if_invalid_request=True,
        )


@pytest.mark.asyncio
async def test_dispatch_nok_topic_not_present():
    with pytest.raises(pubsub_dispatcher.DispatchError):
        await pubsub_dispatcher.dispatch(
            _TEST_TOPIC_TO_PUBSUB,
            _TEST_REQUEST.clone(topic=_TEST_REQUEST.topic + "_NOT"),
            raise_if_invalid_request=True,
        )


@pytest.mark.parametrize(
    "value",
    [
        _TEST_REQUEST,
        request.ScaleRequestCollection.from_lst([_TEST_REQUEST]),
        command_test_data.TEST_COMMAND_SEND_SCALING_REQUESTS,
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CACHE,
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CREDENTIALS_SECRET,
        request.Range(period_minutes=10, now_diff_minutes=-1),
    ],
)
def test__dto_from_event_ok(monkeypatch, value: dto_defaults.HasFromDict):
    # Given
    pubsub = _MyPubSub()

    def mocked_parse_pubsub(
        *,
        event: Union[flask.Request, Dict[str, Any]],
        dict_to_obj_fn: Callable[[Dict[str, Any], int], Any],
        iso_str_timestamp: Optional[str] = None,
    ) -> Any:
        nonlocal pubsub
        return pubsub.parse_pubsub(
            event=event,
            dict_to_obj_fn=dict_to_obj_fn,
            iso_str_timestamp=iso_str_timestamp,
        )

    monkeypatch.setattr(
        pubsub_dispatcher.pubsub,
        pubsub_dispatcher.pubsub.parse_pubsub.__name__,
        mocked_parse_pubsub,
    )
    # When
    result = pubsub_dispatcher._dto_from_event(
        event=value.as_dict(), result_type=value.__class__
    )
    # Then
    assert isinstance(result, value.__class__)


def test_from_event_ok(monkeypatch):
    # Given
    pubsub = _MyPubSub()
    req = _TEST_REQUEST

    def mocked_parse_pubsub(
        *,
        event: Union[flask.Request, Dict[str, Any]],
        dict_to_obj_fn: Callable[[Dict[str, Any], int], Any],
        iso_str_timestamp: Optional[str] = None,
    ) -> Any:
        nonlocal pubsub
        return pubsub.parse_pubsub(
            event=event,
            dict_to_obj_fn=dict_to_obj_fn,
            iso_str_timestamp=iso_str_timestamp,
        )

    monkeypatch.setattr(
        pubsub_dispatcher.pubsub,
        pubsub_dispatcher.pubsub.parse_pubsub.__name__,
        mocked_parse_pubsub,
    )
    # When
    result = pubsub_dispatcher.from_event(
        event=request.ScaleRequestCollection.from_lst([req]).as_dict()
    )
    # Then
    assert isinstance(result, list)
    assert result[0] == req.clone(original_json_event=None)
