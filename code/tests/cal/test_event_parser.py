# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from datetime import datetime
from typing import Any, Dict, Tuple

import pytz

import pytest

from yaas.cal import event_parser
from yaas.dto import request

_TEST_EVENT_START_TIME: str = "2022-10-18T16:00:00+02:00"
_TEST_EVENT_DESCRIPTION_TMPL: str = "Description event repeat daily<br>%s<br>"
# pylint: disable=line-too-long
_TEST_EVENT: Dict[str, Any] = {
    "kind": "cal#event",
    "etag": '"3332030328331000"',
    "id": "3johpi0lpma4f08f9p2n4vleu4_20221018T140000Z",
    "status": "confirmed",
    "htmlLink": "https://www.google.com/calendar/event?eid=M2pvaHBpMGxwbWE0ZjA4ZjlwMm40dmxldTRfMjAyMjEwMThUMTQwMDAwWiBhamJlZm80cnQ0ajhtdGQ4MDhwaTRnaTV1Y0Bn",
    "created": "2022-10-17T13:54:04.000Z",
    "updated": "2022-10-17T13:59:25.067Z",
    "summary": "Event repeat daily",
    "description": "",
    "creator": {"email": "yaas.scaler@gmail.com"},
    "organizer": {
        "email": "ajbefo4rt4j8mtd808pi4gi5uc@group.cal.google.com",
        "displayName": "YAAS",
        "self": True,
    },
    "start": {
        "dateTime": _TEST_EVENT_START_TIME,
        "timeZone": "Europe/Berlin",
    },
    "end": {"dateTime": "2022-10-18T17:00:00+02:00", "timeZone": "Europe/Berlin"},
    "recurringEventId": "3johpi0lpma4f08f9p2n4vleu4",
    "originalStartTime": {
        "dateTime": "2022-10-18T16:00:00+02:00",
        "timeZone": "Europe/Berlin",
    },
    "iCalUID": "3johpi0lpma4f08f9p2n4vleu4@google.com",
    "sequence": 0,
    "reminders": {"useDefault": False},
    "eventType": "default",
}
# pylint: enable=line-too-long


def _str_to_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(pytz.UTC).timestamp())


_TEST_SCALE_REQUEST: request.ScaleRequest = request.ScaleRequest(
    topic="TEST_TOPIC",
    resource="TEST_RESOURCE",
    command="TEST_COMMAND",
    timestamp_utc=_str_to_timestamp(_TEST_EVENT_START_TIME),
)


def _to_scaling_str(topic: str, resource: str, command: str) -> str:
    return event_parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP.join(
        [topic, resource, command]
    )


@pytest.mark.parametrize(
    "scaling_str",
    [
        _to_scaling_str(
            f"{_TEST_SCALE_REQUEST.topic}",
            f"{_TEST_SCALE_REQUEST.resource}",
            f"{_TEST_SCALE_REQUEST.command}",
        ),
        _to_scaling_str(
            f"   {_TEST_SCALE_REQUEST.topic}",
            f"{_TEST_SCALE_REQUEST.resource}  ",
            f"  {_TEST_SCALE_REQUEST.command}  ",
        ),
        _to_scaling_str(
            f"  .{_TEST_SCALE_REQUEST.topic}.  ",
            f".{_TEST_SCALE_REQUEST.resource}.",
            f".  {_TEST_SCALE_REQUEST.command}  .",
        ),
        _to_scaling_str(
            f".{_TEST_SCALE_REQUEST.topic}.",
            f".{_TEST_SCALE_REQUEST.resource}.",
            f".{_TEST_SCALE_REQUEST.command}.",
        ),
    ],
)
def test_to_request_ok(scaling_str: str):
    # Given
    event = {
        **_TEST_EVENT,
        **dict(description=scaling_str),
    }
    # When
    result = event_parser.to_request(event)
    # Then
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == _TEST_SCALE_REQUEST


def test_to_request_ok_multiple():
    # Given
    total = 5
    lines = []
    for ndx in range(total):
        lines.append(
            _to_scaling_str(
                f"{_TEST_SCALE_REQUEST.topic}_{ndx}",
                f"{_TEST_SCALE_REQUEST.resource}_{ndx}",
                f"{_TEST_SCALE_REQUEST.command}_{ndx}",
            )
        )
        lines.append(f"Some comment about {ndx}")
    event = {
        **_TEST_EVENT,
        **dict(description=_TEST_EVENT_DESCRIPTION_TMPL % "\n".join(lines)),
    }
    # When
    result = event_parser.to_request(event)
    # Then
    assert isinstance(result, list)
    assert len(result) == total
    for ndx, req in enumerate(result):
        assert req.topic == f"{_TEST_SCALE_REQUEST.topic}_{ndx}"


def _generate_event_start_and_expected(
    timezone: int, hour: int = 10
) -> Tuple[Dict[str, Any], datetime]:
    hour_val = f"{hour + timezone:02}"
    tz_val = f"{abs(timezone):02}"
    if timezone < 0:
        tz_val = "-" + tz_val
    else:
        tz_val = "+" + tz_val
    datetime_str = f"2022-10-18T{hour_val}:00:00{tz_val}:00"
    value = {"dateTime": datetime_str, "timeZone": "TO BE IGNORED"}
    expected = datetime.fromisoformat(datetime_str).astimezone(pytz.UTC)
    return value, expected


@pytest.mark.parametrize(
    "value,expected",
    [
        _generate_event_start_and_expected(0),
        _generate_event_start_and_expected(-1),
        _generate_event_start_and_expected(1),
    ],
)
def test__parse_start_to_utc_ok(value: str, expected: datetime):
    # Given/When
    result = event_parser._parse_start_to_utc(value)
    # Then
    assert result == expected
