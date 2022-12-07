# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Callable, Optional

import pytest

from yaas.cal import snapshot
from yaas.dto import event

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
        snapshot.compare(snapshot_a=snapshot_a, snapshot_b=snapshot_b)


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
    res = snapshot.merge(
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

    monkeypatch.setattr(snapshot, snapshot.compare.__name__, mocked_compare)
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
        snapshot.merge(
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
