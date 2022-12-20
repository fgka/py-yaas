# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for Google Calendar as event source.
"""
import pathlib
import threading
from typing import List, Optional

import aiofiles

from yaas.dto import event, request
from yaas.event.store import base
from yaas import const, logger

_LOGGER = logger.get(__name__)


class JsonLineFileStore(base.Store):
    """
    A very inefficient version of a text file store,
    where each line is JSON entry representing a scale request.
    """

    def __init__(
        self,
        *,
        json_line_file: pathlib.Path,
        archive_json_line_file: pathlib.Path,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(json_line_file, pathlib.Path):
            raise TypeError(
                f"JSON line file must be a {pathlib.Path.__name__}. "
                f"Got: <{json_line_file}>({type(json_line_file)})"
            )
        if not isinstance(archive_json_line_file, pathlib.Path):
            raise TypeError(
                f"Archive JSON line file must be a {pathlib.Path.__name__}. "
                f"Got: <{archive_json_line_file}>({type(archive_json_line_file)})"
            )
        json_line_file = json_line_file.absolute()
        archive_json_line_file = archive_json_line_file.absolute()
        if json_line_file == archive_json_line_file:
            raise ValueError(
                f"JSON line file <{json_line_file}> "
                f"can *NOT* be the same as <{archive_json_line_file}>"
            )
        self._json_line_file = json_line_file
        self._archive_json_line_file = archive_json_line_file
        # required to make it thread-safe
        self._file_lock = threading.Lock()

    @property
    def json_line_file(self) -> pathlib.Path:
        """
        Where is the data being stored.
        """
        return self._json_line_file

    @property
    def archive_json_line_file(self) -> pathlib.Path:
        """
        Where to archive data.
        """
        return self._archive_json_line_file

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        request_lst = None
        with self._file_lock:
            async with aiofiles.open(
                self._json_line_file, "r", encoding=const.ENCODING_UTF8
            ) as in_file:
                async for line in in_file:
                    if line.strip():
                        req = request.ScaleRequest.from_json(line.strip())
                        request_lst = self._populate_timestamp_to_request(
                            request_lst=request_lst,
                            req=req,
                            start_ts_utc=start_ts_utc,
                            end_ts_utc=end_ts_utc,
                        )
        return self._snapshot_from_request_lst(request_lst)

    def _snapshot_from_request_lst(
        self, request_lst: Optional[List[request.ScaleRequest]] = None
    ) -> event.EventSnapshot:
        return event.EventSnapshot.from_list_requests(
            source=self._json_line_file.name,
            request_lst=request_lst,
        )

    @staticmethod
    def _populate_timestamp_to_request(
        *,
        request_lst: List[request.ScaleRequest],
        req: request.ScaleRequest,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> List[request.ScaleRequest]:
        to_add = (
            not isinstance(start_ts_utc, int) or req.timestamp_utc >= start_ts_utc
        ) and (not isinstance(end_ts_utc, int) or req.timestamp_utc <= end_ts_utc)
        if request_lst is None:
            request_lst = []
        if to_add:
            request_lst.append(req)
        return request_lst

    async def _write(self, value: event.EventSnapshot) -> None:
        await self._write_only_new(value, is_archive=False)

    async def _write_only_new(
        self, value: event.EventSnapshot, *, is_archive: Optional[bool] = False
    ) -> None:
        all_existent = set(await self._read_all(is_archive=is_archive))
        path = self._json_line_file if not is_archive else self._archive_json_line_file
        with self._file_lock:
            async with aiofiles.open(
                path, "a", encoding=const.ENCODING_UTF8
            ) as out_file:
                for req_lst in value.timestamp_to_request.values():
                    # only add non-existent
                    await out_file.writelines(
                        [
                            f"\n{val.as_json()}"
                            for val in req_lst
                            if val not in all_existent
                        ]
                    )

    async def _read_all(
        self, *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        result = []
        path = self._json_line_file if not is_archive else self._archive_json_line_file
        if path.exists():
            with self._file_lock:
                async with aiofiles.open(
                    path, "r", encoding=const.ENCODING_UTF8
                ) as in_file:
                    result = [
                        request.ScaleRequest.from_json(line.strip())
                        async for line in in_file
                        if line.strip()
                    ]
        return result

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        request_lst = []
        all_request_lst = await self._read_all()
        with self._file_lock:
            async with aiofiles.open(
                self._json_line_file, "w", encoding=const.ENCODING_UTF8
            ) as out_file:
                for req in all_request_lst:
                    if start_ts_utc <= req.timestamp_utc <= end_ts_utc:
                        request_lst.append(req)
                    else:
                        await out_file.write(f"\n{req.as_json()}")
        return self._snapshot_from_request_lst(request_lst)

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        to_archive = await self.remove(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
        try:
            await self._write_only_new(to_archive, is_archive=True)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Could not archive into <%s> snapshot <%s>. Error: %s",
                self._archive_json_line_file,
                to_archive,
                err,
            )
            try:
                await self._write_only_new(to_archive, is_archive=False)
            except Exception as err_roll_back:
                raise RuntimeError(
                    f"[DATA LOSS] Removed snapshot <{to_archive} for store, "
                    f"failed to archive <{self._archive_json_line_file}>(see logs), "
                    f"and failed to reinsert into <{self._json_line_file}>. "
                    f"Archive error: {err}. "
                    f"Error: {err_roll_back}"
                ) from err_roll_back
