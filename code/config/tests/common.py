# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pathlib
import tempfile

from yaas_config import config

#############
# Test Data #
#############

_TEST_DATA_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.joinpath(
    "test_data"
)
TEST_DATA_CONFIG_JSON: pathlib.Path = _TEST_DATA_DIR / "config.json"

##########
# Config #
##########


_TEST_PUBSUB_TOPIC: str = "test_yaas_pubsub_topic"

# pylint: disable=consider-using-with
TEST_CONFIG_LOCAL_JSON: config.Config = config.Config(
    calendar_config=config.CalendarCacheConfig(
        type=config.CacheType.CALENDAR.value,
        calendar_id="test_calendar_id",
        secret_name="test_calendar_secret_name",
    ),
    cache_config=config.LocalJsonLineCacheConfig(
        type=config.CacheType.LOCAL_JSON_LINE.value,
        json_line_file=tempfile.NamedTemporaryFile().name,
        archive_json_line_file=tempfile.NamedTemporaryFile().name,
    ),
    topic_to_pubsub={
        "YAAS": _TEST_PUBSUB_TOPIC,
        "STANDARD": _TEST_PUBSUB_TOPIC,
    },
)
