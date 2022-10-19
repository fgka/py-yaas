# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,no-self-use,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
import base64
from datetime import datetime
import json
import pytz
from typing import Any, Dict, Tuple

import pytest

from yaas.calendar import parser, scaling_target

_TEST_EVENT_CLOUD_RUN_START_TIME: str = "2022-10-18T16:00:00+02:00"
_TEST_EVENT_CLOUD_RUN_SERVICE_NAME: str = "hello"
_TEST_EVENT_CLOUD_RUN_LOCATION: str = "europe-west3"
_TEST_EVENT_CLOUD_RUN_PROJECT: str = "src-bq"
_TEST_EVENT_CLOUD_RUN_RESOURCE_NAME: str = f"projects/{_TEST_EVENT_CLOUD_RUN_PROJECT}/locations/{_TEST_EVENT_CLOUD_RUN_LOCATION}/services/{_TEST_EVENT_CLOUD_RUN_SERVICE_NAME}"
_TEST_EVENT_CLOUD_RUN_SIMPLE_RESOURCE_NAME: str = f"CloudRun / {_TEST_EVENT_CLOUD_RUN_SERVICE_NAME} @ {_TEST_EVENT_CLOUD_RUN_PROJECT} / {_TEST_EVENT_CLOUD_RUN_LOCATION}"
_TEST_EVENT_CLOUD_RUN_TARGET_VALUE: int = 10
_TEST_EVENT_CLOUD_RUN_DESCRIPTION_TMPL: str = "Description event repeat daily<br>%s<br>"
_TEST_EVENT_CLOUD_RUN: Dict[str, Any] = {
    "kind": "calendar#event",
    "etag": '"3332030328331000"',
    "id": "3johpi0lpma4f08f9p2n4vleu4_20221018T140000Z",
    "status": "confirmed",
    "htmlLink": "https://www.google.com/calendar/event?eid=M2pvaHBpMGxwbWE0ZjA4ZjlwMm40dmxldTRfMjAyMjEwMThUMTQwMDAwWiBhamJlZm80cnQ0ajhtdGQ4MDhwaTRnaTV1Y0Bn",
    "created": "2022-10-17T13:54:04.000Z",
    "updated": "2022-10-17T13:59:25.067Z",
    "summary": "Event repeat daily",
    "description": "",
    "creator": {"email": "ds.env.poc.error@gmail.com"},
    "organizer": {
        "email": "ajbefo4rt4j8mtd808pi4gi5uc@group.calendar.google.com",
        "displayName": "YAAS",
        "self": True,
    },
    "start": {
        "dateTime": _TEST_EVENT_CLOUD_RUN_START_TIME,
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

_TEST_EVENT_SCALING: scaling_target.BaseScalingTarget = (
    scaling_target.CloudRunScalingTarget(
        name=_TEST_EVENT_CLOUD_RUN_RESOURCE_NAME,
        start=datetime.fromisoformat(_TEST_EVENT_CLOUD_RUN_START_TIME).astimezone(
            pytz.UTC
        ),
        scaling_value=_TEST_EVENT_CLOUD_RUN_TARGET_VALUE,
    )
)


@pytest.mark.parametrize(
    "event,expected",
    [
        (
            {
                **_TEST_EVENT_CLOUD_RUN,
                **dict(
                    description=(
                        f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                        f":{_TEST_EVENT_CLOUD_RUN_RESOURCE_NAME}"
                        f"={_TEST_EVENT_CLOUD_RUN_TARGET_VALUE}"
                    )
                ),
            },
            _TEST_EVENT_SCALING,
        ),
        (
            {
                **_TEST_EVENT_CLOUD_RUN,
                **dict(
                    description=(
                        f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                        f":CloudRun / {_TEST_EVENT_CLOUD_RUN_SERVICE_NAME}"
                        f"@{_TEST_EVENT_CLOUD_RUN_PROJECT}"
                        f"/{_TEST_EVENT_CLOUD_RUN_LOCATION}"
                        f"={_TEST_EVENT_CLOUD_RUN_TARGET_VALUE}"
                    )
                ),
            },
            _TEST_EVENT_SCALING,
        ),
    ],
)
def test_to_scaling_ok(
    event: Dict[str, Any], expected: scaling_target.BaseScalingTarget
):
    # Given/When
    result = parser.to_scaling(event)
    # Then
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == expected


_TEST_EVENT_CLOUD_RUN_DESCRIPTION_EXAMPLE: str = "<html-blob><u></u>Description event repeat daily<br>&nbsp;target: projects/src-bq/locations/europe-west3/services/hello = 10<br>&nbsp;target : projects/src-bq/locations/europe-west3/services/hello = 10<u></u><br><u></u>target:projects/src-bq/locations/europe-west3/services/hello=10<br>&nbsp; &nbsp; target:&nbsp; &nbsp; projects/src-bq/locations/europe-west3/services/hello =&nbsp; &nbsp; &nbsp; 10&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<br>target :CloudRun / hello@&nbsp; src-bq/europe-west3= 10&nbsp; &nbsp; &nbsp;<u></u><br><u></u>target:CloudRun/hello@src-bq/europe-west3=10</html-blob><br><html-blob><br></html-blob><br><html-blob><u></u>&nbsp; target : CloudRun / hello&nbsp; &nbsp;@&nbsp; src-bq/europe-west3&nbsp; =&nbsp; 10&nbsp; &nbsp; &nbsp;&nbsp;<br><u></u><br><u></u>target : CloudRun / hello&nbsp; &nbsp;@&nbsp; src-bq/europe-west3&nbsp; &nbsp;=&nbsp; 10<br><u></u></html-blob>"


def test_to_scaling_ok_multiple():
    # Given
    event = {
        **_TEST_EVENT_CLOUD_RUN,
        **dict(description=_TEST_EVENT_CLOUD_RUN_DESCRIPTION_EXAMPLE),
    }
    # When
    result = parser.to_scaling(event)
    # Then
    assert isinstance(result, list)
    assert len(result) == 8


@pytest.mark.parametrize(
    "event",
    [
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(description=None),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(description=""),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(description="Simple description"),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(
                description=(
                    f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                    f":{_TEST_EVENT_CLOUD_RUN_RESOURCE_NAME}"
                )  # missing value
            ),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(
                description=(
                    f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                    f":projects/"
                    f"={_TEST_EVENT_CLOUD_RUN_TARGET_VALUE}"
                )  # missing name
            ),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(
                description=(
                    f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                    f":CloudRun / {_TEST_EVENT_CLOUD_RUN_SERVICE_NAME}"
                    f"@{_TEST_EVENT_CLOUD_RUN_PROJECT}"
                    f"/{_TEST_EVENT_CLOUD_RUN_LOCATION}"
                )  # missing value
            ),
        },
        {
            **_TEST_EVENT_CLOUD_RUN,
            **dict(
                description=(
                    f"{parser._GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX}"
                    f":CloudRun / {_TEST_EVENT_CLOUD_RUN_SIMPLE_RESOURCE_NAME}"
                    f"@{_TEST_EVENT_CLOUD_RUN_PROJECT}"  # missing location
                    f"={_TEST_EVENT_CLOUD_RUN_TARGET_VALUE}"
                )
            ),
        },
    ],
)
def test_to_scaling_ok_description_invalid(event: Dict[str, Any]):
    # Given/When
    result = parser.to_scaling(event)
    # Then
    assert isinstance(result, list)
    assert len(result) == 0


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
