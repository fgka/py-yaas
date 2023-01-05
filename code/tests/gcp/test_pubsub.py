# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import json
from typing import Any, Dict, List, Optional

import pytest

from yaas import const
from yaas.gcp import pubsub

from tests import common

_ISO_DATE_STR_PREFIX: str = "2022-10-07T11:01:38"
_ISO_DATE_TO_TS: str = 1665140498


@pytest.mark.parametrize(
    "value,expected",
    [
        (_ISO_DATE_STR_PREFIX, _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".1", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".12", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".123", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + "Z", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".1Z", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".12Z", _ISO_DATE_TO_TS),
        (_ISO_DATE_STR_PREFIX + ".123Z", _ISO_DATE_TO_TS),
    ],
)
def test__extract_timestamp_from_iso_str_ok(value: str, expected: int):
    # Given/When
    result = pubsub._extract_timestamp_from_iso_str(value)
    # Then
    assert result == expected


_TEST_VALUE_DICT: Dict[str, Any] = dict(key_a="value", key_b=123, key_c=dict(key_d=321))


@pytest.mark.parametrize(
    "expected,asbytes",
    [
        (_TEST_VALUE_DICT, False),
        (_TEST_VALUE_DICT, True),
    ],
)
def test__parse_json_data_ok(expected: Any, asbytes: bool):
    # Given
    value = common.create_event_str(expected, asbytes)
    # When
    result = pubsub._parse_json_data(value)
    # Then
    assert result == expected


@pytest.mark.parametrize(
    "exp_obj_dict,as_request",
    [
        (_TEST_VALUE_DICT, False),
        (_TEST_VALUE_DICT, True),
    ],
)
def test_parse_pubsub_ok(exp_obj_dict: Dict[str, Any], as_request: bool):
    # Given
    publish_date_str = _ISO_DATE_STR_PREFIX
    event = common.create_event(
        exp_obj_dict, as_request, publish_date_str=publish_date_str
    )
    called = {}
    expected = "TEST_EXPECTED"

    def dict_to_obj_fn(obj_dict: Dict[str, Any], timestamp: int) -> Any:
        nonlocal called
        called[dict_to_obj_fn.__name__] = True
        assert timestamp == _ISO_DATE_TO_TS
        assert obj_dict == exp_obj_dict
        return expected

    # When
    result = pubsub.parse_pubsub(
        event=event,
        dict_to_obj_fn=dict_to_obj_fn,
        iso_str_timestamp=publish_date_str,
    )
    # Then
    assert result == expected
    assert called.get(dict_to_obj_fn.__name__)


class _MyClient:
    def __init__(self, result: Optional[Any] = "FUTURES"):
        self._result = result
        self.called = {}

    def publish(self, topic_path: str, data: str) -> Any:
        self.called[_MyClient.publish.__name__] = topic_path, data
        return self._result


_TEST_VALUE: Dict[str, Any] = dict(key="TEST_VALUE")
_TEST_TOPIC_PATH: str = "TEST_TOPIC_PATH"


@pytest.mark.asyncio
async def test_publish_ok(monkeypatch):
    # Given
    result_publish = "TEST_PUBLISH"
    client = _MyClient(result_publish)
    called = {}

    def mocked_client() -> _MyClient:
        called[mocked_client.__name__] = True
        return client

    def mocked_wait(  # pylint: disable=unused-argument
        lst_futures: List[Any], **kwargs
    ) -> None:
        called[mocked_wait.__name__] = True
        assert result_publish in lst_futures

    monkeypatch.setattr(pubsub, pubsub._client.__name__, mocked_client)
    monkeypatch.setattr(pubsub.futures, pubsub.futures.wait.__name__, mocked_wait)
    # When
    await pubsub.publish(_TEST_VALUE, _TEST_TOPIC_PATH)
    # Then
    topic_path, data = client.called.get(_MyClient.publish.__name__)
    assert topic_path == _TEST_TOPIC_PATH
    assert data == bytes(json.dumps(_TEST_VALUE), encoding=const.ENCODING_UTF8)
    assert called.get(mocked_client.__name__)
    assert called.get(mocked_wait.__name__)
