# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Parses an event content into a scaling target. Events are expected to come
out of `list API`_.

.. _list API: https://developers.google.com/calendar/api/v3/reference/events/list
"""
import json
import re
import string
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Union

import bs4
import icalendar
import pytz

from yaas_common import const, logger, request

_LOGGER = logger.get(__name__)

_GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD: str = "description"
_GOOGLE_CALENDAR_EVENT_START_FIELD: str = "start"
_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD: str = "dateTime"
# How to identify targets in the description field
_GOOGLE_CALENDAR_EVENT_DESCRIPTION_STANDARD_TOPIC: str = "yaas_gcp-scaler-scheduler_service-common"
_GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP: str = "|"
# The, apparently superfluous, pattern '\.?' is added
#   to account for Google Calendar behaviour to add a period ('.') after words
#   if you add more than 1 space after a word.
# pylint: disable=anomalous-backslash-in-string
_GOOGLE_CALENDAR_EVENT_DESCRIPTION_SCALING_SPEC_REGEX: re.Pattern = re.compile(
    pattern=r"^\s*\.?\s*"  # space prefix
    + "([^\\.\s][^"
    + "\\"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP
    + "]+[^\\.\s])"  # topic
    + r"\s*\.?\s*"
    + "\\"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP
    + r"\s*\.?\s*"  # separator
    + "([^\\.\s][^"
    + "\\"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP
    + "]+[^\\.\s])"  # resource
    + r"\s*\.?\s*"
    + "\\"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP
    + r"\s*\.?\s*"  # separator
    + "([^\\.\s][^"
    + "\\"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SEP
    + "]+[^\\.\s])"  # what/command
    + r"\s*\.?\s*$",  # trailing space and/or period ('.')
    flags=re.IGNORECASE | re.MULTILINE,
)
# pylint: enable=anomalous-backslash-in-string
# pylint: disable=line-too-long
"""
Example input::
    value = " yaas_gcp-scaler-scheduler_service-common.  | projects/my_project/locations/europe-west3/services/my_service |min_instances 10.
Parsed as::
    topic = "yaas_gcp-scaler-scheduler_service-common"
    resource = "projects/my_project/locations/europe-west3/services/my_service"
    command = "min_instances 10"
Groups on matching are::
    topic, resource, command = _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SCALING_SPEC_REGEX.match(line).groups()
"""
# pylint: enable=line-too-long

_ICALENDAR_VEVENT_COMPONENT_NAME: str = "VEVENT"
_ICALENDAR_VEVENT_DESCRIPTION_FIELD: str = "description"
_ICALENDAR_VEVENT_START_FIELD: str = "dtstart"
_ICALENDAR_VEVENT_END_FIELD: str = "dtend"


def to_request(
    *,
    event: Optional[Union[Dict[str, Any], icalendar.Calendar]] = None,
) -> List[request.ScaleRequest]:
    """Parses the event for scaling targets. It uses `start` for the start time
    and `description` to get the resources and values to be scaled.

    Args:
        event: Google calendar event.

    Returns:
        List of py:cls:`request.ScaleRequest` parsed from the event.
    """
    _LOGGER.debug("Extracting '%s' from event '%s'(%s)", request.ScaleRequest.__name__, event, type(event))
    result = []
    # validation
    if isinstance(event, dict):
        result = _to_request_from_google_calendar_event(event)
    else:
        _LOGGER.warning(
            "Event <%s>(%s) cannot be parsed, it needs to be instance of '%s'",
            event,
            type(event),
            dict.__name__,
        )
    return result


def _to_request_from_google_calendar_event(
    value: Dict[str, Any],
) -> List[request.ScaleRequest]:
    result = []
    # validation
    description = value.get(_GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD)
    if not isinstance(description, str):
        _LOGGER.warning(
            "Could not extract '%s' from event '%s'",
            _GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD,
            value,
        )
    else:
        start = value.get(_GOOGLE_CALENDAR_EVENT_START_FIELD)
        start_utc = _parse_start_to_utc(start)
        result = _parse_event_description(description, start_utc, json.dumps(value))
    return result


def _to_request_from_icalendar_calendar(
    value: icalendar.Calendar,
) -> List[request.ScaleRequest]:
    """
    Source: https://icalendar.readthedocs.io/en/latest/usage.html#example
    """
    result = []
    for component in value.walk(_ICALENDAR_VEVENT_COMPONENT_NAME):
        description = component.get(_ICALENDAR_VEVENT_DESCRIPTION_FIELD)
        if not isinstance(description, str):
            _LOGGER.warning(
                "Could not extract '%s' from component '%s' in '%s'",
                _ICALENDAR_VEVENT_DESCRIPTION_FIELD,
                component,
                value,
            )
        else:
            start = None
            start_vddd = value.get(_ICALENDAR_VEVENT_START_FIELD)
            if isinstance(start_vddd, icalendar.prop.vDDDTypes):
                start = start_vddd.dt
            json_event = json.dumps(value.to_ical().decode(const.ENCODING_UTF8))
            result = _parse_event_description(description, start, json_event)
    return result


def _parse_start_to_utc(value: Dict[str, str]) -> datetime:
    """
    Value example::
        value = {
            'dateTime': '2022-10-18T16:00:00+02:00',
            'timeZone': 'Europe/Berlin'
        },

    Args:
        value:

    Returns:

    """
    # validate
    if not isinstance(value, dict):
        raise TypeError(f"Event start entry must be a {dict.__name__}, got: <{value}>({type(value)})")
    value_datetime = value.get(_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD)
    if not value_datetime:
        raise ValueError(
            f"Could find field {_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD} " f"in event start: <{value}>"
        )
    # convert
    return datetime.fromisoformat(value_datetime).astimezone(pytz.UTC)


def _parse_event_description(
    value: str,
    start_utc: datetime,
    json_event: str,
) -> List[request.ScaleRequest]:
    # pylint: disable=line-too-long
    """
    Description field example::
        'Description event repeat daily<br>name: projects/core-bq/locations/europe-west3/services/hello<br>
        value: 10<br>
        project: core-bq<br>
        location:&nbsp;<span style="background-color: var(--textfield-surface); color: var(--on-surface);">europe-west3</span><br>
        <span style="background-color: var(--textfield-surface); color: var(--on-surface);">type: CloudRun</span><br>
        <span style="background-color: var(--textfield-surface); color: var(--on-surface);">service: hello</span>'

    Returns:
        :py:cls:`request.ScaleRequest` instances corresponding to the lines in the value.
    """
    # pylint: enable=line-too-long
    return parse_lines(
        lines=_extract_text_from_html(value),
        timestamp_utc=int(start_utc.timestamp()),
        json_event=json_event,
    )


def _extract_text_from_html(value: str) -> List[str]:
    result = []
    value = "".join(filter(lambda x: x in set(string.printable), value))
    for val in value.split("\n"):
        soup = bs4.BeautifulSoup(markup=val, features="html.parser")
        for tag_br in soup.find_all("br"):
            tag_br.replace_with("\n" + tag_br.text)
        for tag_span in soup.find_all("span"):
            tag_span.replace_with(tag_span.text)
        text = soup.text
        result.extend([item for item in text.split("\n") if item])
    return result


def parse_lines(
    *,
    lines: Iterable[str],
    timestamp_utc: int,
    json_event: Optional[Dict[str, Any]] = None,
) -> List[request.ScaleRequest]:
    """
    Will assume each line in `lines` is a request string
        to be converted to :py:class:`request.ScaleRequest` instances.
    Example of a line::
        "topic | resource | command target"
    Args:
        lines:
        timestamp_utc:
        json_event:

    Returns:

    """
    # input validation
    if not isinstance(lines, Iterable):
        raise TypeError(f"Argument lines is not iterable. Got: <{lines}>({type(lines)})")
    if not isinstance(timestamp_utc, int) or timestamp_utc < 0:
        raise ValueError(
            "Timestamp must be an integer greater than 0. " f"Got: <{timestamp_utc}>({type(timestamp_utc)})"
        )
    # logic
    result = []
    for ndx, line in enumerate(lines):
        try:
            req = _parse_description_target_line(line.strip(), timestamp_utc, json_event)
            if req is not None:
                result.append(req)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not parse line: <%s>[%s](%s). Full content: %s. Error: %s. Ignoring",
                line,
                ndx,
                type(line),
                lines,
                err,
            )
    return result


def _parse_description_target_line(
    value: str,
    timestamp_utc: int,
    json_event: str,
) -> Optional[request.ScaleRequest]:
    result = None
    resource_spec_value_match = _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SCALING_SPEC_REGEX.match(value)
    if resource_spec_value_match:
        topic, resource, command = resource_spec_value_match.groups()
        result = request.ScaleRequest(
            topic=topic.strip(),
            resource=resource.strip(),
            command=command.strip(),
            timestamp_utc=timestamp_utc,
            original_json_event=json_event,
        )
    else:
        _LOGGER.debug(
            "Value has does not comply with %s. Ignoring value: %s.",
            _GOOGLE_CALENDAR_EVENT_DESCRIPTION_SCALING_SPEC_REGEX,
            value,
        )
    return result
