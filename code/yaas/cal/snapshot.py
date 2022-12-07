# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
List Google Calendar events in the future and consolidate it in a datastore.
The difficulty here is to build and merge snapshots,
 in case the current cached values deviate from what is in newly fetched upcoming events.
"""
# pylint: enable=line-too-long
from typing import Callable

from yaas import logger
from yaas.dto import event

_LOGGER = logger.get(__name__)


def merge(
    *,
    snapshot_a: event.EventSnapshot,
    snapshot_b: event.EventSnapshot,
    merge_strategy: Callable[[event.EventSnapshotComparison], event.EventSnapshot],
) -> event.EventSnapshot:
    """
    This is just wrapper to chain :py:func:`compare`
        and calling ``strategy`` on the comparison result.

    Args:
        snapshot_a:
        snapshot_b:
        merge_strategy:

    Returns:

    """
    # validation
    if not callable(merge_strategy):
        raise TypeError(
            f"Strategy argument must be a {Callable.__name__} object. "
            f"Got <{merge_strategy}>({type(merge_strategy)})"
        )
    # logic
    try:
        comparison = compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    except Exception as err:
        raise RuntimeError(
            f"Could not compare <{snapshot_a}> to <{snapshot_b}>. Got: {err}"
        ) from err
    try:
        result = merge_strategy(comparison)
    except Exception as err:
        raise RuntimeError(
            f"Could not apply merge strategy <{merge_strategy}> to comparison <{comparison}>. "
            f"Got: {err}"
        ) from err
    return result


def compare(
    *, snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot
) -> event.EventSnapshotComparison:
    """
    Repeating the documentation in :py:cls:`event.EventSnapshotComparison`.

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
        * snapshot A timeline goes from event 1 through 4;
        * snapshot B timeline goes from event 2 through 5.
    The resulting object should have:
        * non_overlapping_a: [snapshot_a_event_1];
        * non_overlapping_b: [snapshot_b_event_5];
        * non_conflicting_a: [snapshot_a_event_2];
        * only_in_a: [snapshot_a_event_4];
        * only_in_b: [snapshot_b_event_3].

    Args:
        snapshot_a:
        snapshot_b:

    Returns:
    """
    # validation
    if not isinstance(snapshot_a, event.EventSnapshot):
        raise TypeError(
            f"Argument snapshot_a is not {event.EventSnapshot.__name__}. "
            f"Got <{snapshot_a}>({type(snapshot_a)})"
        )
    if not isinstance(snapshot_b, event.EventSnapshot):
        raise TypeError(
            f"Argument snapshot_b is not {event.EventSnapshot.__name__}. "
            f"Got <{snapshot_b}>({type(snapshot_b)})"
        )
    # logic
    # TODO
    return None
