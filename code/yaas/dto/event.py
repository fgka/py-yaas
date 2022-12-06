# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
from typing import Dict, List
import attrs

from yaas.dto import dto_defaults, request
from yaas import const


@attrs.define(**const.ATTRS_DEFAULTS)
class EventSnapshot(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Holds a snapshot of, supposedly, upcoming events/requests.
    """

    source: str = attrs.field(validator=attrs.validators.instance_of(str))
    timestamp_to_request: Dict[int, List[request.ScaleRequest]] = attrs.field(
        default=attrs.Factory(dict),
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(request.ScaleRequest),
            mapping_validator=attrs.validators.instance_of(dict),
        ),
    )


@attrs.define(**const.ATTRS_DEFAULTS)
class EventSnapshotComparison(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Holds a comparison between two instances of :py:class:`EventSnapshot`.
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
    """

    non_overlapping_a: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(EventSnapshot)
        ),
    )
    """
    All requests that are in snapshot A and outside the range of snapshot B.
    """
    non_overlapping_b: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(EventSnapshot)
        ),
    )
    """
    All requests that are in snapshot B and outside the range of snapshot A.
    """
    non_conflicting_a: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(EventSnapshot)
        ),
    )
    """
    All requests that are in snapshot A but are also present in snapshot B exactly as is.
    """
    only_in_a: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(EventSnapshot)
        ),
    )
    """
    All requests that are only in snapshot A but not in snapshot B.
    """
    only_in_b: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(EventSnapshot)
        ),
    )
    """
    All requests that are only in snapshot B but not in snapshot A.
    """
