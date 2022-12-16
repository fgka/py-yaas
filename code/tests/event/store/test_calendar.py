# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pathlib
import tempfile
from typing import Any, Dict, List

import pytest

from yaas.dto import event, request
from yaas.event.store import calendar

_TEST_CALENDAR_ID: str = "TEST_CALENDAR_ID"
# pylint: disable=consider-using-with
_TEST_CREDENTIALS_JSON: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
# pylint: enable=consider-using-with
_TEST_SCALE_REQUEST: request.ScaleRequest = request.ScaleRequest(
    topic="TEST_TOPIC", resource="TEST_RESOURCE", timestamp_utc=13
)


class TestReadOnlyGoogleCalendarStore:
    def setup(self):
        self.obj = calendar.ReadOnlyGoogleCalendarStore(
            calendar_id=_TEST_CALENDAR_ID, credentials_json=_TEST_CREDENTIALS_JSON
        )

    @pytest.mark.parametrize(
        "calendar_id,credentials_json",
        [
            (None, None),
            (None, _TEST_CREDENTIALS_JSON),
            (_TEST_CALENDAR_ID, None),
        ],
    )
    def test_ctor_nok(self, calendar_id: str, credentials_json: pathlib.Path):
        with pytest.raises(TypeError):
            calendar.ReadOnlyGoogleCalendarStore(
                calendar_id=calendar_id, credentials_json=credentials_json
            )

    def test_properties_ok(self):
        assert self.obj.calendar_id == _TEST_CALENDAR_ID
        assert self.obj.credentials_json == _TEST_CREDENTIALS_JSON

    def test_read_ok(self, monkeypatch):
        start_ts_utc = 0
        end_ts_utc = start_ts_utc + 123
        event_lst = [{"key": "value"}]

        def mocked_list_upcoming_events(**kwargs) -> List[Dict[str, Any]]:
            assert kwargs.get("calendar_id") == _TEST_CALENDAR_ID
            assert kwargs.get("credentials_json") == _TEST_CREDENTIALS_JSON
            assert kwargs.get("start") == start_ts_utc
            assert kwargs.get("end") == end_ts_utc
            return event_lst

        def mocked_to_request(value: Dict[str, Any]) -> List[request.ScaleRequest]:
            assert value == event_lst[0]
            return [_TEST_SCALE_REQUEST]

        monkeypatch.setattr(
            calendar.google_cal,
            calendar.google_cal.list_upcoming_events.__name__,
            mocked_list_upcoming_events,
        )
        monkeypatch.setattr(
            calendar.parser, calendar.parser.to_request.__name__, mocked_to_request
        )

        # When
        result = self.obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert result.source == _TEST_CALENDAR_ID
        assert len(result.timestamp_to_request) == 1
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert (
            result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0]
            == _TEST_SCALE_REQUEST
        )
