# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""Reads an object from `Cloud Storage API`_ and `examples`_.

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364

.. _Cloud Storage API: https://cloud.google.com/python/docs/reference/storage/latest
.. _examples: https://cloud.google.com/appengine/docs/standard/python/googlecloudstorageclient/read-write-to-cloud-storage
"""
# pylint: enable=line-too-long
import logging
import pathlib
import re
from typing import Generator, Optional, Tuple, Union

import cachetools
from google.cloud import storage

from yaas_common import logger

_LOGGER = logger.get(__name__)

_GCS_URI_PREFIX: str = "gs://"
GCS_PATH_SEP: str = "/"
_BUCKET_NAME_REGEX: re.Pattern = re.compile(r"^\s*[a-z\d][a-z\d\_-]{1,61}[a-z\d]\s*$", flags=re.ASCII)
_PATH_SEGMENT_REGEX: re.Pattern = re.compile(r"^[\w\.\_-]+$", flags=re.ASCII)


class CloudStorageError(Exception):
    """To code all GCS related errors."""


def get_bucket_and_prefix_from_uri(value: str) -> Tuple[str, Optional[str]]:
    """
    Will break down a GCS URI into bucket and prefix.
    Example::
        bucket_name, prefix = get_bucket_and_prefix_from_uri("gs://my-bucket/path/to/object")
        assert bucket_name == "my-bucket"
        assert prefix == "path/to/object"

    Args:
        value:

    Returns:

    """
    # input validation
    if not isinstance(value, str):
        raise TypeError(f"Argument must be a string. Got: '{value}'({type(value)})")
    if not value.startswith(_GCS_URI_PREFIX):
        raise ValueError(f"Argument must a GCS URI, as in: 'gs://my-bucket/path/to/object'. Got '{value}'")
    # logic
    # value = "gs://my-bucket/path/to/object"
    value = value[len(_GCS_URI_PREFIX) :]
    # value = "my-bucket/path/to/object"
    tokens = value.split(GCS_PATH_SEP)
    # tokens = ["my-bucket", "path, "to", "object"]
    if not tokens:
        raise ValueError(
            f"Argument does not seem to contain, at least, a bucket name, as in: 'gs://my-bucket'. Got '{value}'"
        )
    # bucket
    bucket_name = validate_and_clean_bucket_name(tokens[0])
    prefix = None
    if len(tokens) > 1:
        prefix = validate_and_clean_object_path(GCS_PATH_SEP.join(tokens[1:]))
    return bucket_name, prefix


def list_objects(
    *,
    bucket_name: str,
    prefix: str,
    project: Optional[str] = None,
) -> Generator[storage.Blob, None, None]:
    """Will list all blobs in the bucket's prefix.

    Args:
        bucket_name:
        prefix:
        project:

    Returns:
    """
    # validate input
    bucket_name, prefix = validate_and_clean_bucket_and_path(bucket_name, prefix)
    return _list_objects(bucket_name=bucket_name, prefix=prefix, project=project)


def _list_objects(
    *,
    bucket_name: str,
    prefix: str,
    project: Optional[str] = None,
) -> Generator[storage.Blob, None, None]:
    """Uses ``Client``_ class.

    .. _Bucket: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.client.Client
    """
    gcs_uri = f"gs://{bucket_name}/{prefix}"
    _LOGGER.debug("Listing '%s'", gcs_uri)
    try:
        client = _client(project=project)
        for blob in client.list_blobs(bucket_name, prefix=prefix):
            yield blob
    except Exception as err:
        raise CloudStorageError(f"Could not list blobs from '{gcs_uri}' in project '{project}' Error: {err}") from err
    _LOGGER.info("Listed blogs in '%s'", gcs_uri)


def read_object(
    *,
    bucket_name: str,
    object_path: str,
    project: Optional[str] = None,
    filename: Optional[pathlib.Path] = None,
    warn_read_failure: Optional[bool] = True,
) -> Union[bytes, bool]:
    """

    Args:
        bucket_name:
            Bucket name
        object_path:
            Path to the object to read from (**WITHOUT** leading `/`)
        project:
            Which project to use to create the GCS client, optional.
        filename:
            If provided, will download the content into the file and return :py:obj:`None`.
        warn_read_failure:
            If :py:obj:`True` will warn about failure to read,
            if :py:obj:`False` will just inform about it.

    Returns:
        Content of the object if no output file is given, else :py:obj:`True` if read.

    """
    # validate input
    bucket_name, object_path = validate_and_clean_bucket_and_path(bucket_name, object_path)
    if filename is not None and not isinstance(filename, pathlib.Path):
        raise TypeError(
            f"If filename is given, it must an instance of {pathlib.Path.__name__}. "
            f"Got '{filename}'({type(filename)})"
        )
    # logic
    return _read_object(
        bucket_name=bucket_name,
        object_path=object_path,
        project=project,
        filename=filename,
        warn_read_failure=warn_read_failure,
    )


def validate_and_clean_bucket_and_path(  # pylint: disable=invalid-name
    bucket_name: str, object_path: str
) -> Tuple[str, str]:
    """Validate and clean-up bucket name and object path.

    Args:
        bucket_name:
        object_path:

    Returns:
        Cleaned up versions of the bucket name and object path.
    """
    return validate_and_clean_bucket_name(bucket_name), validate_and_clean_object_path(object_path)


def validate_and_clean_bucket_name(value: str) -> str:
    """
    Validates the argument as a bucket name and returns the cleaned up version of it.
    Args:
        value:
            Bucket name

    Returns:
        Cleaned up version of the argument.
    """
    # validate input
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"Bucket name must be a non-empty string. Got: '{value}'({type(value)})")
    if not _BUCKET_NAME_REGEX.match(value):
        raise ValueError(f"Bucket name does not comply with {_BUCKET_NAME_REGEX}. Got: '{value}'")
    return value.strip()


def validate_and_clean_object_path(value: str) -> str:
    """
    Validates the argument as an object path and returns the cleaned up version of it.
    Args:
        value:
            Object path

    Returns:
        Cleaned up version of the argument.
    """
    # validate input
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"Object path must be a non-empty string. Got: '{value}'({type(value)})")
    # cleaning leading '/' from path
    value = value.strip().lstrip(GCS_PATH_SEP).strip()
    for segment in value.split(GCS_PATH_SEP):
        if not _PATH_SEGMENT_REGEX.match(segment):
            raise ValueError(f"Path part '{segment}' does not comply with {_PATH_SEGMENT_REGEX}. Path: '{value}'")
    return value


def _read_object(
    *,
    bucket_name: str,
    object_path: str,
    project: Optional[str] = None,
    filename: Optional[pathlib.Path] = None,
    warn_read_failure: Optional[bool] = True,
) -> Union[bytes, bool]:
    """Uses ``Bucket``_ and ``Blob``_ classes.

    .. _Bucket: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.bucket.Bucket
    .. _Blob: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.blob.Blob
    """
    result = None
    gcs_uri = f"gs://{bucket_name}/{object_path}"
    _LOGGER.debug("Reading '%s'", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name, project)
        blob = bucket_obj.blob(object_path)
        if blob.exists():
            if filename:
                blob.download_to_filename(filename)
                result = True
            else:
                result = blob.download_as_bytes()
            _LOGGER.debug("Read '%s'", gcs_uri)
        else:
            _LOGGER.log(
                logging.WARN if warn_read_failure else logging.INFO,
                "Object %s does not exist or does not contain data. Returning %s",
                gcs_uri,
                result,
            )
            if filename:
                result = False
    except Exception as err:
        raise CloudStorageError(
            f"Could not download content from '{gcs_uri}' in project '{project}' "
            f"into '{filename}'. "
            f"Error: {err}"
        ) from err
    _LOGGER.info("Read '%s'", gcs_uri)
    return result


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _client(project: Optional[str] = None) -> storage.Client:
    try:
        result = storage.Client(project)
    except Exception as err:
        raise CloudStorageError(f"Could not create storage client for project '{project}'. Error: {err}") from err
    return result


def _bucket(bucket_name: str, project: Optional[str] = None) -> storage.Bucket:
    try:
        result = _client(project).get_bucket(bucket_name)
    except Exception as err:
        raise CloudStorageError(
            f"Could not get bucket '{bucket_name}' with client in project '{project}'. Error: {err}"
        ) from err
    if not isinstance(result, storage.Bucket) or not result.exists():
        raise CloudStorageError(f"Bucket '{bucket_name}' in project '{project}' does not exist.")
    return result


def write_object(
    *,
    bucket_name: str,
    object_path: str,
    content_source: Union[bytes, pathlib.Path],
    project: Optional[str] = None,
) -> None:
    """Will write the ``content`` on the object in ``path`` into the bucket
    ``bucket_name``.

    Args:
        bucket_name:
            Bucket name
        object_path:
            Path to the object to read from (**WITHOUT** leading `/`)
        project:
            Which project to use to create the GCS client, optional.
        content_source:
            What to write, either :py:class:`bytes` or :py:class:`pathlib.Path`.
    """
    # validate input
    bucket_name, object_path = validate_and_clean_bucket_and_path(bucket_name, object_path)
    if not isinstance(content_source, bytes) and not isinstance(content_source, pathlib.Path):
        raise TypeError(
            f"Content must be {bytes.__name__} or {pathlib.Path.__name__}. "
            f"Got: '{content_source}'({type(content_source)})"
        )
    # logic
    _write_object(
        bucket_name=bucket_name,
        object_path=object_path,
        content_source=content_source,
        project=project,
    )


def _write_object(
    *,
    bucket_name: str,
    object_path: str,
    content_source: Union[bytes, pathlib.Path],
    project: Optional[str] = None,
) -> None:
    """Uses ``Bucket``_ and ``Blob``_ classes.

    .. _Bucket: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.bucket.Bucket
    .. _Blob: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.blob.Blob
    """
    gcs_uri = f"gs://{bucket_name}/{object_path}"
    _LOGGER.debug("Writing '%s'", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name, project)
        blob = bucket_obj.blob(object_path)
        if isinstance(content_source, pathlib.Path):
            blob.upload_from_filename(content_source)
        else:
            with blob.open("wb") as out_blob:
                out_blob.write(content_source)
                _LOGGER.debug("Wrote '%s'", gcs_uri)
    except Exception as err:
        raise CloudStorageError(
            "Could not upload content from "
            f"'{content_source if isinstance(content_source, pathlib.Path) else 'bytes content'}' "
            f"into '{gcs_uri}' in project '{project}'. "
            f"Error: {err}"
        ) from err
    _LOGGER.info("Wrote '%s'", gcs_uri)
