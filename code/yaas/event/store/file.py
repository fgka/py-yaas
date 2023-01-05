# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for using local files.
"""
# pylint: enable=line-too-long
import abc
import tempfile
from datetime import datetime
import pathlib
import sqlite3
from typing import Generator, List, Optional, Tuple, Type

import aiofiles
import attrs

from yaas.dto import event, request
from yaas.event.store import base
from yaas import const, logger


_LOGGER = logger.get(__name__)

_DEFAULT_LOCK_TIMEOUT_IN_SEC: int = 10


class StoreLockTimeoutError(base.StoreError):
    """
    Encodes timeouts when dealing with file locks.
    """


class BaseFileStoreContextManager(base.StoreContextManager, abc.ABC):
    """
    Basic functionality for file based :py:class:`base.StoreContextManager`
    """

    def __init__(
        self,
        *,
        lock_file: pathlib.Path,
        lock_timeout_in_sec: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._lock = base.FileBasedLockContextManager(
            lock_file=lock_file, lock_timeout_in_sec=lock_timeout_in_sec
        )

    @property
    def lock(self) -> base.FileBasedLockContextManager:
        """
        Lock
        """
        return self._lock

    async def _read(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> event.EventSnapshot:
        request_lst = []
        async for req in self._read_scale_requests_in_range(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
        ):
            if self._is_request_in_range(
                req=req, start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
            ):
                request_lst.append(req)
        return self._snapshot_from_request_lst(request_lst)

    async def _read_scale_requests_in_range(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> Generator[request.ScaleRequest, None, None]:
        async with self._lock:
            async for result in self._read_scale_requests(
                start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
            ):
                if self._is_request_in_range(
                    req=result, start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc
                ):
                    yield result

    @abc.abstractmethod
    async def _read_scale_requests(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> Generator[request.ScaleRequest, None, None]:
        """
        The start and end timestamps are here to help guide the read,
            the requests will be properly filtered out if the result does not comply.
        """

    @staticmethod
    def _is_request_in_range(
        *,
        req: request.ScaleRequest,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> bool:
        return (
            not isinstance(start_ts_utc, int) or req.timestamp_utc >= start_ts_utc
        ) and (not isinstance(end_ts_utc, int) or req.timestamp_utc <= end_ts_utc)

    async def _write(self, value: event.EventSnapshot) -> None:
        start_ts_utc, end_ts_utc = value.range()
        all_existent = set()
        async for req in self._read_scale_requests_in_range(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=False
        ):
            all_existent.add(req)
        to_write = []
        for req_lst in value.timestamp_to_request.values():
            for req in req_lst:
                if req not in all_existent:
                    to_write.append(req)
        written = await self._write_scale_requests_with_lock(to_write, is_archive=False)
        self._validate_all_requests_were_dealt_with(to_write, written, "written")

    @staticmethod
    def _validate_all_requests_were_dealt_with(
        expected: List[request.ScaleRequest],
        result: List[request.ScaleRequest],
        error_msg_verb_in_past_tense: str,
    ) -> None:
        if expected is None:
            expected = set()
        if result is None:
            result = set()
        expected_minus_result = set(expected) - set(result)
        if expected_minus_result:
            raise base.StoreError(
                f"Not all requests where {error_msg_verb_in_past_tense}. "
                f"Not {error_msg_verb_in_past_tense}: {expected_minus_result}. "
                f"From: {expected}"
            )

    async def _write_scale_requests_with_lock(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        async with self._lock:
            result = await self._write_scale_requests(value, is_archive=is_archive)
        return result

    @abc.abstractmethod
    async def _write_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        """
        Persists all :py:class:`request.ScaleRequest` into current or archive file.
        """

    async def _remove(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        removed = await self._remove_scale_requests_in_range(
            start_ts_utc, end_ts_utc, is_archive=False
        )
        return self._snapshot_from_request_lst(removed)

    async def _remove_scale_requests_in_range(
        self,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        *,
        is_archive: Optional[bool] = False,
    ) -> List[request.ScaleRequest]:
        to_remove = []
        async for req in self._read_scale_requests_in_range(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
        ):
            to_remove.append(req)
        async with self._lock:
            removed = await self._remove_scale_requests(
                to_remove, is_archive=is_archive
            )
        self._validate_all_requests_were_dealt_with(to_remove, removed, "removed")
        return removed

    @abc.abstractmethod
    async def _remove_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        """
        Removes all :py:class:`request.ScaleRequest` from current or archive file.
        """

    async def _archive(
        self, *, start_ts_utc: Optional[int] = None, end_ts_utc: Optional[int] = None
    ) -> event.EventSnapshot:
        to_archive = await self._remove_scale_requests_in_range(
            start_ts_utc, end_ts_utc, is_archive=False
        )
        try:
            archived = await self._write_scale_requests_with_lock(
                to_archive, is_archive=True
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Could not archive snapshot <%s>. Error: %s",
                to_archive,
                err,
            )
            try:
                recovered = await self._write_scale_requests_with_lock(
                    to_archive, is_archive=False
                )
            except Exception as err_roll_back:
                raise RuntimeError(
                    f"[DATA LOSS] Removed snapshot <{to_archive} for store, "
                    "failed to archive (see logs), and failed to reinsert. "
                    f"Archive error: {err}. "
                    f"Error: {err_roll_back}"
                ) from err_roll_back
            self._validate_all_requests_were_dealt_with(
                to_archive, recovered, "rolled back"
            )
        self._validate_all_requests_were_dealt_with(to_archive, archived, "archived")
        return self._snapshot_from_request_lst(archived)


class JsonLineFileStoreContextManager(BaseFileStoreContextManager):
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
        archive_json_line_file: Optional[pathlib.Path] = None,
        **kwargs,
    ):
        if not isinstance(json_line_file, pathlib.Path):
            raise TypeError(
                f"JSON line file must be a {pathlib.Path.__name__}. "
                f"Got: <{json_line_file}>({type(json_line_file)})"
            )
        if archive_json_line_file is None:
            archive_json_line_file = json_line_file.with_suffix(".archive")
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
        super().__init__(
            source=self._json_line_file.name,
            lock_file=self._json_line_file.with_suffix(".lock"),
            **kwargs,
        )
        self._archive_json_line_file = archive_json_line_file

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

    async def _read_scale_requests(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> Generator[request.ScaleRequest, None, None]:
        path = self._json_line_file if not is_archive else self._archive_json_line_file
        if path.exists():
            async with aiofiles.open(
                path, "r", encoding=const.ENCODING_UTF8
            ) as in_file:
                async for line in in_file:
                    line = line.strip()
                    if line:
                        yield request.ScaleRequest.from_json(line)

    async def _write_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        path = self._json_line_file if not is_archive else self._archive_json_line_file
        async with aiofiles.open(path, "a", encoding=const.ENCODING_UTF8) as out_file:
            await out_file.writelines([f"\n{val.as_json()}" for val in value])
        return value

    async def _remove_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        # pylint: disable=consider-using-with
        tmp_file = pathlib.Path(tempfile.NamedTemporaryFile().name)
        # pylint: enable=consider-using-with
        async with aiofiles.open(
            tmp_file, "w", encoding=const.ENCODING_UTF8
        ) as out_file:
            async for req in self._read_scale_requests(is_archive=is_archive):
                if req not in value:
                    await out_file.write(f"\n{req.as_json()}")
        json_file = self._archive_json_line_file if is_archive else self._json_line_file
        try:
            tmp_file.rename(json_file)
        except Exception as err:
            raise RuntimeError(
                f"[DATA LOSS] Could not move content from {tmp_file} into {json_file}. "
                f"Error: {err}"
            ) from err
        return value


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


class SQLiteStoreContextManager(BaseFileStoreContextManager):
    """
    Uses a `SQLite`_ database to back the store.

    .. _SQLite: https://www.sqlite.org/
    """

    def __init__(
        self,
        *,
        sqlite_file: pathlib.Path,
        **kwargs,
    ):
        if not isinstance(sqlite_file, pathlib.Path):
            raise TypeError(
                f"SQLite file must be a {pathlib.Path.__name__}. "
                f"Got: <{sqlite_file}>({type(sqlite_file)})"
            )
        sqlite_file = sqlite_file.absolute()
        self._sqlite_file = sqlite_file
        if "source" not in kwargs:
            kwargs["source"] = self._sqlite_file.name
        super().__init__(lock_file=self._sqlite_file.with_suffix(".lock"), **kwargs)
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
        create_stmt = _sqlite_schema_from_dto(request.ScaleRequest)
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

    async def _read_scale_requests(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> Generator[request.ScaleRequest, None, None]:
        cursor = self._create_cursor()
        cursor.execute(
            self._select_stmt_by_timestamp_utc(start_ts_utc, end_ts_utc, is_archive)
        )
        for row in cursor.fetchall():
            yield self._dto_from_row(row)
        cursor.close()

    @staticmethod
    def _select_stmt_by_timestamp_utc(
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> str:
        # table name
        table_name = SQLiteStoreContextManager._table_name(is_archive)
        # where clause
        where_clause = SQLiteStoreContextManager._ts_where_clause(
            start_ts_utc, end_ts_utc
        )
        return f"SELECT * FROM {table_name} {where_clause};"

    @staticmethod
    def _ts_where_clause(
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
    ) -> str:
        result = ""
        if start_ts_utc is not None or end_ts_utc is not None:
            result = f"WHERE {request.ScaleRequest.timestamp_utc.__name__}"
            if start_ts_utc is not None and end_ts_utc is not None:
                result = f"{result} BETWEEN {start_ts_utc} AND {end_ts_utc}"
            elif start_ts_utc is not None:
                result = f"{result} >= {start_ts_utc}"
            elif end_ts_utc is not None:
                result = f"{result} <= {end_ts_utc}"
        return result

    @staticmethod
    def _table_name(is_archive: Optional[bool] = False) -> str:
        return (
            SQLiteStoreContextManager._archive_table_name()
            if is_archive
            else SQLiteStoreContextManager._current_table_name()
        )

    @staticmethod
    def _dto_from_row(row: Tuple) -> request.ScaleRequest:
        kwargs = dict(zip(SQLiteStoreContextManager._column_names(), row))
        return request.ScaleRequest.from_dict(kwargs)

    @staticmethod
    def _column_names() -> List[str]:
        return sorted([field.name for field in attrs.fields(request.ScaleRequest)])

    async def _write_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> List[request.ScaleRequest]:
        insert_stmt = self._insert_stmt_tmpl(is_archive)
        cursor = self._create_cursor()
        cursor.executemany(insert_stmt, [self._to_row(val) for val in value])
        cursor.close()
        return value

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
        # pylint: disable=consider-using-generator
        return tuple([value_dict.get(key) for key in sorted(value_dict.keys())])

    async def _remove_scale_requests_in_range(
        self,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        *,
        is_archive: Optional[bool] = False,
    ) -> List[request.ScaleRequest]:
        result = []
        async for req in self._read_scale_requests_in_range(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
        ):
            result.append(req)
        await self._remove_scale_requests_in_range_from_db(
            start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc, is_archive=is_archive
        )
        return result

    async def _remove_scale_requests_in_range_from_db(
        self,
        *,
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> None:
        delete_stmt = self._delete_stmt_by_timestamp_utc(
            start_ts_utc, end_ts_utc, is_archive
        )
        cursor = self._create_cursor()
        cursor.execute(delete_stmt)
        cursor.close()

    @staticmethod
    def _delete_stmt_by_timestamp_utc(
        start_ts_utc: Optional[int] = None,
        end_ts_utc: Optional[int] = None,
        is_archive: Optional[bool] = False,
    ) -> str:
        # table name
        table_name = SQLiteStoreContextManager._table_name(is_archive)
        # where clause
        where_clause = SQLiteStoreContextManager._ts_where_clause(
            start_ts_utc, end_ts_utc
        )
        return f"DELETE FROM {table_name} {where_clause};"

    async def _remove_scale_requests(
        self, value: List[request.ScaleRequest], *, is_archive: Optional[bool] = False
    ) -> None:
        raise NotImplementedError(
            f"This method {SQLiteStoreContextManager._remove_scale_requests.__name__} "
            "should be called."
        )


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
