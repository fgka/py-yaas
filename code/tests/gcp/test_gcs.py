# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Optional

import pytest

from yaas import const
from yaas.gcp import gcs

_TEST_BUCKET_NAME: str = "test_bucket_name"
_TEST_PATH: str = "path/to/object"
_TEST_CONTENT: bytes = bytes("EXPECTED", encoding=const.ENCODING_UTF8)


@pytest.mark.parametrize(
    "bucket_name,path",
    [
        (_TEST_BUCKET_NAME, None),
        (None, _TEST_PATH),
        (_TEST_BUCKET_NAME, " "),
        (" ", _TEST_PATH),
    ],
)
def test__validate_and_clean_bucket_and_path_nok_wrong_type(
    bucket_name: str, path: str
):
    with pytest.raises(TypeError):
        gcs.validate_and_clean_bucket_and_path(bucket_name, path)


@pytest.mark.parametrize(
    "bucket_name,path",
    [
        ("/", _TEST_PATH),
        (" bucket name ", _TEST_PATH),
        (_TEST_BUCKET_NAME, "///"),
        (_TEST_BUCKET_NAME, "path/ /"),
        (_TEST_BUCKET_NAME, "/path /"),
    ],
)
def test__validate_and_clean_bucket_and_path_nok_wrong_value(
    bucket_name: str, path: str
):
    with pytest.raises(ValueError):
        gcs.validate_and_clean_bucket_and_path(bucket_name, path)


@pytest.mark.parametrize(
    "bucket_name,path",
    [
        (_TEST_BUCKET_NAME, _TEST_PATH),
        (f" {_TEST_BUCKET_NAME} ", _TEST_PATH),
        (_TEST_BUCKET_NAME, f" {_TEST_PATH} "),
        (_TEST_BUCKET_NAME, f" /{_TEST_PATH} "),
    ],
)
def test__validate_and_clean_bucket_and_path_ok(bucket_name: str, path: str):
    # Given/When
    res_bucket_name, res_path = gcs.validate_and_clean_bucket_and_path(
        bucket_name, path
    )
    # Then
    assert res_bucket_name == _TEST_BUCKET_NAME
    assert res_path == _TEST_PATH


class _MyBlobWriter:
    def __init__(self):
        self.called = {}

    def __enter__(self) -> Any:
        self.called[_MyBlobWriter.__enter__.__name__] = True
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.called[_MyBlobWriter.__exit__.__name__] = args, kwargs

    def write(self, content: bytes) -> None:
        self.called[_MyBlobWriter.write.__name__] = content


class _MyBlob:
    def __init__(
        self, content: Optional[bytes] = _TEST_CONTENT, exists: Optional[bool] = True
    ):
        self._content = content
        self._exists = exists
        self.called = {}

    def download_as_bytes(self) -> bytes:
        self.called[_MyBlob.download_as_bytes.__name__] = True
        return self._content

    def exists(self) -> bool:
        self.called[_MyBlob.exists.__name__] = True
        return self._exists

    def open(self, mode: str) -> _MyBlobWriter:
        result = _MyBlobWriter()
        self.called[_MyBlob.open.__name__] = mode, result
        return result


class _MyBucket:
    def __init__(self, content: Optional[bytes] = _TEST_CONTENT):
        self._content = content
        self.called = {}

    def blob(self, path: str) -> _MyBlob:
        result = _MyBlob(self._content, self._content is not None)
        self.called[_MyBucket.blob.__name__] = path, result
        return result


@pytest.mark.parametrize(
    "expected",
    [
        None,
        _TEST_CONTENT,
    ],
)
def test_read_object_ok(monkeypatch, expected: bytes):
    # Given
    bucket = _MyBucket(expected)
    called = {}

    def mocked_bucket(bucket_name: str) -> _MyBucket:
        nonlocal called
        called[gcs._bucket.__name__] = bucket_name
        return bucket

    monkeypatch.setattr(gcs, gcs._bucket.__name__, mocked_bucket)
    # When
    result = gcs.read_object(bucket_name=_TEST_BUCKET_NAME, object_path=_TEST_PATH)
    # Then
    assert result == expected
    assert called.get(gcs._bucket.__name__) == _TEST_BUCKET_NAME
    path, blob = bucket.called.get(_MyBucket.blob.__name__)
    assert path == _TEST_PATH
    assert blob.called.get(_MyBlob.exists.__name__)
    assert bool(blob.called.get(_MyBlob.download_as_bytes.__name__)) == bool(
        expected is not None
    )


def test_write_object_ok(monkeypatch):
    # Given
    bucket = _MyBucket()
    called = {}

    def mocked_bucket(bucket_name: str) -> _MyBucket:
        nonlocal called
        called[gcs._bucket.__name__] = bucket_name
        return bucket

    monkeypatch.setattr(gcs, gcs._bucket.__name__, mocked_bucket)
    # When
    gcs.write_object(
        bucket_name=_TEST_BUCKET_NAME, object_path=_TEST_PATH, content=_TEST_CONTENT
    )
    # Then
    assert called.get(gcs._bucket.__name__) == _TEST_BUCKET_NAME
    path, blob = bucket.called.get(_MyBucket.blob.__name__)
    assert path == _TEST_PATH
    mode, writer = blob.called.get(_MyBlob.open.__name__)
    assert mode == "wb"
    assert writer.called.get(_MyBlobWriter.write.__name__) == _TEST_CONTENT
    assert writer.called.get(_MyBlobWriter.__enter__.__name__)
    assert writer.called.get(_MyBlobWriter.__exit__.__name__)
