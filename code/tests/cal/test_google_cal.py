# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from datetime import datetime, timedelta
import pathlib
import pickle
import tempfile
from typing import Any, Dict, List, Optional

import pytest

from google.auth.transport import requests
from google.oauth2 import credentials
from googleapiclient import discovery, http  # pylint: disable=unused-import

from yaas.cal import google_cal

# pylint: disable=consider-using-with
_TEST_PATH_VALUE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
_TEST_DEFAULT_PATH_VALUE_ENV_VAR: str = "TEST_ENV_VAR"
_TEST_DEFAULT_PATH_VALUE_ENV_VAR_VALUE: pathlib.Path = pathlib.Path(
    tempfile.NamedTemporaryFile().name
)
_TEST_DEFAULT_PATH_VALUE: pathlib.Path = pathlib.Path(
    tempfile.NamedTemporaryFile().name
)
# pylint: enable=consider-using-with


def _create_credentials(expired: bool = False) -> credentials.Credentials:
    return credentials.Credentials(
        token="TEST_TOKEN",
        refresh_token="TEST_REFRESH_TOKEN",
        expiry=datetime.utcnow() + timedelta(days=1 if not expired else -1),
    )


_TEST_CREDENTIALS: credentials.Credentials = _create_credentials()
_TEST_CREDENTIALS_JSON: str = _TEST_CREDENTIALS.to_json()
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
async def test_list_upcoming_events_ok(  # pylint: disable=too-many-locals
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

    async def mocked_list_all_events(
        *, service: Any, amount: int, kwargs_for_list: Dict[str, Any]
    ) -> List[Any]:
        nonlocal amount_used, kwargs_for_list_arg
        amount_used = amount
        kwargs_for_list_arg = kwargs_for_list
        assert service == service_arg
        return expected

    monkeypatch.setattr(
        google_cal, google_cal._calendar_service.__name__, mocked_calendar_service
    )
    monkeypatch.setattr(
        google_cal, google_cal._list_all_events.__name__, mocked_list_all_events
    )

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
    """
    Stub of :py:class:`http.HttpRequest`.
    """

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._result = result
        self.called = {}

    def execute(self) -> Dict[str, Any]:
        self.called[_StubHttpRequest.execute.__name__] = True
        return dict(items=self._result)


class _StubEvents:
    """
    Stub of :py:class:`discovery.Resource`.
    """

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._executable = _StubHttpRequest(result=result)
        self.called = {}

    def list(self, **kwargs) -> _StubHttpRequest:
        self.called[_StubEvents.list.__name__] = kwargs
        return self._executable


class _StubGoogleCalServiceResource:
    """
    Stub of :py:class:`discovery.Resource`.
    """

    def __init__(self, *, result: Optional[List[Dict[str, Any]]] = None):
        self._events = _StubEvents(result=result)
        self.called = {}

    def events(self) -> _StubEvents:
        self.called[_StubGoogleCalServiceResource.events.__name__] = True
        return self._events


@pytest.mark.asyncio
async def test__list_all_events_ok_amount_given():
    # Given
    amount = 10
    list_results = []
    for ndx in range(amount + 1):
        list_results.append(dict(key=f"value_{ndx}"))
    service = _StubGoogleCalServiceResource(result=list_results)
    kwargs_for_list = dict(arg_1="value_1", arg_2="value_2")
    # When
    result = await google_cal._list_all_events(
        service=service, amount=amount, kwargs_for_list=kwargs_for_list
    )
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
    result = google_cal._file_path_from_env_default_value(
        value, _TEST_DEFAULT_PATH_VALUE_ENV_VAR, default_value
    )
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


@pytest.mark.asyncio
@pytest.mark.parametrize("expired", [True, False])
async def test__refresh_credentials_if_needed_ok(monkeypatch, expired):
    creds = _create_credentials(expired=expired)
    called = {}

    def mocked_refresh(value: requests.Request) -> None:
        nonlocal called
        called["refresh"] = value

    monkeypatch.setattr(creds, creds.refresh.__name__, mocked_refresh)
    # When
    result = await google_cal._refresh_credentials_if_needed(creds)
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


# TODO with credentials for appflow and regular, currently only regular
@pytest.mark.asyncio
async def test__secret_credentials_ok(monkeypatch):
    secret_name = "TEST_SECRET"
    expected = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(expected)
    called = {}

    def mocked_from_client_secrets_file(
        in_file: pathlib.Path, scopes: List[str]
    ) -> credentials.Credentials:
        nonlocal called
        called["from_client_secrets_file"] = (in_file, scopes)
        return app_flow

    def mocked_from_authorized_user_file(
        in_file: pathlib.Path,
    ) -> credentials.Credentials:
        nonlocal called
        called["from_authorized_user_file"] = in_file
        return _TEST_CREDENTIALS

    async def mocked_get(value: str) -> str:
        nonlocal called
        called["get"] = value
        return expected.to_json()

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
    # When
    result = await google_cal._secret_credentials(secret_name)
    # Then
    assert result == expected
    assert called.get("get") == secret_name


@pytest.mark.asyncio
async def test__secret_credentials_ok_env_secret_name(monkeypatch):
    secret_name = "TEST_SECRET"
    expected = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(expected)
    called = {}

    def mocked_from_client_secrets_file(
        in_file: pathlib.Path, scopes: List[str]
    ) -> credentials.Credentials:
        nonlocal called
        called["from_client_secrets_file"] = (in_file, scopes)
        return app_flow

    async def mocked_get(value: str) -> str:
        nonlocal called
        called["get"] = value
        return expected.to_json()

    monkeypatch.setattr(
        google_cal.flow.InstalledAppFlow,
        google_cal.flow.InstalledAppFlow.from_client_secrets_file.__name__,
        mocked_from_client_secrets_file,
    )
    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, secret_name)
    # When
    result = await google_cal._secret_credentials(None)
    # Then
    assert result == expected
    assert called.get("get") == secret_name


@pytest.mark.asyncio
async def test__secret_credentials_ok_no_env_secret_name(monkeypatch):
    called = {}

    async def mocked_get(value: str) -> credentials.Credentials:
        nonlocal called
        called["get"] = value
        return _TEST_CREDENTIALS_JSON

    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, "")
    # When
    result = await google_cal._secret_credentials(None)
    # Then
    assert result is None
    assert called.get("get") is None


@pytest.mark.asyncio
async def test__json_credentials_ok(monkeypatch):
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    creds = _TEST_CREDENTIALS
    app_flow = _StubInstalledAppFlow(creds)
    called = {}

    def mocked_from_client_secrets_file(
        in_file: pathlib.Path, scopes: List[str]
    ) -> credentials.Credentials:
        nonlocal called
        called["from_client_secrets_file"] = (in_file, scopes)
        return app_flow

    monkeypatch.setattr(
        google_cal.flow.InstalledAppFlow,
        google_cal.flow.InstalledAppFlow.from_client_secrets_file.__name__,
        mocked_from_client_secrets_file,
    )
    # When
    result = await google_cal._json_credentials(value)
    # Then
    assert result == creds
    assert called.get("from_client_secrets_file") == (
        value,
        google_cal._CALENDAR_SCOPES,
    )
    assert app_flow.called.get(_StubInstalledAppFlow.run_local_server.__name__) == 0


@pytest.mark.asyncio
async def test__json_credentials_ok_file_does_not_exist():
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = await google_cal._json_credentials(value)
    # Then
    assert result is None
