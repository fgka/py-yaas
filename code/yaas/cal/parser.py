# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Parses an event content into a scaling target.
Events are expected to come out of `list API`_.

.. _list API: https://developers.google.com/calendar/api/v3/reference/events/list
"""
# pylint: enable=line-too-long
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

import bs4
import pytz

from yaas.cal import scaling_target
from yaas import logger

_LOGGER = logger.get(__name__)

_GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD: str = "description"
_GOOGLE_CALENDAR_EVENT_START_FIELD: str = "start"
_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD: str = "dateTime"
# How to identify targets in the description field
_GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX: str = "target"
# The, apparently superfluous, pattern '\.?' is added
# to account for Google Calendar behaviour to add a period ('.') after words
# if you add more than 1 space after a word.
# pylint: disable=anomalous-backslash-in-string
_GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_SPEC_REGEX: re.Pattern = re.compile(
    pattern=r"^\s*?"
    + _GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX
    + "\.?\s*:\.?\s*([^=]+\.?)=\.?\s*(\d+)\.?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
# pylint: enable=anomalous-backslash-in-string
"""
Groups on matching are::
    resource, value = _GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_SPEC_REGEX.match(line).groups()
"""
_FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"\.?\s*projects/([^/\s]+)/locations/([^/\s]+)/services/([^/\s]+)\.?\s*",
    flags=re.IGNORECASE,
)
"""
Groups on matching are::
    project, location, service = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
# pylint: disable=line-too-long
_SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"\.?\s*CloudRun\.?\s*/\.?\s*([^@\s]+)\.?\s*@\.?\s*([^/\s]+)\.?\s*/\.?\s*([^\s]+)\.?\s*",
    flags=re.IGNORECASE,
)
# pylint: enable=line-too-long
"""
Groups on matching are::
    service, project, location = _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
_CLOUD_RUN_RESOURCE_NAME_TMPL: str = "projects/{}/locations/{}/services/{}"


def to_scaling(
    event: Optional[Dict[str, Any]] = None
) -> List[scaling_target.BaseScalingTarget]:
    """

    Args:
        event:

    Returns:

    """
    _LOGGER.debug(
        "Extracting %s from event %s", scaling_target.BaseScalingTarget.__name__, event
    )
    result = []
    # validation
    if isinstance(event, dict):
        description = event.get(_GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD)
        if not isinstance(description, str):
            _LOGGER.warning(
                "Could not extract %s from event %s",
                _GOOGLE_CALENDAR_EVENT_DESCRIPTION_FIELD,
                event,
            )
        else:
            start = event.get(_GOOGLE_CALENDAR_EVENT_START_FIELD)
            start_value = _parse_start_to_utc(start)
            result = _parse_event_description(description, start_value)
    else:
        _LOGGER.warning(
            "Event <%s>(%s) cannot be parsed, it needs to be instance of %s",
            event,
            type(event),
            dict.__name__,
        )
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
        raise TypeError(
            f"Event start entry must be a {dict.__name__}, got: <{value}>({type(value)})"
        )
    value_datetime = value.get(_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD)
    if not value_datetime:
        raise ValueError(
            f"Could find field {_GOOGLE_CALENDAR_EVENT_START_DATE_TIME_FIELD} "
            f"in event start: <{value}>"
        )
    # convert
    return datetime.fromisoformat(value_datetime).astimezone(pytz.UTC)


def _parse_event_description(
    value: str, start: datetime
) -> List[scaling_target.BaseScalingTarget]:
    # pylint: disable=line-too-long
    """
    Description field example::
        'Description event repeat daily<br>name: projects/src-bq/locations/europe-west3/services/hello<br>value: 10<br>project: src-bq<br>location:&nbsp;<span style="background-color: var(--textfield-surface); color: var(--on-surface);">europe-west3</span><br><span style="background-color: var(--textfield-surface); color: var(--on-surface);">type: CloudRun</span><br><span style="background-color: var(--textfield-surface); color: var(--on-surface);">service: hello</span>'

    Returns:

    """
    # pylint: enable=line-too-long
    result = []
    for line in _extract_text_from_html(value).split("\n"):
        item_name, item_value = _parse_description_target_line(line)
        if item_name and item_value:
            result.append(scaling_target.from_arguments(item_name, item_value, start))
    return result


def _extract_text_from_html(value: str) -> str:
    soup = bs4.BeautifulSoup(markup=value, features="html.parser")
    return soup.get_text(separator="\n", strip=True)


def _parse_description_target_line(value: str) -> Optional[Tuple[str, int]]:
    """

    Args:
        value:

    Returns:

    """
    item_name, item_value = None, None
    value = value.strip()
    if value.startswith(_GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX):
        resource_spec_value_match = (
            _GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_SPEC_REGEX.match(value)
        )
        if resource_spec_value_match:
            resource_spec, item_value = resource_spec_value_match.groups()
            item_value = int(item_value)
            item_name = _parse_resource_name_from_desc_spec(resource_spec)
    else:
        _LOGGER.debug(
            "Value has no %s prefix. Ignoring value: %s.",
            _GOOGLE_CALENDAR_EVENT_DESCRIPTION_TARGET_PREFIX,
            value,
        )
    return item_name, item_value


def _parse_resource_name_from_desc_spec(value: str) -> str:
    """

    Args:
        value:

    Returns:

    """
    # CloudRun
    result = _parse_cloud_run_name_from_desc_spec(value)
    return result


def _parse_cloud_run_name_from_desc_spec(value: str) -> Optional[str]:
    """

    Args:
        value:

    Returns:

    """
    result = None
    project, location, service = None, None, None
    # FQN match
    match = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(value)
    if match:
        project, location, service = match.groups()
    else:
        match = _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(value)
        if match:
            service, project, location = match.groups()
        else:
            _LOGGER.debug(
                "Value does not specify a CloudRun resource name. Ignoring value <%s>",
                value,
            )
    # build result
    # Why the construct below?
    # pylint: disable=line-too-long
    # https://stackoverflow.com/questions/42360956/what-is-the-most-pythonic-way-to-check-if-multiple-variables-are-not-none
    # pylint: enable=line-too-long
    if not [x for x in (project, location, service) if x is None]:
        result = _CLOUD_RUN_RESOURCE_NAME_TMPL.format(project, location, service)
    return result
