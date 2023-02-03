# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Main entry-points.
"""
from datetime import datetime
from typing import Any, Dict, List, Callable, Optional, Tuple, Union

import flask

from yaas.cal import google_cal
from yaas.dto import config, event
from yaas.entry_point import pubsub_dispatcher
from yaas.event.store import base, calendar, factory
from yaas.event import version_control
from yaas.scaler import base as base_scaler
from yaas import logger

_LOGGER = logger.get(__name__)


def _merge_strategy_always_a(
    comparison: event.EventSnapshotComparison,
) -> event.EventSnapshot:
    return comparison.snapshot_a


async def update_calendar_credentials(  # pylint: disable=too-many-arguments
    configuration: config.Config,
) -> None:
    """
    Will update the credentials for Google Calendar, if needed.

    Args:
        configuration:

    Returns:

    """
    await google_cal.update_secret_credentials(
        calendar_id=configuration.calendar_config.calendar_id,
        secret_name=configuration.calendar_config.secret_name,
    )


async def update_cache(
    *,
    start_ts_utc: int,
    end_ts_utc: int,
    configuration: config.Config,
    merge_strategy: Optional[
        Callable[[event.EventSnapshotComparison], event.EventSnapshot]
    ] = None,
) -> None:
    """
    Will read from the calendar specified in ``configuration`` in the range specified
        and store in the cache, also specified in ``configuration``.
    On merge, calendar snapshot is always snapshot ``A``.

    Args:
        start_ts_utc:
        end_ts_utc:
        configuration:
        merge_strategy:
            Default merge strategy is to always use values fresh from Calendar.

    """
    _LOGGER.debug("Starting %s with %s", update_cache.__name__, locals())
    # validate input
    _validate_configuration(configuration)
    if merge_strategy is None:
        merge_strategy = _merge_strategy_always_a
    # logic: snapshots
    calendar_snapshot = await _calendar_snapshot(
        calendar_id=configuration.calendar_config.calendar_id,
        secret_name=configuration.calendar_config.secret_name,
        start_ts_utc=start_ts_utc,
        end_ts_utc=end_ts_utc,
    )
    cache_store, cache_snapshot = await _cache_store_and_snapshot(
        cache_config=configuration.cache_config,
        start_ts_utc=start_ts_utc,
        end_ts_utc=end_ts_utc,
    )
    # logic: merge
    is_required, merged_snapshot = version_control.merge(
        snapshot_a=calendar_snapshot,
        snapshot_b=cache_snapshot,
        merge_strategy=merge_strategy,
    )
    _LOGGER.info(
        "Merged snapshots using <%s>. Merge required: %s. Range <%s> and amount of requests: <%s>",
        merge_strategy,
        is_required,
        str(merged_snapshot.range() if merged_snapshot else None),
        str(merged_snapshot.amount_requests() if merged_snapshot else None),
    )
    async with cache_store as obj:
        # logic: overwrite cache
        if is_required:
            await obj.write(merged_snapshot, overwrite_within_range=True)
            _LOGGER.info(
                "Wrote merged snapshot with overwrite. Store: %s", cache_store.source
            )
        # logic: clean-up
        archived, removed = await obj.clean_up(configuration.retention_config)
        _LOGGER.info(
            "Clean-up on %s archived <%s> and removed <%s>",
            cache_store.source,
            archived,
            removed,
        )


def _validate_configuration(value: config.Config) -> None:
    if not isinstance(value, config.Config):
        raise TypeError(
            f"Configuration must be an instance of {config.Config.__name__}. "
            f"Got: <{value}>({type(value)})"
        )


async def _calendar_snapshot(
    *, calendar_id: str, secret_name: str, start_ts_utc: int, end_ts_utc: int
) -> event.EventSnapshot:
    result = calendar.ReadOnlyGoogleCalendarStore(
        calendar_id=calendar_id, secret_name=secret_name
    )
    async with result as obj:
        result = await obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
    _LOGGER.info(
        "Got calendar snapshot using id <%s> and secret <%s>. "
        "Range <%s> and amount of requests: <%d>",
        calendar_id,
        secret_name,
        result.range(),
        result.amount_requests(),
    )
    return result


async def _cache_store_and_snapshot(
    *,
    cache_config: config.CacheConfig,
    start_ts_utc: int,
    end_ts_utc: int,
) -> Tuple[base.StoreContextManager, event.EventSnapshot]:
    _LOGGER.info(
        "Reading range [%d, %d] (%s, %s) from cache <%s>",
        start_ts_utc,
        end_ts_utc,
        datetime.fromtimestamp(start_ts_utc),
        datetime.fromtimestamp(end_ts_utc),
        cache_config,
    )
    cache_store = factory.store_from_cache_config(cache_config)
    async with cache_store as obj:
        result = await obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
    _LOGGER.info(
        "Got snapshot from <%s>. "
        "Retrieved range <%s> and amount of requests retrieved: <%d>",
        cache_config,
        result.range(),
        result.amount_requests(),
    )
    return cache_store, result


async def send_requests(
    *,
    start_ts_utc: int,
    end_ts_utc: int,
    configuration: config.Config,
) -> None:
    """
    Will read the cached snapshot within the range and dispatch them via PubSub.

    Args:
        start_ts_utc:
        end_ts_utc:
        configuration:

    Returns:

    """
    _LOGGER.debug("Starting %s with %s", send_requests.__name__, locals())
    # validate input
    _validate_configuration(configuration)
    # logic: snapshot
    _, cache_snapshot = await _cache_store_and_snapshot(
        cache_config=configuration.cache_config,
        start_ts_utc=start_ts_utc,
        end_ts_utc=end_ts_utc,
    )
    if cache_snapshot.amount_requests():
        # logic: send
        await pubsub_dispatcher.dispatch(
            configuration.topic_to_pubsub,
            *cache_snapshot.all_requests(),
            raise_if_invalid_request=True,
        )
    else:
        _LOGGER.debug(
            "There are no requests to dispatch in snapshot: %s", cache_snapshot
        )


async def enact_requests(
    *,
    parser: base_scaler.CategoryScaleRequestParser,
    pubsub_event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
) -> None:
    """
    Given the input event, will extract all requests and enact them.
    Args:
        parser:
        pubsub_event:
        iso_str_timestamp:

    Returns:

    """
    _LOGGER.debug("Starting %s with %s", enact_requests.__name__, locals())
    # validate input
    if not isinstance(parser, base_scaler.CategoryScaleRequestParser):
        raise TypeError(
            f"Parser must be an instance of {base_scaler.CategoryScaleRequestParser.__name__}. "
            f"Got: <{parser}>({type(parser)})"
        )
    # logic
    req_lst = pubsub_dispatcher.from_event(
        event=pubsub_event, iso_str_timestamp=iso_str_timestamp
    )
    if not isinstance(req_lst, list):
        raise TypeError(
            f"Expecting a list of requests from event. Got: <{req_lst}>({type(req_lst)}). "
            f"Event: {pubsub_event}"
        )
    result: List[Tuple[bool, base_scaler.Scaler]] = await parser.enact(
        *req_lst, singulate_if_only_one=False, raise_if_invalid_request=True
    )
    for success_scaler in result:
        success, scaler = success_scaler
        if not success:
            _LOGGER.error("Could not enact request <%s>. Check logs", scaler.definition)
