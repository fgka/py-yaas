# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of event stores.
"""
# pylint: enable=line-too-long
import abc
import asyncio
import contextlib
import fcntl
import threading
from datetime import datetime, timedelta
import pathlib
from types import TracebackType
from typing import Any, Callable, List, Optional, Union, Type

from yaas.dto import event, request
from yaas import const, logger

_LOGGER = logger.get(__name__)

_DEFAULT_END_TS_FROM_NOW_IN_DAYS: int = 7
_MAXIMUM_END_TS_FROM_NOW_IN_DAYS: int = 30
_DEFAULT_LOCK_TIMEOUT_IN_SEC: int = 30
_LOCK_SLEEP_STEP_IN_SEC: int = 1


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


class StoreLockTimeoutError(StoreError):
    """
    Encodes timeouts when dealing with file locks.
    """


class FileBasedLockContextManager(contextlib.AbstractAsyncContextManager):
    """
    Creates a local file based lock mechanism.
    """

    def __init__(
        self,
        *,
        lock_file: pathlib.Path,
        lock_timeout_in_sec: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(lock_timeout_in_sec, int):
            lock_timeout_in_sec = _DEFAULT_LOCK_TIMEOUT_IN_SEC
        if lock_timeout_in_sec <= 0:
            raise ValueError(
                f"Lock timeout must be an integer > 0. Got: {lock_timeout_in_sec}"
            )
        if not isinstance(lock_file, pathlib.Path):
            raise TypeError(
                f"Lock file must be a {pathlib.Path.__name__}. "
                f"Got: <{lock_file}>({type(lock_file)})"
            )
        self._lock_file = lock_file
        self._lock_timeout_in_sec = lock_timeout_in_sec
        # pylint: disable=consider-using-with
        self._open_lock_file = open(self._lock_file, "w", encoding=const.ENCODING_UTF8)
        # pylint: enable=consider-using-with
        self._thread_lock = threading.Lock()

    def __del__(self):
        self._unlock()
        self._open_lock_file.close()

    @property
    def lock_file(self) -> pathlib.Path:
        """
        Lock file location
        """
        return self._lock_file

    @property
    def lock_timeout_in_sec(self) -> int:
        """
        How long to wait for a lock before raising :py:class:`StoreLockTimeoutError`.
        """
        return self._lock_timeout_in_sec

    def is_locked(self) -> bool:
        """
        Based on the internal thread lock.
        """
        return self._thread_lock.locked()

    def _lock(self) -> bool:
        """
        Blocks all file operations globally,
            so that writes don't trump each other and corrupt the files.

        Returns:
            :py:obj:`True` if lock has been acquired.
        """
        # pylint: disable=consider-using-with
        result = self._thread_lock.acquire(blocking=False)
        # pylint: enable=consider-using-with
        if result:
            result = self._fcntl_flock(True)
            if not result:
                self._thread_lock.release()
        else:
            _LOGGER.info("Could not acquire thread lock")
        return result

    def _fcntl_flock(self, is_lock: bool) -> bool:
        flag = fcntl.LOCK_EX if is_lock else fcntl.LOCK_UN
        try:
            fcntl.flock(self._open_lock_file, flag | fcntl.LOCK_NB)
            result = True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.info(
                "Could not %s lock on file %s. Error: %s",
                "acquire" if is_lock else "release",
                self._lock_file,
                err,
            )
            result = False
        return result

    def _unlock(self) -> bool:
        """
        UN-Blocks all file operations globally.
        """
        result = self._fcntl_flock(False)
        if result:
            self._thread_lock.release()
        else:
            _LOGGER.info("Could not unlock file %s", self._lock_file)
        return result

    async def _wait_for_lock_release_and_lock(self) -> None:
        """
        Holds and waits for the lock to be released.
        """
        end_ts_in_sec = datetime.utcnow().timestamp() + self._lock_timeout_in_sec
        remaining_time_in_sec = self._lock_timeout_in_sec
        while not self._lock():
            _LOGGER.info(
                "Waiting for lock. Sleeping %d sec, remaining wait time: %d sec",
                _LOCK_SLEEP_STEP_IN_SEC,
                remaining_time_in_sec,
            )
            await asyncio.sleep(_LOCK_SLEEP_STEP_IN_SEC)
            remaining_time_in_sec = int(end_ts_in_sec - datetime.utcnow().timestamp())
            if remaining_time_in_sec <= 0:
                raise StoreLockTimeoutError(
                    f"Could not acquire lock in the past {self._lock_timeout_in_sec} seconds. "
                    f"Lock state: {self.lock_state()}"
                )

    def lock_state(self) -> Any:
        """
        Information that helps to inform why it timeout-ed, it is "string-able"
        """
        stat = self._lock_file.stat()
        return dict(
            thread_lock=self._thread_lock.locked(),
            lock_file=self._lock_file,
            lock_created_time=f"{stat.st_ctime} / {datetime.fromtimestamp(stat.st_ctime)}",
            lock_modified_time=f"{stat.st_mtime} / {datetime.fromtimestamp(stat.st_mtime)}",
            lock_mode=oct(stat.st_mode),
        )

    async def __aenter__(self) -> "StoreContextManager":
        await self._wait_for_lock_release_and_lock()
        return self

    async def __aexit__(
        self,
        __exc_type: Optional[Type[BaseException]] = None,
        __exc_value: Optional[BaseException] = None,
        __traceback: Optional[TracebackType] = None,
    ) -> Optional[bool]:
        return self._unlock()


class StoreContextManager(contextlib.AbstractAsyncContextManager, abc.ABC):
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
        source: Optional[str] = None,
        default_start_ts_utc_fn: Optional[Callable[[], int]] = _default_start_ts_utc,
        default_end_ts_utc_fn: Optional[Callable[[], int]] = _default_end_ts_utc,
        max_end_ts_utc_fn: Optional[Callable[[], int]] = _default_max_end_ts_utc,
    ):
        _LOGGER.debug("New %s with <%s>", self.__class__.__name__, locals())
        if not isinstance(source, str):
            source = self.__class__.__name__
        self._source = source
        self._default_start_ts_utc_fn = default_start_ts_utc_fn
        self._default_end_ts_utc_fn = default_end_ts_utc_fn
        self._max_end_ts_utc_fn = max_end_ts_utc_fn
        self._has_changed = False

    @property
    def source(self) -> str:
        """
        How are the snapshots source identified.
        """
        return self._source

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

    async def __aenter__(self) -> "StoreContextManager":
        await self._open()
        return self

    async def __aexit__(
        self,
        __exc_type: Optional[Type[BaseException]] = None,
        __exc_value: Optional[BaseException] = None,
        __traceback: Optional[TracebackType] = None,
    ) -> Optional[bool]:
        await self._close()

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

    def _snapshot_from_request_lst(
        self, request_lst: Optional[List[request.ScaleRequest]] = None
    ) -> event.EventSnapshot:
        """
        Utility to create :py:class:`event.EventSnapshot`s.
        """
        return event.EventSnapshot.from_list_requests(
            source=self._source,
            request_lst=request_lst,
        )

    @property
    def has_changed(self) -> bool:
        """
        If any data modifying method has been called, it will be flagged here.
        """
        return self._has_changed

    async def read(
        self,
        *,
        start_ts_utc: Optional[Union[int, float, datetime]] = None,
        end_ts_utc: Optional[Union[int, float, datetime]] = None,
        is_archive: Optional[bool] = False,
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
            is_archive: if :py:obj:`True` will retrieve from archive instead of current.

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
            result = await self._read(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
            )
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
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
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
            removed = await self.remove(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
            )
            _LOGGER.debug("Removed existing before writing: %s", removed)
        if value.all_requests():
            try:
                await self._write(value)
                self._has_changed = True
            except Exception as err:
                raise StoreError(
                    f"Could not write {value} to store. Error: {err}"
                ) from err

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
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        """
        Will remove all events within the range specified by ``[start_ts_utc, end_ts_utc]``
            and return them.

        Args:
            start_ts_utc: earliest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.
            end_ts_utc: latest event possible in the snapshot.
                Default: :py:obj:`None`, meaning is given by implementation.
            is_archive: if :py:obj:`True` will remove from archive instead of current.

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
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
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
        if result.all_requests():
            self._has_changed = True
        return result

    @abc.abstractmethod
    async def _remove(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        raise NotImplementedError

    async def archive(
        self,
        *,
        start_ts_utc: Optional[Union[int, float, datetime]] = None,
        end_ts_utc: Optional[Union[int, float, datetime]] = None,
    ) -> event.EventSnapshot:
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
            result = await self._archive(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
            )
        except Exception as err:
            raise StoreError(
                f"Could not remove events for effective range [{start_ts_utc}, {end_ts_utc}]. "
                f"Error: {err}"
            ) from err
        if not isinstance(result, event.EventSnapshot):
            raise StoreError(
                f"Archive did not return a valid {event.EventSnapshot.__class__.__name__} "
                "instance. "
                f"Got <{result}>({type(result)})"
            )
        if result.all_requests():
            self._has_changed = True
        return result

    @abc.abstractmethod
    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise NotImplementedError


class ReadOnlyStoreContextManager(StoreContextManager, abc.ABC):
    """
    To be implemented by read-only stores.
    """

    async def _read(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool],
    ) -> event.EventSnapshot:
        if is_archive:
            raise StoreError(
                f"This is a {self.__class__.__name__} instance which is also read-only. "
                f"There is no archive."
            )
        return await self._read_ro(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)

    @abc.abstractmethod
    async def _read_ro(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ):
        pass

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> event.EventSnapshot:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )

    async def _remove(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        raise StoreError(
            f"This is a {self.__class__.__name__} instance which is also read-only."
        )
