# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pathlib
import tempfile
from typing import Any, List

import pytest

from yaas import const
from yaas.dto import event, request
from yaas.event.store import base, file

_TEST_CALENDAR_ID: str = "TEST_CALENDAR_ID"
# pylint: disable=consider-using-with
_TEST_JSON_LINE_FILE: pathlib.Path = pathlib.Path(tempfile.NamedTemporaryFile().name)
# pylint: enable=consider-using-with
_TEST_SCALE_REQUEST: request.ScaleRequest = request.ScaleRequest(
    topic="TEST_TOPIC", resource="TEST_RESOURCE", timestamp_utc=13
)


class TestJsonLineFileStore:  # pylint: disable=too-many-public-methods
    def setup(self):
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            with tempfile.NamedTemporaryFile(delete=True) as tmp_archive:
                self.obj = file.JsonLineFileStore(
                    json_line_file=pathlib.Path(tmp_file.name),
                    archive_json_line_file=pathlib.Path(tmp_archive.name),
                )

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
            file.JsonLineFileStore(
                json_line_file=json_line_file,
                archive_json_line_file=archive_json_line_file,
            )

    def test_ctor_nok_same_file(self):
        with pytest.raises(ValueError):
            file.JsonLineFileStore(
                json_line_file=_TEST_JSON_LINE_FILE,
                archive_json_line_file=_TEST_JSON_LINE_FILE,
            )

    @pytest.mark.asyncio
    async def test_read_nok_file_does_not_exist(self):
        with pytest.raises(base.StoreError):
            await self.obj.read()

    @pytest.mark.asyncio
    async def test_read_ok_file_empty(self):
        # Given
        self._create_file_with_content()
        # When
        result = await self.obj.read()
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert result.source == self.obj.json_line_file.name
        assert not result.timestamp_to_request

    def _create_file_with_content(self, *values: List[request.ScaleRequest]) -> None:
        with open(
            self.obj.json_line_file, "a", encoding=const.ENCODING_UTF8
        ) as out_file:
            if values:
                lines = [f"\n{val.as_json()}" for val in values]
                out_file.writelines(lines)

    @pytest.mark.asyncio
    async def test_read_ok(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        # When
        result = await self.obj.read(
            start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
        )
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert result.source == self.obj.json_line_file.name
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert (
            result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0]
            == _TEST_SCALE_REQUEST
        )

    @pytest.mark.parametrize(
        "request_lst,req,start_ts_utc,end_ts_utc",
        [
            (None, _TEST_SCALE_REQUEST, None, None),
            ([], _TEST_SCALE_REQUEST, None, None),
            (None, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST.timestamp_utc, None),
            (None, _TEST_SCALE_REQUEST, None, _TEST_SCALE_REQUEST.timestamp_utc),
            (
                None,
                _TEST_SCALE_REQUEST,
                _TEST_SCALE_REQUEST.timestamp_utc,
                _TEST_SCALE_REQUEST.timestamp_utc,
            ),
        ],
    )
    def test__populate_timestamp_to_request_ok(
        self,
        request_lst: List[request.ScaleRequest],
        req: request.ScaleRequest,
        start_ts_utc: int,
        end_ts_utc: int,
    ):
        # Given/When
        result = self.obj._populate_timestamp_to_request(
            request_lst=request_lst,
            req=req,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == req

    @pytest.mark.parametrize(
        "request_lst,req,start_ts_utc,end_ts_utc",
        [
            (None, _TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST.timestamp_utc + 1, None),
            (None, _TEST_SCALE_REQUEST, None, _TEST_SCALE_REQUEST.timestamp_utc - 1),
        ],
    )
    def test__populate_timestamp_to_request_nok(
        self,
        request_lst: List[request.ScaleRequest],
        req: request.ScaleRequest,
        start_ts_utc: int,
        end_ts_utc: int,
    ):
        # Given/When
        result = self.obj._populate_timestamp_to_request(
            request_lst=request_lst,
            req=req,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        # Then
        assert isinstance(result, list)
        assert not result

    @pytest.mark.asyncio
    async def test__read_all_ok_file_does_not_exist(self):
        # Given/When
        result = await self.obj._read_all()
        # Then
        assert isinstance(result, list)
        assert not result

    @pytest.mark.asyncio
    async def test__read_all_ok_file_empty(self):
        # Given
        self._create_file_with_content()
        # When
        result = await self.obj._read_all()
        # Then
        assert isinstance(result, list)
        assert not result

    @pytest.mark.asyncio
    async def test__read_all_ok(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST)
        # When
        result = await self.obj._read_all()
        # Then
        assert len(result) == 2
        for val in result:
            assert val == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_remove_ok_empty(self):
        # Given/When
        result = await self.obj.remove()
        # Then
        assert result
        assert result.source == self.obj.json_line_file.name
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok_start_not_in_range(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        # When
        result = await self.obj.remove(
            start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc + 1
        )
        # Then
        assert result
        assert result.source == self.obj.json_line_file.name
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok_end_not_in_range(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        # When
        result = await self.obj.remove(
            start_ts_utc=0, end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc - 1
        )
        # Then
        assert result
        assert result.source == self.obj.json_line_file.name
        assert not result.timestamp_to_request

    @pytest.mark.asyncio
    async def test_remove_ok(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        # When
        result = await self.obj.remove(
            start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
        )
        # Then
        assert result
        assert result.source == self.obj.json_line_file.name
        assert _TEST_SCALE_REQUEST.timestamp_utc in result.timestamp_to_request
        assert (
            result.timestamp_to_request.get(_TEST_SCALE_REQUEST.timestamp_utc)[0]
            == _TEST_SCALE_REQUEST
        )
        # Then: read
        request_lst = await self.obj._read_all()
        assert not request_lst

    @pytest.mark.asyncio
    async def test_write_ok_empty(self):
        # Given
        value = event.EventSnapshot(source="TEST_SOURCE")
        # When
        await self.obj.write(value)
        # Then
        result = await self.obj._read_all()
        assert not result

    @pytest.mark.asyncio
    async def test_write_ok(self):
        # Given
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        await self.obj.write(value)
        # Then
        result = await self.obj._read_all()
        assert len(result) == 1
        assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_overwrite(self):
        # Given
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        await self.obj.write(value, overwrite_within_range=False)
        # Then
        result = await self.obj._read_all()
        assert len(result) == 1
        assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_already_exist(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[_TEST_SCALE_REQUEST]
        )
        # When
        await self.obj.write(value, overwrite_within_range=False)
        # Then
        result = await self.obj._read_all()
        assert len(result) == 1
        assert result[0] == _TEST_SCALE_REQUEST

    @pytest.mark.asyncio
    async def test_write_ok_overwrite_with_existing(self):
        # Given
        existing_value = request.ScaleRequest(
            topic="TEST_TOPIC", resource="TEST_RESOURCE_EXIST", timestamp_utc=13
        )
        new_value = request.ScaleRequest(
            topic="TEST_TOPIC", resource="TEST_RESOURCE_NEW", timestamp_utc=13
        )

        self._create_file_with_content(existing_value)
        value = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[new_value]
        )
        # When
        await self.obj.write(value, overwrite_within_range=True)
        # Then
        result = await self.obj._read_all()
        assert len(result) == 1
        assert result[0] == new_value

    @pytest.mark.asyncio
    async def test_archive_ok_no_file(self):
        # Given/When
        await self.obj.archive()
        # Then
        assert not await self.obj._read_all(is_archive=True)

    @pytest.mark.asyncio
    async def test_archive_ok_empty(self):
        # Given
        self._create_file_with_content()
        # When
        await self.obj.archive()
        # Then
        assert not await self.obj._read_all(is_archive=True)

    @pytest.mark.asyncio
    async def test_archive_ok(self):
        # Given
        self._create_file_with_content(_TEST_SCALE_REQUEST)
        # When
        await self.obj.archive(
            start_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
            end_ts_utc=_TEST_SCALE_REQUEST.timestamp_utc,
        )
        # Then: archive
        result = await self.obj._read_all(is_archive=True)
        assert len(result) == 1
        assert result[0] == _TEST_SCALE_REQUEST
        # Then: store
        current = await self.obj._read_all(is_archive=False)
        assert not current
