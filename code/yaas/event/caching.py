# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
List Google Calendar events in the future and consolidate it in a datastore.
The difficulty here is to build and merge snapshots,
 in case the current cached values deviate from what is in newly fetched upcoming events.
"""
# pylint: enable=line-too-long
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from yaas import logger
from yaas.dto import event
from yaas.event.store import base
from yaas.event import version_control

_LOGGER = logger.get(__name__)

DEFAULT_UPDATE_REQUEST_TIME_SPAN_IN_DAYS: int = 10


class CachingError(Exception):
    """To code all caching operation errors."""


def update_event_cache(
    *,
    start_utc: int,
    end_utc: int,
    merge_strategy: Callable[[event.EventSnapshotComparison], event.EventSnapshot],
    calendar_reader: Callable[[int, int], event.EventSnapshot],
    cache_reader: Callable[[int, int], event.EventSnapshot],
    cache_writer: Callable[[event.EventSnapshot], bool],
) -> bool:
    """
    This function is the entry-point for updating the current events cache.
    It needs to do the following:
    * Read upcoming events from the source (Google Calendar);
    * Parse the events and provide a canonical list of scaling requests;
    * Compare the overlapping timerange with what is in the cache;
    * Ignore already cached events;
    * Add new events, i.e., in the listing from source but outside the overlapping timerange;
    * Apply a merging strategy, if necessary, for the overlapping and conflicting events:
        * Remove or keep old cached events not present in new listing?
        * Add or ignore new events not yet cached?

    Returns:
        :py:obj:`True` if successfully updated the cache.
    """
    # validate
    if not isinstance(start_utc, int):
        raise TypeError(
            f"The argument start_utc must be an {int.__name__}. "
            f"Got: <{start_utc}>({type(start_utc)})"
        )
    if not isinstance(end_utc, int):
        raise TypeError(
            f"The argument end_utc must be an {int.__name__}. "
            f"Got: <{end_utc}>({type(end_utc)})"
        )
    if start_utc < 0 or end_utc < 0 or start_utc >= end_utc:
        raise ValueError(
            f"The arguments start_utc <{start_utc}> and end_utc <{end_utc}> must be non-negative "
            f"as end - start, which must be greater than 0 too: <{end_utc - start_utc}>"
        )
    _validate_callable("calendar_reader", calendar_reader)
    _validate_callable("cache_reader", cache_reader)
    _validate_callable("cache_writer", cache_writer)
    _validate_callable("merge_strategy", merge_strategy)
    # logic
    # read calendar
    try:
        calendar_snapshot = calendar_reader(start_utc, end_utc)
    except Exception as err:
        raise RuntimeError(
            f"Could not read calendar for the range [{start_utc}, {end_utc}]. Got: {err}"
        ) from err
    # read cache
    try:
        cached_snapshot = cache_reader(start_utc, end_utc)
    except Exception as err:
        raise RuntimeError(
            f"Could not read cache for the range [{start_utc}, {end_utc}]. Got: {err}"
        ) from err
    # merge
    try:
        merged_snapshot = version_control.merge(
            snapshot_a=cached_snapshot,
            snapshot_b=calendar_snapshot,
            merge_strategy=merge_strategy,
        )
    except Exception as err:
        raise RuntimeError(
            f"Could not merge snapshots using <{merge_strategy}> "
            f"on calendar snapshot <{calendar_snapshot}> "
            f"and cached snapshot <{cached_snapshot}>. "
            f"Got: {err}"
        ) from err
    # write cache
    try:
        result = cache_writer(merged_snapshot)
    except Exception as err:
        raise RuntimeError(
            f"Could not write snapshot <{merged_snapshot}> to cache using <{cache_writer}>. "
            f"Got: {err}"
        ) from err
    return result


def _validate_callable(name: str, value: Any) -> None:
    if not callable(value):
        raise TypeError(
            f"The argument {name} must be callable. Got: <{value}>({type(value)})"
        )


async def update_cache(
    *,
    source: base.StoreContextManager,
    cache: base.StoreContextManager,
    merge_strategy: Callable[[event.EventSnapshotComparison], event.EventSnapshot],
    start: Optional[datetime] = None,
    time_span_in_days: Optional[int] = DEFAULT_UPDATE_REQUEST_TIME_SPAN_IN_DAYS,
) -> None:
    """
    Will fetch entries from ``source``
    (within the timespan in ``time_span_in_days`` starting in ``start``),
    read the currently cached events from ``cache``,
    merge them using ``merge_strategy``,
    and store back into the store.
    Args:
        source:
        cache:
        merge_strategy:
        start: when the period starts, if :py:obj:`None` it will revert to current time.
        time_span_in_days: how many days to cache.

    Returns:

    Raises:
        py:class:`CachingError` in case o errors.

    """
    # input validation
    if not isinstance(source, base.StoreContextManager):
        raise TypeError(
            f"Source must be an instance of {base.StoreContextManager.__name__}. "
            f"Got: <{cache}>({type(cache)})"
        )
    if not isinstance(cache, base.StoreContextManager):
        raise TypeError(
            f"Cache must be an instance of {base.StoreContextManager.__name__}. "
            f"Got: <{cache}>({type(cache)})"
        )
    if not callable(merge_strategy):
        raise TypeError(
            f"Merge strategy must be callable. "
            f"Got: <{merge_strategy}>({type(merge_strategy)})"
        )
    if start is None:
        start = datetime.utcnow()
    if not isinstance(start, datetime):
        raise TypeError(
            f"Start must be an instance of {datetime.__name__}. "
            f"Got: <{start}>({type(start)})"
        )
    if not isinstance(time_span_in_days, int) or time_span_in_days <= 0:
        raise TypeError(
            f"Time span must be integer greater than 0. "
            f"Got: <{time_span_in_days}>({type(time_span_in_days)})"
        )
    # logic
    await _update_cache(
        source=source,
        cache=cache,
        merge_strategy=merge_strategy,
        start=start,
        time_span_in_days=time_span_in_days,
    )


async def _update_cache(
    *,
    source: base.StoreContextManager,
    cache: base.StoreContextManager,
    merge_strategy: Callable[[event.EventSnapshotComparison], event.EventSnapshot],
    start: datetime,
    time_span_in_days: int,
) -> None:
    # convert times
    start_ts_utc = start.timestamp()
    end_ts_utc = (start + timedelta(days=time_span_in_days)).timestamp()
    # read source
    try:
        source_snapshot = await source.read(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
        )
    except Exception as err:
        raise CachingError(
            f"Could not read source starting on {start} for {time_span_in_days} days. "
            f"Got: {err}"
        ) from err
    # read cache
    try:
        cached_snapshot = await cache.read(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
        )
    except Exception as err:
        raise CachingError(
            f"Could not read cache starting on {start} for {time_span_in_days} days. "
            f"Got: {err}"
        ) from err
    # merge
    try:
        merged_snapshot = version_control.merge(
            snapshot_a=cached_snapshot,
            snapshot_b=source_snapshot,
            merge_strategy=merge_strategy,
        )
    except Exception as err:
        raise CachingError(
            f"Could not merge snapshots using <{merge_strategy}> "
            f"on source snapshot <{source_snapshot}> "
            f"and cached snapshot <{cached_snapshot}>. "
            f"Got: {err}"
        ) from err
    # write cache
    try:
        await cache.write(merged_snapshot, overwrite_within_range=True)
    except Exception as err:
        raise CachingError(
            f"Could not write snapshot <{merged_snapshot}> to cache using <{cache}>. "
            f"Got: {err}"
        ) from err
