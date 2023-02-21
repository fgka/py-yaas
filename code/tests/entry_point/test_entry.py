# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pathlib
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import flask

import pytest

from yaas.dto import config, event, request
from yaas.event.store import base
from yaas.scaler import base as scaler_base
from yaas.entry_point import entry

from tests import common
from tests.dto import command_test_data

_TEST_REQUEST: request.ScaleRequest = common.create_scale_request()
_TEST_TOPIC_TO_PUBSUB: Dict[str, str] = {_TEST_REQUEST.topic: "test_pubsub_topic"}
_TEST_START_TS_UTC: int = 100
_TEST_END_TS_UTC: int = _TEST_START_TS_UTC + 1000


@pytest.mark.asyncio
async def test_process_command_ok_update_cal_credentials(monkeypatch):
    # Given
    kwargs = dict(
        value=command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CREDENTIALS_SECRET,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    called = False

    async def mocked_update_calendar_credentials(configuration: config.Config) -> None:
        nonlocal called, kwargs
        assert configuration == kwargs.get("configuration")
        called = True

    monkeypatch.setattr(
        entry,
        entry.update_calendar_credentials.__name__,
        mocked_update_calendar_credentials,
    )

    # When
    await entry.process_command(**kwargs)
    # Then
    assert called


@pytest.mark.asyncio
async def test_process_command_ok_update_cal_cache(monkeypatch):
    # Given
    kwargs = dict(
        value=command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CACHE,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    called = False

    async def mocked_update_cache(
        *,
        start_ts_utc: int,
        end_ts_utc: int,
        configuration: config.Config,
        merge_strategy: Optional[
            Callable[[event.EventSnapshotComparison], event.EventSnapshot]
        ] = None,
    ) -> None:
        nonlocal called, kwargs
        assert configuration == kwargs.get("configuration")
        cmd_range = kwargs.get("value").range
        assert int((end_ts_utc - start_ts_utc) / 60) == cmd_range.period_minutes
        assert merge_strategy is None
        called = True

    monkeypatch.setattr(
        entry,
        entry.update_cache.__name__,
        mocked_update_cache,
    )

    # When
    await entry.process_command(**kwargs)
    # Then
    assert called


@pytest.mark.asyncio
async def test_process_command_ok_send_scaling_reqs(monkeypatch):
    # Given
    kwargs = dict(
        value=command_test_data.TEST_COMMAND_SEND_SCALING_REQUESTS,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    called = False

    async def mocked_send_requests(
        *,
        start_ts_utc: int,
        end_ts_utc: int,
        configuration: config.Config,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> None:
        nonlocal called, kwargs
        assert configuration == kwargs.get("configuration")
        cmd_range = kwargs.get("value").range
        assert int((end_ts_utc - start_ts_utc) / 60) == cmd_range.period_minutes
        assert not raise_if_invalid_request
        called = True

    monkeypatch.setattr(
        entry,
        entry.send_requests.__name__,
        mocked_send_requests,
    )

    # When
    await entry.process_command(**kwargs)
    # Then
    assert called


@pytest.mark.asyncio
async def test_update_calendar_credentials_ok(monkeypatch):
    # Given
    called = _mock_entry(monkeypatch)
    kwargs = dict(
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    # When
    await entry.update_calendar_credentials(**kwargs)
    # Then
    await _verify_calendar_credentials_called(called)


def _mock_entry(
    monkeypatch,
    *,
    calendar_snapshot: Optional[event.EventSnapshot] = None,
    cache_store: Optional[base.StoreContextManager] = None,
    cache_snapshot: Optional[event.EventSnapshot] = None,
    event_requests: Optional[List[request.ScaleRequest]] = None,
) -> Dict[str, Any]:
    called = {}
    if cache_store is None:
        cache_store = common.MyStoreContextManager()

    async def mocked_update_secret_credentials(  # pylint: disable=unused-argument
        *,
        calendar_id: str,
        secret_name: str,
        initial_credentials_json: Optional[pathlib.Path] = None,
    ) -> None:
        nonlocal called
        called[entry.google_cal.update_secret_credentials.__name__] = locals()

    async def mocked_clean_up(  # pylint: disable=unused-argument
        value: config.DataRetentionConfig,
    ) -> Tuple[event.EventSnapshot, event.EventSnapshot]:
        nonlocal cache_store
        cache_store.called[base.StoreContextManager.clean_up.__name__] = locals()
        return cache_store.result_snapshot, cache_store.result_snapshot

    async def mocked_calendar_snapshot(  # pylint: disable=unused-argument
        *, calendar_id: str, secret_name: str, start_ts_utc: int, end_ts_utc: int
    ) -> event.EventSnapshot:
        nonlocal called, calendar_snapshot
        if calendar_snapshot is None:
            calendar_snapshot = common.create_event_snapshot("calendar")
        called[entry._calendar_snapshot.__name__] = locals()
        return calendar_snapshot

    async def mocked_cache_store_and_snapshot(  # pylint: disable=unused-argument
        *,
        cache_config: config.CacheConfig,
        start_ts_utc: int,
        end_ts_utc: int,
    ) -> Tuple[base.StoreContextManager, event.EventSnapshot]:
        nonlocal called, cache_snapshot, cache_store
        if cache_snapshot is None:
            cache_snapshot = common.create_event_snapshot("cache")
        called[entry._cache_store_and_snapshot.__name__] = locals()
        return cache_store, cache_snapshot

    async def mocked_dispatch(  # pylint: disable=unused-argument
        topic_to_pubsub: Dict[str, str],
        *value: request.ScaleRequest,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> None:
        nonlocal called
        called[entry.pubsub_dispatcher.dispatch.__name__] = locals()

    def mocked_from_event(  # pylint: disable=unused-argument
        *,
        event: Union[flask.Request, Dict[str, Any]],
        iso_str_timestamp: Optional[str] = None,
    ) -> List[request.ScaleRequest]:
        nonlocal called, event_requests
        if event_requests is None:
            event_requests = [
                common.create_scale_request(topic=common.MyCategoryType.CATEGORY_A.name)
            ]
        called[entry.pubsub_dispatcher.from_event.__name__] = locals()
        return event_requests

    monkeypatch.setattr(
        entry.google_cal,
        entry.google_cal.update_secret_credentials.__name__,
        mocked_update_secret_credentials,
    )
    monkeypatch.setattr(cache_store, cache_store.clean_up.__name__, mocked_clean_up)
    monkeypatch.setattr(
        entry, entry._calendar_snapshot.__name__, mocked_calendar_snapshot
    )
    monkeypatch.setattr(
        entry, entry._cache_store_and_snapshot.__name__, mocked_cache_store_and_snapshot
    )
    monkeypatch.setattr(
        entry.pubsub_dispatcher,
        entry.pubsub_dispatcher.dispatch.__name__,
        mocked_dispatch,
    )
    monkeypatch.setattr(
        entry.pubsub_dispatcher,
        entry.pubsub_dispatcher.from_event.__name__,
        mocked_from_event,
    )
    return called


async def _verify_calendar_credentials_called(called: Dict[str, Any]) -> None:
    called_update = called.get(entry.google_cal.update_secret_credentials.__name__)
    assert (
        called_update.get("calendar_id")
        == common.TEST_CONFIG_LOCAL_JSON.calendar_config.calendar_id
    )
    assert (
        called_update.get("secret_name")
        == common.TEST_CONFIG_LOCAL_JSON.calendar_config.secret_name
    )
    assert called_update.get("initial_credentials_json") is None


@pytest.mark.asyncio
async def test_update_cache_ok_no_change(monkeypatch):
    # Given
    called = _mock_entry(monkeypatch)
    kwargs = dict(
        start_ts_utc=_TEST_START_TS_UTC,
        end_ts_utc=_TEST_END_TS_UTC,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    # When
    await entry.update_cache(**kwargs)
    # Then
    await _verify_update_cal_cache_called(called, kwargs)


async def _verify_update_cal_cache_called(
    called: Dict[str, Any],
    kwargs: Dict[str, Any],
    expected_cache_store: event.EventSnapshot = None,
) -> None:
    # Then: calendar
    _verify_calendar_snapshot_called(
        called.get(entry._calendar_snapshot.__name__), kwargs
    )
    # Then: cache
    called_cache_snapshot = called.get(entry._cache_store_and_snapshot.__name__)
    _verify_cache_snapshot_called(called_cache_snapshot, kwargs)
    assert bool(
        called_cache_snapshot.get("cache_store").called.get(
            base.StoreContextManager.write.__name__
        )
    ) == bool(expected_cache_store is not None)
    assert called_cache_snapshot.get("cache_store").called.get(
        base.StoreContextManager.clean_up.__name__
    )
    if expected_cache_store is not None:
        # Then: store
        store_called = called_cache_snapshot.get("cache_store").called
        assert isinstance(store_called, dict)
        assert (
            store_called.get(base.StoreContextManager.write.__name__).get("value")
            == expected_cache_store
        )
        assert (
            store_called.get(base.StoreContextManager.clean_up.__name__).get("value")
            == common.TEST_CONFIG_LOCAL_JSON.retention_config
        )


def _verify_calendar_snapshot_called(
    called_calendar_snapshot: Dict[str, Any], kwargs: Dict[str, Any]
) -> None:
    assert isinstance(called_calendar_snapshot, dict)
    assert (
        called_calendar_snapshot.get("calendar_id")
        == kwargs["configuration"].calendar_config.calendar_id
    )
    assert (
        called_calendar_snapshot.get("secret_name")
        == kwargs["configuration"].calendar_config.secret_name
    )
    assert called_calendar_snapshot.get("start_ts_utc") == kwargs["start_ts_utc"]
    assert called_calendar_snapshot.get("end_ts_utc") == kwargs["end_ts_utc"]


def _verify_cache_snapshot_called(
    cache_snapshot: Dict[str, Any], kwargs: Dict[str, Any]
) -> None:
    assert isinstance(cache_snapshot, dict)
    assert cache_snapshot.get("cache_config") == kwargs["configuration"].cache_config
    assert cache_snapshot.get("start_ts_utc") == kwargs["start_ts_utc"]
    assert cache_snapshot.get("end_ts_utc") == kwargs["end_ts_utc"]


@pytest.mark.asyncio
async def test_update_cache_ok(monkeypatch):
    # Given
    expected = common.create_event_snapshot("calendar", [_TEST_START_TS_UTC + 1])
    cache_store = common.MyStoreContextManager()
    called = _mock_entry(
        monkeypatch, calendar_snapshot=expected, cache_store=cache_store
    )
    kwargs = dict(
        start_ts_utc=_TEST_START_TS_UTC,
        end_ts_utc=_TEST_END_TS_UTC,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    # When
    await entry.update_cache(**kwargs)
    # Then
    await _verify_update_cal_cache_called(called, kwargs, expected)


@pytest.mark.asyncio
async def test_send_requests_ok_empty(monkeypatch):
    # Given
    called = _mock_entry(monkeypatch)
    kwargs = dict(
        start_ts_utc=_TEST_START_TS_UTC,
        end_ts_utc=_TEST_END_TS_UTC,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    # When
    await entry.send_requests(**kwargs)
    # Then: cache
    called_calendar_snapshot = called.get(entry._cache_store_and_snapshot.__name__)
    _verify_cache_snapshot_called(called_calendar_snapshot, kwargs)
    assert not called_calendar_snapshot.get("cache_store").called
    # Then: dispatch
    called_dispatch = called.get(entry.pubsub_dispatcher.dispatch.__name__)
    assert not called_dispatch


@pytest.mark.asyncio
async def test_send_requests_ok(monkeypatch):
    # Given
    expected = common.create_event_snapshot("calendar", [_TEST_START_TS_UTC + 1])
    called = _mock_entry(monkeypatch, cache_snapshot=expected)
    kwargs = dict(
        start_ts_utc=_TEST_START_TS_UTC,
        end_ts_utc=_TEST_END_TS_UTC,
        configuration=common.TEST_CONFIG_LOCAL_JSON,
    )
    # When
    await entry.send_requests(**kwargs)
    # Then: cache
    called_calendar_snapshot = called.get(entry._cache_store_and_snapshot.__name__)
    _verify_cache_snapshot_called(called_calendar_snapshot, kwargs)
    assert not called_calendar_snapshot.get("cache_store").called
    # Then: dispatch
    called_dispatch = called.get(entry.pubsub_dispatcher.dispatch.__name__)
    assert list(called_dispatch.get("value")) == expected.all_requests()


@pytest.mark.asyncio
async def test_enact_requests_ok(monkeypatch):
    # Given
    parser = common.MyCategoryScaleRequestParser()
    pubsub_event = common.create_event(
        dict(key_a="value", key_b=123, key_c=dict(key_d=321)), True
    )
    iso_str_timestamp = None
    kwargs = dict(
        parser=parser,
        pubsub_event=pubsub_event,
        iso_str_timestamp=iso_str_timestamp,
    )
    called = _mock_entry(monkeypatch)
    # When
    await entry.enact_requests(**kwargs)
    # Then: from event
    called_from_event = called.get(entry.pubsub_dispatcher.from_event.__name__)
    assert isinstance(called_from_event, dict)
    assert called_from_event.get("event") == kwargs.get("pubsub_event")
    assert called_from_event.get("iso_str_timestamp") == kwargs.get("iso_str_timestamp")
    # Then: parser
    scaler_args = parser.obj_called.get(
        scaler_base.CategoryScaleRequestParser._scaler.__name__
    )
    assert isinstance(scaler_args, dict)
    assert scaler_args.get("result").called.get(scaler_base.Scaler._safe_enact.__name__)
