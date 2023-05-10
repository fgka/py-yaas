# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
This is a shim on top of Python `caldav`_ library to support Google and non-Google Calendars.
For the how to connect, read the `URL notes`_.
Returns calendar objects from `icalendar`_.

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364

Source: https://github.com/python-caldav/caldav
Source: https://caldav.readthedocs.io/en/latest/

.. _caldav: https://pypi.org/project/caldav/
.. _icalendar: https://pypi.org/project/icalendar/
.. _URL notes: https://developers.google.com/calendar/caldav/v2/guide#connecting_to_googles_caldav_server
"""
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, Union

import cachetools
import caldav
import icalendar

from yaas_common import logger, preprocess
from yaas_gcp import secrets

_LOGGER = logger.get(__name__)

_DEFAULT_END_TIME_NOW_DRIFT_IN_HOURS: int = 48

GOOGLE_DAV_URL_TMPL: str = "https://www.google.com/calendar/dav/%s/events"
"""
The reason for the old version, instead of the given the `official documentation`_,
 is documented in the `Github issue 119`_.

**NOTE**: the Calendar ID, for Google, is in the following format::
    <long alpha numerical value>@group.calendar.google.com

.. _official documentation: https://developers.google.com/calendar/caldav/v2/guide#connecting_to_googles_caldav_server
.. _Github issue 119: https://github.com/python-caldav/caldav/issues/119
"""


async def list_upcoming_events(
    *,
    url: str,
    username: str,
    secret_name: str,
    amount: Optional[int] = None,
    start: Optional[Union[datetime, int]] = None,
    end: Optional[Union[datetime, int]] = None,
) -> AsyncGenerator[icalendar.Calendar, None]:
    """

    Args:
        url: CalDAV URL.
        username: calendar username, usually your email.
        secret_name: Secret Manager secret name that holds the password, in the format:
          `projects/<<project id>>/secrets/<<secret id>>/versions/<<version>>`
        amount: how many events to list, default: py:data:`DEFAULT_LIST_EVENTS_AMOUNT`.
        start: from when to start listing, default: current date/time.
        end: up until when to list, if given, will discard ``amount``.

    Returns:

    .. _list API: https://developers.google.com/calendar/api/v3/reference/events/list
    """
    _LOGGER.debug("Listing upcoming events using: <%s>", locals())
    # input validation
    url = preprocess.string(url, "url")
    username = preprocess.string(username, "username")
    secret_name = preprocess.string(secret_name, "secret_name")
    # logic
    password = await _password(secret_name)
    cal = await _calendar(url, username, password)
    # get UTC datetime objects
    start_time = _to_utc_datetime(start)
    end_time = _to_utc_datetime(end, now_drift_in_hours=_DEFAULT_END_TIME_NOW_DRIFT_IN_HOURS)
    # return events
    async for event in _fetch_events(cal, start_time, end_time, amount):
        yield event.icalendar_instance


def _to_utc_datetime(value: Optional[Union[datetime, int]], *, now_drift_in_hours: int = 0) -> datetime:
    if not isinstance(value, datetime):
        if isinstance(value, int):
            value = datetime.utcfromtimestamp(value)
        else:
            value = datetime.utcnow() + timedelta(hours=now_drift_in_hours)
    return value


async def _password(value: str) -> str:
    _LOGGER.debug("Fetching password from secret '%s'", value)
    try:
        result = await secrets.get(value)
        _LOGGER.info(
            "Retrieved cal credentials from cloud secret name: <%s>(%s)",
            value,
            type(value),
        )
    except Exception as err:
        raise RuntimeError(f"Could not fetch secret '{value}'. Error: {err}") from err
    return result


async def _calendar(url: str, username: str, password: str) -> caldav.Calendar:
    _LOGGER.debug("Getting calendar in DAV URL '%s' using username '%s' (password omitted)", username, password)
    try:
        await asyncio.sleep(0)
        dav_principal = _principal(url=url, username=username, password=password)
        await asyncio.sleep(0)
        result = dav_principal.calendar(cal_url=url)
        await asyncio.sleep(0)
    except Exception as err:
        raise RuntimeError(
            f"Could not get calendar in URL '{url}' with username '{username}' and password <omitted>. Error: {err}"
        ) from err
    _LOGGER.info("Retrieved calendar from '%s' using username '%s'", url, username)
    return result


def _principal(url: str, username: str, password: str) -> caldav.Principal:
    _LOGGER.debug("Connecting to DAV URL '%s' using username '%s' (password omitted)", username, password)
    try:
        result = _client(url, username, password).principal()
    except Exception as err:
        raise RuntimeError(
            f"Could not connect to DAV calendar in URL '{url}' with username '{username}' and password <omitted>. "
            f"Error: {err}"
        ) from err
    return result


@cachetools.cached(cache=cachetools.LRUCache(maxsize=10))
def _client(url: str, username: str, password: str) -> caldav.DAVClient:
    _LOGGER.debug("Connecting to DAV URL '%s' using username '%s' (password omitted)", username, password)
    try:
        result = caldav.DAVClient(url=url, username=username, password=password)
    except Exception as err:
        raise RuntimeError(
            f"Could not connect to DAV calendar in URL '{url}' with username '{username}' and password <omitted>. "
            f"Error: {err}"
        ) from err
    return result


async def _fetch_events(
    cal: caldav.Calendar, start: datetime, end: datetime, amount: int
) -> AsyncGenerator[caldav.Event, None]:
    _LOGGER.debug("Fetching calendar events between '%s' and '%s' from '%s'", start, end, cal.url)
    try:
        count = 0
        for event in cal.search(start=start, end=end, event=True, expand=True):
            if amount is not None and count >= amount:
                return
            await asyncio.sleep(0)
            yield event
            count += 1
    except Exception as err:
        raise RuntimeError(
            f"Could not list events from '{start}' to '{end}' from calendar in '{cal.url}'. Error: {err}"
        ) from err
