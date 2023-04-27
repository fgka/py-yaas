# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,protected-access,too-few-public-methods,invalid-name,missing-class-docstring
# type: ignore
from datetime import datetime, timedelta
from typing import List

import caldav
import pytest
from googleapiclient import discovery, http  # pylint: disable=unused-import; # noqa: F401

from yaas_calendar import dav


@pytest.mark.parametrize("now_drift_in_hours", [0, -13, 11])
def test__to_utc_datetime_ok_none_with_drift(now_drift_in_hours: int):
    min_exp = datetime.utcnow() + timedelta(hours=now_drift_in_hours)
    max_exp = datetime.utcnow() + timedelta(hours=now_drift_in_hours, minutes=10)
    result = dav._to_utc_datetime(None, now_drift_in_hours=now_drift_in_hours)
    assert max_exp >= result >= min_exp


@pytest.mark.asyncio
async def test__fetch_events_ok(monkeypatch):
    # Given
    cal = caldav.Calendar()
    start_time = datetime.utcfromtimestamp(0)
    end_time = datetime.utcfromtimestamp(123)
    expected = caldav.Event(id="TEST_EVENT")

    def mocked_search(start=None, end=None, event: bool = None, expand: bool = None):
        nonlocal start_time, end_time, expected
        assert start == start_time
        assert end == end_time
        assert event is True
        assert expand is True
        return [expected]

    monkeypatch.setattr(cal, caldav.Calendar.search.__name__, mocked_search)
    # When
    result = [item async for item in dav._fetch_events(cal, start_time, end_time)]
    # Then
    assert result
    assert len(result) == 1
    assert result[0] == expected


class _MyCalendar:
    def __init__(self, events: List[caldav.Event]):
        self.url = "test_url"
        self.called = None
        self.events = events

    def search(self, start: int, end: int, event: bool, expand: bool) -> List[caldav.Event]:
        self.called = locals()
        return self.events


class _MyPrincipal:
    def __init__(self, calendar: _MyCalendar):
        self.result = calendar
        self.called = None

    def calendar(self, cal_url: str) -> _MyCalendar:
        self.called = cal_url
        return self.result


class _MyDavClient:
    def __init__(self, principal: _MyPrincipal):
        self.result = principal

    def principal(self) -> _MyPrincipal:
        return self.result


def _create_client(amount_events: int = 123) -> _MyDavClient:
    events = [caldav.Event(id=f"test_event_id_{ndx}") for ndx in range(amount_events)]
    calendar = _MyCalendar(events)
    principal = _MyPrincipal(calendar)
    return _MyDavClient(principal)


@pytest.mark.asyncio
async def test_list_upcoming_events_ok(monkeypatch):
    # Given
    arg_url = "test_url"
    arg_username = "test_username"
    arg_secret_name = "test_secret_name"
    arg_password = "test_password"
    arg_amount = 10
    arg_start = datetime.utcnow()
    arg_end = datetime.utcnow() + timedelta(days=10)
    arg_client = _create_client(arg_amount + 11)

    async def mocked_secrets_get(value: str) -> str:
        nonlocal arg_secret_name, arg_password
        assert value == arg_secret_name
        return arg_password

    def mocked_client(url: str, username: str, password: str) -> caldav.DAVClient:
        nonlocal arg_url, arg_username, arg_password, arg_client
        assert url == arg_url
        assert username == arg_username
        assert password == arg_password
        return arg_client

    monkeypatch.setattr(dav.secrets, dav.secrets.get.__name__, mocked_secrets_get)
    monkeypatch.setattr(dav, dav._client.__name__, mocked_client)

    # When
    result = [
        item
        async for item in dav.list_upcoming_events(
            url=arg_url,
            username=arg_username,
            secret_name=arg_secret_name,
            amount=arg_amount,
            start=arg_start,
            end=arg_end,
        )
    ]
    # Then
    assert len(result) == arg_amount
    # Then: principal
    principal_called = arg_client.result.called
    assert principal_called == arg_url
    # Then: calendar
    calendar_called = arg_client.result.result.called
    assert calendar_called
    assert calendar_called.get("start") == arg_start
    assert calendar_called.get("end") == arg_end
    assert calendar_called.get("event") is True
    assert calendar_called.get("expand") is True
