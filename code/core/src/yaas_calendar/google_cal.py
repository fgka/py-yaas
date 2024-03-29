# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364

Source: https://developers.google.com/calendar/api/quickstart/python
Source: https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/
"""
import asyncio
import json
import os
import pathlib
import pickle
import tempfile
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import aiofiles
from google.auth.transport import requests
from google.oauth2 import credentials
from google_auth_oauthlib import flow
from googleapiclient import discovery

from yaas_common import const, logger
from yaas_gcp import secrets, secrets_const

_LOGGER = logger.get(__name__)

DEFAULT_LIST_EVENTS_AMOUNT: int = 10


async def list_upcoming_events(
    *,
    calendar_id: str,
    credentials_json: Optional[pathlib.Path] = None,
    credentials_pickle: Optional[pathlib.Path] = None,
    secret_name: Optional[str] = None,
    amount: Optional[int] = None,
    start: Optional[Union[datetime, int]] = None,
    end: Optional[Union[datetime, int]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    # pylint: disable=line-too-long
    """Wraps the `list API`_.

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
            'description': '<html-blob><u></u>Description event repeat daily<br>&nbsp;target: projects/core-bq/locations/europe-west3/services/hello = 10<br>&nbsp;target : projects/core-bq/locations/europe-west3/services/hello = 10<u></u><br><u></u>target:projects/core-bq/locations/europe-west3/services/hello=10<br>&nbsp; &nbsp; target:&nbsp; &nbsp; projects/core-bq/locations/europe-west3/services/hello =&nbsp; &nbsp; &nbsp; 10&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<br>target :CloudRun / hello@&nbsp; core-bq/europe-west3= 10&nbsp; &nbsp; &nbsp;<u></u><br><u></u>target:CloudRun/hello@core-bq/europe-west3=10</html-blob><br><html-blob><br></html-blob><br><html-blob><u></u>&nbsp; target : CloudRun / hello&nbsp; &nbsp;@&nbsp; core-bq/europe-west3&nbsp; =&nbsp; 10&nbsp; &nbsp; &nbsp;&nbsp;<br><u></u><br><u></u>target : CloudRun / hello&nbsp; &nbsp;@&nbsp; core-bq/europe-west3&nbsp; &nbsp;=&nbsp; 10<br><u></u></html-blob>',
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
        credentials_json: calendar JSON credentials, if existing.
        credentials_pickle: cached Pickle file with credentials, if existing.
        secret_name: secret name containing the calendar credentials, if existing, in the format:
          `projects/<project id>/secrets/<secret id>/versions/<version>`
        amount: how many events to list, default: py:data:`DEFAULT_LIST_EVENTS_AMOUNT`.
        start: from when to start listing, default: current date/time.
        end: up until when to list, if given, will discard ``amount``.

    Returns:

    .. _list API: https://developers.google.com/calendar/api/v3/reference/events/list
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Listing upcoming events using: '%s'", locals())
    # Normalize input
    try:
        service = await _calendar_service(
            secret_name=secret_name,
            credentials_json=credentials_json,
            credentials_pickle=credentials_pickle,
        )
    except Exception as err:
        raise RuntimeError(
            f"Could NOT create calendar client for secret '{secret_name}', "
            f"JSON file: '{credentials_json}', "
            f"and Pickle file: '{credentials_pickle}'. "
            f"Error: {err}"
        ) from err
    if end is None:
        if not isinstance(amount, int):
            amount = DEFAULT_LIST_EVENTS_AMOUNT
    start_time = _iso_utc_zulu(start)
    _LOGGER.debug("Getting the upcoming %d events starting at %s", amount, start_time)
    # Prepare call
    kwargs_for_list = dict(
        calendarId=calendar_id,
        timeMin=start_time,
        singleEvents=True,
        orderBy="startTime",
    )
    if end:
        kwargs_for_list["timeMax"] = _iso_utc_zulu(end)
        amount = None
    # Retrieve entries
    try:
        async for event in _list_all_events(service=service, amount=amount, kwargs_for_list=kwargs_for_list):
            yield event
    except Exception as err:
        raise RuntimeError(
            f"Could not list calendar events using arguments: '{kwargs_for_list}', "
            f"amount: '{amount}', "
            f"and service: '{service}'. "
            f"Error: {err}"
        ) from err


def _iso_utc_zulu(value: Optional[Union[datetime, int]] = None) -> str:
    if not isinstance(value, datetime):
        if isinstance(value, int):
            value = datetime.utcfromtimestamp(value)
        else:
            value = datetime.utcnow()
    return value.isoformat() + "Z"


async def _list_all_events(
    *,
    service: discovery.Resource,
    amount: Optional[int],
    kwargs_for_list: Dict[str, Any],
) -> AsyncGenerator[Dict[str, Any], None]:
    count = 0
    # pagination/while trick
    while amount is None or count < amount:
        await asyncio.sleep(0)
        events_result = service.events().list(**kwargs_for_list).execute()
        for event in events_result.get("items", []):
            yield event
            await asyncio.sleep(0)
            count += 1
            if amount is not None and count >= amount:
                return
        # next page token
        next_page_token = events_result.get("nextPageToken")
        if not next_page_token:
            return
        # update kwargs only AFTER retrieving items AND getting the next page token
        kwargs_for_list["pageToken"] = next_page_token


async def _calendar_service(
    *,
    secret_name: Optional[str] = None,
    credentials_pickle: Optional[pathlib.Path] = None,
    credentials_json: Optional[pathlib.Path] = None,
) -> discovery.Resource:
    try:
        cal_creds = await _calendar_credentials(
            credentials_pickle=credentials_pickle,
            secret_name=secret_name,
            credentials_json=credentials_json,
        )
    except Exception as err:
        raise RuntimeError(
            f"Could not get Google Calendar using secret: '{secret_name}', "
            f"JSON: '{credentials_json}', "
            f"and Pickle: '{credentials_pickle}'. "
            f"Error: {err}"
        ) from err
    _refresh_credentials_if_needed(cal_creds)
    result: discovery.Resource = None
    if isinstance(cal_creds, credentials.Credentials):
        _LOGGER.debug(
            "Creating cal credentials service for client ID %s",
            cal_creds.client_id,
        )
        result = discovery.build("calendar", "v3", credentials=cal_creds, cache_discovery=False)
        _LOGGER.info("Created cal credentials service for client ID %s", cal_creds.client_id)
    else:
        _LOGGER.warning(
            "No credentials retrieved from either pickle file '%s', cloud secret '%s', or JSON file '%s'",
            credentials_pickle,
            secret_name,
            credentials_json,
        )
    return result


async def _calendar_credentials(
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
    result: credentials.Credentials = await _pickle_credentials(credentials_pickle)
    # Second: Cloud Secrets
    if not result:
        result = await _secret_credentials(secret_name, credentials_json)
    # Third: JSON
    if not result:
        result = _json_credentials(credentials_json)
    if not result:
        raise RuntimeError(
            "Could not find credentials for cal access."
            f" Tried pickle file '{credentials_pickle}'"
            f", cloud secrets '{secret_name}'"
            f", and JSON file '{credentials_json}'"
        )
    # Cache values on pickle file
    await _persist_credentials_pickle(result, credentials_pickle)
    return result


_CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_PICKLE_FILENAME"
_DEFAULT_CREDENTIALS_PICKLE_FILE: str = "calendar_credentials.pickle"


def _pickle_filepath(value: Optional[pathlib.Path] = None) -> pathlib.Path:
    return _file_path_from_env_default_value(
        value, _CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME, _DEFAULT_CREDENTIALS_PICKLE_FILE
    )


def _file_path_from_env_default_value(  # pylint: disable=invalid-name
    value: pathlib.Path, env_var: str, default_value: str
) -> pathlib.Path:
    result: pathlib.Path = value
    if not isinstance(value, pathlib.Path):
        result = None
        result_str = os.environ.get(env_var)
        if not result_str and default_value:
            result_str = default_value
        if result_str:
            result = pathlib.Path(result_str)
    if isinstance(result, pathlib.Path):
        result = result.absolute()
    return result


async def _pickle_credentials(
    value: Optional[pathlib.Path] = None,
) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug("Retrieving cal credentials from pickle file: '%s'(%s)", value, type(value))
    value = _pickle_filepath(value)
    if value.exists():
        async with aiofiles.open(value, "rb") as in_file:
            content = await in_file.read()
        if content:
            result = pickle.loads(content)
            _LOGGER.info("Retrieved cal credentials from pickle file %s", value)
        else:
            _LOGGER.warning("File %s exists, but it is empty, ignoring", value)
    else:
        _LOGGER.info("Pickle file %s does not exist, ignoring", value)
    return result


async def _persist_credentials_pickle(
    value: Optional[credentials.Credentials] = None,
    credentials_pickle: Optional[pathlib.Path] = None,
) -> bool:
    result = False
    _LOGGER.debug(
        "Persisting cal credentials into pickle file: '%s'(%s)",
        credentials_pickle,
        type(credentials_pickle),
    )
    if isinstance(value, credentials.Credentials):
        credentials_pickle = _pickle_filepath(credentials_pickle)
        if not isinstance(credentials_pickle, pathlib.Path):
            raise TypeError(
                f"Expecting a {pathlib.Path.__name__} as credentials pickle file path."
                f" Got '{credentials_pickle}'({type(credentials_pickle)})"
            )
        content = pickle.dumps(value)
        async with aiofiles.open(credentials_pickle, "wb") as out_file:
            await out_file.write(content)
        result = True
        _LOGGER.info(
            "Persisted cal credentials with client ID %s into pickle file: %s",
            value.client_id,
            credentials_pickle,
        )
    return result


_CREDENTIALS_SECRET_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_SECRET_NAME"


async def _secret_credentials(
    value: Optional[str] = None, credentials_json: Optional[pathlib.Path] = None
) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug(
        "Retrieving cal credentials from cloud secret name: '%s'(%s)",
        value,
        type(value),
    )
    if not isinstance(value, str):
        value = os.environ.get(_CREDENTIALS_SECRET_ENV_VAR_NAME, None)
    if value:
        secret_content = await secrets.get(value)
        _LOGGER.info(
            "Retrieved cal credentials from cloud secret name: '%s'(%s)",
            value,
            type(value),
        )
        await _persist_json_credentials(json.loads(secret_content), credentials_json)
        result = _json_credentials(credentials_json)
    return result


def _refresh_credentials_if_needed(
    value: credentials.Credentials,
) -> credentials.Credentials:
    if isinstance(value, credentials.Credentials) and value.expired and value.refresh_token:
        _LOGGER.debug("Refreshing cal credentials for client ID: %s", value.client_id)
        value.refresh(requests.Request())
        _LOGGER.info("Refreshed cal credentials for client ID: %s", value.client_id)
    return value


async def _persist_json_credentials(
    value: Union[credentials.Credentials, Dict[str, Any]],
    credentials_json: Optional[pathlib.Path] = None,
) -> bool:
    _LOGGER.debug(
        "Persisting cal credentials into JSON file: '%s'(%s)",
        credentials_json,
        type(credentials_json),
    )
    result = False
    if isinstance(value, credentials.Credentials):
        _LOGGER.info("Converting credentials object into dict")
        value = json.loads(value.to_json())
    if isinstance(value, dict):
        credentials_json = _json_filepath(credentials_json)
        if not isinstance(credentials_json, pathlib.Path):
            raise TypeError(
                f"Expecting a {pathlib.Path.__name__} as credentials JSON file path."
                f" Got '{credentials_json}'({type(credentials_json)})"
            )
        async with aiofiles.open(credentials_json, "w") as out_file:
            await out_file.write(json.dumps(value))
        result = True
        _LOGGER.info(
            "Persisted cal credentials with client ID %s into JSON file: %s",
            value.get("client_id"),
            credentials_json,
        )
    return result


_CALENDAR_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _json_credentials(
    value: Optional[pathlib.Path] = None,
) -> credentials.Credentials:
    result: credentials.Credentials = None
    _LOGGER.debug("Retrieving cal credentials from JSON file: '%s'(%s)", value, type(value))
    value = _json_filepath(value)
    if value.exists():
        if _is_initial_credentials(value):
            app_flow = flow.InstalledAppFlow.from_client_secrets_file(value, _CALENDAR_SCOPES)
            result = app_flow.run_local_server(port=0)
        else:
            result = credentials.Credentials.from_authorized_user_file(value)
        _LOGGER.info("Retrieved cal credentials from JSON file %s", value)
        _refresh_credentials_if_needed(result)
    else:
        _LOGGER.info("JSON file %s does not exist, ignoring", value)
    return result


_INITIAL_CREDENTIALS_KEYS: List[str] = ["installed", "web"]


def _is_initial_credentials(value: pathlib.Path) -> bool:
    result = False
    try:
        with open(value, "r", encoding=const.ENCODING_UTF8) as in_json:
            content = json.load(in_json)
    except Exception as err:
        raise RuntimeError(f"Could not decode JSON content from '{value}'. Error: {err}") from err
    if isinstance(content, dict):
        for key in _INITIAL_CREDENTIALS_KEYS:
            if key in content:
                result = True
                break
    return result


_CREDENTIALS_JSON_FILE_ENV_VAR_NAME: str = "CALENDAR_CREDENTIALS_JSON_FILENAME"
_DEFAULT_CREDENTIALS_JSON_FILE: str = f"{os.getcwd()}/calendar_credentials.json"


def _json_filepath(value: Optional[pathlib.Path] = None) -> pathlib.Path:
    return _file_path_from_env_default_value(value, _CREDENTIALS_JSON_FILE_ENV_VAR_NAME, _DEFAULT_CREDENTIALS_JSON_FILE)


async def update_secret_credentials(
    *,
    calendar_id: str,
    secret_name: str,
    initial_credentials_json: Optional[pathlib.Path] = None,
) -> None:
    """If needed, will update the secret with the user authorization for using
    Google Calendar.

    Args:
        calendar_id: which cal to list.
        secret_name: secret name containing the calendar credentials, if existing.
        initial_credentials_json: initial JSON file with Google Calendar credentials.

    Returns:
    """
    _LOGGER.debug(
        "Updating calendar secret credentials in '%s' for calendar ID '%s' and initial JSON credentials '%s'",
        secret_name,
        calendar_id,
        initial_credentials_json,
    )
    # validate input
    if not isinstance(calendar_id, str) or not calendar_id:
        raise ValueError(f"Calendar ID must be a non-empty string. Got: '{calendar_id}'({type(calendar_id)})")
    if not isinstance(secret_name, str) or not secret_name:
        raise ValueError(f"Secret name must be a non-empty string. Got: '{secret_name}'({type(secret_name)})")
    # secret name
    fqn_secret_name = secret_name
    if secrets_const.VERSION_SUB_STR not in secret_name:
        fqn_secret_name = secret_name + secrets_const.LATEST_VERSION_SUFFIX
    # push initial credentials
    if initial_credentials_json is not None and initial_credentials_json.exists():
        await _put_secret_credentials(secret_name, initial_credentials_json.absolute())
    else:
        secret_exists = await _secret_exists(fqn_secret_name)
        if not secret_exists:
            raise RuntimeError(
                f"Secret '{fqn_secret_name}' does not exist. "
                "In this case give an initial credentials JSON with content. "
                f"Got: '{initial_credentials_json}'"
            )
    # to by-pass caching
    # pylint: disable=consider-using-with
    credentials_json = pathlib.Path(tempfile.NamedTemporaryFile().name)
    credentials_pickle = pathlib.Path(tempfile.NamedTemporaryFile().name)
    # pylint: enable=consider-using-with
    # force checking credentials
    try:
        await list_upcoming_events(
            calendar_id=calendar_id,
            secret_name=fqn_secret_name,
            credentials_pickle=credentials_pickle,
            credentials_json=credentials_json,
            amount=1,
        )
    except Exception as err:
        raise RuntimeError(
            f"Could not list events for calendar {calendar_id} using secret {fqn_secret_name}. Error: {err}"
        ) from err
    # create JSON content
    cal_creds = await _pickle_credentials(credentials_pickle)
    await _persist_json_credentials(cal_creds, credentials_json)
    _LOGGER.info(
        "Refreshed JSON file '%s' with credentials from pickle cache in '%s'",
        credentials_json,
        credentials_pickle,
    )
    # push credentials with authorization.
    await _put_secret_credentials(secret_name, credentials_json.absolute())
    _LOGGER.info(
        "Updated calendar secret credentials in '%s' for calendar ID '%s' and initial JSON credentials '%s'",
        fqn_secret_name,
        calendar_id,
        initial_credentials_json,
    )


async def _put_secret_credentials(
    secret_name: str,
    credentials_json: Optional[pathlib.Path] = None,
) -> None:
    _LOGGER.info(
        "Updating secret '%s' with content from JSON file: '%s'",
        secret_name,
        credentials_json,
    )
    if isinstance(credentials_json, pathlib.Path):
        if credentials_json.exists():
            with open(credentials_json, "r", encoding=const.ENCODING_UTF8) as in_json:
                content = in_json.read()
            try:
                version = await secrets.put(secret_name=secret_name, content=content)
                _LOGGER.info("Secret content put into: %s", version)
            except Exception as err:
                raise RuntimeError(f"Could not put secret {secret_name}. Error: {err}") from err
            try:
                await secrets.clean_up(secret_name=secret_name)
                _LOGGER.info("Cleaned up secret: %s", secret_name)
            except Exception as err:
                raise RuntimeError(f"Could not clean up secret {secret_name}. Error: {err}") from err
        else:
            _LOGGER.warning(
                "Credentials JSON file does not exist. Got: '%s'",
                credentials_json.absolute(),
            )
    else:
        _LOGGER.warning(
            "Credentials JSON is not valid. Ignoring put to secret '%s'. Got file: '%s'(%s)",
            secret_name,
            credentials_json,
            type(credentials_json),
        )


async def _secret_exists(secret_name: str) -> bool:
    """For testing."""
    return await secrets.exists(secret_name)
