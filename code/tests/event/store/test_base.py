# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import asyncio
from datetime import datetime, timedelta
from concurrent import futures
import pathlib
import time
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

# START: for multiprocessing #


async def _get_lock(obj, start_sleep: int) -> bool:
    await asyncio.sleep(start_sleep)
    async with obj:
        await asyncio.sleep(obj.lock_timeout_in_sec * 2)
    return True


def _run_sync(lock_file: pathlib.Path, start_sleep):
    obj = base.FileBasedLockContextManager(lock_file=lock_file, lock_timeout_in_sec=1)
    # This is to let all objects be created before trying to lock
    time.sleep(1)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_get_lock(obj, start_sleep))


# END: for multiprocessing #


class TestFileBasedLockContextManager:
    def setup(self):
        self.instance = base.FileBasedLockContextManager(
            lock_file=common.lock_file(), lock_timeout_in_sec=1
        )

    def test_properties_ok(self):
        assert isinstance(self.instance.lock_file, pathlib.Path)
        assert self.instance.lock_file.exists()
        assert isinstance(self.instance.lock_timeout_in_sec, int)
        assert self.instance.lock_timeout_in_sec > 0

    def test_ctor_ok_existing_lock_file(self):
        lock_file = common.lock_file(existing=True)
        assert lock_file.exists()
        # When
        obj = base.FileBasedLockContextManager(lock_file=lock_file)
        # Then
        assert obj.lock_file.exists()

    def test_ctor_ok_timeout_non_int(self):
        # Given/When
        obj = base.FileBasedLockContextManager(
            lock_file=self.instance.lock_file, lock_timeout_in_sec=None
        )
        # Then
        assert obj.lock_timeout_in_sec == base._DEFAULT_LOCK_TIMEOUT_IN_SEC

    @pytest.mark.parametrize(
        "lock_file,lock_timeout_in_sec",
        [
            (common.lock_file(), 0),
            (common.lock_file(), -1),
            (pathlib.Path("/bin/test"), 10),  # file does not have write access
        ],
    )
    def test_ctor_nok(self, lock_file: pathlib.Path, lock_timeout_in_sec: int):
        with pytest.raises(Exception):
            base.FileBasedLockContextManager(
                lock_file=lock_file, lock_timeout_in_sec=lock_timeout_in_sec
            )

    @pytest.mark.asyncio
    async def test_enter_ok(self):
        assert not self.instance.is_locked()
        async with self.instance:
            assert self.instance.is_locked()
        assert not self.instance.is_locked()

    def test_enter_nok_multiprocess(self):

        lock_file = common.lock_file()

        with futures.ProcessPoolExecutor() as executor:
            first = executor.submit(_run_sync, lock_file, 0)
            second = executor.submit(_run_sync, lock_file, 1)
            assert first.result()
            with pytest.raises(base.StoreLockTimeoutError):
                second.result()

    @pytest.mark.asyncio
    async def test_enter_nok_reentrant(self):
        async with self.instance:
            assert self.instance.is_locked()
            with pytest.raises(base.StoreLockTimeoutError):
                async with self.instance:
                    assert False, f"Should not be reached"


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
        self.result_snapshot = result_snapshot
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
        return self.result_snapshot

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
        return self.result_snapshot

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager.archive.__name__] = (
            start_ts_utc,
            end_ts_utc,
        )
        if base.StoreContextManager.archive.__name__ in self.to_raise:
            raise RuntimeError
        return self.result_snapshot


_TEST_DATETIME: datetime = datetime.utcnow()


class TestStoreContextManager:  # pylint: disable=too-many-public-methods
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
        assert not self.object.has_changed

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
        assert not self.object.has_changed

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
        assert self.object.called.get(base.StoreContextManager.write.__name__) is None
        assert not self.object.has_changed

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
        assert self.object.has_changed

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
        assert not self.object.has_changed

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
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_remove_ok_empty(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_EMPTY
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
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_remove_ok(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
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
        assert self.object.has_changed

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
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_archive_ok_empty(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_EMPTY
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
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_archive_ok(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
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
        assert self.object.has_changed


class _MyReadOnlyStoreContextManager(base.ReadOnlyStoreContextManager):
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


class TestReadOnlyStoreContextManager:
    def setup(self):
        self.object = _MyReadOnlyStoreContextManager()

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
        assert not self.object.has_changed

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
        assert not self.object.has_changed
