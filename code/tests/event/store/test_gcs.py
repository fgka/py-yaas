# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pathlib
from typing import Optional, Union

import pytest

from yaas.event.store import gcs

_TEST_BUCKET_NAME: str = "test_bucket"
_TEST_DB_OBJECT_PATH: str = "path/to/sql.db"


class TestGcsObjectStoreContextManager:
    def setup(self):
        self.instance = gcs.GcsObjectStoreContextManager(
            bucket_name=_TEST_BUCKET_NAME, db_object_path=_TEST_DB_OBJECT_PATH
        )

    def test_properties_ok(self):
        assert (
            self.instance.source == f"gs://{_TEST_BUCKET_NAME}/{_TEST_DB_OBJECT_PATH}"
        )
        assert self.instance.source == self.instance.gcs_uri
        assert self.instance.bucket_name == _TEST_BUCKET_NAME
        assert self.instance.db_object_path == _TEST_DB_OBJECT_PATH
        assert self.instance.source != self.instance.sqlite_file

    @pytest.mark.asyncio
    async def test_with_stmt_ok(self, monkeypatch):

        called = {}

        def mocked_read_object(  # pylint: disable=unused-argument
            *,
            bucket_name: str,
            object_path: str,
            filename: Optional[pathlib.Path] = None,
            warn_read_failure: Optional[bool] = True,
        ) -> Optional[bytes]:
            nonlocal called
            assert bucket_name == self.instance.bucket_name
            assert object_path == self.instance.db_object_path
            called[gcs.gcs.read_object.__name__] = filename

        def mocked_write_object(
            *, bucket_name: str, object_path: str, content: Union[bytes, pathlib.Path]
        ) -> None:
            nonlocal called
            assert bucket_name == self.instance.bucket_name
            assert object_path == self.instance.db_object_path
            called[gcs.gcs.write_object.__name__] = content

        monkeypatch.setattr(gcs.gcs, gcs.gcs.read_object.__name__, mocked_read_object)
        monkeypatch.setattr(gcs.gcs, gcs.gcs.write_object.__name__, mocked_write_object)

        # When
        async with self.instance:
            pass
        # Then
        assert called.get(gcs.gcs.read_object.__name__) == self.instance.sqlite_file
        assert called.get(gcs.gcs.write_object.__name__) == self.instance.sqlite_file
