# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Reads an object from `Cloud Storage API`_ and `examples`_.

.. _Cloud Storage API: https://cloud.google.com/python/docs/reference/storage/latest
.. _examples: https://cloud.google.com/appengine/docs/standard/python/googlecloudstorageclient/read-write-to-cloud-storage
"""
# pylint: enable=line-too-long
import logging
import pathlib
import re
from typing import Optional, Tuple, Union

import cachetools

from google.cloud import storage

from yaas import logger

_LOGGER = logger.get(__name__)

_GCS_PATH_SEP: str = "/"
# pylint: disable=anomalous-backslash-in-string
_BUCKET_NAME_REGEX: re.Pattern = re.compile(
    "^\s*[a-z\d][a-z\d\_-]{1,61}[a-z\d]\s*$", flags=re.ASCII
)
_PATH_SEGMENT_REGEX: re.Pattern = re.compile("^\w+$", flags=re.ASCII)
# pylint: enable=anomalous-backslash-in-string


class CloudStorageError(Exception):
    """To code all GCS related errors"""


def read_object(
    *,
    bucket_name: str,
    object_path: str,
    filename: Optional[pathlib.Path] = None,
    warn_read_failure: Optional[bool] = True,
) -> Optional[bytes]:
    """

    Args:
        bucket_name:
            Bucket name
        object_path:
            Path to the object to read from (**WITHOUT** leading `/`)
        filename:
            If provided, will download the content into the file and return :py:obj:`None`.
        warn_read_failure:
            If :py:obj:`True` will warn about failure to read,
            if :py:obj:`False` will just inform about it.

    Returns:
        Content of the object

    """
    bucket_name, object_path = validate_and_clean_bucket_and_path(
        bucket_name, object_path
    )
    if filename is not None and not isinstance(filename, pathlib.Path):
        raise TypeError(
            f"If filename is given, it must an instance of {pathlib.Path.__name__}. Got <{filename}>({type(filename)})"
        )
    return _read_object(bucket_name, object_path, filename, warn_read_failure)


def validate_and_clean_bucket_and_path(
    bucket_name: str, object_path: str
) -> Tuple[str, str]:
    """
    Validate and clean-up bucket name and object path.

    Args:
        bucket_name:
        object_path:

    Returns:
        Cleaned up versions of the bucket name and object path.
    """
    return validate_and_clean_bucket_name(bucket_name), validate_and_clean_object_path(
        object_path
    )


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
        raise TypeError(
            f"Bucket name must be a non-empty string. " f"Got: <{value}>({type(value)})"
        )
    if not _BUCKET_NAME_REGEX.match(value):
        raise ValueError(
            f"Bucket name does not comply with {_BUCKET_NAME_REGEX}. " f"Got: <{value}>"
        )
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
        raise TypeError(
            f"Object path must be a non-empty string. " f"Got: <{value}>({type(value)})"
        )
    # cleaning leading '/' from path
    value = value.strip().lstrip(_GCS_PATH_SEP).strip()
    for segment in value.split(_GCS_PATH_SEP):
        if not _PATH_SEGMENT_REGEX.match(segment):
            raise ValueError(
                f"Path part <{segment}> does not comply with {_PATH_SEGMENT_REGEX}. "
                f"Path: <{value}>"
            )
    return value


def _read_object(
    bucket_name: str,
    object_path: str,
    filename: Optional[pathlib.Path] = None,
    warn_read_failure: Optional[bool] = True,
) -> Optional[bytes]:
    result = None
    gcs_uri = f"gs://{bucket_name}/{object_path}"
    _LOGGER.debug("Reading <%s>", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name)
        blob = bucket_obj.blob(object_path)
        if blob.exists():
            if filename:
                blob.download_to_filename(filename)
            else:
                result = blob.download_as_bytes()
            _LOGGER.debug("Read <%s>", gcs_uri)
        else:
            _LOGGER.log(
                logging.WARN if warn_read_failure else logging.INFO,
                "Object %s does not exist or does not contain data. Returning %s",
                gcs_uri,
                result,
            )
    except Exception as err:
        raise CloudStorageError(
            f"Could not download content from <{gcs_uri}>. Error: {err}"
        ) from err
    return result


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _client() -> storage.Client:
    return storage.Client()


def _bucket(bucket_name: str) -> storage.Bucket:
    return _client().get_bucket(bucket_name)


def write_object(
    *, bucket_name: str, object_path: str, content: Union[bytes, pathlib.Path]
) -> None:
    """
    Will write the ``content`` on the object in ``path`` into the bucket ``bucket_name``.

    Args:
        bucket_name:
            Bucket name
        object_path:
            Path to the object to read from (**WITHOUT** leading `/`)
        content:
            What to write, either :py:class:`bytes` or :py:class:`pathlib.Path`.
    """
    # validate input
    bucket_name, object_path = validate_and_clean_bucket_and_path(
        bucket_name, object_path
    )
    if not isinstance(content, bytes):
        raise TypeError(
            f"Content must be {bytes.__name__}. Got: <{content}>({type(content)})"
        )
    # logic
    _write_object(bucket_name, object_path, content)


def _write_object(
    bucket_name: str, object_path: str, content: Union[bytes, pathlib.Path]
) -> None:
    gcs_uri = f"gs://{bucket_name}/{object_path}"
    _LOGGER.debug("Writing <%s>", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name)
        blob = bucket_obj.blob(object_path)
        if isinstance(content, pathlib.Path):
            blob.upload_from_filename(content)
        else:
            with blob.open("wb") as out_blob:
                out_blob.write(content)
                _LOGGER.debug("Wrote <%s>", gcs_uri)
    except Exception as err:
        raise CloudStorageError(
            f"Could not download content from <{gcs_uri}>. Error: {err}"
        ) from err
