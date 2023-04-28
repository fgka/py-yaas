# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,redefined-outer-name,attribute-defined-outside-init
# pylint: disable=protected-access
# type: ignore
import asyncio
import pathlib
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import icalendar
import pytest

from tests import common
from yaas_caching import calendar, event
from yaas_common import request

_TEST_CALENDAR_SOURCE: str = "TEST_CALENDAR_SOURCE"
_TEST_EVENTS: List[Union[Dict[str, Any], icalendar.Calendar]] = [
    {"key": "value"},
    icalendar.Calendar(id="TEST_CALENDAR_ID"),
]


class _MyReadOnlyBaseCalendarStore(calendar.ReadOnlyBaseCalendarStore):
    def __init__(
        self,
        *,
        calendar_source: Optional[str] = _TEST_CALENDAR_SOURCE,
        events: Optional[Union[Dict[str, Any], icalendar.Calendar]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._calendar_source = calendar_source
        self.events = events

    def calendar_source(self) -> str:
        return self._calendar_source

    async def _calendar_events(
        self, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> AsyncGenerator[Union[Dict[str, Any], icalendar.Calendar], None]:
        if self.events is None:
            return
        for event in self.events:
            yield event
            await asyncio.sleep(0)


_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request()


class TestReadOnlyBaseCalendarStore:
    def setup_method(self):
        self.object = _MyReadOnlyBaseCalendarStore(
            calendar_source=_TEST_CALENDAR_SOURCE,
        )

    def test_calendar_source_ok(self):
        # Given/When
        result = self.object.calendar_source()
        # Then
        assert result == _TEST_CALENDAR_SOURCE

    @pytest.mark.asyncio
    async def test_read_ok(self, monkeypatch):
        # Given
        start_ts_utc = 0
        end_ts_utc = start_ts_utc + 123
        event_lst = _TEST_EVENTS
        self.object.events = event_lst

        def mocked_to_request(*, event: Dict[str, Any]) -> List[request.ScaleRequest]:
            assert event in event_lst
            return [_TEST_SCALE_REQUEST]

        monkeypatch.setattr(calendar.parser, calendar.parser.to_request.__name__, mocked_to_request)

        # When
        async with self.object:
            result = await self.object.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert result.source == self.object.calendar_source()
        assert len(result.timestamp_to_request) == 1
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0] == _TEST_SCALE_REQUEST


_TEST_CALENDAR_ID: str = "TEST_CALENDAR_ID"
# pylint: disable=consider-using-with
_TEST_CREDENTIALS_JSON: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
# pylint: enable=consider-using-with
_TEST_SECRET_NAME: str = "test_secret_name"


class TestReadOnlyGoogleCalendarStore:
    def setup_method(self):
        self.object = calendar.ReadOnlyGoogleCalendarStore(
            calendar_id=_TEST_CALENDAR_ID,
            credentials_json=_TEST_CREDENTIALS_JSON,
        )

    def test_ctor_nok_without_either_credentials_or_secret(self):
        with pytest.raises(TypeError):
            calendar.ReadOnlyGoogleCalendarStore(
                calendar_id=_TEST_CALENDAR_ID,
                secret_name=None,
                credentials_json=None,
            )

    def test_properties_ok(self):
        assert self.object.calendar_id == _TEST_CALENDAR_ID
        assert self.object.calendar_source() == self.object.calendar_id
        assert self.object.credentials_json == _TEST_CREDENTIALS_JSON

    @pytest.mark.asyncio
    async def test__calendar_events_ok(self, monkeypatch):
        # Given
        start_ts_utc = 0
        end_ts_utc = start_ts_utc + 123
        event_lst = [{"key_a": "value_a"}, {"key_b": "value_b"}]

        async def mocked_list_upcoming_events(**kwargs) -> AsyncGenerator[Dict[str, Any], None]:
            assert kwargs.get("calendar_id") == self.object.calendar_id
            assert kwargs.get("credentials_json") == self.object.credentials_json
            assert kwargs.get("start") == start_ts_utc
            assert kwargs.get("end") == end_ts_utc
            for event in event_lst:
                yield event
                await asyncio.sleep(0)

        monkeypatch.setattr(
            calendar.google_cal,
            calendar.google_cal.list_upcoming_events.__name__,
            mocked_list_upcoming_events,
        )

        # When
        async with self.object:
            result = [
                item async for item in self.object._calendar_events(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
            ]
        # Then
        assert len(result) == len(event_lst)
        for item in result:
            assert item in event_lst


_TEST_CALDAV_URL: str = "https://www.example/dav/v1/calendar_id"
_TEST_USERNAME: str = "test_username"


class TestReadOnlyCalDavStore:
    def setup_method(self):
        self.object = calendar.ReadOnlyCalDavStore(
            caldav_url=_TEST_CALDAV_URL,
            username=_TEST_USERNAME,
            secret_name=_TEST_SECRET_NAME,
        )

    def test_properties_ok(self):
        assert self.object.caldav_url == _TEST_CALDAV_URL
        assert self.object.calendar_source() == self.object.caldav_url
        assert self.object.username == _TEST_USERNAME
        assert self.object.secret_name == _TEST_SECRET_NAME

    @pytest.mark.asyncio
    async def test__calendar_events_ok(self, monkeypatch):
        # Given
        start_ts_utc = 0
        end_ts_utc = start_ts_utc + 123
        event_lst = [icalendar.Calendar(id="calendar_a"), icalendar.Calendar(id="calendar_b")]

        async def mocked_list_upcoming_events(**kwargs) -> AsyncGenerator[Dict[str, Any], None]:
            assert kwargs.get("url") == self.object.caldav_url
            assert kwargs.get("username") == self.object.username
            assert kwargs.get("secret_name") == self.object.secret_name
            assert kwargs.get("start") == start_ts_utc
            assert kwargs.get("end") == end_ts_utc
            for event in event_lst:
                yield event
                await asyncio.sleep(0)

        monkeypatch.setattr(
            calendar.dav,
            calendar.dav.list_upcoming_events.__name__,
            mocked_list_upcoming_events,
        )

        # When
        async with self.object:
            result = [
                item async for item in self.object._calendar_events(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
            ]
        # Then
        assert len(result) == len(event_lst)
        for item in result:
            assert item in event_lst


def test_ReadOnlyGoogleCalDavStore_ctor_ok():  # pylint: disable=invalid-name
    # Given
    exp_url = calendar.dav.GOOGLE_DAV_URL_TMPL % _TEST_CALENDAR_ID
    # When
    instance = calendar.ReadOnlyGoogleCalDavStore(
        calendar_id=_TEST_CALENDAR_ID, username=_TEST_USERNAME, secret_name=_TEST_SECRET_NAME
    )
    # Then
    assert instance.caldav_url == exp_url
    assert instance.calendar_source() == exp_url
    assert instance.username == _TEST_USERNAME
    assert instance.secret_name == _TEST_SECRET_NAME
