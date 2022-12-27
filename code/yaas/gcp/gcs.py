# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Reads an object from `Cloud Storage API`_ and `examples`_.

.. _Cloud Storage API: https://cloud.google.com/python/docs/reference/storage/latest
.. _examples: https://cloud.google.com/appengine/docs/standard/python/googlecloudstorageclient/read-write-to-cloud-storage
"""
# pylint: enable=line-too-long
import logging
import re
from typing import Optional, Tuple

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
    *, bucket_name: str, path: str, warn_read_failure: Optional[bool] = True
) -> bytes:
    """

    Args:
        bucket_name:
            Bucket name
        path:
            Path to the object to read from (**WITHOUT** leading `/`)
        warn_read_failure:
            If :py:obj:`True` will warn about failure to read,
            if :py:obj:`False` will just inform about it.

    Returns:
        Content of the object

    """
    bucket_name, path = _validate_and_clean_bucket_and_path(bucket_name, path)
    return _read_object(bucket_name, path, warn_read_failure)


def _validate_and_clean_bucket_and_path(bucket_name: str, path: str) -> Tuple[str, str]:
    # validate input
    if not isinstance(bucket_name, str) or not bucket_name.strip():
        raise TypeError(
            f"Bucket name must be a non-empty string. Got: <{bucket_name}>({type(bucket_name)})"
        )
    if not isinstance(path, str) or not path.strip():
        raise TypeError(
            f"Path name must be a non-empty string. Got: <{path}>({type(path)})"
        )
    if not _BUCKET_NAME_REGEX.match(bucket_name):
        raise ValueError(
            f"Bucket name does not comply wiht {_BUCKET_NAME_REGEX}. Got: <{bucket_name}>"
        )
    # removing '/' affixes from bucket name
    bucket_name = bucket_name.strip()
    # cleaning leading '/' from path
    path = path.strip().lstrip(_GCS_PATH_SEP).strip()
    for segment in path.split(_GCS_PATH_SEP):
        if not _PATH_SEGMENT_REGEX.match(segment):
            raise ValueError(
                f"Path part <{segment}> does not comply with {_PATH_SEGMENT_REGEX}. Path: <{path}>"
            )
    return bucket_name.strip(), path


def _read_object(
    bucket_name: str, path: str, warn_read_failure: Optional[bool] = True
) -> bytes:
    gcs_uri = f"gs://{bucket_name}/{path}"
    _LOGGER.debug("Reading <%s>", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name)
        blob = bucket_obj.get_blob(path)
        if blob is not None:
            result = blob.download_as_bytes()
            _LOGGER.debug("Read <%s>", gcs_uri)
        else:
            result = None
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


def write_object(*, bucket_name: str, path: str, content: bytes) -> None:
    """
    Will write the ``content`` on the object in ``path`` into the bucket ``bucket_name``.

    Args:
        bucket_name:
            Bucket name
        path:
            Path to the object to read from (**WITHOUT** leading `/`)
        content:
            What to write
    """
    # validate input
    bucket_name, path = _validate_and_clean_bucket_and_path(bucket_name, path)
    if not isinstance(content, bytes):
        raise TypeError(
            f"Content must be {bytes.__name__}. Got: <{content}>({type(content)})"
        )
    # logic
    _write_object(bucket_name, path, content)


def _write_object(bucket_name: str, path: str, content: bytes) -> None:
    gcs_uri = f"gs://{bucket_name}/{path}"
    _LOGGER.debug("Writing <%s>", gcs_uri)
    try:
        bucket_obj = _bucket(bucket_name)
        blob = bucket_obj.blob(path)
        with blob.open("wb") as out_blob:
            out_blob.write(content)
            _LOGGER.debug("Wrote <%s>", gcs_uri)
    except Exception as err:
        raise CloudStorageError(
            f"Could not download content from <{gcs_uri}>. Error: {err}"
        ) from err
