# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
List Google Calendar events in the future and consolidate it in a datastore.
The difficulty here is to build and merge snapshots,
 in case the current cached values deviate from what is in newly fetched upcoming events.
"""
# pylint: enable=line-too-long
from typing import Any, Callable

from yaas import logger
from yaas.dto import event
from yaas.event import snapshot

_LOGGER = logger.get(__name__)


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
        merged_snapshot = snapshot.merge(
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
