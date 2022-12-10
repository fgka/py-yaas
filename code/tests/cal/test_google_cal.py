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
from typing import List

import pytest

from google.auth.transport import requests
from google.oauth2 import credentials

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


def _create_credentials(expired: bool = False):
    return credentials.Credentials(
        token="TEST_TOKEN",
        refresh_token="TEST_REFRESH_TOKEN",
        expiry=datetime.utcnow() + timedelta(days=1 if not expired else -1),
    )


_TEST_CREDENTIALS: credentials.Credentials = _create_credentials()


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


def test__pickle_credentials_ok():
    # Given
    # pylint: disable=consider-using-with
    expected = "TEST"
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    with open(value, "wb") as out_file:
        pickle.dump(expected, out_file)
    # When
    result = google_cal._pickle_credentials(value)
    # Then
    assert result == expected


def test__pickle_credentials_ok_file_does_not_exist():
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = google_cal._pickle_credentials(value)
    # Then
    assert result is None


def test__persist_credentials_pickle_ok():
    # Given
    value = _TEST_CREDENTIALS
    # pylint: disable=consider-using-with
    credentials_pickle = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = google_cal._persist_credentials_pickle(value, credentials_pickle)
    # Then
    assert result
    content = google_cal._pickle_credentials(credentials_pickle)
    assert content.token == _TEST_CREDENTIALS.token


def test__persist_credentials_pickle_ok_no_credentials():
    # Given
    # pylint: disable=consider-using-with
    credentials_pickle = pathlib.Path(tempfile.NamedTemporaryFile(delete=True).name)
    # When
    result = google_cal._persist_credentials_pickle("TEST", credentials_pickle)
    # Then
    assert not result


def test__persist_credentials_pickle_nok_no_file(monkeypatch):
    # Given
    value = _TEST_CREDENTIALS
    monkeypatch.setenv(google_cal._CREDENTIALS_PICKLE_FILE_ENV_VAR_NAME, "")
    monkeypatch.setattr(google_cal, "_DEFAULT_CREDENTIALS_PICKLE_FILE", None)
    # When/Then
    with pytest.raises(TypeError):
        google_cal._persist_credentials_pickle(value, None)


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


def test__secret_credentials_ok(monkeypatch):
    secret_name = "TEST_SECRET"
    called = {}

    def mocked_get(value: str) -> credentials.Credentials:
        nonlocal called
        called["get"] = value
        return _TEST_CREDENTIALS

    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    # When
    result = google_cal._secret_credentials(secret_name)
    # Then
    assert result == _TEST_CREDENTIALS
    assert called.get("get") == secret_name


def test__secret_credentials_ok_env_secret_name(monkeypatch):
    secret_name = "TEST_SECRET"
    called = {}

    def mocked_get(value: str) -> credentials.Credentials:
        nonlocal called
        called["get"] = value
        return _TEST_CREDENTIALS

    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, secret_name)
    # When
    result = google_cal._secret_credentials(None)
    # Then
    assert result == _TEST_CREDENTIALS
    assert called.get("get") == secret_name


def test__secret_credentials_ok_no_env_secret_name(monkeypatch):
    called = {}

    def mocked_get(value: str) -> credentials.Credentials:
        nonlocal called
        called["get"] = value
        return _TEST_CREDENTIALS

    monkeypatch.setattr(google_cal.secrets, google_cal.secrets.get.__name__, mocked_get)
    monkeypatch.setenv(google_cal._CREDENTIALS_SECRET_ENV_VAR_NAME, "")
    # When
    result = google_cal._secret_credentials(None)
    # Then
    assert result is None
    assert called.get("get") is None


class _StubInstalledAppFlow:
    def __init__(self, creds: credentials.Credentials = _TEST_CREDENTIALS):
        self._creds = creds
        self.called = {}

    def run_local_server(self, port: int) -> credentials.Credentials:
        self.called[_StubInstalledAppFlow.run_local_server.__name__] = port
        return self._creds


def test__json_credentials_ok(monkeypatch):
    # Given
    # pylint: disable=consider-using-with
    value = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    app_flow = _StubInstalledAppFlow(_TEST_CREDENTIALS)
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
    result = google_cal._json_credentials(value)
    # Then
    assert result == _TEST_CREDENTIALS
    assert called.get("from_client_secrets_file") == (
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
