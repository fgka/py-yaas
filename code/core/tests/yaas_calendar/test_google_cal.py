# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,protected-access,too-few-public-methods,invalid-name,missing-class-docstring
# type: ignore
import json
import pathlib
import pickle
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pytest
from google.auth.transport import requests
from google.oauth2 import credentials
from google_auth_oauthlib import flow
from googleapiclient import discovery, http  # pylint: disable=unused-import; # noqa: F401

from yaas_calendar import google_cal
from yaas_common import const

# pylint: disable=consider-using-with
_TEST_PATH_VALUE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
_TEST_DEFAULT_PATH_VALUE_ENV_VAR: str = "TEST_ENV_VAR"
_TEST_DEFAULT_PATH_VALUE_ENV_VAR_VALUE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
_TEST_DEFAULT_PATH_VALUE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
# pylint: enable=consider-using-with


def _create_credentials(expired: bool = False) -> credentials.Credentials:
    return credentials.Credentials(
        token="TEST_TOKEN",
        refresh_token="TEST_REFRESH_TOKEN",
        expiry=datetime.utcnow() + timedelta(days=1 if not expired else -1),
    )


_TEST_CREDENTIALS: credentials.Credentials = _create_credentials()
_TEST_CREDENTIALS_JSON: str = _TEST_CREDENTIALS.to_json()
_TEST_INITIAL_CREDENTIALS_JSON: str = dict(installed=_TEST_CREDENTIALS_JSON)
_TEST_CALENDAR_ID: str = "TEST_CALENDAR_ID"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "amount_arg,exp_amount,end,exp_kwargs",
    [
        (None, google_cal.DEFAULT_LIST_EVENTS_AMOUNT, None, dict(timeMax=None)),
        (10, 10, None, dict(timeMax=None)),
        (None, None, 123, dict(timeMax=google_cal._iso_utc_zulu(123))),
        (10, None, 123, dict(timeMax=google_cal._iso_utc_zulu(123))),
    ],
)
async def test_list_upcoming_events_ok(
    monkeypatch, amount_arg: int, exp_amount: int, end: int, exp_kwargs: Dict[str, Any]
):
    # Given
    amount_arg = 10
    calendar_id = _TEST_CALENDAR_ID
    credentials_json = _TEST_CREDENTIALS_JSON
    service_arg = "TEST_SERVICE"
    credentials_json_arg = None
    kwargs_for_list_arg = None
    amount_used = None
    expected = ["TEST"]

    async def mocked_calendar_service(**kwargs) -> Any:
        nonlocal credentials_json_arg
        credentials_json_arg = kwargs.get("credentials_json")
        return service_arg

    def mocked_list_all_events(*, service: Any, amount: int, kwargs_for_list: Dict[str, Any]) -> List[Any]:
        nonlocal amount_used, kwargs_for_list_arg
        amount_used = amount
        kwargs_for_list_arg = kwargs_for_list
        assert service == service_arg
        return expected

    monkeypatch.setattr(google_cal, google_cal._calendar_service.__name__, mocked_calendar_service)
    monkeypatch.setattr(google_cal, google_cal._list_all_events.__name__, mocked_list_all_events)

    # When
    result = await google_cal.list_upcoming_events(
        calendar_id=calendar_id,
        credentials_json=credentials_json,
        amount=amount_arg,
        start=0,
        end=end,
    )
    # Then
    assert result == expected
    assert credentials_json_arg == credentials_json
    assert amount_used == exp_amount
    for key, val in exp_kwargs.items():
        assert kwargs_for_list_arg.get(key) == val


class _StubHttpRequest:
    """Stub of :py:class:`http.HttpRequest`."""

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._result = result
        self.called = {}

    def execute(self) -> Dict[str, Any]:
        self.called[_StubHttpRequest.execute.__name__] = True
        return dict(items=self._result)


class _StubEvents:
    """Stub of :py:class:`discovery.Resource`."""

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._executable = _StubHttpRequest(result=result)
        self.called = {}

    def list(self, **kwargs) -> _StubHttpRequest:
        self.called[_StubEvents.list.__name__] = kwargs
        return self._executable


class _StubGoogleCalServiceResource:
    """Stub of :py:class:`discovery.Resource`."""

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._events = _StubEvents(result=result)
        self.called = {}

    def events(self) -> _StubEvents:
        self.called[_StubGoogleCalServiceResource.events.__name__] = True
        return self._events


def test__list_all_events_ok_amount_given():
    # Given
    amount = 10
    list_results = []
    for ndx in range(amount + 1):
        list_results.append(dict(key=f"value_{ndx}"))
    service = _StubGoogleCalServiceResource(result=list_results)
    kwargs_for_list = dict(arg_1="value_1", arg_2="value_2")
    # When
    result = google_cal._list_all_events(service=service, amount=amount, kwargs_for_list=kwargs_for_list)
    # Then
    assert len(result) == amount
    assert service.called.get(_StubGoogleCalServiceResource.events.__name__)
    assert service._events.called.get(_StubEvents.list.__name__) == kwargs_for_list
    assert service._events._executable.called.get(_StubHttpRequest.execute.__name__)


@pytest.mark.parametrize(
    "value,env_var_value,default_value,expected",
    [
        (  # value is correct
            _TEST_PATH_VALUE,
            str(_TEST_DEFAULT_PATH_VALUE_ENV_VAR_VALUE),
            str(_TEST_DEFAULT_PATH_VALUE),
            _TEST_PATH_VALUE,
        ),
        (  # env var value, since it is provided and value is None
            None,
            str(_TEST_DEFAULT_PATH_VALUE_ENV_VAR_VALUE),
            str(_TEST_DEFAULT_PATH_VALUE),
            _TEST_DEFAULT_PATH_VALUE_ENV_VAR_VALUE,
        ),
        (  # default value, because env var and value are None
            None,
            "",
            str(_TEST_DEFAULT_PATH_VALUE),
            _TEST_DEFAULT_PATH_VALUE,
        ),
    ],
)
def test__file_path_from_env_default_value_ok(
    monkeypatch,
    value: pathlib.Path,
    env_var_value: pathlib.Path,
    default_value: pathlib.Path,
    expected: pathlib.Path,
):
    # Given
    monkeypatch.setenv(_TEST_DEFAULT_PATH_VALUE_ENV_VAR, env_var_value)
    # When
    result = google_cal._file_path_from_env_default_value(value, _TEST_DEFAULT_PATH_VALUE_ENV_VAR, default_value)
    # Then
    assert result == expected


@pytest.mark.asyncio
async def test__pickle_credentials_ok():
    # Given
    # pylint: disable=consider-using-with
    expected = "TEST"
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    with open(value, "wb") as out_file:
        pickle.dump(expected, out_file)
    # When
    result = await google_cal._pickle_credentials(value)
    # Then
    assert result == expected


@pytest.mark.asyncio
async def test__pickle_credentials_ok_file_does_not_exist():
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = await google_cal._pickle_credentials(value)
    # Then
    assert result is None


@pytest.mark.asyncio
async def test__persist_credentials_pickle_ok():
    # Given
    value = _TEST_CREDENTIALS
    # pylint: disable=consider-using-with
    credentials_pickle = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = await google_cal._persist_credentials_pickle(value, credentials_pickle)
    # Then
    assert result
    content = await google_cal._pickle_credentials(credentials_pickle)
    assert content.token == value.token


@pytest.mark.asyncio
async def test__persist_credentials_pickle_ok_no_credentials():
    # Given
    # pylint: disable=consider-using-with
    credentials_pickle = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = await google_cal._persist_credentials_pickle("TEST", credentials_pickle)
    # Then
    assert not result


@pytest.mark.asyncio
async def test__persist_credentials_pickle_nok_no_file(monkeypatch):
    # Given
    value = _TEST_CREDENTIALS
    monkeypatch.setenv(google_cal._CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME, "")
    monkeypatch.setattr(google_cal, "_DEFAULT_CREDENTIALS_PICKLE_FILE", None)
    # When/Then
    with pytest.raises(TypeError):
        await google_cal._persist_credentials_pickle(value, None)


@pytest.mark.parametrize("expired", [True, False])
def test__refresh_credentials_if_needed_ok(monkeypatch, expired):
    creds = _create_credentials(expired=expired)
    called = {}

    def mocked_refresh(value: requests.Request) -> None:
        nonlocal called
        called["refresh"] = value

    monkeypatch.setattr(creds, creds.refresh.__name__, mocked_refresh)
    # When
    result = google_cal._refresh_credentials_if_needed(creds)
    # Then
    assert result == creds
    assert (called.get("refresh") is not None) == expired
    if expired:
        assert isinstance(called.get("refresh"), requests.Request)


class _StubInstalledAppFlow:
    def __init__(self, creds: credentials.Credentials = _TEST_CREDENTIALS):
        self._creds = creds
        self.called = {}

    def run_local_server(self, port: int) -> credentials.Credentials:
        self.called[_StubInstalledAppFlow.run_local_server.__name__] = port
        return self._creds


@pytest.mark.asyncio
async def test__secret_credentials_ok(monkeypatch):
    secret_name = "TEST_SECRET"
    expected = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(expected)
    called = _mock_credentials(monkeypatch, cal_creds=expected, app_flow=app_flow)
    # When
    result = await google_cal._secret_credentials(secret_name)
    # Then
    assert result == expected
    assert called.get(google_cal.secrets.get.__name__) == secret_name


def _mock_credentials(
    monkeypatch,
    *,
    cal_creds: Optional[credentials.Credentials] = None,
    app_flow: Optional[flow.InstalledAppFlow] = None,
) -> Dict[str, Any]:
    called = {}
    if cal_creds is None:
        cal_creds = _TEST_CREDENTIALS
    if app_flow is None:
        app_flow = _StubInstalledAppFlow(cal_creds)

    def mocked_from_client_secrets_file(in_file: pathlib.Path, scopes: List[str]) -> credentials.Credentials:
        nonlocal called
        called[google_cal.flow.InstalledAppFlow.from_client_secrets_file.__name__] = (
            in_file,
            scopes,
        )
        return app_flow

    def mocked_from_authorized_user_file(
        in_file: pathlib.Path,
    ) -> credentials.Credentials:
        nonlocal called
        called[google_cal.credentials.Credentials.from_authorized_user_file.__name__] = in_file
        return _TEST_CREDENTIALS

    async def mocked_get(value: str) -> str:
        nonlocal called
        called[google_cal.secrets.get.__name__] = value
        return cal_creds.to_json()

    async def mocked_put(*, secret_name: str, content: str) -> str:  # pylint: disable=unused-argument
        nonlocal called
        called[google_cal.secrets.put.__name__] = locals()
        return secret_name

    async def mocked_clean_up(  # pylint: disable=unused-argument
        *, secret_name: str, amount_to_keep: Optional[int] = None
    ) -> None:
        nonlocal called
        called[google_cal.secrets.clean_up.__name__] = locals()

    monkeypatch.setattr(
        google_cal.flow.InstalledAppFlow,
        google_cal.flow.InstalledAppFlow.from_client_secrets_file.__name__,
        mocked_from_client_secrets_file,
    )
    monkeypatch.setattr(
        google_cal.credentials.Credentials,
        google_cal.credentials.Credentials.from_authorized_user_file.__name__,
        mocked_from_authorized_user_file,
    )
    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.put.__name__, mocked_put)
    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.clean_up.__name__, mocked_clean_up)

    return called


@pytest.mark.asyncio
async def test__secret_credentials_ok_env_secret_name(monkeypatch):
    secret_name = "TEST_SECRET"
    expected = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(expected)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, secret_name)
    called = _mock_credentials(monkeypatch, cal_creds=expected, app_flow=app_flow)
    # When
    result = await google_cal._secret_credentials(None)
    # Then
    assert result == expected
    assert called.get(google_cal.secrets.get.__name__) == secret_name


@pytest.mark.asyncio
async def test__secret_credentials_ok_no_env_secret_name(monkeypatch):
    called = {}

    async def mocked_get(value: str) -> credentials.Credentials:
        nonlocal called
        called[google_cal.secrets.get.__name__] = value
        return _TEST_CREDENTIALS_JSON

    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, "")
    # When
    result = await google_cal._secret_credentials(None)
    # Then
    assert result is None
    assert called.get(google_cal.secrets.get.__name__) is None


def test__json_credentials_ok_non_initial(monkeypatch):
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    creds = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(creds)
    called = _mock_credentials(monkeypatch, cal_creds=creds, app_flow=app_flow)
    with open(value, "w", encoding=const.ENCODING_UTF8) as out_json:
        out_json.write(creds.to_json())
    # When
    result = google_cal._json_credentials(value)
    # Then
    assert result == creds
    assert called.get(google_cal.credentials.Credentials.from_authorized_user_file.__name__) == value
    assert app_flow.called.get(_StubInstalledAppFlow.run_local_server.__name__) is None


def test__json_credentials_ok_initial(monkeypatch):
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    creds = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(creds)
    called = _mock_credentials(monkeypatch, cal_creds=creds, app_flow=app_flow)
    with open(value, "w", encoding=const.ENCODING_UTF8) as out_json:
        json.dump(_TEST_INITIAL_CREDENTIALS_JSON, out_json)
    # When
    result = google_cal._json_credentials(value)
    # Then
    assert result == creds
    assert called.get(google_cal.flow.InstalledAppFlow.from_client_secrets_file.__name__) == (
        value,
        google_cal._CALENDAR_SCOPES,
    )
    assert app_flow.called.get(_StubInstalledAppFlow.run_local_server.__name__) == 0


def test__json_credentials_ok_file_does_not_exist():
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = google_cal._json_credentials(value)
    # Then
    assert result is None


_TEST_SECRET_NAME: str = "projects/test-project/secrets/test-secret"


@pytest.mark.asyncio
async def test__put_secret_credentials_ok(monkeypatch):
    # Given
    secret_name = _TEST_SECRET_NAME
    full_secret_name = secret_name + "/versions/latest"
    content = "CONTENT"
    # pylint: disable=consider-using-with
    credentials_json = pathlib.Path(tempfile.NamedTemporaryFile().name)
    # pylint: enable=consider-using-with
    with open(credentials_json, "w", encoding=const.ENCODING_UTF8) as out_json:
        out_json.write(content)
    called = _mock_credentials(monkeypatch)
    # When
    await google_cal._put_secret_credentials(full_secret_name, credentials_json)
    # Then: put
    assert called.get(google_cal.secrets.put.__name__, {}).get("secret_name") == full_secret_name
    assert called.get(google_cal.secrets.put.__name__, {}).get("content") == content
    # Then: clean_up
    assert called.get(google_cal.secrets.clean_up.__name__, {}).get("secret_name") == full_secret_name


@pytest.mark.asyncio
async def test_update_secret_credentials_ok(monkeypatch):
    # Given
    arg_calendar_id = _TEST_CALENDAR_ID
    arg_secret_name = _TEST_SECRET_NAME
    full_secret_name = arg_secret_name + "/versions/latest"
    # pylint: disable=consider-using-with
    arg_initial_credentials_json = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    # pylint: enable=consider-using-with
    called = {}

    async def mocked_secret_exists(  # pylint: disable=unused-argument
        secret_name: str,
    ) -> bool:
        nonlocal called
        if google_cal._put_secret_credentials.__name__ not in called:
            called[google_cal._secret_exists.__name__] = []
        called[google_cal._secret_exists.__name__].append(locals())
        return True

    async def mocked_put_secret_credentials(  # pylint: disable=unused-argument
        secret_name: str,
        credentials_json: Optional[pathlib.Path] = None,
    ) -> None:
        nonlocal called
        if google_cal._put_secret_credentials.__name__ not in called:
            called[google_cal._put_secret_credentials.__name__] = []
        called[google_cal._put_secret_credentials.__name__].append(locals())

    async def mocked_list_upcoming_events(  # pylint: disable=unused-argument
        *,
        calendar_id: str,
        credentials_json: Optional[pathlib.Path] = None,
        credentials_pickle: Optional[pathlib.Path] = None,
        secret_name: Optional[str] = None,
        amount: Optional[int] = None,
        start: Optional[Union[datetime, int]] = None,
        end: Optional[Union[datetime, int]] = None,
    ) -> List[Dict[str, Any]]:
        nonlocal called
        called[google_cal.list_upcoming_events.__name__] = locals()
        return []

    async def mocked_pickle_credentials(  # pylint: disable=unused-argument
        value: Optional[pathlib.Path] = None,
    ) -> credentials.Credentials:
        nonlocal called
        called[google_cal._pickle_credentials.__name__] = locals()

    async def mocked_persist_json_credentials(  # pylint: disable=unused-argument
        value: Union[credentials.Credentials, Dict[str, Any]],
        credentials_json: Optional[pathlib.Path] = None,
    ) -> bool:
        nonlocal called
        called[google_cal._persist_json_credentials.__name__] = locals()

    monkeypatch.setattr(
        google_cal,
        google_cal._secret_exists.__name__,
        mocked_secret_exists,
    )
    monkeypatch.setattr(
        google_cal,
        google_cal._put_secret_credentials.__name__,
        mocked_put_secret_credentials,
    )
    monkeypatch.setattr(
        google_cal,
        google_cal.list_upcoming_events.__name__,
        mocked_list_upcoming_events,
    )
    monkeypatch.setattr(google_cal, google_cal._pickle_credentials.__name__, mocked_pickle_credentials)
    monkeypatch.setattr(
        google_cal,
        google_cal._persist_json_credentials.__name__,
        mocked_persist_json_credentials,
    )

    # When
    await google_cal.update_secret_credentials(
        calendar_id=arg_calendar_id,
        secret_name=arg_secret_name,
        initial_credentials_json=arg_initial_credentials_json,
    )
    # Then: _put_secret_credentials
    called_put = called.get(google_cal._put_secret_credentials.__name__, [])
    assert len(called_put) == 2
    # Then: _put_secret_credentials[0]
    assert called_put[0].get("secret_name") == arg_secret_name
    assert called_put[0].get("credentials_json") == arg_initial_credentials_json
    # Then: list_upcoming_events
    assert called.get(google_cal.list_upcoming_events.__name__, {}).get("calendar_id") == arg_calendar_id
    assert called.get(google_cal.list_upcoming_events.__name__, {}).get("secret_name") == full_secret_name
    # Then: _pickle_credentials
    assert called.get(google_cal._pickle_credentials.__name__, {}).get("value") == called.get(
        google_cal.list_upcoming_events.__name__, {}
    ).get("credentials_pickle")
    # Then: _persist_json_credentials
    assert called.get(google_cal._persist_json_credentials.__name__, {}).get("credentials_json") == called.get(
        google_cal.list_upcoming_events.__name__, {}
    ).get("credentials_json")
    assert (
        called.get(google_cal._persist_json_credentials.__name__, {}).get("credentials_json")
        != arg_initial_credentials_json
    )
    # Then: _put_secret_credentials[1]
    assert called_put[1].get("secret_name") == arg_secret_name
    assert called_put[1].get("credentials_json") == called.get(google_cal.list_upcoming_events.__name__, {}).get(
        "credentials_json"
    )
