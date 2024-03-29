# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,protected-access,attribute-defined-outside-init
# type: ignore
import pathlib
from typing import Optional, Union

import pytest

from yaas_caching import gcs

_TEST_BUCKET_NAME: str = "test_bucket"
_TEST_DB_OBJECT_PATH: str = "path/to/sql.db"


class TestGcsObjectStoreContextManager:
    def setup_method(self):
        self.instance = gcs.GcsObjectStoreContextManager(
            bucket_name=_TEST_BUCKET_NAME, db_object_path=_TEST_DB_OBJECT_PATH
        )

    def test_properties_ok(self):
        assert self.instance.source == f"gs://{_TEST_BUCKET_NAME}/{_TEST_DB_OBJECT_PATH}"
        assert self.instance.source == self.instance.gcs_uri
        assert self.instance.bucket_name == _TEST_BUCKET_NAME
        assert self.instance.db_object_path == _TEST_DB_OBJECT_PATH
        assert self.instance.source != self.instance.sqlite_file

    @pytest.mark.parametrize("has_changed", [True, False])
    @pytest.mark.asyncio
    async def test_with_stmt_ok(self, monkeypatch, has_changed: bool):
        called = {}

        def mocked_read_object(  # pylint: disable=unused-argument
            *,
            bucket_name: str,
            object_path: str,
            project: Optional[str] = None,
            filename: Optional[pathlib.Path] = None,
            warn_read_failure: Optional[bool] = True,
        ) -> Union[bytes, bool]:
            nonlocal called
            assert bucket_name == self.instance.bucket_name
            assert object_path == self.instance.db_object_path
            called[gcs.gcs.read_object.__name__] = filename
            return True

        def mocked_write_object(  # pylint: disable=unused-argument
            *,
            bucket_name: str,
            object_path: str,
            content_source: Union[bytes, pathlib.Path],
            project: Optional[str] = None,
        ) -> None:
            nonlocal called
            assert bucket_name == self.instance.bucket_name
            assert object_path == self.instance.db_object_path
            called[gcs.gcs.write_object.__name__] = content_source

        monkeypatch.setattr(gcs.gcs, gcs.gcs.read_object.__name__, mocked_read_object)
        monkeypatch.setattr(gcs.gcs, gcs.gcs.write_object.__name__, mocked_write_object)
        self.instance._has_changed = has_changed
        # When
        async with self.instance:
            pass
        # Then
        assert called.get(gcs.gcs.read_object.__name__) == self.instance.sqlite_file
        if has_changed:
            assert called.get(gcs.gcs.write_object.__name__) == self.instance.sqlite_file
        else:
            assert called.get(gcs.gcs.write_object.__name__) is None
