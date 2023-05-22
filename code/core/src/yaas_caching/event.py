# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Basic definition of types and expected functionality for resource scaler."""
from typing import Any, Dict, List, Optional, Tuple, Union

import attrs

from yaas_common import const, dto_defaults, logger, request

_LOGGER = logger.get(__name__)


def _json_timestamp_to_request_converter(  # pylint: disable=invalid-name
    value: Union[Dict[str, List[Dict[str, Any]]], Dict[int, List[request.ScaleRequest]]]
) -> Dict[int, List[request.ScaleRequest]]:
    if isinstance(value, dict):
        value = {
            _str_or_int_to_int(key): [_dict_or_scale_request_to_scale_request(item) for item in val]
            for key, val in value.items()
        }
    return value


def _str_or_int_to_int(value: Union[str, int]) -> int:
    if isinstance(value, str):
        value = int(value)
    return value


def _dict_or_scale_request_to_scale_request(  # pylint: disable=invalid-name
    value: Union[Dict[str, Any], request.ScaleRequest]
) -> request.ScaleRequest:
    if isinstance(value, dict):
        value = request.ScaleRequest.from_dict(value)
    return value


@attrs.define(**const.ATTRS_DEFAULTS)
class EventSnapshot(dto_defaults.HasFromJsonString):
    """Holds a snapshot of, supposedly, upcoming events/requests."""

    source: str = attrs.field(validator=attrs.validators.instance_of(str))
    timestamp_to_request: Dict[int, List[request.ScaleRequest]] = attrs.field(
        default=attrs.Factory(dict),
        converter=_json_timestamp_to_request_converter,
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.ge(0),
            value_validator=attrs.validators.deep_iterable(
                member_validator=attrs.validators.instance_of(request.ScaleRequest),
                iterable_validator=attrs.validators.instance_of(list),
            ),
            mapping_validator=attrs.validators.instance_of(dict),
        ),
    )

    def range(self) -> Tuple[Optional[int], Optional[int]]:
        """Returns the range ot timestamps present here or :py:obj:`None` if ``timestamp_to_request`` is empty."""
        result = None, None
        if self.timestamp_to_request:
            ts_lst = sorted(self.timestamp_to_request)
            result = ts_lst[0], ts_lst[-1]
        return result

    def all_requests(self) -> List[request.ScaleRequest]:
        """All requests it contains."""
        return [req for req_list in self.timestamp_to_request.values() for req in req_list]

    def amount_requests(self) -> int:
        """How many requests it contains."""
        return len(self.all_requests())

    @staticmethod
    def from_list_requests(
        *,
        source: str,
        request_lst: List[request.ScaleRequest],
        discard_invalid: Optional[bool] = False,
    ) -> "EventSnapshot":
        """Assumes all items in ``request_list`` do have a valid
        ``timestamp_utc`` value. If any item does not have the timestamp set
        and ``discard_invalid`` is :py:obj:`False`, it will raise
        :py:class:`ValueError`.

        Args:
            source: source
            request_lst: list of requests
            discard_invalid: if :py:obj:`False` raises :py:class:`ValueError`
                for items in ``request_lst`` that do not have a proper ``timestamp_utc`` value.

        Returns:
        """
        # Build map
        timestamp_to_request = {}
        if request_lst:
            for item in request_lst:
                key = item.timestamp_utc
                if not key:
                    msg = f"Item '{item}' from request list does not have a proper timestamp value."
                    if not discard_invalid:
                        raise ValueError(msg)
                    _LOGGER.warning(msg + " Ignoring")  # pylint: disable=logging-not-lazy
                    continue
                if key not in timestamp_to_request:
                    timestamp_to_request[key] = []
                timestamp_to_request[key].append(item)
        # return
        return EventSnapshot(source=source, timestamp_to_request=timestamp_to_request)


@attrs.define(**const.ATTRS_DEFAULTS)
class EventSnapshotComparison(dto_defaults.HasFromJsonString):
    """Holds a comparison between two instances of :py:class:`EventSnapshot`. It is intention is to provide a DTO to
    something like::

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
        * overlapping: [snapshot_a_event_2, snapshot_b_event_2];
        * only_in_a: [snapshot_a_event_1, snapshot_a_event_4];
        * only_in_b: [snapshot_b_event_3, snapshot_b_event_5].

    """

    snapshot_a: EventSnapshot = attrs.field(validator=attrs.validators.instance_of(EventSnapshot))
    snapshot_b: EventSnapshot = attrs.field(validator=attrs.validators.instance_of(EventSnapshot))

    overlapping: Tuple[EventSnapshot] = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.deep_iterable(
                member_validator=attrs.validators.instance_of(EventSnapshot),
                iterable_validator=attrs.validators.instance_of(tuple),
            )
        ),
    )
    """All requests that share the same timestamp in both snapshots."""
    only_in_a: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(EventSnapshot)),
    )
    """All requests that are only in snapshot A but not in snapshot B."""
    only_in_b: EventSnapshot = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(EventSnapshot)),
    )
    """All requests that are only in snapshot B but not in snapshot A."""

    def are_different(self) -> bool:
        """A quick way to tell if the snapshots differ."""
        result = not self._is_snapshot_empty(self.only_in_a) or not self._is_snapshot_empty(self.only_in_b)
        if not result and self.overlapping is not None:
            overlapping_a, overlapping_b = self.overlapping
            result = not self._is_snapshot_empty(overlapping_a) or not self._is_snapshot_empty(overlapping_b)
        return result

    @staticmethod
    def _is_snapshot_empty(value: EventSnapshot) -> bool:
        return value is None or not value.all_requests()
