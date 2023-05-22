# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""List Google Calendar events in the future and consolidate it in a datastore.

The difficulty here is to build and merge snapshots,  in case the
current cached values deviate from what is in newly fetched upcoming
events.
"""
from typing import Callable, List, Optional, Tuple

from yaas_caching import event
from yaas_common import logger

_LOGGER = logger.get(__name__)


def merge(
    *,
    snapshot_a: event.EventSnapshot,
    snapshot_b: event.EventSnapshot,
    merge_strategy: Callable[[event.EventSnapshotComparison], event.EventSnapshot],
) -> Tuple[bool, Optional[event.EventSnapshot]]:
    """This is just wrapper to chain :py:func:`compare` and calling
    ``strategy`` on the comparison result.

    Args:
        snapshot_a:
        snapshot_b:
        merge_strategy:

    Returns:
        A :py:class:`tuple` in the format: ``<is merge required>,<merge result>``.
        If the merge is not required, the merge result will be :py:obj:`None`.
    """
    # validation
    if not callable(merge_strategy):
        raise TypeError(
            f"Strategy argument must be a {Callable.__name__} object. "
            f"Got '{merge_strategy}'({type(merge_strategy)})"
        )
    # logic: comparison
    try:
        comparison = compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    except Exception as err:
        raise RuntimeError(f"Could not compare '{snapshot_a}' to '{snapshot_b}'. Got: {err}") from err
    # logic: merge
    result = None
    is_required = comparison.are_different()
    if is_required:
        try:
            result = merge_strategy(comparison)
        except Exception as err:
            raise RuntimeError(
                f"Could not apply merge strategy '{merge_strategy}' to comparison '{comparison}'. Got: {err}"
            ) from err
    return is_required, result


def compare(*, snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot) -> event.EventSnapshotComparison:
    """Repeating the documentation in :py:cls:`event.EventSnapshotComparison`.

    Returns a comparison between two instances of :py:class:`event.EventSnapshot`.
    It is intention is to provide a DTO to something like::

        comparison = compare(snapshot_a, snapshot_b)

    The semantics, to make it clear is the following in a timeline::

        1  2  3  4  5
      --+--+--+--+--+--
        |  |  |  |  +- snapshot_b_event_5
        |  |  |  +---- snapshot_a_event_4
        |  |  +------- snapshot_b_event_3
        |  +---------- snapshot_a_event_2, snapshot_b_event_2
        +------------- snapshot_a_event_1

    This means that:
        * snapshot A timeline goes from event 1 through 4.
        * snapshot B timeline goes from event 2 through 5.
    The resulting object should have:
        * non_overlapping_a: [snapshot_a_event_1].
        * non_overlapping_b: [snapshot_b_event_5].
        * overlapping: [snapshot_a_event_2, snapshot_b_event_2].
        * only_in_a: [snapshot_a_event_4].
        * only_in_b: [snapshot_b_event_3].

    Args:
        snapshot_a:
        snapshot_b:

    Returns:
    """
    # validation
    if not isinstance(snapshot_a, event.EventSnapshot):
        raise TypeError(
            f"Argument snapshot_a is not {event.EventSnapshot.__name__}. Got '{snapshot_a}'({type(snapshot_a)})"
        )
    if not isinstance(snapshot_b, event.EventSnapshot):
        raise TypeError(
            f"Argument snapshot_b is not {event.EventSnapshot.__name__}. Got '{snapshot_b}'({type(snapshot_b)})"
        )
    # logic:
    overlapping = None
    only_in_a = None
    only_in_b = None
    # logic: simple/emtpy
    if not snapshot_a.timestamp_to_request and snapshot_b.timestamp_to_request:
        only_in_b = snapshot_b
    if not snapshot_b.timestamp_to_request and snapshot_a.timestamp_to_request:
        only_in_a = snapshot_a
    # logic: potential conflict
    if snapshot_a.timestamp_to_request and snapshot_b.timestamp_to_request:
        result = _compare_potential_conflict(snapshot_a, snapshot_b)
    else:
        result = event.EventSnapshotComparison(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            overlapping=overlapping,
            only_in_a=only_in_a,
            only_in_b=only_in_b,
        )
    return result


def _compare_potential_conflict(
    snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot
) -> event.EventSnapshotComparison:
    # break down timestamp to request
    (
        only_in_a_ts,
        only_in_b_ts,
        overlapping_a_ts,
        overlapping_b_ts,
    ) = _breakdown_timestamp_to_request(snapshot_a, snapshot_b)
    overlapping = None
    only_in_a = None
    only_in_b = None
    if only_in_a_ts:
        only_in_a = event.EventSnapshot(source=snapshot_a.source, timestamp_to_request=only_in_a_ts)
    if only_in_b_ts:
        only_in_b = event.EventSnapshot(source=snapshot_b.source, timestamp_to_request=only_in_b_ts)
    if overlapping_a_ts and overlapping_b_ts:
        overlapping = (
            event.EventSnapshot(source=snapshot_a.source, timestamp_to_request=overlapping_a_ts),
            event.EventSnapshot(source=snapshot_b.source, timestamp_to_request=overlapping_b_ts),
        )
    # build result
    return event.EventSnapshotComparison(
        snapshot_a=snapshot_a,
        snapshot_b=snapshot_b,
        overlapping=overlapping,
        only_in_a=only_in_a,
        only_in_b=only_in_b,
    )


def _breakdown_timestamp_to_request(snapshot_a, snapshot_b):
    overlapping_a_ts = {}
    overlapping_b_ts = {}
    only_in_a_ts = {}
    only_in_b_ts = {}
    # get timeline
    timeline = _get_timestamp_timeline(snapshot_a, snapshot_b)
    for t_stamp in timeline:
        req_list_a = snapshot_a.timestamp_to_request.get(t_stamp)
        req_list_b = snapshot_b.timestamp_to_request.get(t_stamp)
        if req_list_a and req_list_b:
            overlapping_a_ts[t_stamp] = req_list_a
            overlapping_b_ts[t_stamp] = req_list_b
        elif not req_list_a:
            only_in_b_ts[t_stamp] = req_list_b
        elif not req_list_b:
            only_in_a_ts[t_stamp] = req_list_a
    return only_in_a_ts, only_in_b_ts, overlapping_a_ts, overlapping_b_ts


def _get_timestamp_timeline(snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot) -> List[int]:
    all_timestamps = set(snapshot_a.timestamp_to_request.keys())
    all_timestamps = all_timestamps.union(set(snapshot_b.timestamp_to_request.keys()))
    return sorted(all_timestamps)
