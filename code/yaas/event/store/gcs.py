# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Store interface for `Google Cloud Storage`_.

.. _Google Cloud Storage: https://cloud.google.com/storage
"""
# pylint: enable=line-too-long
import pathlib
import tempfile

from yaas import logger
from yaas.event.store import file
from yaas.gcp import gcs

_LOGGER = logger.get(__name__)


class GcsObjectStoreContextManager(file.SQLiteStoreContextManager):
    """
    This implementation is very simple remote storage for SQLite databases.
    It will, at opening, retrieve the remote object into the local file
        and, at closing, write the object with the local file content.
    """

    def __init__(
        self,
        *,
        bucket_name: str,
        db_object_path: str,
        **kwargs,
    ):
        self._bucket_name = gcs.validate_and_clean_bucket_name(bucket_name)
        self._db_object_path = gcs.validate_and_clean_object_path(db_object_path)
        super().__init__(
            sqlite_file=self._temporary_file(), source=self.gcs_uri, **kwargs
        )

    @staticmethod
    def _temporary_file() -> pathlib.Path:
        return pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)

    @property
    def bucket_name(self) -> str:
        """
        Remote GCS bucket name
        """
        return self._bucket_name

    @property
    def db_object_path(self) -> str:
        """
        Remote GCS DB object path
        """
        return self._db_object_path

    @property
    def gcs_uri(self) -> str:
        """
        GCS URI
        """
        return f"gs://{self._bucket_name}/{self._db_object_path}"

    async def _open(self) -> None:
        gcs.read_object(
            bucket_name=self._bucket_name,
            object_path=self._db_object_path,
            filename=self.sqlite_file,
        )
        await super()._open()

    async def _close(self) -> None:
        await super()._close()
        gcs.write_object(
            bucket_name=self._bucket_name,
            object_path=self._db_object_path,
            content=self.sqlite_file,
        )
