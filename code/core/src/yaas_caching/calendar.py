# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Store interface for Google Calendar as event source."""
import abc
import pathlib
from typing import Any, Dict, Generator, List, Optional

from yaas_caching import base, event
from yaas_calendar import dav, google_cal, parser
from yaas_common import logger, request

_LOGGER = logger.get(__name__)


class ReadOnlyBaseCalendarStore(base.ReadOnlyStoreContextManager):
    async def _read_ro(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> event.EventSnapshot:
        request_lst: List[request.ScaleRequest] = []
        async for item in self._calendar_events(start_ts_utc, end_ts_utc):
            for req in parser.to_request(event=item):
                if start_ts_utc <= req.timestamp_utc <= end_ts_utc:
                    request_lst.append(req)
        return event.EventSnapshot.from_list_requests(source=self._calendar_id, request_lst=request_lst)

    @abc.abstractmethod
    async def _calendar_events(
        self, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> Generator[Any, None, None]:
        pass


class ReadOnlyGoogleCalendarStore(ReadOnlyBaseCalendarStore):
    """This class bridge the :py:module:`yaas_calendar.google_cal` calls to comply with
    :py:class:`base.Store` interface.

    It also leverages :py:module:`yaas_calendar.parser`
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
            raise TypeError(f"Calendar ID must be a string. Got: <{calendar_id}>({type(calendar_id)})")
        if not isinstance(credentials_json, pathlib.Path) and not isinstance(secret_name, str):
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
        """Google Calendar ID."""
        return self._calendar_id

    @property
    def credentials_json(self) -> pathlib.Path:
        """Google Calendar corresponding credentials JSON file."""
        return self._credentials_json

    @property
    def secret_name(self) -> str:
        """Secret Manager secret name for Google Calendar credentials."""
        return self._secret_name

    async def _calendar_events(
        self, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> Generator[Any, None, None]:
        async for item in google_cal.list_upcoming_events(
            calendar_id=self._calendar_id,
            credentials_json=self._credentials_json,
            secret_name=self._secret_name,
            start=start_ts_utc,
            end=end_ts_utc,
        ):
            yield item


class ReadOnlyCalDavStore(ReadOnlyBaseCalendarStore):
    """This class bridge the :py:module:`yaas_calendar.caldav` calls to comply with
    :py:class:`base.Store` interface.

    It also leverages :py:module:`yaas_calendar.parser`
        to convert content into py:class:`request.ScaleRequest`.
    """

    def __init__(
        self,
        *,
        caldav_url: str,
        username: str,
        secret_name: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(caldav_url, str):
            raise TypeError(f"CalDAV URL must be a string. Got: <{caldav_url}>({type(caldav_url)})")
        if not isinstance(username, str):
            raise TypeError(f"Username must be provided. " f"Got <{username}>({type(username)})")
        if not isinstance(secret_name, str):
            raise TypeError(f"Secret name must be provided. " f"Got <{secret_name}>({type(secret_name)})")
        self._caldav_url = caldav_url
        self._username = username
        self._secret_name = secret_name

    @property
    def caldav_url(self) -> str:
        """CalDAV URL."""
        return self._caldav_url

    @property
    def username(self) -> str:
        """CalDAV username."""
        return self._username

    @property
    def secret_name(self) -> str:
        """Secret Manager secret name for CalDAV password."""
        return self._secret_name

    async def _calendar_events(
        self, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> Generator[Any, None, None]:
        async for item in dav.list_upcoming_events(
            url=self._caldav_url,
            username=self._username,
            secret_name=self._secret_name,
            start=start_ts_utc,
            end=end_ts_utc,
        ):
            yield item


class ReadOnlyGoogleCalDavStore(ReadOnlyCalDavStore):
    """
    Just convenient way to use CalDAV to access Google calendar using :py:class:`ReadOnlyCalDavStore`.
    """

    def __init__(
        self,
        *,
        calendar_id: str,
        username: str,
        secret_name: str,
        **kwargs,
    ):
        caldav_url = dav.GOOGLE_DAV_URL_TMPL % calendar_id
        super().__init__(caldav_url=caldav_url, username=username, secret_name=secret_name, **kwargs)
