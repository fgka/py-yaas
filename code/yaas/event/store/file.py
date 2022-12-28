# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for using local files.
"""
# pylint: enable=line-too-long
from datetime import datetime
import pathlib
import sqlite3
import threading
from typing import List, Optional, Tuple, Type

import aiofiles
import attrs

from yaas.dto import event, request
from yaas.event.store import base
from yaas import const, logger


_LOGGER = logger.get(__name__)


class JsonLineFileStoreContextManager(base.StoreContextManager):
    """
    A very inefficient version of a text file store,
    using the `JSON Lines`_ format, where each line is a JSON entry representing a scale request.
    `JSON Lines`_ files.

    Ways it can be improved:
    * Compress the files;
    * Use Pickle instead;
    * Keep it sorted by timestamp and use binary search to find where to insert/find data.

    .. _JSON Lines: https://jsonlines.org/
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


def _sqlite_column_type_from_attr(attribute: attrs.Attribute) -> str:
    """
    Based on https://www.sqlite.org/datatype3.html
    """
    result = "BLOB"
    if attribute.type == str:
        result = "TEXT"
    elif attribute.type == int:
        result = "INTEGER"
    elif attribute.type == float:
        result = "REAL"
    elif attribute.type in (bool, datetime):
        result = "NUMERIC"
    return result


def _sqlite_column_definition_from_attr(
    attribute: attrs.Attribute, is_primary_key: Optional[bool] = False
) -> str:
    col_type = _sqlite_column_type_from_attr(attribute)
    result = f"{attribute.name} {col_type}"
    if is_primary_key:
        result = f"{result} PRIMARY KEY"
    return result


_SQLITE_SCHEMA_NAME_TOKEN: str = "@@SCHEMA_NAME@@"


def _sqlite_schema_from_dto(dto_class: Type, primary_key: Optional[str] = None) -> str:
    fields_dict = attrs.fields_dict(dto_class)
    column_def_list = []
    for field in sorted(fields_dict.keys()):
        column_def_list.append(
            _sqlite_column_definition_from_attr(
                fields_dict.get(field), field == primary_key
            )
        )
    columns_stmt = ", ".join(column_def_list)
    return (
        f"CREATE TABLE IF NOT EXISTS {_SQLITE_SCHEMA_NAME_TOKEN}_{dto_class.__name__} "
        f"({columns_stmt});"
    )


_SQLITE_TABLE_SCHEMA_TMPL: str = _sqlite_schema_from_dto(request.ScaleRequest)
_SQLITE_CURRENT_SCHEMA_NAME: str = "current"
_SQLITE_ARCHIVE_SCHEMA_NAME: str = "archive"


class SQLiteStoreContextManager(base.StoreContextManager):
    """
    Uses a `SQLite`_ database to back the store.

    .. _SQLite: https://www.sqlite.org/
    """

    def __init__(
        self,
        *,
        sqlite_file: pathlib.Path,
        source_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not isinstance(sqlite_file, pathlib.Path):
            raise TypeError(
                f"SQLite file must be a {pathlib.Path.__name__}. "
                f"Got: <{sqlite_file}>({type(sqlite_file)})"
            )
        sqlite_file = sqlite_file.absolute()
        self._sqlite_file = sqlite_file
        if not isinstance(source_name, str):
            source_name = sqlite_file.name
        self._source_name = source_name
        self._connection = None

    @property
    def sqlite_file(self) -> pathlib.Path:
        """
        Which is the SQLite file being used.
        """
        return self._sqlite_file

    async def _open(self) -> None:
        self._connection = _sqlite_connection(self._sqlite_file)
        self._create_tables(self._create_cursor())

    def _create_cursor(self) -> sqlite3.Cursor:
        if self._connection is None:
            raise RuntimeError(
                "SQLite connection does not exists. "
                "Most likely the you didn't use open the class using 'async with' statement."
            )
        return self._connection.cursor()

    @staticmethod
    def _create_tables(cursor: sqlite3.Cursor) -> None:
        # template
        create_stmt = _sqlite_schema_from_dto(
            request.ScaleRequest, request.ScaleRequest.timestamp_utc.__name__
        )
        # current
        cursor.execute(
            create_stmt.replace(_SQLITE_SCHEMA_NAME_TOKEN, _SQLITE_CURRENT_SCHEMA_NAME)
        )
        # archive
        cursor.execute(
            create_stmt.replace(_SQLITE_SCHEMA_NAME_TOKEN, _SQLITE_ARCHIVE_SCHEMA_NAME)
        )
        # done
        cursor.close()

    @staticmethod
    def _current_table_name() -> str:
        return f"{_SQLITE_CURRENT_SCHEMA_NAME}_{request.ScaleRequest.__name__}"

    @staticmethod
    def _archive_table_name() -> str:
        return f"{_SQLITE_ARCHIVE_SCHEMA_NAME}_{request.ScaleRequest.__name__}"

    async def _close(self) -> None:
        self._connection.commit()
        self._connection.close()
        self._connection = None

    async def _read(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        cursor = self._create_cursor()
        cursor.execute(
            self._select_stmt_by_timestamp_utc(start_ts_utc, end_ts_utc, False)
        )
        request_lst = []
        for row in cursor.fetchall():
            request_lst.append(self._dto_from_row(row))
        return self._snapshot_from_request_lst(request_lst)

    @staticmethod
    def _select_stmt_by_timestamp_utc(
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> str:
        # table name
        table_name = SQLiteStoreContextManager._table_name(is_archive)
        # where clause
        where_clause = ""
        if start_ts_utc is not None or end_ts_utc is not None:
            where_clause = f"WHERE {request.ScaleRequest.timestamp_utc.__name__}"
            if start_ts_utc is not None and end_ts_utc is not None:
                where_clause = f"{where_clause} BETWEEN {start_ts_utc} AND {end_ts_utc}"
            elif start_ts_utc is not None:
                where_clause = f"{where_clause} >= {start_ts_utc}"
            elif end_ts_utc is not None:
                where_clause = f"{where_clause} <= {end_ts_utc}"
        return f"SELECT * FROM {table_name} {where_clause};"

    @staticmethod
    def _table_name(is_archive: Optional[bool] = False) -> str:
        return (
            SQLiteStoreContextManager._archive_table_name()
            if is_archive
            else SQLiteStoreContextManager._current_table_name()
        )

    @staticmethod
    def _dto_from_row(row: Tuple) -> request.ScaleRequest:
        kwargs = {
            key: val for key, val in zip(SQLiteStoreContextManager._column_names(), row)
        }
        return request.ScaleRequest.from_dict(kwargs)

    @staticmethod
    def _column_names() -> List[str]:
        return sorted([field.name for field in attrs.fields(request.ScaleRequest)])

    def _snapshot_from_request_lst(
        self, request_lst: Optional[List[request.ScaleRequest]] = None
    ) -> event.EventSnapshot:
        return event.EventSnapshot.from_list_requests(
            source=self._source_name,
            request_lst=request_lst,
        )

    async def _write(self, value: event.EventSnapshot) -> None:
        pass

    @staticmethod
    def _insert_stmt_tmpl(is_archive: Optional[bool] = False) -> str:
        table_name = SQLiteStoreContextManager._table_name(is_archive)
        values_place_holders = ", ".join(
            ["?"] * len(attrs.fields(request.ScaleRequest))
        )
        return f"INSERT INTO {table_name} VALUES({values_place_holders})"

    @staticmethod
    def _to_row(value: request.ScaleRequest) -> tuple:
        value_dict = value.as_dict()
        return tuple([value_dict.get(key) for key in sorted(value_dict.keys())])

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        pass

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> None:
        pass


def _sqlite_connection(database: Optional[pathlib.Path] = None) -> sqlite3.Connection:
    """
    Do not cache the connection using external libraries as cachetools due to thread-safety.
    Sources:
    * https://ricardoanderegg.com/posts/python-sqlite-thread-safety/#conclusion
    * https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety
    * https://www.sqlite.org/threadsafe.html
    """
    # validate input
    if database is None:
        database = ":memory:"
    elif not isinstance(database, pathlib.Path):
        raise TypeError(
            f"The database argument can be None of {pathlib.Path.__name__}. "
            f"Got: <{database}>({type(database)})"
        )
    # logic
    if sqlite3.threadsafety == 0:
        _LOGGER.warning(
            "SQLite3 is built in single-thread mode (0). "
            "Consider using a different build that is, at least, multi-thread (1) enabled. "
            "More information at: https://www.sqlite.org/threadsafe.html"
        )
    check_same_thread = sqlite3.threadsafety != 3
    return sqlite3.connect(database, check_same_thread=check_same_thread)
