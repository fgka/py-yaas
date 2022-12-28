# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of event stores.
"""
# pylint: enable=line-too-long
import abc
from collections import abc as collections_abc
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Union

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


class StoreContextManager(collections_abc.Coroutine, abc.ABC):
    # pylint: disable=line-too-long
    """
    Generic class to define a :py:class:`event.EventSnapshot` store
        as an `Asynchronous Context Manager`_.

    Usage::
        my_store = MyStore()
        async with my_store:
            result = await my_store.read(start_ts_utc=0, end_ts_utc=1)

    .. _Asynchronous Context Manager: https://peps.python.org/pep-0492/#asynchronous-context-managers-and-async-with
    """
    # pylint: enable=line-too-long

    def __init__(
        self,
        *,
        default_start_ts_utc_fn: Optional[Callable[[], int]] = _default_start_ts_utc,
        default_end_ts_utc_fn: Optional[Callable[[], int]] = _default_end_ts_utc,
        max_end_ts_utc_fn: Optional[Callable[[], int]] = _default_max_end_ts_utc,
    ):
        _LOGGER.debug("New %s with <%s>", self.__class__.__name__, locals())
        self._default_start_ts_utc_fn = default_start_ts_utc_fn
        self._default_end_ts_utc_fn = default_end_ts_utc_fn
        self._max_end_ts_utc_fn = max_end_ts_utc_fn

    def _effective_start_ts_utc(
        self, value: Optional[Union[int, float, datetime]] = None
    ) -> Optional[Any]:
        result = self._get_int_ts(value)
        if result is None:
            result = self._default_start_ts_utc_fn()
        if isinstance(result, int):
            result = max(0, result)
        if result != value:
            _LOGGER.info(
                "Original 'start_ts_utc' changed from <%s> to <%s>", value, result
            )
        return result

    @staticmethod
    def _get_int_ts(value: Optional[Union[int, float, datetime]] = None) -> int:
        result = value
        if isinstance(value, float):
            result = int(value)
        elif isinstance(value, datetime):
            result = int(value.timestamp())
        return result

    def _effective_end_ts_utc(
        self, value: Optional[Union[int, float, datetime]] = None
    ) -> Optional[int]:
        result = self._get_int_ts(value)
        if result is None:
            result = self._default_end_ts_utc_fn()
        if isinstance(result, int):
            result = max(0, min(result, self._max_end_ts_utc_fn()))
        if result != value:
            _LOGGER.info(
                "Original 'end_ts_utc' changed from <%s> to <%s>", value, result
            )
        return result

    def __await__(self):
        _LOGGER.debug("Called %s", self.__await__.__name__)
        return None

    async def __aenter__(self) -> "StoreContextManager":
        await self._open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._close()

    def send(self, value: Any) -> None:
        """
        From :py:class:`collections_abc.Coroutine`
        """
        _LOGGER.debug("Called %s with <%s>", self.send.__name__, value)

    def throw(self, err_type: Any, err_value: Any, err_traceback: Any) -> None:
        """
        From :py:class:`collections_abc.Coroutine`
        """
        _LOGGER.debug(
            "Called throw with <%s>, <%s>, and <%s>", err_type, err_value, err_traceback
        )
        raise err_type(err_value, err_traceback)

    def close(self) -> None:
        """
        From :py:class:`collections_abc.Coroutine`
        """
        _LOGGER.debug("Called %s", self.close.__name__)

    async def _open(self) -> None:
        """
        To be overwritten in case of resource allocation,
        like opening files or database connections.
        """

    async def _close(self) -> None:
        """
        To be overwritten in case of resource disposal,
        like closing files or database connections.
        """

    async def read(
        self,
        *,
        start_ts_utc: Optional[Union[int, float, datetime]] = None,
        end_ts_utc: Optional[Union[int, float, datetime]] = None,
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
        _LOGGER.debug("Read with %s", locals())
        start_ts_utc = self._effective_start_ts_utc(start_ts_utc)
        end_ts_utc = self._effective_end_ts_utc(end_ts_utc)
        if start_ts_utc > end_ts_utc:
            raise ValueError(
                f"Start value <{start_ts_utc}> must be greater or equal end value <{end_ts_utc}>. "
                f"Got start - end = {start_ts_utc - end_ts_utc}"
            )
        try:
            result = await self._read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        except Exception as err:
            raise StoreError(
                f"Could not read {event.EventSnapshot.__name__} "
                f"for effective range [{start_ts_utc}, {end_ts_utc}]. "
                f"Error: {err}"
            ) from err
        if not isinstance(result, event.EventSnapshot):
            raise StoreError(
                f"Read did not return a valid {event.EventSnapshot.__name__} instance. "
                f"Got <{result}>({type(result)})"
            )
        return result

    @abc.abstractmethod
    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise NotImplementedError

    async def write(
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
        _LOGGER.debug("Write with %s", locals())
        if not isinstance(value, event.EventSnapshot):
            raise TypeError(
                f"Value argument must be an instance of {event.EventSnapshot.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        if overwrite_within_range and value.timestamp_to_request:
            start_ts_utc, end_ts_utc = value.range()
            await self.remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        try:
            await self._write(value)
        except Exception as err:
            raise StoreError(f"Could not write {value} to store. Error: {err}") from err

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        raise NotImplementedError

    async def remove(
        self,
        *,
        start_ts_utc: Optional[Union[int, float, datetime]] = None,
        end_ts_utc: Optional[Union[int, float, datetime]] = None,
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
        _LOGGER.debug("Remove with %s", locals())
        start_ts_utc = self._effective_start_ts_utc(start_ts_utc)
        end_ts_utc = self._effective_end_ts_utc(end_ts_utc)
        try:
            result = await self._remove(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
            )
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
    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise NotImplementedError

    async def archive(
        self,
        *,
        start_ts_utc: Optional[Union[int, float, datetime]] = None,
        end_ts_utc: Optional[Union[int, float, datetime]] = None,
    ) -> None:
        """
        Similar to :py:meth:`remove` but will move the data out of the current store into a
            _cold_ storage.
        The archiving content is the one within the range specified by
            ``[start_ts_utc, end_ts_utc]`` and return them.

        Args:
            start_ts_utc: earliest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.
            end_ts_utc: latest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.

        Returns:

        Raises:
            :py:class:`StoreError`
        """
        _LOGGER.debug("Archive with %s", locals())
        start_ts_utc = self._effective_start_ts_utc(start_ts_utc)
        end_ts_utc = self._effective_end_ts_utc(end_ts_utc)
        try:
            await self._archive(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        except Exception as err:
            raise StoreError(
                f"Could not remove events for effective range [{start_ts_utc}, {end_ts_utc}]. "
                f"Error: {err}"
            ) from err

    @abc.abstractmethod
    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        raise NotImplementedError


class ReadOnlyStoreContextManager(StoreContextManager, abc.ABC):
    """
    To be implemented by read-only stores.
    """

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )
