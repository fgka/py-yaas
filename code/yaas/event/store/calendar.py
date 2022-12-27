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


class ReadOnlyGoogleCalendarStore(base.ReadOnlyStore):
    """
    This class bridge the :py:module:`yaas.cal.google_cal` calls
        to comply with :py:class:`base.Store` interface.
    It also leverages :py:module:`yaas.cal.parser`
        to convert content into py:class:`request.ScaleRequest`.
    """

    def __init__(
        self,
        *,
        calendar_id: str,
        credentials_json: pathlib.Path,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(calendar_id, str):
            raise TypeError(
                f"Calendar ID must be a string. Got: <{calendar_id}>({type(calendar_id)})"
            )
        if not isinstance(credentials_json, pathlib.Path):
            raise TypeError(
                f"Credentials JSON must be a {pathlib.Path.__name__}. "
                f"Got: <{credentials_json}>({type(credentials_json)})"
            )
        self._calendar_id = calendar_id
        self._credentials_json = credentials_json

    @property
    def calendar_id(self) -> str:
        """
        Google Calendar ID
        """
        return self._calendar_id

    @property
    def credentials_json(self) -> pathlib.Path:
        """
        Google Calendar corresponding credentials JSON file.
        """
        return self._credentials_json

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        event_lst: List[Dict[str, Any]] = await google_cal.list_upcoming_events(
            calendar_id=self._calendar_id,
            credentials_json=self._credentials_json,
            start=start_ts_utc,
            end=end_ts_utc,
        )
        request_lst: List[request.ScaleRequest] = []
        for item in event_lst:
            for req in parser.to_request(event=item):
                if start_ts_utc <= req.timestamp_utc <= end_ts_utc:
                    request_lst.append(req)
        return event.EventSnapshot.from_list_requests(
            source=self._calendar_id, request_lst=request_lst
        )
