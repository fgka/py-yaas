# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for Google Calendar as event source.
"""
import pathlib
from typing import Any, Dict, List, Optional

from yaas.cal import google_cal, parser
from yaas.dto import event, request
from yaas.event.store import base
from yaas import logger

_LOGGER = logger.get(__name__)

_DEFAULT_END_TS_FROM_NOW_IN_DAYS: int = 7
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS_LOWER_BOUND: int = 1
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS_UPPER_BOUND: int = 360
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS: int = 30


class PickleFileStore(base.Store):
    """
    This class bridge the :py:module:`yaas.cal.google_cal` calls
        to comply with :py:class:`base.Store` interface.
    It also leverages :py:module:`yaas.cal.parser`
        to convert content into py:class:`request.ScaleRequest`.
    """

    def __init__(self, *, pickle_file: pathlib.Path, **kwargs):
        super(PickleFileStore, self).__init__(**kwargs)
        if not isinstance(pickle_file, pathlib.Path):
            raise TypeError(
                f"Credentials JSON must be a {pathlib.Path.__name__}. Got: <{pickle_file}>({type(pickle_file)})"
            )
        self._pickle_file = pickle_file

    def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        event_lst: List[Dict[str, Any]] = google_cal.list_upcoming_events(
            calendar_id=self._calendar_id,
            credentials_json=self._credentials_json,
            start=start_ts_utc,
            end=end_ts_utc,
        )
        request_lst: List[request.ScaleRequest] = []
        for item in event_lst:
            for req in parser.to_request(item):
                request_lst.append(req)
        return event.EventSnapshot.from_list_requests(
            source=self._calendar_id, request_lst=request_lst
        )
