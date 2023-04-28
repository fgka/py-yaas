# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Store interface for Google Calendar as event source."""
import abc
import pathlib
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import icalendar

from yaas_caching import base, event
from yaas_calendar import dav, google_cal, parser
from yaas_common import logger, preprocess, request

_LOGGER = logger.get(__name__)


class ReadOnlyBaseCalendarStore(base.ReadOnlyStoreContextManager):
    """
    Provides a generalization of calendar event fetching.
    """

    @abc.abstractmethod
    def calendar_source(self) -> str:
        """
        Calendar identifier.
        """

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
        return event.EventSnapshot.from_list_requests(source=self.calendar_source(), request_lst=request_lst)

    @abc.abstractmethod
    async def _calendar_events(
        self, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> AsyncGenerator[Union[Dict[str, Any], icalendar.Calendar], None]:
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
        if credentials_json is None and secret_name is None:
            raise TypeError(
                f"Either the secret name or JSON file for credentials be provided. "
                f"Got: <{credentials_json}>({type(credentials_json)}) "
                f"and <{secret_name}>({type(secret_name)})"
            )
        self._calendar_id = preprocess.string(calendar_id, "calendar_id")
        self._credentials_json = preprocess.validate_type(
            credentials_json, "credentials_json", pathlib.Path, is_none_valid=True
        )
        self._secret_name = preprocess.string(secret_name, "secret_name", is_none_valid=True)

    @property
    def calendar_id(self) -> str:
        """Google Calendar ID."""
        return self._calendar_id

    def calendar_source(self) -> str:
        return self.calendar_id

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
    ) -> AsyncGenerator[Union[Dict[str, Any], icalendar.Calendar], None]:
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
        self._caldav_url = preprocess.string(caldav_url, "caldav_url")
        self._username = preprocess.string(username, "username")
        self._secret_name = preprocess.string(secret_name, "secret_name")

    @property
    def caldav_url(self) -> str:
        """CalDAV URL."""
        return self._caldav_url

    def calendar_source(self) -> str:
        return self.caldav_url

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
    ) -> AsyncGenerator[Union[Dict[str, Any], icalendar.Calendar], None]:
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
        calendar_id = preprocess.string(calendar_id, "calendar_id")
        caldav_url = dav.GOOGLE_DAV_URL_TMPL % calendar_id
        super().__init__(caldav_url=caldav_url, username=username, secret_name=secret_name, **kwargs)
