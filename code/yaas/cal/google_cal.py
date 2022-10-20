# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Source: https://developers.google.com/calendar/api/quickstart/python
Source: https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/
"""
# pylint: enable=line-too-long
from datetime import datetime
import os
import pathlib
import pickle
from typing import Any, Dict, List, Optional

import cachetools

from google.auth.transport import requests
from google.oauth2 import credentials
from googleapiclient import discovery
from google_auth_oauthlib import flow

from yaas.gcp import secrets
from yaas import logger

_LOGGER = logger.get(__name__)

DEFAULT_LIST_EVENTS_AMOUNT: int = 10


def list_upcoming_events(
    *,
    calendar_id: str,
    credentials_json: Optional[pathlib.Path] = None,
    amount: Optional[int] = None,
    start: Optional[datetime] = None,
) -> List[Dict]:
    # pylint: disable=line-too-long
    """
    Wraps the `list API`_.

    Returns a list of events in the format::
    result = [
        {
            'kind': 'cal#event',
            'etag': '"3325291402132000"',
            'id': '135ovu6ls85i7006std2kb9adk',
            'status': 'confirmed',
            'htmlLink': 'https://www.google.com/calendar/event?eid=MTM1b3Z1NmxzODVpNzAwNnN0ZDJrYjlhZGsgYWpiZWZvNHJ0NGo4bXRkODA4cGk0Z2k1dWNAZw',
            'created': '2022-09-08T14:01:37.000Z',
            'updated': '2022-09-08T14:01:41.066Z',
            'summary': 'Scale up',
            'creator': {
                'email': 'ds.env.poc.error@gmail.com'
            },
            'organizer': {
                'email': 'ajbefo4rt4j8mtd808pi4gi5uc@group.cal.google.com',
                'displayName': 'YAAS',
                'self': True
            },
            'start': {
                'dateTime': '2022-09-09T07:30:00+02:00',
                'timeZone': 'Europe/Berlin'
            },
            'end': {
                'dateTime': '2022-09-09T07:45:00+02:00',
                'timeZone': 'Europe/Berlin'
            },
            'iCalUID': '135ovu6ls85i7006std2kb9adk@google.com',
            'sequence': 1,
            'reminders': {
                'useDefault': True
            },
            'eventType': 'default'
        },
        {
            'kind': 'cal#event',
            'etag': '"3332030328331000"',
            'id': '3johpi0lpma4f08f9p2n4vleu4_20221018T140000Z',
            'status': 'confirmed',
            'htmlLink': 'https://www.google.com/calendar/event?eid=M2pvaHBpMGxwbWE0ZjA4ZjlwMm40dmxldTRfMjAyMjEwMThUMTQwMDAwWiBhamJlZm80cnQ0ajhtdGQ4MDhwaTRnaTV1Y0Bn',
            'created': '2022-10-17T13:54:04.000Z',
            'updated': '2022-10-17T13:59:25.067Z',
            'summary': 'Event repeat daily',
            'description': '<html-blob><u></u>Description event repeat daily<br>&nbsp;target: projects/src-bq/locations/europe-west3/services/hello = 10<br>&nbsp;target : projects/src-bq/locations/europe-west3/services/hello = 10<u></u><br><u></u>target:projects/src-bq/locations/europe-west3/services/hello=10<br>&nbsp; &nbsp; target:&nbsp; &nbsp; projects/src-bq/locations/europe-west3/services/hello =&nbsp; &nbsp; &nbsp; 10&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<br>target :CloudRun / hello@&nbsp; src-bq/europe-west3= 10&nbsp; &nbsp; &nbsp;<u></u><br><u></u>target:CloudRun/hello@src-bq/europe-west3=10</html-blob><br><html-blob><br></html-blob><br><html-blob><u></u>&nbsp; target : CloudRun / hello&nbsp; &nbsp;@&nbsp; src-bq/europe-west3&nbsp; =&nbsp; 10&nbsp; &nbsp; &nbsp;&nbsp;<br><u></u><br><u></u>target : CloudRun / hello&nbsp; &nbsp;@&nbsp; src-bq/europe-west3&nbsp; &nbsp;=&nbsp; 10<br><u></u></html-blob>',
            'creator': {
                'email': 'ds.env.poc.error@gmail.com'
            },
            'organizer': {
                'email': 'ajbefo4rt4j8mtd808pi4gi5uc@group.cal.google.com',
                'displayName': 'YAAS',
                'self': True
            },
            'start': {
                'dateTime': '2022-10-18T16:00:00+02:00',
                'timeZone': 'Europe/Berlin'
            },
            'end': {
                'dateTime': '2022-10-18T17:00:00+02:00',
                'timeZone': 'Europe/Berlin'
            },
            'recurringEventId': '3johpi0lpma4f08f9p2n4vleu4',
            'originalStartTime': {
                'dateTime': '2022-10-18T16:00:00+02:00',
                'timeZone': 'Europe/Berlin'
            },
            'iCalUID': '3johpi0lpma4f08f9p2n4vleu4@google.com',
            'sequence': 0,
            'reminders': {
                'useDefault': False
            },
            'eventType': 'default'
        }
    ]

    Args:
        calendar_id: which cal to list.
        credentials_json: cal JSON credentials, if existing.
        amount: how many events to list, default: py:data:`DEFAULT_LIST_EVENTS_AMOUNT`.
        start: from when to start listing, default: current date/time.

    Returns:

    .. _list API: https://developers.google.com/calendar/api/v3/reference/events/list
    """
    # pylint: enable=line-too-long
    # Normalize input
    service = _calendar_service(credentials_json=credentials_json)
    if not isinstance(amount, int):
        amount = DEFAULT_LIST_EVENTS_AMOUNT
    start_time = _iso_utc_zulu(start)
    _LOGGER.debug("Getting the upcoming %d events starting at %s", amount, start_time)
    # Prepare call
    list_kwargs = dict(
        calendarId=calendar_id,
        timeMin=start_time,
        singleEvents=True,
        orderBy="startTime",
    )
    # Retrieve entries
    result = _list_all_events(service, amount, list_kwargs)
    #
    _LOGGER.info(
        "Got the upcoming %d (desired %d) events starting in %s",
        len(result),
        amount,
        start_time,
    )
    return result


def _iso_utc_zulu(value: Optional[datetime] = None) -> str:
    if not isinstance(value, datetime):
        value = datetime.utcnow()
    return value.isoformat() + "Z"


def _list_all_events(
    service: discovery.Resource, amount: int, list_kwargs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    # pagination/while trick
    while len(result) < amount:
        events_result = service.events().list(**list_kwargs).execute()
        result.extend(events_result.get("items", []))
        # next page token
        next_page_token = events_result.get("nextPageToken")
        if not next_page_token:
            break
        # update kwargs only AFTER retrieving items AND getting the next page token
        list_kwargs["pageToken"] = next_page_token
    return result[0:amount]


def _calendar_service(
    *,
    credentials_pickle: Optional[pathlib.Path] = None,
    secret_name: Optional[str] = None,
    credentials_json: Optional[pathlib.Path] = None,
) -> discovery.Resource:
    cal_creds = _calendar_credentials(
        credentials_pickle=credentials_pickle,
        secret_name=secret_name,
        credentials_json=credentials_json,
    )
    _refresh_credentials_if_needed(cal_creds)
    result: discovery.Resource = None
    if isinstance(cal_creds, credentials.Credentials):
        _LOGGER.debug(
            "Creating cal credentials service for client ID %s",
            cal_creds.client_id,
        )
        result = discovery.build("cal", "v3", credentials=cal_creds)
        _LOGGER.info(
            "Created cal credentials service for client ID %s", cal_creds.client_id
        )
    else:
        _LOGGER.warning(
            "No credentials retrieved from either pickle file <%s>"
            ", cloud secret <%s>"
            ", or JSON file <%s>",
            credentials_pickle,
            secret_name,
            credentials_json,
        )
    return result


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _calendar_credentials(
    *,
    credentials_pickle: Optional[pathlib.Path] = None,
    secret_name: Optional[str] = None,
    credentials_json: Optional[pathlib.Path] = None,
) -> credentials.Credentials:
    """
    *CAVEAT*: This has a strong assumption that the credentials expiration time
        is sufficient for *ALL* calls within the single execution.
    """
    # First: pickle
    result: credentials.Credentials = _pickle_credentials(credentials_pickle)
    # Second: Cloud Secrets
    if not result:
        result = _secret_credentials(secret_name)
    # Third: JSON
    if not result:
        result = _json_credentials(credentials_json)
    if not result:
        raise RuntimeError(
            "Could not find credentials for cal access."
            f" Tried pickle file <{credentials_pickle}>"
            f", cloud secrets <{secret_name}>"
            f", and JSON file <{credentials_json}>"
        )
    # Cache values on pickle file
    _persist_credentials_pickle(result, credentials_pickle)
    return result


_CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_PICKLE_FILENAME"
_DEFAULT_CREDENTIALS_PICKLE_FILE: str = "calendar_credentials.pickle"


def _pickle_filepath(value: Optional[pathlib.Path] = None) -> pathlib.Path:
    return _file_path_from_env_default_value(
        value, _CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME, _DEFAULT_CREDENTIALS_PICKLE_FILE
    )


def _file_path_from_env_default_value(
    value: pathlib.Path, env_var: str, default_value: str
) -> pathlib.Path:
    result: pathlib.Path = value
    if not isinstance(value, pathlib.Path):
        result = pathlib.Path(os.environ.get(env_var, default_value))
        if result:
            result = result.absolute()
    return result


def _pickle_credentials(
    value: Optional[pathlib.Path] = None,
) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug(
        "Retrieving cal credentials from pickle file: <%s>(%s)", value, type(value)
    )
    value = _pickle_filepath(value)
    if value.exists():
        with open(value, "rb") as in_file:
            result = pickle.load(in_file)
        _LOGGER.info("Retrieved cal credentials from pickle file %s", value)
    else:
        _LOGGER.info("Pickle file %s does not exist, ignoring", value)
    return result


def _persist_credentials_pickle(
    value: Optional[credentials.Credentials] = None,
    credentials_pickle: Optional[pathlib.Path] = None,
) -> bool:
    result = False
    _LOGGER.debug(
        "Persisting cal credentials into pickle file: <%s>(%s)",
        credentials_pickle,
        type(credentials_pickle),
    )
    if isinstance(value, credentials.Credentials):
        credentials_pickle = _pickle_filepath(credentials_pickle)
        if not isinstance(credentials_pickle, pathlib.Path):
            raise TypeError(
                f"Expecting a {pathlib.Path.__name__} as credentials pickle file path."
                f" Got <{credentials_pickle}>({type(credentials_pickle)})"
            )
        with open(credentials_pickle, "wb") as out_file:
            pickle.dump(value, out_file)
            result = True
        _LOGGER.info(
            "Persisted cal credentials with client ID %s into pickle file: %s",
            value.client_id,
            credentials_pickle,
        )
    return result


_CREDENTIALS_SECRET_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_SECRET_NAME"


def _secret_credentials(value: Optional[str] = None) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug(
        "Retrieving cal credentials from cloud secret name: <%s>(%s)",
        value,
        type(value),
    )
    if not isinstance(value, str):
        value = os.environ.get(_CREDENTIALS_SECRET_ENV_VAR_NAME, None)
    if value:
        result = secrets.get(value)
        _LOGGER.info(
            "Retrieved cal credentials from cloud secret name: <%s>(%s)",
            value,
            type(value),
        )
        result = _refresh_credentials_if_needed(result)
    return result


def _refresh_credentials_if_needed(
    value: credentials.Credentials,
) -> credentials.Credentials:
    if (
        isinstance(value, credentials.Credentials)
        and value.expired
        and value.refresh_token
    ):
        _LOGGER.debug("Refreshing cal credentials for client ID: %s", value.client_id)
        value.refresh(requests.Request())
        _LOGGER.info("Refreshed cal credentials for client ID: %s", value.client_id)
    return value


_CREDENTIALS_JSON_FILE_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_JSON_FILENAME"
_DEFAULT_CREDENTIALS_JSON_FILE: str = "calendar_credentials.json"
_CALENDAR_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _json_credentials(
    value: Optional[pathlib.Path] = None,
) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug(
        "Retrieving cal credentials from JSON file: <%s>(%s)", value, type(value)
    )
    value = _json_filepath(value)
    if value.exists():
        app_flow = flow.InstalledAppFlow.from_client_secrets_file(
            value, _CALENDAR_SCOPES
        )
        result = app_flow.run_local_server(port=0)
        _LOGGER.info("Retrieved cal credentials from JSON file %s", value)
        _refresh_credentials_if_needed(result)
    else:
        _LOGGER.info("JSON file %s does not exist, ignoring", value)
    return result


def _json_filepath(value: Optional[pathlib.Path] = None) -> pathlib.Path:
    return _file_path_from_env_default_value(
        value, _CREDENTIALS_JSON_FILE_ENV_VAR_NAME, _DEFAULT_CREDENTIALS_JSON_FILE
    )
