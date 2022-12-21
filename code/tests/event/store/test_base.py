# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest

from yaas.dto import event, request
from yaas.event.store import base

_TEST_SCALE_REQUEST: request.ScaleRequest = request.ScaleRequest(
    topic="TEST_TOPIC", resource="TEST_RESOURCE"
)
_TEST_EVENT_SNAPSHOT_WITH_REQUEST: event.EventSnapshot = event.EventSnapshot(
    source="A", timestamp_to_request={0: [_TEST_SCALE_REQUEST]}
)
_TEST_EVENT_SNAPSHOT_EMPTY: event.EventSnapshot = event.EventSnapshot(source="B")


def test__default_start_ts_utc_ok():
    # Given
    min_result = datetime.utcnow()
    # When
    result = base._default_start_ts_utc()
    # Then
    _assert_ts_in_range(result, min_result)


def _assert_ts_in_range(value: int, min_value: datetime) -> None:
    max_value = min_value + timedelta(seconds=10)
    assert isinstance(value, int)
    assert (
        int(min_value.timestamp()) <= value
    ), f"Value: {value}, min: {min_value} = {min_value.timestamp()}"
    assert value < int(
        max_value.timestamp()
    ), f"Value: {value}, max: {max_value} = {max_value.timestamp()}"


def test__default_end_ts_utc_ok():
    # Given
    min_result = datetime.utcnow() + timedelta(
        days=base._DEFAULT_END_TS_FROM_NOW_IN_DAYS
    )
    # When
    result = base._default_end_ts_utc()
    # Then
    _assert_ts_in_range(result, min_result)


def test__default_max_end_ts_utc_ok():
    # Given
    min_result = datetime.utcnow() + timedelta(
        days=base._MAXIMUM_END_TS_FROM_NOW_IN_DAYS
    )
    # When
    result = base._default_max_end_ts_utc()
    # Then
    _assert_ts_in_range(result, min_result)


class _MyStore(base.Store):
    def __init__(
        self,
        result_snapshot: event.EventSnapshot = _TEST_EVENT_SNAPSHOT_EMPTY,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._result_snapshot = result_snapshot
        self.called = {}
        self.to_raise = set()

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.Store.read.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.Store.read.__name__ in self.to_raise:
            raise RuntimeError
        return self._result_snapshot

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        self.called[base.Store.write.__name__] = value
        if base.Store.write.__name__ in self.to_raise:
            raise RuntimeError

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.Store.remove.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.Store.remove.__name__ in self.to_raise:
            raise RuntimeError
        return self._result_snapshot

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        self.called[base.Store.archive.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.Store.archive.__name__ in self.to_raise:
            raise RuntimeError


class TestStore:
    def setup(self):
        self.object = _MyStore()

    def test__effective_start_ts_utc_ok_value_none(self):
        # Given
        expected = 123
        self.object._default_start_ts_utc_fn = lambda: expected
        # When
        result = self.object._effective_start_ts_utc(None)
        # Then
        assert result == expected

    def test__effective_start_ts_utc_ok_value_given(self):
        # Given
        expected = 123
        default_value = 51
        self.object._default_start_ts_utc_fn = lambda: default_value
        # When
        result = self.object._effective_start_ts_utc(expected)
        # Then
        assert result == expected

    def test__effective_start_ts_utc_ok_value_negative(self):
        # Given
        expected = 0
        default_value = 51
        self.object._default_start_ts_utc_fn = lambda: default_value
        # When
        result = self.object._effective_start_ts_utc(-1)
        # Then
        assert result == expected

    def test__effective_start_ts_utc_ok_default_is_none(self):
        # Given
        expected = "TEST"
        self.object._default_start_ts_utc_fn = lambda: None
        # When
        result = self.object._effective_start_ts_utc(expected)
        # Then
        assert result == expected

    def test__effective_end_ts_utc_ok_value_none(self):
        # Given
        expected = 123
        self.object._default_end_ts_utc_fn = lambda: expected
        # When
        result = self.object._effective_end_ts_utc(None)
        # Then
        assert result == expected

    def test__effective_end_ts_utc_ok_value_given(self):
        # Given
        expected = 123
        default_value = 51
        self.object._default_end_ts_utc_fn = lambda: default_value
        # When
        result = self.object._effective_end_ts_utc(expected)
        # Then
        assert result == expected

    def test__effective_end_ts_utc_ok_value_negative(self):
        # Given
        expected = 0
        default_value = 51
        self.object._default_end_ts_utc_fn = lambda: default_value
        # When
        result = self.object._effective_end_ts_utc(-1)
        # Then
        assert result == expected

    def test__effective_end_ts_utc_ok_value_none_default_ge_max(self):
        # Given
        max_value = 123
        self.object._default_end_ts_utc_fn = lambda: max_value + 1
        self.object._max_end_ts_utc_fn = lambda: max_value
        # When
        result = self.object._effective_end_ts_utc(None)
        # Then
        assert result == max_value

    def test__effective_end_ts_utc_ok_value_given_ge_max(self):
        # Given
        max_value = 123
        self.object._default_end_ts_utc_fn = lambda: 0
        self.object._max_end_ts_utc_fn = lambda: max_value
        # When
        result = self.object._effective_end_ts_utc(max_value + 1)
        # Then
        assert result == max_value

    def test__effective_end_ts_utc_ok_default_is_none(self):
        # Given
        expected = "TEST"
        self.object._default_end_ts_utc_fn = lambda: None
        # When
        result = self.object._effective_end_ts_utc(expected)
        # Then
        assert result == expected

    @pytest.mark.asyncio
    async def test_read_nok_start_gt_end(self):
        # Given
        start = 123
        end = start - 1
        # When/Then
        with pytest.raises(ValueError):
            await self.object.read(start_ts_utc=start, end_ts_utc=end)

    @pytest.mark.asyncio
    async def test_read_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.Store.read.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            await self.object.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.Store.read.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    def _assert_called_only(self, value: str, secondary: Optional[str] = None) -> Any:
        result = self.object.called.get(value)
        assert result
        amount = 1
        if secondary is not None:
            assert self.object.called.get(secondary)
            amount = 2
        assert len(self.object.called) == amount
        return result

    @pytest.mark.asyncio
    async def test_write_ok_empty_request(self):
        # Given
        value = _TEST_EVENT_SNAPSHOT_EMPTY
        # When
        await self.object.write(value, overwrite_within_range=True)
        # Then
        called = self._assert_called_only(base.Store.write.__name__)
        assert called == value

    @pytest.mark.asyncio
    async def test_write_ok_non_empty_request(self):
        # Given
        value = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        # When
        await self.object.write(value, overwrite_within_range=True)
        # Then
        called = self._assert_called_only(
            base.Store.write.__name__, base.Store.remove.__name__
        )
        assert called == value

    @pytest.mark.parametrize("overwrite", [True, False])
    @pytest.mark.asyncio
    async def test_write_nok_raises(self, overwrite: bool):
        # Given
        value = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        self.object.to_raise.add(base.Store.write.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            await self.object.write(value, overwrite_within_range=overwrite)
        # Then: write
        called = self.object.called.get(base.Store.write.__name__)
        assert called == value
        # Then: read/remove
        assert self.object.called.get(base.Store.read.__name__) is None
        assert self.object.called.get(base.Store.archive.__name__) is None
        assert (
            self.object.called.get(base.Store.remove.__name__) is not None
        ) == overwrite

    @pytest.mark.asyncio
    async def test_remove_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.Store.remove.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            await self.object.remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.Store.remove.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    @pytest.mark.asyncio
    async def test_remove_ok(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        # When
        result = await self.object.remove(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
        )
        # Then
        assert isinstance(result, event.EventSnapshot)
        called = self._assert_called_only(base.Store.remove.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    @pytest.mark.asyncio
    async def test_archive_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.Store.archive.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            await self.object.archive(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.Store.archive.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    @pytest.mark.asyncio
    async def test_archive_ok(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        # When
        await self.object.archive(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.Store.archive.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc


class _MyReadOnlyStore(base.ReadOnlyStore):
    def __init__(
        self, read_result: event.EventSnapshot = _TEST_EVENT_SNAPSHOT_EMPTY, **kwargs
    ):
        super().__init__(**kwargs)
        self.called = False
        self._read_result = read_result

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called = True
        return self._read_result


class TestReadOnlyStore:
    @pytest.mark.parametrize("overwrite", [True, False])
    @pytest.mark.asyncio
    async def test_write_ok(self, overwrite: bool):
        # Given
        obj = _MyReadOnlyStore()
        # When/Then
        with pytest.raises(base.StoreError):
            await obj.write(
                _TEST_EVENT_SNAPSHOT_WITH_REQUEST, overwrite_within_range=overwrite
            )

    @pytest.mark.parametrize(
        "start_ts_utc,end_ts_utc",
        [
            (None, None),
            (0, None),
            (None, 1),
            (0, 1),
            (1, 0),
        ],
    )
    @pytest.mark.asyncio
    async def test_remove_and_archive_ok(self, start_ts_utc: int, end_ts_utc: int):
        # Given
        obj = _MyReadOnlyStore()
        # When/Then
        with pytest.raises(base.StoreError):
            await obj.remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        with pytest.raises(base.StoreError):
            await obj.archive(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
