# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import base64
import json
import pathlib
import tempfile
from typing import Any, Dict, List, Optional, Union

import flask

from yaas_common import const, request
from yaas_config import config
from yaas_caching import base, event
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


#################
# EventSnapshot #
#################


def create_event_snapshot(
    source: str, ts_list: Optional[List[int]] = None
) -> event.EventSnapshot:
    """
    Creates an :py:class:`event.EventSnapshot` instance.

    Args:
        source:
        ts_list:

    Returns:

    """
    timestamp_to_request = {}
    if ts_list:
        for ts in ts_list:
            timestamp_to_request[ts] = [
                create_scale_request(
                    topic="topic",
                    resource="resource",
                    command=f"{source} = {ts}",
                    timestamp_utc=ts,
                )
            ]
    return event.EventSnapshot(source=source, timestamp_to_request=timestamp_to_request)


TEST_CALENDAR_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="calendar")
TEST_CACHE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="cache")
TEST_COMPARISON_SNAPSHOT: event.EventSnapshotComparison = event.EventSnapshotComparison(
    snapshot_a=TEST_CALENDAR_SNAPSHOT,
    snapshot_b=TEST_CACHE_SNAPSHOT,
)
TEST_COMPARISON_SNAPSHOT_NON_EMPTY: event.EventSnapshotComparison = (
    event.EventSnapshotComparison(
        snapshot_a=TEST_CALENDAR_SNAPSHOT,
        snapshot_b=TEST_CACHE_SNAPSHOT,
        only_in_a=create_event_snapshot(source="onlu_in_a", ts_list=[123]),
    )
)
TEST_MERGE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="merge")


#######################
# StoreContextManager #
#######################


def tmpfile(
    *, existing: Optional[bool] = False, chmod: Optional[int] = None
) -> pathlib.Path:
    if chmod is not None:
        existing = True
    with tempfile.NamedTemporaryFile(delete=not existing) as tmp_file:
        result = pathlib.Path(tmp_file.name)
    if chmod is not None:
        result.chmod(chmod)
    return result


class MyStoreContextManager(base.StoreContextManager):
    def __init__(
        self,
        result_snapshot: event.EventSnapshot = create_event_snapshot("test"),
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.result_snapshot = result_snapshot
        self.called = {}
        self.to_raise = set()

    async def _open(self) -> None:
        self.called[base.StoreContextManager._open.__name__] = True

    async def _close(self) -> None:
        self.called[base.StoreContextManager._close.__name__] = True

    async def _read(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.read.__name__] = locals()
        if base.StoreContextManager.read.__name__ in self.to_raise:
            raise RuntimeError
        return self.result_snapshot

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        self.called[base.StoreContextManager.write.__name__] = locals()
        if base.StoreContextManager.write.__name__ in self.to_raise:
            raise RuntimeError

    async def _remove(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.remove.__name__] = locals()
        if base.StoreContextManager.remove.__name__ in self.to_raise:
            raise RuntimeError
        return self.result_snapshot

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.archive.__name__] = locals()
        if base.StoreContextManager.archive.__name__ in self.to_raise:
            raise RuntimeError
        return self.result_snapshot


##########
# Config #
##########


_TEST_PUBSUB_TOPIC: str = "test_yaas_pubsub_topic"

# pylint: disable=consider-using-with
TEST_CONFIG_LOCAL_JSON: config.Config = config.Config(
    calendar_config=config.CalendarCacheConfig(
        type=config.CacheType.CALENDAR.value,
        calendar_id="test_calendar_id",
        secret_name="test_calendar_secret_name",
    ),
    cache_config=config.LocalJsonLineCacheConfig(
        type=config.CacheType.LOCAL_JSON_LINE.value,
        json_line_file=tempfile.NamedTemporaryFile().name,
        archive_json_line_file=tempfile.NamedTemporaryFile().name,
    ),
    topic_to_pubsub={
        "yaas": _TEST_PUBSUB_TOPIC,
        "standard": _TEST_PUBSUB_TOPIC,
    },
)


# pylint: enable=consider-using-with


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
