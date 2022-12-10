# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Callable, List, Optional

import pytest

from yaas.event import version_control
from yaas.dto import event, request

_TEST_SNAPSHOT_A: event.EventSnapshot = event.EventSnapshot(source="A")
_TEST_SNAPSHOT_B: event.EventSnapshot = event.EventSnapshot(source="B")
_TEST_COMPARISON_SNAPSHOT: event.EventSnapshotComparison = (
    event.EventSnapshotComparison()
)
_TEST_MERGE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="merge")


@pytest.mark.parametrize(
    "snapshot_a,snapshot_b",
    [
        (None, None),  # no snapshots
        (None, _TEST_SNAPSHOT_B),  # missing A
        (_TEST_SNAPSHOT_A, None),  # missing B
    ],
)
def test_compare_nok(snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot):
    with pytest.raises(TypeError):
        version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)


def test_merge_ok(monkeypatch):
    # Given
    snapshot_a_arg = _TEST_SNAPSHOT_A
    snapshot_b_arg = _TEST_SNAPSHOT_B
    expected = _TEST_MERGE_SNAPSHOT
    called = {}

    def callback_fn(name: str) -> None:
        nonlocal called
        called[name] = True

    merge_strategy = _create_merge_arguments(
        monkeypatch,
        snapshot_a_arg=snapshot_a_arg,
        snapshot_b_arg=snapshot_b_arg,
        callback_fn=callback_fn,
        expected=expected,
    )
    # When
    res = version_control.merge(
        snapshot_a=snapshot_a_arg,
        snapshot_b=snapshot_b_arg,
        merge_strategy=merge_strategy,
    )
    # Then
    assert res == expected
    assert called.get("mocked_compare")
    assert called.get("merge_strategy")


def _create_merge_arguments(
    monkeypatch,
    *,
    snapshot_a_arg: event.EventSnapshot = _TEST_SNAPSHOT_A,
    snapshot_b_arg: event.EventSnapshot = _TEST_SNAPSHOT_B,
    comparison_snapshot: event.EventSnapshotComparison = _TEST_COMPARISON_SNAPSHOT,
    expected: event.EventSnapshot = _TEST_MERGE_SNAPSHOT,
    callback_fn: Optional[Callable[[str], None]] = None,
    raise_exception_if_result_is_none: bool = True,
):
    def merge_strategy(
        comparison: event.EventSnapshotComparison,
    ) -> event.EventSnapshot:
        callback_fn("merge_strategy")
        assert comparison == comparison_snapshot
        if raise_exception_if_result_is_none and expected is None:
            raise RuntimeError
        return expected

    def mocked_compare(
        *, snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot
    ) -> event.EventSnapshotComparison:
        callback_fn("mocked_compare")
        assert snapshot_a == snapshot_a_arg
        assert snapshot_b == snapshot_b_arg
        if raise_exception_if_result_is_none and comparison_snapshot is None:
            raise RuntimeError
        return comparison_snapshot

    monkeypatch.setattr(version_control, version_control.compare.__name__, mocked_compare)
    return merge_strategy


@pytest.mark.parametrize(
    "exception,comparison_snapshot,expected",
    [
        (
            RuntimeError,
            None,  # compare raises exception
            _TEST_MERGE_SNAPSHOT,
        ),
        (
            RuntimeError,
            _TEST_COMPARISON_SNAPSHOT,
            None,  # merge raises exception
        ),
    ],
)
def test_merge_nok(
    monkeypatch,
    exception: Exception,
    comparison_snapshot: event.EventSnapshotComparison,
    expected: event.EventSnapshot,
):
    # Given
    snapshot_a_arg = _TEST_SNAPSHOT_A
    snapshot_b_arg = _TEST_SNAPSHOT_B
    called = {}

    def callback_fn(name: str) -> None:
        nonlocal called
        called[name] = True

    merge_strategy = _create_merge_arguments(
        monkeypatch,
        snapshot_a_arg=snapshot_a_arg,
        snapshot_b_arg=snapshot_b_arg,
        comparison_snapshot=comparison_snapshot,
        callback_fn=callback_fn,
        expected=expected,
    )
    # When
    with pytest.raises(exception):
        version_control.merge(
            snapshot_a=snapshot_a_arg,
            snapshot_b=snapshot_b_arg,
            merge_strategy=merge_strategy,
        )
    # Then
    if exception == RuntimeError:
        assert called.get("mocked_compare")
        if comparison_snapshot is None:
            assert called.get("merge_strategy") is None
        else:
            assert called.get("merge_strategy")
    else:
        assert not called


def test_compare_ok_empty_a():
    snapshot_a = _create_event_snapshot("A")
    snapshot_b = _create_event_snapshot("B", [1, 2, 3])
    # When
    res = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(res, event.EventSnapshotComparison)
    assert res.only_in_a is None
    assert res.only_in_b == snapshot_b
    assert res.overlapping is None
    _validate_comparison_source(snapshot_a, snapshot_b, res)


def _create_event_snapshot(
    source: str, ts_list: Optional[List[int]] = None
) -> event.EventSnapshot:
    timestamp_to_request = {}
    if ts_list:
        for ts in ts_list:
            timestamp_to_request[ts] = [
                request.ScaleRequest(
                    topic="topic", resource="resource", command=f"{source} = {ts}"
                )
            ]
    return event.EventSnapshot(source=source, timestamp_to_request=timestamp_to_request)


def _validate_comparison_source(
    snapshot_a: event.EventSnapshot,
    snapshot_b: event.EventSnapshot,
    comparison: event.EventSnapshotComparison,
) -> None:
    if comparison.overlapping is not None:
        overlapping_a, overlapping_b = comparison.overlapping
        assert overlapping_a.source == snapshot_a.source
        assert overlapping_b.source == snapshot_b.source
    if comparison.only_in_a is not None:
        assert comparison.only_in_a.source == snapshot_a.source
    if comparison.only_in_b is not None:
        assert comparison.only_in_b.source == snapshot_b.source


def test_compare_ok_empty_b():
    snapshot_a = _create_event_snapshot("A", [1, 2, 3])
    snapshot_b = _create_event_snapshot("B")
    # When
    res = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(res, event.EventSnapshotComparison)
    assert res.only_in_a == snapshot_a
    assert res.only_in_b is None
    assert res.overlapping is None
    _validate_comparison_source(snapshot_a, snapshot_b, res)


def test_compare_ok_disjoint():
    """
      1  2  3  4  5
    --+--+--+--+--+--
      |  |  |  |  +- B_5
      |  |  |  +---- B_4
      |  |  +------- B_3
      |  +---------- A_2
      +------------- A_1
    """
    snapshot_a = _create_event_snapshot("A", [1, 2])
    snapshot_b = _create_event_snapshot("B", [3, 4, 5])
    # When
    res = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(res, event.EventSnapshotComparison)
    assert res.overlapping is None
    assert res.only_in_a == snapshot_a
    assert res.only_in_b == snapshot_b
    _validate_comparison_source(snapshot_a, snapshot_b, res)


def test_compare_ok_only_conflict():
    """
      1  2  3
    --+--+--+--
      |  |  +- A_3, B_3
      |  +---- A_2, B_2
      +------- A_1, B_1
    """
    snapshot_a = _create_event_snapshot("A", [1, 2, 3])
    snapshot_b = _create_event_snapshot("B", [1, 2, 3])
    # When
    res = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(res, event.EventSnapshotComparison)
    assert res.only_in_a is None
    assert res.only_in_b is None
    assert res.overlapping is not None
    overlapping_a, overlapping_b = res.overlapping
    assert overlapping_a == snapshot_a
    assert overlapping_b == snapshot_b
    _validate_comparison_source(snapshot_a, snapshot_b, res)


def test_compare_ok_with_conflict():
    """
    different commands, always conflicting.
      1  2  3  4  5
    --+--+--+--+--+--
      |  |  |  |  +- B_5
      |  |  |  +---- A_4
      |  |  +------- B_3
      |  +---------- A_2, B_2
      +------------- A_1
    """
    snapshot_a = _create_event_snapshot("A", [1, 2, 4])
    snapshot_b = _create_event_snapshot("B", [2, 3, 5])
    # When
    res = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(res, event.EventSnapshotComparison)
    # Then: only A
    assert len(res.only_in_a.timestamp_to_request) == 2
    for ts in [1, 4]:
        assert res.only_in_a.timestamp_to_request.get(ts) is not None
        assert res.only_in_a.timestamp_to_request.get(
            ts
        ) == snapshot_a.timestamp_to_request.get(ts)
    # Then: only B
    assert len(res.only_in_b.timestamp_to_request) == 2
    for ts in [3, 5]:
        assert res.only_in_b.timestamp_to_request.get(ts) is not None
        assert res.only_in_b.timestamp_to_request.get(
            ts
        ) == snapshot_b.timestamp_to_request.get(ts)
    # Then: overlapping
    assert res.overlapping is not None
    overlap_a, overlap_b = res.overlapping
    assert len(overlap_a.timestamp_to_request) == len(overlap_b.timestamp_to_request)
    for ts in [2]:
        assert overlap_a.timestamp_to_request.get(ts)
        assert overlap_b.timestamp_to_request.get(ts)
    # Then: sources
    _validate_comparison_source(snapshot_a, snapshot_b, res)
