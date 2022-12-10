# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for Google Calendar as event source.
"""
from typing import Optional

from yaas.dto import event
from yaas.event.store import base
from yaas import logger

_LOGGER = logger.get(__name__)

_DEFAULT_END_TS_FROM_NOW_IN_DAYS: int = 7
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS_LOWER_BOUND: int = 1
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS_UPPER_BOUND: int = 360
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS: int = 30


class ReadOnlyGoogleCalendarStore(base.ReadOnlyStore):
    """
    This class bridge the :py:module:`yaas.cal.google_cal` calls
        to comply with :py:class:`base.Store` interface.
    It also leverages :py:module:`yaas.cal.parser`
        to convert content into py:class:`request.ScaleRequest`.
    """

    def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        # TODO
        pass
