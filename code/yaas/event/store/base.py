# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of event stores.
"""
import abc
from datetime import datetime, timedelta
from typing import Callable, Optional

from yaas.dto import event
from yaas import logger

_LOGGER = logger.get(__name__)

_DEFAULT_END_TS_FROM_NOW_IN_DAYS: int = 7
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS: int = 30


def _default_start_ts_utc() -> int:
    """
    Returns current UTC timestamp.
    """
    return int(datetime.utcnow().timestamp())


def _default_end_ts_utc() -> int:
    """
    Returns the current UTC timestamp + :py:data:`_DEFAULT_END_TS_FROM_NOW_IN_DAYS`.
    """
    result = datetime.utcnow() + timedelta(days=_DEFAULT_END_TS_FROM_NOW_IN_DAYS)
    return int(result.timestamp())


def _default_max_end_ts_utc() -> int:
    """
    Returns current UTC timestamp + :py:data:`_MAXIMUM_END_TS_FROM_NOW_IN_DAYS`.
    """
    result = datetime.utcnow() + timedelta(days=_MAXIMUM_END_TS_FROM_NOW_IN_DAYS)
    return int(result.timestamp())


class StoreError(Exception):
    """To code Store errors"""


class Store(abc.ABC):
    """
    Generic class to define a :py:class:`event.EventSnapshot` store.
    """

    def __init__(
        self,
        *,
        default_start_ts_utc_fn: Optional[Callable[[], int]] = _default_start_ts_utc,
        default_end_ts_utc_fn: Optional[Callable[[], int]] = _default_end_ts_utc,
        max_end_ts_utc_fn: Optional[Callable[[], int]] = _default_max_end_ts_utc,
    ):
        self._default_start_ts_utc_fn = default_start_ts_utc_fn
        self._default_end_ts_utc_fn = default_end_ts_utc_fn
        self._max_end_ts_utc_fn = max_end_ts_utc_fn

    def _effective_start_ts_utc(self, value: Optional[int] = None) -> Optional[int]:
        result = value
        if result is None:
            result = self._default_start_ts_utc_fn()
        if isinstance(result, int):
            result = max(0, result)
        if result != value:
            _LOGGER.info(
                "Original 'start_ts_utc' changed from <%s> to <%s>", value, result
            )
        return result

    def _effective_end_ts_utc(self, value: Optional[int] = None) -> Optional[int]:
        result = value
        if result is None:
            result = self._default_end_ts_utc_fn()
        if isinstance(result, int):
            result = max(0, min(result, self._max_end_ts_utc_fn()))
        if result != value:
            _LOGGER.info(
                "Original 'end_ts_utc' changed from <%s> to <%s>", value, result
            )
        return result

    def read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        """
        Will retrieve a snapshot from the store that contains all events
            within the range specified by ``[start_ts_utc, end_ts_utc]``.

        Args:
            start_ts_utc: earliest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.
            end_ts_utc: latest event possible in the snapshot.
                It *must* respect the constraint: ``start_ts_utc > end_ts_utc``.
                Default: :py:obj:`None`, meaning is given by implementation.

        Returns:
            returns an instance of :py:class:`event.EventSnapshot`, event if empty.

        Raises:
            :py:class:`StoreError`
        """
        start_ts_utc = self._effective_start_ts_utc(start_ts_utc)
        end_ts_utc = self._effective_end_ts_utc(end_ts_utc)
        if start_ts_utc > end_ts_utc:
            raise ValueError(
                f"Start value <{start_ts_utc}> must be greater or equal end value <{end_ts_utc}>. Got start - end = {start_ts_utc - end_ts_utc}"
            )
        try:
            result = self._read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        except Exception as err:
            raise StoreError(
                f"Could not read {event.EventSnapshot.__name__} for effective range [{start_ts_utc}, {end_ts_utc}]. Error: {err}"
            ) from err
        if not isinstance(result, event.EventSnapshot):
            raise StoreError(
                f"Read did not return a valid {event.EventSnapshot.__name__} instance. Got <{result}>({type(result)})"
            )
        return result

    @abc.abstractmethod
    def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise NotImplementedError

    def write(
        self,
        value: event.EventSnapshot,
        *,
        overwrite_within_range: Optional[bool] = True,
    ) -> None:
        """
        Will store the snapshot and, if overwrite is set to :py:obj:`True`,
            will remove all entries within the period contained in the snapshot.

        Args:
            value: events to be stored.
            overwrite_within_range: to tell store to overwrite the period.
                It is equivalent to calling :py:meth:`remove` before calling this.

        Raises:
            :py:class:`StoreError`
        """
        if not isinstance(value, event.EventSnapshot):
            raise TypeError(
                f"Value argument must be an instance of {event.EventSnapshot.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        if overwrite_within_range and value.timestamp_to_request:
            start_ts_utc, end_ts_utc = value.range()
            self.remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        try:
            self._write(value)
        except Exception as err:
            raise StoreError(f"Could not write {value} to store. Error: {err}") from err

    def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        raise NotImplementedError

    def remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        """
        Will remove all events within the range specified by ``[start_ts_utc, end_ts_utc]``
            and return them.

        Args:
            start_ts_utc: earliest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.
            end_ts_utc: latest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.

        Returns:
            returns an instance of :py:class:`event.EventSnapshot`, with removed events.

        Raises:
            :py:class:`StoreError`
        """
        start_ts_utc = self._effective_start_ts_utc(start_ts_utc)
        end_ts_utc = self._effective_end_ts_utc(end_ts_utc)
        try:
            result = self._remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        except Exception as err:
            raise StoreError(
                f"Could not remove events for effective range [{start_ts_utc}, {end_ts_utc}]. "
                f"Error: {err}"
            ) from err
        if not isinstance(result, event.EventSnapshot):
            raise StoreError(
                f"Remove did not return a valid {event.EventSnapshot.__class__.__name__} instance. "
                f"Got <{result}>({type(result)})"
            )
        return result

    @abc.abstractmethod
    def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise NotImplementedError


class ReadOnlyStore(Store, abc.ABC):
    """
    To be implemented by read-only stores.
    """

    def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )

    def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )
