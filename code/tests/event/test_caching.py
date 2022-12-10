# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Callable, Dict, List, Optional

import pytest

from yaas.event import caching
from yaas.dto import event

_TEST_CALENDAR_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="calendar")
_TEST_CACHE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="cache")
_TEST_COMPARISON_SNAPSHOT: event.EventSnapshotComparison = (
    event.EventSnapshotComparison()
)
_TEST_MERGE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="merge")


@pytest.mark.parametrize(
    "start_utc,end_utc,cache_write_result",
    [
        (0, 1, True),
        (0, 1, False),
    ],
)
def test_update_event_cache_ok(
    monkeypatch,
    start_utc: int,
    end_utc: int,
    cache_write_result: bool,
):
    # Given
    called = {}

    def callback_fn(name: str) -> None:
        nonlocal called
        called[name] = True

    (
        cache_reader,
        cache_writer,
        calendar_reader,
        merge_strategy,
    ) = _create_update_callable_arguments(
        monkeypatch,
        start_utc=start_utc,
        end_utc=end_utc,
        callback_fn=callback_fn,
        cache_write_result=cache_write_result,
    )
    # When
    res = caching.update_event_cache(
        start_utc=start_utc,
        end_utc=end_utc,
        merge_strategy=merge_strategy,
        calendar_reader=calendar_reader,
        cache_reader=cache_reader,
        cache_writer=cache_writer,
    )
    # Then
    assert res == cache_write_result
    assert called.get("calendar_reader")
    assert called.get("cache_reader")
    assert called.get("snapshot.compare")
    assert called.get("merge_strategy")
    assert called.get("cache_writer")


def _create_update_callable_arguments(
    monkeypatch,
    *,
    start_utc: int = 123,
    end_utc: int = 321,
    callback_fn: Optional[Callable[[str], None]] = None,
    calendar_snapshot: event.EventSnapshot = _TEST_CALENDAR_SNAPSHOT,
    cache_snapshot: event.EventSnapshot = _TEST_CACHE_SNAPSHOT,
    comparison_snapshot: event.EventSnapshotComparison = _TEST_COMPARISON_SNAPSHOT,
    merge_snapshot: event.EventSnapshot = _TEST_MERGE_SNAPSHOT,
    cache_write_result: bool = True,
):
    merge_strategy = _create_fn(
        name="merge_strategy",
        expected_args=[comparison_snapshot],
        result=merge_snapshot,
        callback_fn=callback_fn,
    )
    calendar_reader = _create_fn(
        name="calendar_reader",
        expected_args=[start_utc, end_utc],
        result=calendar_snapshot,
        callback_fn=callback_fn,
    )
    cache_reader = _create_fn(
        name="cache_reader",
        expected_args=[start_utc, end_utc],
        result=cache_snapshot,
        callback_fn=callback_fn,
    )
    cache_writer = _create_fn(
        name="cache_writer",
        expected_args=[merge_snapshot],
        result=cache_write_result,
        callback_fn=callback_fn,
    )
    mocked_compare = _create_fn(
        name="snapshot.compare",
        expected_kwargs=dict(snapshot_a=cache_snapshot, snapshot_b=calendar_snapshot),
        result=comparison_snapshot,
        callback_fn=callback_fn,
    )
    monkeypatch.setattr(
        caching.version_control, caching.version_control.compare.__name__, mocked_compare
    )
    return cache_reader, cache_writer, calendar_reader, merge_strategy


def _create_fn(
    *,
    name: str,
    expected_args: Optional[List[Any]] = None,
    expected_kwargs: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
    callback_fn: Callable[[str], None] = None,
    raise_exception_if_result_is_none: bool = True,
) -> Callable[[Any], Any]:
    def func(*args, **kwargs) -> Any:
        if callback_fn is not None:
            callback_fn(name)
        if expected_args:
            for arg, exp in zip(args, expected_args):
                assert arg == exp
        if expected_kwargs:
            for key in expected_kwargs:
                assert kwargs.get(key) == expected_kwargs.get(key)
        if raise_exception_if_result_is_none and result is None:
            raise RuntimeError(f"Raising error on {name}")
        return result

    return func


@pytest.mark.parametrize(
    "exception,"
    "start_utc,"
    "end_utc,"
    "calendar_snapshot,"
    "cache_snapshot,"
    "comparison_snapshot,"
    "merge_snapshot,"
    "cache_write_result",
    [
        (
            TypeError,
            "111",  # start_utc is not an int
            222,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            TypeError,
            111,
            "222",  # end_utc is not an int
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            ValueError,
            -1,  # start_utc < 0
            111,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            ValueError,
            222,  # start_utc > end_utc
            111,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            ValueError,
            111,  # start_utc is NOT > end_utc
            111,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            RuntimeError,
            111,
            222,
            None,  # calendar_reader raises exception
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            RuntimeError,
            111,
            222,
            _TEST_CALENDAR_SNAPSHOT,
            None,  # cache_reader raises exception
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            RuntimeError,
            111,
            222,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            None,  # snapshot.compare raises exception
            _TEST_MERGE_SNAPSHOT,
            True,
        ),
        (
            RuntimeError,
            111,
            222,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            None,  # merge_strategy raises exception
            True,
        ),
        (
            RuntimeError,
            111,
            222,
            _TEST_CALENDAR_SNAPSHOT,
            _TEST_CACHE_SNAPSHOT,
            _TEST_COMPARISON_SNAPSHOT,
            _TEST_MERGE_SNAPSHOT,
            None,  # cache_writer raises exception
        ),
    ],
)
def test_update_event_cache_nok(  # pylint: disable=too-many-arguments
    monkeypatch,
    exception: Exception,
    start_utc: int,
    end_utc: int,
    calendar_snapshot: event.EventSnapshot,
    cache_snapshot: event.EventSnapshot,
    comparison_snapshot: event.EventSnapshotComparison,
    merge_snapshot: event.EventSnapshot,
    cache_write_result: bool,
):
    # Given
    called = {}

    def callback_fn(name: str) -> None:
        nonlocal called
        called[name] = True

    (
        cache_reader,
        cache_writer,
        calendar_reader,
        merge_strategy,
    ) = _create_update_callable_arguments(
        monkeypatch,
        start_utc=start_utc,
        end_utc=end_utc,
        callback_fn=callback_fn,
        calendar_snapshot=calendar_snapshot,
        cache_snapshot=cache_snapshot,
        merge_snapshot=merge_snapshot,
        comparison_snapshot=comparison_snapshot,
        cache_write_result=cache_write_result,
    )
    # When
    with pytest.raises(exception):
        caching.update_event_cache(
            start_utc=start_utc,
            end_utc=end_utc,
            merge_strategy=merge_strategy,
            calendar_reader=calendar_reader,
            cache_reader=cache_reader,
            cache_writer=cache_writer,
        )
    # Then
    if exception == RuntimeError:
        # it always marks the function as called but the other in the chain are not.
        assert called.get("calendar_reader")
        if calendar_snapshot is None:
            assert called.get("cache_reader") is None
        else:
            assert called.get("cache_reader")
            if cache_snapshot is None:
                assert called.get("snapshot.compare") is None
            else:
                assert called.get("snapshot.compare")
                if comparison_snapshot is None:
                    assert called.get("merge_strategy") is None
                else:
                    assert called.get("merge_strategy")
                    if merge_snapshot is None:
                        assert called.get("cache_writer") is None
                    else:
                        assert called.get("cache_writer")
    else:
        assert not called
