# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Callable, Optional, Tuple

import pytest

from yaas_caching import event, version_control

from tests import common


@pytest.mark.parametrize(
    "snapshot_a,snapshot_b",
    [
        (None, None),  # no snapshots
        (None, common.TEST_CALENDAR_SNAPSHOT),  # missing A
        (common.TEST_CACHE_SNAPSHOT, None),  # missing B
    ],
)
def test_compare_nok(snapshot_a: event.EventSnapshot, snapshot_b: event.EventSnapshot):
    with pytest.raises(TypeError):
        version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)


def test_merge_ok_empty(monkeypatch):
    # Given
    snapshot_a_arg = common.TEST_CALENDAR_SNAPSHOT
    snapshot_b_arg = common.TEST_CACHE_SNAPSHOT
    expected = common.TEST_MERGE_SNAPSHOT
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
    is_required, result = version_control.merge(
        snapshot_a=snapshot_a_arg,
        snapshot_b=snapshot_b_arg,
        merge_strategy=merge_strategy,
    )
    # Then
    assert not is_required
    assert result is None
    assert called.get("mocked_compare")
    assert called.get("merge_strategy") is None


def _create_merge_arguments(
    monkeypatch,
    *,
    snapshot_a_arg: event.EventSnapshot = common.TEST_CALENDAR_SNAPSHOT,
    snapshot_b_arg: event.EventSnapshot = common.TEST_CACHE_SNAPSHOT,
    comparison_snapshot: event.EventSnapshotComparison = common.TEST_COMPARISON_SNAPSHOT,
    expected: event.EventSnapshot = common.TEST_MERGE_SNAPSHOT,
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
    ) -> Tuple[bool, event.EventSnapshotComparison]:
        callback_fn("mocked_compare")
        assert snapshot_a == snapshot_a_arg
        assert snapshot_b == snapshot_b_arg
        if raise_exception_if_result_is_none and comparison_snapshot is None:
            raise RuntimeError
        return comparison_snapshot

    monkeypatch.setattr(
        version_control, version_control.compare.__name__, mocked_compare
    )
    return merge_strategy


def test_merge_ok(monkeypatch):
    # Given
    snapshot_a = common.create_event_snapshot("A", [1, 2, 3])
    snapshot_b = common.create_event_snapshot("B")
    called = {}

    def callback_fn(name: str) -> None:
        nonlocal called
        called[name] = True

    merge_strategy = _create_merge_arguments(
        monkeypatch,
        snapshot_a_arg=snapshot_a,
        snapshot_b_arg=snapshot_b,
        callback_fn=callback_fn,
        comparison_snapshot=common.TEST_COMPARISON_SNAPSHOT_NON_EMPTY,
    )
    # When
    is_required, result = version_control.merge(
        snapshot_a=snapshot_a,
        snapshot_b=snapshot_b,
        merge_strategy=merge_strategy,
    )
    # Then
    assert is_required
    assert isinstance(result, event.EventSnapshot)
    assert called.get("mocked_compare")
    assert called.get("merge_strategy")


@pytest.mark.parametrize(
    "exception,comparison_snapshot,expected",
    [
        (
            RuntimeError,
            None,  # compare raises exception
            common.TEST_MERGE_SNAPSHOT,
        ),
        (
            RuntimeError,
            common.TEST_COMPARISON_SNAPSHOT_NON_EMPTY,
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
    snapshot_a_arg = common.TEST_CALENDAR_SNAPSHOT
    snapshot_b_arg = common.TEST_CACHE_SNAPSHOT
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
        raise_exception_if_result_is_none=True,
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
    snapshot_a = common.create_event_snapshot("A")
    snapshot_b = common.create_event_snapshot("B", [1, 2, 3])
    # When
    result = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(result, event.EventSnapshotComparison)
    assert result.only_in_a is None
    assert result.only_in_b == snapshot_b
    assert result.overlapping is None
    _validate_comparison_source(snapshot_a, snapshot_b, result)
    assert result.are_different()
    assert result.snapshot_a == snapshot_a
    assert result.snapshot_b == snapshot_b


def _validate_comparison_source(
    snapshot_a: event.EventSnapshot,
    snapshot_b: event.EventSnapshot,
    comparison: event.EventSnapshotComparison,
) -> None:
    assert comparison.snapshot_a == snapshot_a
    assert comparison.snapshot_b == snapshot_b
    if comparison.overlapping is not None:
        overlapping_a, overlapping_b = comparison.overlapping
        assert overlapping_a.source == snapshot_a.source
        assert overlapping_b.source == snapshot_b.source
    if comparison.only_in_a is not None:
        assert comparison.only_in_a.source == snapshot_a.source
    if comparison.only_in_b is not None:
        assert comparison.only_in_b.source == snapshot_b.source


def test_compare_ok_empty_b():
    snapshot_a = common.create_event_snapshot("A", [1, 2, 3])
    snapshot_b = common.create_event_snapshot("B")
    # When
    result = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(result, event.EventSnapshotComparison)
    assert result.only_in_a == snapshot_a
    assert result.only_in_b is None
    assert result.overlapping is None
    _validate_comparison_source(snapshot_a, snapshot_b, result)
    assert result.are_different()


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
    snapshot_a = common.create_event_snapshot("A", [1, 2])
    snapshot_b = common.create_event_snapshot("B", [3, 4, 5])
    # When
    result = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(result, event.EventSnapshotComparison)
    assert result.overlapping is None
    assert result.only_in_a == snapshot_a
    assert result.only_in_b == snapshot_b
    _validate_comparison_source(snapshot_a, snapshot_b, result)
    assert result.are_different()


def test_compare_ok_only_conflict():
    """
      1  2  3
    --+--+--+--
      |  |  +- A_3, B_3
      |  +---- A_2, B_2
      +------- A_1, B_1
    """
    snapshot_a = common.create_event_snapshot("A", [1, 2, 3])
    snapshot_b = common.create_event_snapshot("B", [1, 2, 3])
    # When
    result = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(result, event.EventSnapshotComparison)
    assert result.only_in_a is None
    assert result.only_in_b is None
    assert result.overlapping is not None
    overlapping_a, overlapping_b = result.overlapping
    assert overlapping_a == snapshot_a
    assert overlapping_b == snapshot_b
    _validate_comparison_source(snapshot_a, snapshot_b, result)
    assert result.are_different()


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
    snapshot_a = common.create_event_snapshot("A", [1, 2, 4])
    snapshot_b = common.create_event_snapshot("B", [2, 3, 5])
    # When
    result = version_control.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
    # Then
    assert isinstance(result, event.EventSnapshotComparison)
    assert result.are_different()
    # Then: only A
    assert len(result.only_in_a.timestamp_to_request) == 2
    for ts in [1, 4]:
        assert result.only_in_a.timestamp_to_request.get(ts) is not None
        assert result.only_in_a.timestamp_to_request.get(
            ts
        ) == snapshot_a.timestamp_to_request.get(ts)
    # Then: only B
    assert len(result.only_in_b.timestamp_to_request) == 2
    for ts in [3, 5]:
        assert result.only_in_b.timestamp_to_request.get(ts) is not None
        assert result.only_in_b.timestamp_to_request.get(
            ts
        ) == snapshot_b.timestamp_to_request.get(ts)
    # Then: overlapping
    assert result.overlapping is not None
    overlap_a, overlap_b = result.overlapping
    assert len(overlap_a.timestamp_to_request) == len(overlap_b.timestamp_to_request)
    for ts in [2]:
        assert overlap_a.timestamp_to_request.get(ts)
        assert overlap_b.timestamp_to_request.get(ts)
    # Then: sources
    _validate_comparison_source(snapshot_a, snapshot_b, result)
