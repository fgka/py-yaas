# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for Google Calendar as event source.
"""
# pylint: enable=line-too-long
import pathlib
from typing import Any, Dict, List, Optional

from yaas_calendar import google_cal, parser
from yaas_caching import base, event
from yaas_common import logger, request

_LOGGER = logger.get(__name__)


class ReadOnlyGoogleCalendarStore(base.ReadOnlyStoreContextManager):
    """
    This class bridge the :py:module:`yaas_gcp-scaler-scheduler-common.cal.google_cal` calls
        to comply with :py:class:`base.Store` interface.
    It also leverages :py:module:`yaas_gcp-scaler-scheduler-common.cal.parser`
        to convert content into py:class:`request.ScaleRequest`.
    """

    def __init__(
        self,
        *,
        calendar_id: str,
        credentials_json: Optional[pathlib.Path] = None,
        secret_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(calendar_id, str):
            raise TypeError(
                f"Calendar ID must be a string. Got: <{calendar_id}>({type(calendar_id)})"
            )
        if not isinstance(credentials_json, pathlib.Path) and not isinstance(
            secret_name, str
        ):
            raise TypeError(
                f"Either the secret name or JSON file for credentials be provided. "
                f"Got: <{credentials_json}>({type(credentials_json)}) "
                f"and <{secret_name}>({type(secret_name)})"
            )
        self._calendar_id = calendar_id
        self._credentials_json = credentials_json
        self._secret_name = secret_name

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

    @property
    def secret_name(self) -> str:
        """
        Secret Manager secret name for Google Calendar credentials.
        """
        return self._secret_name

    async def _read_ro(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> event.EventSnapshot:
        event_lst: List[Dict[str, Any]] = await google_cal.list_upcoming_events(
            calendar_id=self._calendar_id,
            credentials_json=self._credentials_json,
            secret_name=self._secret_name,
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
