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

from tests import common


_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request()
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


class _MyStoreContextManager(base.StoreContextManager):
    def __init__(
        self,
        result_snapshot: event.EventSnapshot = _TEST_EVENT_SNAPSHOT_EMPTY,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._result_snapshot = result_snapshot
        self.called = {}
        self.to_raise = set()

    async def _open(self) -> None:
        self.called[base.StoreContextManager._open.__name__] = True

    async def _close(self) -> None:
        self.called[base.StoreContextManager._close.__name__] = True

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.read.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.StoreContextManager.read.__name__ in self.to_raise:
            raise RuntimeError
        return self._result_snapshot

    async def _write(
        self,
        value: event.EventSnapshot,
    ) -> None:
        self.called[base.StoreContextManager.write.__name__] = value
        if base.StoreContextManager.write.__name__ in self.to_raise:
            raise RuntimeError

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.remove.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.StoreContextManager.remove.__name__ in self.to_raise:
            raise RuntimeError
        return self._result_snapshot

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        self.called[base.StoreContextManager.archive.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.StoreContextManager.archive.__name__ in self.to_raise:
            raise RuntimeError


_TEST_DATETIME: datetime = datetime.utcnow()


class TestStore:  # pylint: disable=too-many-public-methods
    def setup(self):
        self.object = _MyStoreContextManager()

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, None),
            ("", ""),
            (123, 123),
            (123.5, 123),
            (_TEST_DATETIME, int(_TEST_DATETIME.timestamp())),
        ],
    )
    def test__get_int_ts_ok(self, value: Any, expected: Any):
        # Given/When
        result = self.object._get_int_ts(value)
        # Then
        assert result == expected

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
            async with self.object:
                await self.object.read(start_ts_utc=start, end_ts_utc=end)
        self._assert_context_called()

    def _assert_context_called(self) -> None:
        assert self.object.called.get(base.StoreContextManager._open.__name__)
        assert self.object.called.get(base.StoreContextManager._close.__name__)

    @pytest.mark.asyncio
    async def test_read_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.StoreContextManager.read.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.StoreContextManager.read.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    def _assert_called_only(self, value: str, secondary: Optional[str] = None) -> Any:
        result = self.object.called.get(value)
        assert result
        amount = 3
        if secondary is not None:
            assert self.object.called.get(secondary)
            amount = 4
        assert len(self.object.called) == amount
        self._assert_context_called()
        return result

    @pytest.mark.asyncio
    async def test_write_ok_empty_request(self):
        # Given
        value = _TEST_EVENT_SNAPSHOT_EMPTY
        # When
        async with self.object:
            await self.object.write(value, overwrite_within_range=True)
        # Then
        called = self._assert_called_only(base.StoreContextManager.write.__name__)
        assert called == value

    @pytest.mark.asyncio
    async def test_write_ok_non_empty_request(self):
        # Given
        value = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        # When
        async with self.object:
            await self.object.write(value, overwrite_within_range=True)
        # Then
        called = self._assert_called_only(
            base.StoreContextManager.write.__name__,
            base.StoreContextManager.remove.__name__,
        )
        assert called == value

    @pytest.mark.parametrize("overwrite", [True, False])
    @pytest.mark.asyncio
    async def test_write_nok_raises(self, overwrite: bool):
        # Given
        value = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        self.object.to_raise.add(base.StoreContextManager.write.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.write(value, overwrite_within_range=overwrite)
        # Then: write
        assert self.object.called.get(base.StoreContextManager.write.__name__) == value
        # Then: remove
        assert (
            self.object.called.get(base.StoreContextManager.remove.__name__) is not None
        ) == overwrite

    @pytest.mark.asyncio
    async def test_remove_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.StoreContextManager.remove.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.remove(
                    start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
                )
        # Then
        called = self._assert_called_only(base.StoreContextManager.remove.__name__)
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
        async with self.object:
            result = await self.object.remove(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
            )
        # Then
        assert isinstance(result, event.EventSnapshot)
        called = self._assert_called_only(base.StoreContextManager.remove.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc

    @pytest.mark.asyncio
    async def test_archive_nok_raises(self):
        # Given
        start_ts_utc = 13
        end_ts_utc = 23
        self.object.to_raise.add(base.StoreContextManager.archive.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.archive(
                    start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
                )
        # Then
        called = self._assert_called_only(base.StoreContextManager.archive.__name__)
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
        async with self.object:
            await self.object.archive(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        # Then
        called = self._assert_called_only(base.StoreContextManager.archive.__name__)
        assert called
        res_start, res_end = called
        assert res_start == start_ts_utc
        assert res_end == end_ts_utc


class _MyReadOnlyStore(base.ReadOnlyStoreContextManager):
    def __init__(
        self, read_result: event.EventSnapshot = _TEST_EVENT_SNAPSHOT_EMPTY, **kwargs
    ):
        super().__init__(**kwargs)
        self.called = {}
        self._read_result = read_result

    async def _open(self) -> None:
        self.called[base.StoreContextManager._open.__name__] = True

    async def _close(self) -> None:
        self.called[base.StoreContextManager._close.__name__] = True

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager._read.__name__] = True
        return self._read_result


class TestReadOnlyStore:
    def setup(self):
        self.object = _MyReadOnlyStore()

    @pytest.mark.parametrize("overwrite", [True, False])
    @pytest.mark.asyncio
    async def test_write_ok(self, overwrite: bool):
        # Given/When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.write(
                    _TEST_EVENT_SNAPSHOT_WITH_REQUEST, overwrite_within_range=overwrite
                )
        self._assert_context_called()

    def _assert_context_called(self) -> None:
        assert self.object.called.get(base.StoreContextManager._open.__name__)
        assert self.object.called.get(base.StoreContextManager._close.__name__)

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
        # Given/When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.remove(
                    start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
                )
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.archive(
                    start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
                )
        self._assert_context_called()
