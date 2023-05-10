# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring
# type: ignore
# pytest: ignore=duplicate-code
import pathlib
import tempfile

import pytest

from tests import common
from yaas_common import const
from yaas_config import config

# pylint: disable=consider-using-with
_TEST_CACHE_LOCAL_JSON: config.LocalJsonLineCacheConfig = config.LocalJsonLineCacheConfig(
    type=config.CacheType.LOCAL_JSON_LINE.value,
    json_line_file=tempfile.NamedTemporaryFile().name,
    archive_json_line_file=tempfile.NamedTemporaryFile().name,
)
_TEST_CACHE_LOCAL_SQLITE: config.LocalSqliteCacheConfig = config.LocalSqliteCacheConfig(
    type=config.CacheType.LOCAL_SQLITE.value,
    sqlite_file=tempfile.NamedTemporaryFile().name,
)
_TEST_CACHE_GCS_SQLITE: config.GcsCacheConfig = config.GcsCacheConfig(
    type=config.CacheType.GCS_SQLITE.value, bucket_name="test-bucket-name"
)
# pylint: enable=consider-using-with


class TestCacheConfig:
    @pytest.mark.parametrize("type_arg", [c_type.value for c_type in config.CacheType])
    def test_ctor_ok(self, type_arg: str):
        # Given/When
        obj = config.CacheConfig(type=type_arg)
        # Then
        assert obj is not None

    @pytest.mark.parametrize("type_arg", ["", config.CacheType.LOCAL_JSON_LINE.value + "_NOT"])
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
            config.CacheConfig.from_json(value.as_json().replace(value.type, value.type + "_NOT"))


class TestConfig:
    def test_from_json_ok(self):
        # Given
        expected = common.TEST_CONFIG_LOCAL_JSON
        json = expected.as_json()
        # When
        result = config.Config.from_json(json)
        # Then
        assert result == expected, f"JSON: {json}"

    def test_from_dict_ok(self):
        # Given
        expected = common.TEST_CONFIG_LOCAL_JSON
        value = expected.as_dict()
        # When
        result = config.Config.from_dict(value)
        # Then
        assert result == expected, f"dict: {value}"

    @pytest.mark.parametrize(
        "filepath", [common.TEST_DATA_CONFIG_CAL_API_JSON, common.TEST_DATA_CONFIG_GOOGLE_CALDAV_JSON]
    )
    def test_from_json_ok_from_disk_google_calendar(self, filepath: pathlib.Path):
        with open(filepath, "r", encoding=const.ENCODING_UTF8) as in_json:
            result = config.Config.from_json(in_json.read())
        assert result.calendar_config.calendar_id == "calendar_id"
        assert result.calendar_config.secret_name == "projects/my-project/secrets/my-secret/versions/latest"
        assert result.retention_config is not None

    def test_from_json_ok_from_disk_caldav(self):
        with open(common.TEST_DATA_CONFIG_CALDAV_JSON, "r", encoding=const.ENCODING_UTF8) as in_json:
            result = config.Config.from_json(in_json.read())
        assert result.calendar_config.caldav_url == "https://www.example.com/calendar/dav/calendar_id"
        assert result.calendar_config.username == "test-user@gmail.com"
        assert result.calendar_config.secret_name == "projects/my-project/secrets/my-secret/versions/latest"
        assert result.retention_config is not None

    def test_from_dict_ok_from_disk(self):
        # Given
        with open(common.TEST_DATA_CONFIG_CAL_API_JSON, "r", encoding=const.ENCODING_UTF8) as in_json:
            obj = config.Config.from_json(in_json.read())
            value = obj.as_dict()
        # When
        result = config.Config.from_dict(value)
        # Then
        assert isinstance(result, config.Config)
        assert obj == result

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "gs://bucket-name",
            "gs://bucket-name/path/to/object",
        ],
    )
    def test_ctor_ok_topic_to_pubsub_gcs(self, value: str):
        # Given
        kwargs = common.TEST_CONFIG_LOCAL_JSON.as_dict()
        kwargs[config.Config.topic_to_pubsub_gcs.__name__] = value
        # When
        result = config.Config.from_dict(kwargs)
        # Then
        assert isinstance(result, config.Config)
        assert result.topic_to_pubsub_gcs == value

    @pytest.mark.parametrize(
        "value",
        [
            123,
            {},
            "",
            "-bucket-name",
            "_bucket-name",
            "bucket_name",
            "gs://",
            "gs:///",
        ],
    )
    def test_ctor_nok_topic_to_pubsub_gcs(self, value: str):
        # Given
        kwargs = common.TEST_CONFIG_LOCAL_JSON.as_dict()
        kwargs[config.Config.topic_to_pubsub_gcs.__name__] = value
        # When/Then
        with pytest.raises(ValueError):
            config.Config.from_dict(kwargs)
