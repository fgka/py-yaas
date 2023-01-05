# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import asyncio
import pathlib
import re
import tempfile
from typing import Any, List, Type, Optional, Generator

import attrs

import pytest

from yaas import const
from yaas.dto import event, request
from yaas.event.store import file

from tests import common

_TEST_CALENDAR_ID: str = "TEST_CALENDAR_ID"
# pylint: disable=consider-using-with
_TEST_JSON_LINE_FILE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
# pylint: enable=consider-using-with
_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request(
    timestamp_utc=123
)
_TEST_SCALE_REQUEST_AFTER: request.ScaleRequest = common.create_scale_request(
    timestamp_utc=321
)


class _MyBaseFileStoreContextManager(file.BaseFileStoreContextManager):
    def __init__(self, **kwargs):
        super().__init__(lock_file=common.lock_file(), **kwargs)
        self.current = []
        self.archived = []

    def _which(self, is_archive: Optional[bool] = False) -> List[request.ScaleRequest]:
        return self.archived if is_archive else self.current

    async def _read_scale_requests(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> Generator[request.ScaleRequest, None, None]:
        for req in self._which(is_archive):
            await asyncio.sleep(0)
            yield req

    async def _write_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        self._which(is_archive).extend(value)
        return value

    async def _remove_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        for val in value:
            self._which(is_archive).remove(val)
        return value


class TestBaseFileStoreContextManager:
    def setup(self):
        self.instance = _MyBaseFileStoreContextManager()

    @pytest.mark.parametrize(
        "req,start_ts_utc,end_ts_utc",
        [
            (_TEST_SCALE_REQUEST, None, None),
            (_TEST_SCALE_REQUEST, None, None),
            (_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST.timestamp_utc, None),
            (_TEST_SCALE_REQUEST, None, _TEST_SCALE_REQUEST.timestamp_utc),
            (
                _TEST_SCALE_REQUEST,
                _TEST_SCALE_REQUEST.timestamp_utc,
                _TEST_SCALE_REQUEST.timestamp_utc,
            ),
        ],
    )
    def test__is_request_in_range_ok(
        self,
        req: request.ScaleRequest,
        start_ts_utc: int,
        end_ts_utc: int,
    ):
        # Given/When
        result = self.instance._is_request_in_range(
            req=req,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        # Then
        assert result

    @pytest.mark.parametrize(
        "req,start_ts_utc,end_ts_utc",
        [
            (_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST.timestamp_utc + 1, None),
            (_TEST_SCALE_REQUEST, None, _TEST_SCALE_REQUEST.timestamp_utc - 1),
        ],
    )
    def test__is_request_in_range_nok(
        self,
        req: request.ScaleRequest,
        start_ts_utc: int,
        end_ts_utc: int,
    ):
        # Given/When
        result = self.instance._is_request_in_range(
            req=req,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        # Then
        assert not result

    @pytest.mark.asyncio
    async def test_read_ok_empty(self):
        # Given/When
        async with self.instance as obj:
            result = await obj.read()
        # Then
        self._check_snapshot(result)
        assert not result.timestamp_to_request

    def _check_snapshot(self, value: event.EventSnapshot) -> None:
        assert isinstance(value, event.EventSnapshot)
        assert value.source == self.instance.source

    @pytest.mark.asyncio
    async def test_read_ok(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        # When
        async with self.instance as obj:
            result = await obj.read(
                start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
                end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            )
        # Then
        self._check_snapshot(result)
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert (
            result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0]
            == _TEST_SCALE_REQUEST
        )

    def _add_content(
        self, is_archive: bool, *values: List[request.ScaleRequest]
    ) -> None:
        if is_archive:
            self.instance.archived.extend(values)
        else:
            self.instance.current.extend(values)

    @pytest.mark.asyncio
    async def test_remove_ok_empty(self):
        # Given/When
        async with self.instance as obj:
            result = await obj.remove()
        # Then
        self._check_snapshot(result)
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok_start_not_in_range(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        # When
        async with self.instance as obj:
            result = await obj.remove(
                start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc + 1
            )
        # Then
        self._check_snapshot(result)
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok_end_not_in_range(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        # When
        async with self.instance as obj:
            result = await obj.remove(
                start_ts_utc=0, end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc - 1
            )
        # Then
        self._check_snapshot(result)
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        # When
        async with self.instance as obj:
            result = await obj.remove(
                start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
                end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            )
        # Then
        self._check_snapshot(result)
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert (
            result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0]
            == _TEST_SCALE_REQUEST
        )
        # Then: read
        async with self.instance as obj:
            request_lst = []
            async for req in obj._read_scale_requests(is_archive=False):
                request_lst.append(req)
            assert not request_lst

    @pytest.mark.asyncio
    async def test_write_ok_empty(self):
        # Given
        value = event.EventSnapshot(source="TEST_SOURCE")
        # When
        async with self.instance as obj:
            await obj.write(value)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=False):
                result.append(req)
            assert not result

    @pytest.mark.asyncio
    async def test_write_ok(self):
        # Given
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        async with self.instance as obj:
            await obj.write(value)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=False):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_overwrite(self):
        # Given
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        async with self.instance as obj:
            await obj.write(value, overwrite_within_range=False)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=False):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_already_exist(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        async with self.instance as obj:
            await obj.write(value, overwrite_within_range=False)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=False):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_overwrite_with_existing(self):
        # Given
        existing_value = common.create_scale_request(
            topic="TEST_TOPIC", resource="TEST_RESOURCE_EXIST", timestamp_utc=13
        )
        new_value = common.create_scale_request(
            topic="TEST_TOPIC", resource="TEST_RESOURCE_NEW", timestamp_utc=13
        )

        self._add_content(False, existing_value)
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[new_value]
        )
        # When
        async with self.instance as obj:
            await obj.write(value, overwrite_within_range=True)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=False):
                result.append(req)
            assert len(result) == 1
            assert result[0] == new_value

    @pytest.mark.asyncio
    async def test_archive_ok_no_file(self):
        # Given/When
        async with self.instance as obj:
            await obj.archive()
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=True):
                result.append(req)
            assert not result

    @pytest.mark.asyncio
    async def test_archive_ok_empty(self):
        # Given/When
        async with self.instance as obj:
            await obj.archive()
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=True):
                result.append(req)
            assert not result

    @pytest.mark.asyncio
    async def test_archive_ok(self):
        # Given
        self._add_content(False, _TEST_SCALE_REQUEST)
        # When
        async with self.instance as obj:
            await obj.archive(
                start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
                end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            )
        # Then: archive
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=True):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST
        # Then: store
        async with self.instance as obj:
            current = []
            async for req in obj._read_scale_requests(is_archive=False):
                current.append(req)
            assert not current

##########################
# START: Multiprocessing #
##########################

########################
# END: Multiprocessing #
########################


class TestJsonLineFileStoreContextManager:  # pylint: disable=too-many-public-methods
    def setup(self):
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            with tempfile.NamedTemporaryFile(delete=True) as tmp_archive:
                self.instance = file.JsonLineFileStoreContextManager(
                    json_line_file=pathlib.Path(tmp_file.name),
                    archive_json_line_file=pathlib.Path(tmp_archive.name),
                )

    def test_properties_ok(self):
        assert self.instance.source == self.instance.json_line_file.name
        assert self.instance.json_line_file != self.instance.archive_json_line_file

    @pytest.mark.parametrize(
        "json_line_file,archive_json_line_file",
        [
            (None, _TEST_JSON_LINE_FILE),
            (str(_TEST_JSON_LINE_FILE), _TEST_JSON_LINE_FILE),
            (_TEST_JSON_LINE_FILE, None),
            (_TEST_JSON_LINE_FILE, str(_TEST_JSON_LINE_FILE)),
        ],
    )
    def test_ctor_nok_type(self, json_line_file: Any, archive_json_line_file: Any):
        with pytest.raises(TypeError):
            file.JsonLineFileStoreContextManager(
                json_line_file=json_line_file,
                archive_json_line_file=archive_json_line_file,
            )

    def test_ctor_nok_same_file(self):
        with pytest.raises(ValueError):
            file.JsonLineFileStoreContextManager(
                json_line_file=_TEST_JSON_LINE_FILE,
                archive_json_line_file=_TEST_JSON_LINE_FILE,
            )

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok_file_does_not_exist(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok_file_empty(self, is_archive: bool):
        # Given
        self._create_file_with_content(is_archive)
        # When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert not result

    def _create_file_with_content(
        self, is_archive: bool, *values: List[request.ScaleRequest]
    ) -> None:
        in_file = (
            self.instance.archive_json_line_file
            if is_archive
            else self.instance.json_line_file
        )
        with open(in_file, "a", encoding=const.ENCODING_UTF8) as out_file:
            if values:
                lines = [f"\n{val.as_json()}" for val in values]
                out_file.writelines(lines)

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok(self, is_archive: bool):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST
        )
        # When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert len(result) == 2
        for val in result:
            assert val == _TEST_SCALE_REQUEST

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__write_scale_requests_ok_empty(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            await obj._write_scale_requests([], is_archive=is_archive)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__write_scale_requests_ok(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            await obj._write_scale_requests(
                [_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST], is_archive=is_archive
            )
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert len(result) == 2
            for req in result:
                assert req == _TEST_SCALE_REQUEST

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_ok_empty(self, is_archive: bool):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST
        )
        # When
        async with self.instance as obj:
            await obj._remove_scale_requests([], is_archive=is_archive)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert len(result) == 2

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_ok(self, is_archive: bool):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST_AFTER
        )
        # When
        async with self.instance as obj:
            await obj._remove_scale_requests(
                [_TEST_SCALE_REQUEST], is_archive=is_archive
            )
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST_AFTER


@pytest.mark.parametrize(
    "dto_class,primary_key",
    [
        (request.ScaleRequest, request.ScaleRequest.timestamp_utc.__name__),
        (event.EventSnapshot, event.EventSnapshot.source.__name__),
    ],
)
def test__sqlite_schema_from_dto_ok(dto_class: Type, primary_key: str):
    # Given/When
    result = file._sqlite_schema_from_dto(dto_class, primary_key)
    # Then
    assert isinstance(result, str)
    # Then: table
    assert result.startswith("CREATE TABLE IF NOT EXISTS")
    assert f"{file._SQLITE_SCHEMA_NAME_TOKEN}_{dto_class.__name__}" in result
    # Then: columns
    col_def_match = re.match(r".*\(([^\)]+)\).*", result)
    assert col_def_match
    columns_def = col_def_match.group(1).split(",")
    attributes = attrs.fields_dict(dto_class)
    assert len(columns_def) == len(attributes)
    for col_def in columns_def:
        col_name = col_def.strip().split(" ")[0]
        assert col_name in attributes
        if col_name == primary_key:
            assert "PRIMARY KEY" in col_def


class TestSQLiteStoreContextManager:
    def setup(self):
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            self.instance = file.SQLiteStoreContextManager(
                sqlite_file=pathlib.Path(tmp_file.name),
            )

    def test_properties_ok(self):
        assert self.instance.source == self.instance.sqlite_file.name

    @pytest.mark.parametrize(
        "sqlite_file",
        [
            None,
            str(_TEST_JSON_LINE_FILE),
        ],
    )
    def test_ctor_nok_type(self, sqlite_file: Any):
        with pytest.raises(TypeError):
            file.SQLiteStoreContextManager(
                sqlite_file=sqlite_file,
            )

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok_file_does_not_exist(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok_file_empty(self, is_archive: bool):
        # Given
        self._create_file_with_content(is_archive)
        # When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert not result

    def _create_file_with_content(
        self, is_archive: bool, *values: List[request.ScaleRequest]
    ) -> None:
        connection = file._sqlite_connection(self.instance.sqlite_file)
        cursor = connection.cursor()
        self.instance._create_tables(cursor)
        insert_stmt = self.instance._insert_stmt_tmpl(is_archive)
        cursor = connection.cursor()
        insert_values = [self.instance._to_row(val) for val in values]
        cursor.executemany(insert_stmt, insert_values)
        connection.commit()
        cursor.close()
        connection.close()

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__read_scale_requests_ok(self, is_archive: bool):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST
        )
        # When
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
        # Then
        assert len(result) == 2
        for val in result:
            assert val == _TEST_SCALE_REQUEST

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__write_scale_requests_ok_empty(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            await obj._write_scale_requests([], is_archive=is_archive)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__write_scale_requests_ok(self, is_archive: bool):
        # Given/When
        async with self.instance as obj:
            await obj._write_scale_requests(
                [_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST], is_archive=is_archive
            )
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert len(result) == 2
            for req in result:
                assert req == _TEST_SCALE_REQUEST

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_nok(self, is_archive: bool):
        # Given
        value = [_TEST_SCALE_REQUEST]
        # When
        with pytest.raises(NotImplementedError):
            async with self.instance as obj:
                await obj._remove_scale_requests(value, is_archive=is_archive)

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_in_range_ok_empty(self, is_archive: bool):
        # Given
        self._create_file_with_content(is_archive)
        # When
        async with self.instance as obj:
            await obj._remove_scale_requests_in_range(is_archive=is_archive)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_in_range_ok_remove_all(
        self, is_archive: bool
    ):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST
        )
        # When
        async with self.instance as obj:
            await obj._remove_scale_requests_in_range(is_archive=is_archive)
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert not result

    @pytest.mark.parametrize("is_archive", [True, False])
    @pytest.mark.asyncio
    async def test__remove_scale_requests_in_range_ok(self, is_archive: bool):
        # Given
        self._create_file_with_content(
            is_archive, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST_AFTER
        )
        # When
        async with self.instance as obj:
            await obj._remove_scale_requests_in_range(
                start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
                end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
                is_archive=is_archive,
            )
        # Then
        async with self.instance as obj:
            result = []
            async for req in obj._read_scale_requests(is_archive=is_archive):
                result.append(req)
            assert len(result) == 1
            assert result[0] == _TEST_SCALE_REQUEST_AFTER
