# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytest

from yaas.dto import config


_TEST_CACHE_LOCAL_JSON: config.LocalJsonLineCacheConfig = (
    config.LocalJsonLineCacheConfig(
        type=config.CacheType.LOCAL_JSON_LINE.value,
        json_line_file=tempfile.NamedTemporaryFile().name,
        archive_json_line_file=tempfile.NamedTemporaryFile().name,
    )
)
_TEST_CACHE_LOCAL_SQLITE: config.LocalSqliteCacheConfig = config.LocalSqliteCacheConfig(
    type=config.CacheType.LOCAL_SQLITE.value,
    sqlite_file=tempfile.NamedTemporaryFile().name,
)
_TEST_CACHE_GCS_SQLITE: config.GcsCacheConfig = config.GcsCacheConfig(
    type=config.CacheType.GCS_SQLITE.value, bucket_name="test-bucket-name"
)


class TestCacheConfig:
    @pytest.mark.parametrize("type_arg", [c_type.value for c_type in config.CacheType])
    def test_ctor_ok(self, type_arg: str):
        # Given/When
        obj = config.CacheConfig(type=type_arg)
        # Then
        assert obj is not None

    @pytest.mark.parametrize(
        "type_arg", ["", config.CacheType.LOCAL_JSON_LINE.value + "_NOT"]
    )
    def test_ctor_nok_value(self, type_arg: str):
        with pytest.raises(ValueError):
            config.CacheConfig(type=type_arg)

    @pytest.mark.parametrize(
        "value",
        [
            _TEST_CACHE_LOCAL_JSON,
            _TEST_CACHE_LOCAL_SQLITE,
            _TEST_CACHE_GCS_SQLITE,
        ],
    )
    def test_from_json_ok(self, value: config.CacheConfig):
        # Given/When
        obj = config.CacheConfig.from_json(value.as_json())
        # Then
        assert obj == value

    @pytest.mark.parametrize(
        "value,type_arg",
        [
            (_TEST_CACHE_LOCAL_JSON, _TEST_CACHE_LOCAL_SQLITE.type),
            (_TEST_CACHE_LOCAL_SQLITE, _TEST_CACHE_LOCAL_JSON.type),
            (_TEST_CACHE_GCS_SQLITE, _TEST_CACHE_LOCAL_SQLITE.type),
        ],
    )
    def test_from_json_nok_value_error(self, value: config.CacheConfig, type_arg: str):
        with pytest.raises(ValueError):
            config.CacheConfig.from_json(value.as_json().replace(value.type, type_arg))

    @pytest.mark.parametrize(
        "value",
        [
            _TEST_CACHE_LOCAL_JSON,
            _TEST_CACHE_LOCAL_SQLITE,
            _TEST_CACHE_GCS_SQLITE,
        ],
    )
    def test_from_json_nok_non_existent_type(self, value: config.CacheConfig):
        with pytest.raises(ValueError):
            config.CacheConfig.from_json(
                value.as_json().replace(value.type, value.type + "_NOT")
            )
