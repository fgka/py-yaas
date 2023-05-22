# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Main entry-points."""
from datetime import datetime
from typing import Callable, Optional, Tuple

from yaas_caching import base, event, factory, version_control
from yaas_calendar import google_cal
from yaas_command import pubsub_dispatcher
from yaas_common import command, logger
from yaas_config import config

_LOGGER = logger.get(__name__)


def _merge_strategy_always_a(
    comparison: event.EventSnapshotComparison,
) -> event.EventSnapshot:
    return comparison.snapshot_a


async def process_command(value: command.CommandBase, *, configuration: config.Config) -> None:
    """Processes a command.

    Args:
        value:
        configuration

    Returns:
    """
    # validate input
    if not isinstance(value, command.CommandBase):
        raise ValueError(
            f"Value argument is not an instance '{command.CommandBase.__name__}'. Got: '{value}'({type(value)})"
        )
    # logic
    if value.type == command.CommandType.UPDATE_CALENDAR_CREDENTIALS_SECRET.value:
        await update_calendar_credentials(configuration=configuration)
    elif value.type == command.CommandType.UPDATE_CALENDAR_CACHE.value:
        start_ts_utc, end_ts_utc = value.range.timestamp_range()
        await update_cache(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=configuration,
        )
    elif value.type == command.CommandType.SEND_SCALING_REQUESTS.value:
        start_ts_utc, end_ts_utc = value.range.timestamp_range()
        await send_requests(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=configuration,
            raise_if_invalid_request=False,
        )
    else:
        raise ValueError(
            f"Command type '{value.type}' cannot be processed. "
            f"Check implementation: {__name__}.{process_command.__name__}. "
            f"Got: '{value}'({type(value)})"
        )


async def update_calendar_credentials(
    configuration: config.Config,
) -> None:
    """Will update the credentials for Google Calendar, if needed.

    Args:
        configuration: config

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
    merge_strategy: Optional[Callable[[event.EventSnapshotComparison], event.EventSnapshot]] = None,
) -> None:
    """Will read from the calendar specified in ``configuration`` in the range
    specified and store in the cache, also specified in ``configuration``. On
    merge, calendar snapshot is always snapshot ``A``.

    Args:
        start_ts_utc: start
        end_ts_utc: end
        configuration: config
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
        calendar_config=configuration.calendar_config,
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
        "Merged snapshots using '%s'. Merge required: %s. Range '%s' and amount of requests: '%s'",
        merge_strategy,
        is_required,
        str(merged_snapshot.range() if merged_snapshot else None),
        str(merged_snapshot.amount_requests() if merged_snapshot else None),
    )
    async with cache_store as obj:
        # logic: overwrite cache
        if is_required:
            await obj.write(merged_snapshot, overwrite_within_range=True)
            _LOGGER.info("Wrote merged snapshot with overwrite. Store: %s", cache_store.source)
        # logic: clean-up
        archived, removed = await obj.clean_up(configuration.retention_config)
        _LOGGER.info(
            "Clean-up on %s archived '%s' and removed '%s'",
            cache_store.source,
            archived,
            removed,
        )


def _validate_configuration(value: config.Config) -> None:
    if not isinstance(value, config.Config):
        raise TypeError(f"Configuration must be an instance of {config.Config.__name__}. Got: '{value}'({type(value)})")


async def _calendar_snapshot(
    *, calendar_config: config.CalendarCacheConfig, start_ts_utc: int, end_ts_utc: int
) -> event.EventSnapshot:
    calendar_store = factory.calendar_store_from_cache_config(calendar_config)
    async with calendar_store as obj:
        result = await obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
    _LOGGER.info(
        "Got calendar snapshot from '%s'. Range '%s' and amount of requests: '%d'",
        calendar_config,
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
        "Reading range [%d, %d] (%s, %s) from cache '%s'",
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
        "Got snapshot from '%s'. Retrieved range '%s' and amount of requests retrieved: '%d'",
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
    raise_if_invalid_request: Optional[bool] = True,
) -> None:
    """Will read the cached snapshot within the range and dispatch them via
    PubSub.

    Args:
        start_ts_utc: start
        end_ts_utc: end
        configuration: config
        raise_if_invalid_request: to raise in case of failure

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
            raise_if_invalid_request=raise_if_invalid_request,
        )
    else:
        _LOGGER.debug("There are no requests to dispatch in snapshot: %s", cache_snapshot)
