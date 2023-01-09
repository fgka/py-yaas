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
from typing import Any, Dict, Optional

import pytest

from yaas.dto import config, event, request
from yaas.event.store import base

from tests import common


_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request()
_TEST_EVENT_SNAPSHOT_WITH_REQUEST: event.EventSnapshot = event.EventSnapshot(
    source="A", timestamp_to_request={0: [_TEST_SCALE_REQUEST]}
)
_TEST_EVENT_SNAPSHOT_EMPTY: event.EventSnapshot = event.EventSnapshot(source="B")
_TEST_NOW_DT: datetime = datetime.utcnow()

##########################
# START: Multiprocessing #
##########################


async def _get_lock(obj, start_sleep: int) -> bool:
    await asyncio.sleep(start_sleep)
    async with obj:
        await asyncio.sleep(obj.lock_timeout_in_sec * 2)
    return True


def _run_sync(lock_file: pathlib.Path, start_sleep: int):
    obj = base.FileBasedLockContextManager(lock_file=lock_file, lock_timeout_in_sec=1)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_get_lock(obj, start_sleep))


########################
# END: Multiprocessing #
########################


class TestFileBasedLockContextManager:
    def setup_method(self):
        self.instance = base.FileBasedLockContextManager(
            lock_file=common.tmpfile(), lock_timeout_in_sec=1
        )

    def test_properties_ok(self):
        assert isinstance(self.instance.lock_file, pathlib.Path)
        assert self.instance.lock_file.exists()
        assert isinstance(self.instance.lock_timeout_in_sec, int)
        assert self.instance.lock_timeout_in_sec > 0

    def test_ctor_ok_existing_lock_file(self):
        lock_file = common.tmpfile(existing=True)
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
            (common.tmpfile(), 0),
            (common.tmpfile(), -1),
            (pathlib.Path("/"), 10),  # file does not have write access
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

    @pytest.mark.doesnt_work_cloudbuild
    def test_enter_nok_multiprocess(self):

        lock_file = common.tmpfile()

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
                    assert False, "Should not be reached"


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


_TEST_DATETIME: datetime = datetime.utcnow()


class TestStoreContextManager:  # pylint: disable=too-many-public-methods
    def setup_method(self):
        self.object = common.MyStoreContextManager()

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

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test_read_nok_raises(self, is_archive: bool):
        # Given
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23, is_archive=is_archive)
        self.object.to_raise.add(base.StoreContextManager.read.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.read(**exp_kwargs)
        # Then
        called = self._assert_called_only(base.StoreContextManager.read.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
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

    @staticmethod
    def _assert_called_kwargs(
        called_kwargs: Dict[str, Any], exp_kwargs: Dict[str, Any]
    ) -> None:
        assert isinstance(called_kwargs, dict)
        for key, val in exp_kwargs.items():
            assert called_kwargs.get(key) == val

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
        assert called.get("value") == value
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
        assert (
            self.object.called.get(base.StoreContextManager.write.__name__).get("value")
            == value
        )
        # Then: remove
        assert (
            self.object.called.get(base.StoreContextManager.remove.__name__) is not None
        ) == overwrite
        assert not self.object.has_changed

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test_remove_nok_raises(self, is_archive: bool):
        # Given
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23, is_archive=is_archive)
        self.object.to_raise.add(base.StoreContextManager.remove.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.remove(**exp_kwargs)
        # Then
        called = self._assert_called_only(base.StoreContextManager.remove.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert not self.object.has_changed

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test_remove_ok_empty(self, is_archive: bool):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_EMPTY
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23, is_archive=is_archive)
        # When
        async with self.object:
            result = await self.object.remove(**exp_kwargs)
        # Then
        assert isinstance(result, event.EventSnapshot)
        called = self._assert_called_only(base.StoreContextManager.remove.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert not self.object.has_changed

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test_remove_ok(self, is_archive: bool):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23, is_archive=is_archive)
        # When
        async with self.object:
            result = await self.object.remove(**exp_kwargs)
        # Then
        assert isinstance(result, event.EventSnapshot)
        called = self._assert_called_only(base.StoreContextManager.remove.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert self.object.has_changed

    @pytest.mark.asyncio
    async def test_archive_nok_raises(self):
        # Given
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23)
        self.object.to_raise.add(base.StoreContextManager.archive.__name__)
        # When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.archive(**exp_kwargs)
        # Then
        called = self._assert_called_only(base.StoreContextManager.archive.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_archive_ok_empty(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_EMPTY
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23)
        # When
        async with self.object:
            await self.object.archive(**exp_kwargs)
        # Then
        called = self._assert_called_only(base.StoreContextManager.archive.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert not self.object.has_changed

    @pytest.mark.asyncio
    async def test_archive_ok(self):
        # Given
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        exp_kwargs = dict(start_ts_utc=13, end_ts_utc=23)
        # When
        async with self.object:
            await self.object.archive(**exp_kwargs)
        # Then
        called = self._assert_called_only(base.StoreContextManager.archive.__name__)
        self._assert_called_kwargs(called, exp_kwargs)
        assert self.object.has_changed

    @pytest.mark.parametrize(
        "value",
        [
            1,
            13,
            0,
        ],
    )
    def test__end_ts_utc_from_days_delta_and_logging_ok(self, value: int):
        # Given
        now = _TEST_NOW_DT.timestamp()
        expected = _TEST_NOW_DT - timedelta(days=value)
        # When
        result = base.StoreContextManager._end_ts_utc_from_days_delta_and_logging(
            value, "test", now=now
        )
        # Then
        assert result == int(expected.timestamp())

    @pytest.mark.parametrize("value", [None, -1])
    def test__end_ts_utc_from_days_delta_and_logging_nok(self, value: int):
        now = _TEST_NOW_DT.timestamp()
        with pytest.raises(ValueError):
            base.StoreContextManager._end_ts_utc_from_days_delta_and_logging(
                value, "test", now=now
            )

    @pytest.mark.asyncio
    async def test_clean_up_ok(self, monkeypatch):
        self.object.result_snapshot = _TEST_EVENT_SNAPSHOT_WITH_REQUEST
        configuration = config.DataRetentionConfig(
            expired_entries_max_retention_before_archive_in_days=3,
            max_retention_archive_before_removal_in_days=37,
        )
        now_ts = int(_TEST_NOW_DT.timestamp())
        end_ts_utc_lst = [
            now_ts - 1000,
            now_ts - 10000,
        ]
        called_end_ts = []

        def mocked_end_ts_utc_from_days_delta_and_logging(  # pylint: disable=unused-argument
            _, value: int, log_msg_prefix: str, *, now: Optional[int] = None
        ) -> int:
            nonlocal called_end_ts
            result = end_ts_utc_lst[len(called_end_ts)]
            called_end_ts.append(locals())
            return result

        monkeypatch.setattr(
            base.StoreContextManager,
            base.StoreContextManager._end_ts_utc_from_days_delta_and_logging.__name__,
            mocked_end_ts_utc_from_days_delta_and_logging,
        )
        # When
        async with self.object:
            await self.object.clean_up(configuration)
        # Then: ent_ts
        assert len(called_end_ts) == len(end_ts_utc_lst)
        assert (
            called_end_ts[0].get("value")
            == configuration.expired_entries_max_retention_before_archive_in_days
        )
        assert (
            called_end_ts[1].get("value")
            == configuration.max_retention_archive_before_removal_in_days
        )
        # Then: archive
        called_archive = self.object.called.get(
            base.StoreContextManager.archive.__name__
        )
        assert called_archive.get("start_ts_utc") == 1
        assert called_archive.get("end_ts_utc") == end_ts_utc_lst[0]
        # Then: remove
        called_remove = self.object.called.get(base.StoreContextManager.remove.__name__)
        assert called_remove.get("start_ts_utc") == 1
        assert called_remove.get("end_ts_utc") == end_ts_utc_lst[1]
        assert called_remove.get("is_archive")
        # Then: changed
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

    async def _read_ro(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> event.EventSnapshot:
        self.called[base.StoreContextManager._read.__name__] = True
        return self._read_result


class TestReadOnlyStoreContextManager:
    def setup_method(self):
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

    @pytest.mark.asyncio
    async def test_read_ok_archive(self):
        # Given/When/Then
        with pytest.raises(base.StoreError):
            async with self.object:
                await self.object.read(is_archive=True)
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
