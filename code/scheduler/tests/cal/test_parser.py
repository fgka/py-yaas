# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import json
from datetime import datetime
from typing import Any, Dict, Tuple

import pytz

import pytest

from yaas.cal import parser
from yaas.dto import request

from tests import common


_TEST_EVENT_START_TIME: str = "2022-10-18T16:00:00+02:00"
_TEST_EVENT_DESCRIPTION_TMPL: str = "Description event repeat daily<br>%s<br>"
# pylint: disable=line-too-long
_TEST_EVENT: Dict[str, Any] = {
    "kind": "event#event",
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
        "email": "ajbefo4rt4j8mtd808pi4gi5uc@group.event.google.com",
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
_TEST_FULL_EVENT_DESCRIPTION_EXAMPLE: str = "Description event repeat daily<br> yaas | projects/src-bq/locations/europe-west3/services/hello | min_instances&nbsp; &nbsp;10.<br> standard | projects/src-bq/locations/europe-west3/services/hello | min_instances 11.<br>yaas. | projects/src-bq/locations/europe-west3/services/hello|min_instances  12  <br>    standard. |. projects/src-bq/locations/europe-west3/services/hello. | min_instances 13. <br>yaas |CloudRun / hello@  src-bq/europe-west3 | min_instances 14<br>standard | CloudRun/hello@src-bq/europe-west3 | min_instances 15    <br><br><br>  yaas|CloudRun hello   @  src-bq europe-west3   | min_instances&nbsp; &nbsp;16<br><br>standard | CloudRun hello   @  src-bq europe-west3    | min_instances 17<br><u></u><u></u>"
# pylint: enable=line-too-long
_TEST_FULL_EVENT_DESCRIPTION_EXAMPLE_AMOUNT: int = 8


def _str_to_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(pytz.UTC).timestamp())


_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request(
    timestamp_utc=_str_to_timestamp(_TEST_EVENT_START_TIME),
)


def _to_scaling_str(topic: str, resource: str, command: str) -> str:
    return parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP.join(
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
    result = parser.to_request(event=event)
    # Then
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == _TEST_SCALE_REQUEST.clone(original_json_event=json.dumps(event))
    assert result[0].original_json_event == json.dumps(event)


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
    result = parser.to_request(event=event)
    # Then
    assert isinstance(result, list)
    assert len(result) == total
    for ndx, req in enumerate(result):
        assert req.topic == f"{_TEST_SCALE_REQUEST.topic}_{ndx}"
        assert req.original_json_event == json.dumps(event)


def test_to_request_ok_real_example():
    # Given
    event = {
        **_TEST_EVENT,
        **dict(description=_TEST_FULL_EVENT_DESCRIPTION_EXAMPLE),
    }
    # When
    result = parser.to_request(event=event)
    # Then
    assert isinstance(result, list)
    assert len(result) == _TEST_FULL_EVENT_DESCRIPTION_EXAMPLE_AMOUNT


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
    result = parser._parse_start_to_utc(value)
    # Then
    assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            # this is correct, there are some unconventional unicode spaces after the '|',
            # please do not change
            "gcs | yaas-app-245814988234 | <span>yaas/batch/test.up</span>",
            "gcs |yaas-app-245814988234 |yaas/batch/test.up",
        ),
        (
            "\ngcs|yaas-app-245814988234|yaas/batch/test.up\n",
            "gcs|yaas-app-245814988234|yaas/batch/test.up",
        ),
    ],
)
def test__extract_text_from_html_ok_tricky_strings(value: str, expected: str):
    # Given
    # When
    result = parser._extract_text_from_html(value)
    # Then
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == expected
